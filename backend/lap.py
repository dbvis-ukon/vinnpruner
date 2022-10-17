import argparse
import os
import random
import numpy as np
import storage
import math
import uuid
from copy import deepcopy
from functools import partial

import torch
import torch.optim as optim

from dataset import get_dataset, get_test_dataset
from train import train, test, test_with_stats
from method import get_method
from utils import get_sparsity, generate_network_id
from hyperparameter import get_hyperparameters
from activation import get_activation
from sklearn import metrics

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def prune(args):
    # fix randomness
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)
        torch.cuda.manual_seed_all(args.seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    # define dataset and network
    # train_dataset, test_dataset = get_dataset(args.dataset)
    if args.pruning_type == 'global':
        network, prune_ratios, optimizer, pretrain_iteration, finetune_iteration, batch_size = get_hyperparameters(
            args.network + '_global')
    else:
        network, prune_ratios, optimizer, pretrain_iteration, finetune_iteration, batch_size = get_hyperparameters(
            args.network)

    if args.ratios != None and args.ratios != []:
        prune_ratios = args.ratios

    total_pruning_its = 0
    # prune and fine-tune network
    if args.network_id != None:
        # load model parameters
        net_state_dict, iteration, _ = storage.load(
            args.session_id, args.network_id)
        network.load_state_dict(net_state_dict)
    else:
        network = load_base_network(
            network, args.dataset, args.network, args.seed)

    original_network = network  # keep the original network
    original_prune_ratio = prune_ratios  # keep the original prune ratio
    pruning_method = get_method(args.method)

    for it in range(args.pruning_iteration_start, args.pruning_iteration_end + 1):
        print(f'Pruning iter. {it}')

        # get pruning ratio for current iteration
        # list for layer-wise pruning, and constant for global pruning
        if args.pruning_type == 'oneshot':
            network = deepcopy(original_network).to(device)
            prune_ratios = []
            for idx in range(len(original_prune_ratio)):
                prune_ratios.append(
                    1.0 - ((1.0 - original_prune_ratio[idx]) ** it))
        elif args.pruning_type == 'iterative':
            prune_ratios = []
            for idx in range(len(original_prune_ratio)):
                prune_ratios.append(original_prune_ratio[idx])
        elif args.pruning_type == 'global':
            network = deepcopy(original_network).to(device)
            prune_ratios = [original_prune_ratio[it - 1]]
        else:
            raise ValueError('Unknown pruning_type')

        # perpare weights and masks to prune
        weights = network.get_weights()
        masks = network.get_masks()

        if 'lap_act' in args.method:
            act_rate = get_activation(network, train_dataset)
            assert len(act_rate) == len(weights) - 1
            for i in range(len(weights) - 1):
                if len(act_rate[i].shape) == 1:
                    act = act_rate[i].sqrt()
                    size = list(act.shape)
                    size = [size[0], 1]
                    act = act.view(size).repeat([1, weights[i].shape[1]])
                    weights[i] *= act
                elif len(act_rate[i].shape) == 3:
                    act = act_rate[i].sqrt().sum(dim=1).sum(dim=1)
                    size = list(act.shape)
                    size = [size[0], 1, 1, 1]
                    act = act.view(size).repeat(
                        [1, weights[i].shape[1], weights[i].shape[2], weights[i].shape[3]])
                    weights[i] *= act
                else:
                    assert False

        if 'obd' in args.method:
            assert 'bn' not in args.method  # OBD for BN is not implemented
            masks = pruning_method(
                deepcopy(network), train_dataset, prune_ratios, args.network, args.dataset)
        elif 'bn' in args.method:
            masks = pruning_method(
                weights, masks, prune_ratios, network.get_bn_weights())
        else:
            masks = pruning_method(weights, masks, prune_ratios)

        network.set_masks(masks)
        #train_acc, train_loss, test_acc, test_loss = train(train_dataset, test_dataset, network, optimizer, finetune_iteration, batch_size)

    #sparsity = get_sparsity(network)
    #pre_train_acc, pre_train_loss = test(network, train_dataset)
    #pre_test_acc, pre_test_loss = test(network, test_dataset)

    network_uuid = generate_network_id()
    stats = {
        # 'current_loss': pre_train_loss.item(),
        # 'current_acc': pre_train_acc,
        'current_it': args.pruning_iteration_end,
        'id': network_uuid
    }

    storage.save(network, args.network, args.pruning_iteration_end,
                 args.session_id, network_uuid)
    return original_network, network, stats


def evaluate(network_id, session_id, dataset):
    net_state_dict, iteration, name = storage.load(session_id, network_id)
    network, _, _, _, _, _ = get_hyperparameters(name)
    network.load_state_dict(net_state_dict)
    test_dataset = get_test_dataset(dataset, transform=True)
    idx_to_class = {}
    for key, value in test_dataset.class_to_idx.items():
        idx_to_class[value] = key
    sparsity = get_sparsity(network)
    #train_acc, train_loss = test(network, train_dataset)
    test_acc, test_loss, stats = test_with_stats(network, test_dataset)

    class_dict = {}
    for idx in range(len(idx_to_class)):
        class_dict[idx] = {'originals': [], 'predictions': [], 'correct': [], 'net_output': []}
    
    for idx, data in enumerate(stats['originals']):
        class_dict[data]['originals'].append(data)
        class_dict[data]['predictions'].append(stats['predictions'][idx])
        class_dict[data]['correct'].append(stats['correct'][idx])
        class_dict[data]['net_output'].append(stats['net_output'][idx])

    confusion_matrix = metrics.confusion_matrix(
        stats['originals'], stats['predictions'])
    precision_scores, recall_scores, _, support = metrics.precision_recall_fscore_support(
        stats['originals'], stats['predictions'], average=None, labels=list(idx_to_class.keys()))

    
    class_precision_recall_curves = len(idx_to_class) * [None]
    for key, value in class_dict.items():
        precision, recall, thresholds = metrics.precision_recall_curve(class_dict[key]['correct'], class_dict[key]['net_output'], pos_label=True)
        if math.isnan(recall[0]):
            class_precision_recall_curves[key] = {
                'precision_curve': [0.0],
                'recall_curve': [0.0]
            }
        else:
            class_precision_recall_curves[key] = {
                'precision_curve': np.round(precision, 3)[::10].tolist(),
                'recall_curve': np.round(recall, 3)[::10].tolist()
            }

    data_id = 0

    network_uuid = generate_network_id()
    stats = {
        'current_loss': test_loss.item(),
        'current_acc': test_acc,
        'id': network_id,
        'precision_scores': precision_scores.tolist(),
        'recall_scores': recall_scores.tolist(),
        'confusion_matrix': confusion_matrix.tolist(),
        'support': support.tolist(),
        'class_precision_recall_curves': class_precision_recall_curves,
        'idx_to_class': idx_to_class
    }
    return stats


def get_base_network(args, network, pretrain_iteration, train_dataset, test_dataset, optimizer, batch_size, base_path):
    # load pre-trained network

    if not os.path.exists(base_path):
        os.makedirs(base_path)

    if not os.path.exists(os.path.join(base_path, 'base_model.pth')):
        print('Pre-train network')
        # pre-train network if not exits
        pre_train_acc, pre_train_loss = test(network, train_dataset)
        pre_test_acc, pre_test_loss = test(network, test_dataset)
        train_acc, train_loss, test_acc, test_loss = train(
            train_dataset, test_dataset, network, optimizer, pretrain_iteration, batch_size)

        # save network and logs
        torch.save(network.state_dict(), args.network,
                   os.path.join(base_path, 'base_model.pth'))
        with open(os.path.join(base_path, 'logs.txt'), 'w') as f:
            f.write(f'{pre_train_loss:.3f}\t{pre_test_loss:.3f}\t{train_loss:.3f}\t{test_loss:.3f}\t'
                    f'{pre_train_acc:.2f}\t{pre_test_acc:.2f}\t{train_acc:.2f}\t{test_acc:.2f}\n')
    else:
        print('Load pre-trained network')
        state_dict = torch.load(os.path.join(base_path, 'base_model.pth'), map_location=device)
        network.load_state_dict(state_dict)
    return network


def train_base_network(network, args, pretrain_iteration, train_dataset, test_dataset, optimizer, batch_size):
    base_path = f'./checkpoint/{args.dataset}_{args.network}_{args.seed}'

    if not os.path.exists(base_path):
        os.makedirs(base_path)

    if not os.path.exists(os.path.join(base_path, 'base_model.pth')):
        print('Pre-train network')
        # pre-train network if not exits
        pre_train_acc, pre_train_loss = test(network, train_dataset)
        pre_test_acc, pre_test_loss = test(network, test_dataset)
        train_acc, train_loss, test_acc, test_loss = train(
            train_dataset, test_dataset, network, optimizer, pretrain_iteration, batch_size)
        # save network and logs
        torch.save(network.state_dict(),
                   os.path.join(base_path, 'base_model.pth'))
        with open(os.path.join(base_path, 'logs.txt'), 'w') as f:
            f.write(f'{pre_train_loss:.3f}\t{pre_test_loss:.3f}\t{train_loss:.3f}\t{test_loss:.3f}\t'
                    f'{pre_train_acc:.2f}\t{pre_test_acc:.2f}\t{train_acc:.2f}\t{test_acc:.2f}\n')
    else:
        print("No Pre-train needed")
    return network


def load_base_network(network, dataset, network_name, seed):
    base_path = f'./checkpoint/{dataset}_{network_name}_{seed}/base_model.pth'
    print('Load pre-trained network')
    if os.path.exists(base_path):
        state_dict = torch.load(base_path, map_location=device)
        network.load_state_dict(state_dict)
    else:
        #raise FileNotFoundError
        print("network not pre-trained, could not load")
        print("pretraining network, this will take a while")
        args = dotdict({
            'dataset': dataset,
            'network': network_name,
            'seed': seed,
        })
        resize = None
        if network_name == 'alexnet':
            resize = None
        train_dataset, test_dataset = get_dataset(dataset, resize=resize)
        network, _, optimizer, pretrain_iteration, _, batch_size = get_hyperparameters(network_name)
        train_base_network(network, args, pretrain_iteration, train_dataset, test_dataset, optimizer, batch_size)

def main():
    # get arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=718, help='random seed')
    parser.add_argument('--dataset', type=str, default='mnist',
                        help='dataset (mnist|fmnist|cifar10)')
    parser.add_argument('--network', type=str, default='mlp',
                        help='network (mlp|lenet|conv6|vgg19|resnet18)')
    parser.add_argument('--method', type=str, default='mp',
                        help='method (mp|rp|lap)')
    parser.add_argument('--pruning_type', type=str,
                        default='oneshot', help='(oneshot|iterative|global)')
    parser.add_argument('--pruning_iteration_start', type=int,
                        default=1, help='start iteration for pruning')
    parser.add_argument('--pruning_iteration_end', type=int,
                        default=30, help='end iteration for pruning')
    args = parser.parse_args()

    # fix randomness
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)
        torch.cuda.manual_seed_all(args.seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    # define dataset and network
    train_dataset, test_dataset = get_dataset(args.dataset)
    if args.pruning_type == 'global':
        network, prune_ratios, optimizer, pretrain_iteration, finetune_iteration, batch_size = get_hyperparameters(
            args.network + '_global')
    else:
        network, prune_ratios, optimizer, pretrain_iteration, finetune_iteration, batch_size = get_hyperparameters(
            args.network)

    # load pre-trained network
    base_path = f'./checkpoint/{args.dataset}_{args.network}_{args.pruning_type}_{args.seed}'
    if not os.path.exists(base_path):
        os.makedirs(base_path)

    if not os.path.exists(os.path.join(base_path, 'base_model.pth')):
        print('Pre-train network')
        # pre-train network if not exits
        pre_train_acc, pre_train_loss = test(network, train_dataset)
        pre_test_acc, pre_test_loss = test(network, test_dataset)
        train_acc, train_loss, test_acc, test_loss = train(
            train_dataset, test_dataset, network, optimizer, pretrain_iteration, batch_size)

        # save network and logs
        torch.save(network.state_dict(), os.path.join(
            base_path, 'base_model.pth'))
        with open(os.path.join(base_path, 'logs.txt'), 'w') as f:
            f.write(f'{pre_train_loss:.3f}\t{pre_test_loss:.3f}\t{train_loss:.3f}\t{test_loss:.3f}\t'
                    f'{pre_train_acc:.2f}\t{pre_test_acc:.2f}\t{train_acc:.2f}\t{test_acc:.2f}\n')
    else:
        print('Load pre-trained network')
        state_dict = torch.load(os.path.join(base_path, 'base_model.pth'), map_location=device)
        network.load_state_dict(state_dict)

    # prune and fine-tune network
    exp_path = os.path.join(base_path, args.method)
    if not os.path.exists(exp_path):
        os.makedirs(exp_path)

    original_network = network  # keep the original network
    original_prune_ratio = prune_ratios  # keep the original prune ratio
    pruning_method = get_method(args.method)
    for it in range(args.pruning_iteration_start, args.pruning_iteration_end + 1):
        print(f'Pruning iter. {it}')

        # get pruning ratio for current iteration
        # list for layer-wise pruning, and constant for global pruning
        if args.pruning_type == 'oneshot':
            network = deepcopy(original_network).to(device)
            prune_ratios = []
            for idx in range(len(original_prune_ratio)):
                prune_ratios.append(
                    1.0 - ((1.0 - original_prune_ratio[idx]) ** it))
        elif args.pruning_type == 'iterative':
            prune_ratios = []
            for idx in range(len(original_prune_ratio)):
                prune_ratios.append(original_prune_ratio[idx])
        elif args.pruning_type == 'global':
            network = deepcopy(original_network).to(device)
            prune_ratios = [original_prune_ratio[it - 1]]
        else:
            raise ValueError('Unknown pruning_type')

        # perpare weights and masks to prune
        weights = network.get_weights()
        masks = network.get_masks()

        if 'lap_act' in args.method:
            act_rate = get_activation(network, train_dataset)
            assert len(act_rate) == len(weights) - 1
            for i in range(len(weights) - 1):
                if len(act_rate[i].shape) == 1:
                    act = act_rate[i].sqrt()
                    size = list(act.shape)
                    size = [size[0], 1]
                    act = act.view(size).repeat([1, weights[i].shape[1]])
                    weights[i] *= act
                elif len(act_rate[i].shape) == 3:
                    act = act_rate[i].sqrt().sum(dim=1).sum(dim=1)
                    size = list(act.shape)
                    size = [size[0], 1, 1, 1]
                    act = act.view(size).repeat(
                        [1, weights[i].shape[1], weights[i].shape[2], weights[i].shape[3]])
                    weights[i] *= act
                else:
                    assert False

        if 'obd' in args.method:
            assert 'bn' not in args.method  # OBD for BN is not implemented
            masks = pruning_method(
                deepcopy(network), train_dataset, prune_ratios, args.network, args.dataset)
        elif 'bn' in args.method:
            masks = pruning_method(
                weights, masks, prune_ratios, network.get_bn_weights())
        else:
            masks = pruning_method(weights, masks, prune_ratios)

        network.set_masks(masks)

        sparsity = get_sparsity(network)
        pre_train_acc, pre_train_loss = test(network, train_dataset)
        pre_test_acc, pre_test_loss = test(network, test_dataset)
        train_acc, train_loss, test_acc, test_loss = train(
            train_dataset, test_dataset, network, optimizer, finetune_iteration, batch_size)

        # save network and logs
        with open(os.path.join(exp_path, 'logs.txt'), 'a') as f:
            f.write(f'{it}\t{sparsity:.6f}\t'
                    f'{pre_train_loss:.3f}\t{pre_test_loss:.3f}\t{train_loss:.3f}\t{test_loss:.3f}\t'
                    f'{pre_train_acc:.2f}\t{pre_test_acc:.2f}\t{train_acc:.2f}\t{test_acc:.2f}\n')


if __name__ == '__main__':
    main()
