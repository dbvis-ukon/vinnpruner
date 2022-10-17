import random
import torch
import torch.nn as nn
from network.masked_modules import MaskedLinear, MaskedConv2d
import json
import uuid
import numpy as np
import pytorch_model_summary as pms
from collections import OrderedDict
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def generate_network_id():
    return f"net-{str(uuid.uuid4())}"


def is_base_module(m):
    if isinstance(m, nn.Linear) or isinstance(m, nn.Conv2d):
        return True
    else:
        return False


def is_masked_module(m):
    if isinstance(m, MaskedLinear) or isinstance(m, MaskedConv2d):
        return True
    else:
        return False


def is_batch_norm(m):
    if isinstance(m, nn.BatchNorm2d) or isinstance(m, nn.BatchNorm1d):
        return True
    else:
        return False


def get_sparsity(model):
    # todo: pass this to UI
    nonzero = 0
    total = 0
    for name, m in model.named_modules():
        if is_masked_module(m):
            p = m.mask
            nz_count = (p != 0).type(torch.float).sum()
            total_count = p.numel()
            nonzero += nz_count
            total += total_count

            print(f'{name:20} | nonzeros = {nz_count:7}/{total_count} ({100 * nz_count / total_count:6.2f}%) | total_pruned = {total_count - nz_count:7} | shape= {list(p.data.shape)}')
    print(f'surv: {nonzero}, pruned: {total - nonzero}, total: {total}, Comp. rate: {total / nonzero:10.2f}x ({100 * (total - nonzero) / total:6.2f}% pruned)')

    return nonzero / total


class LayerStat():
    def __init__(self, name, nonzeroes, total_pruned, input_shape, output_shape, kernel_size):
        self.name = name
        #self.mask = mask
        self.nonzeroes = nonzeroes
        self.total_pruned = total_pruned
        self.input_shape = input_shape
        self.output_shape = output_shape
        self.kernel_size = kernel_size


class PruningStats():
    def __init__(self, surv, pruned, total, comp_rate):
        self.surv = surv
        self.pruned = pruned
        self.total = total
        self.comp_rate = comp_rate
        self.sparsity = surv/total


def get_sparsity_stats(model, shape):
    nonzero = 0
    total = 0
    layers = []
    layer_summary = pms.summary(
        model,
        shape,
        show_parent_layers=True,
        max_depth=None,
        print_summary=True)
    masked_summary = OrderedDict()
    for k in list(layer_summary):
        if k.startswith("Masked"):
            masked_summary[k] = layer_summary[k]
    idx = 0
    for name, m in model.named_modules():
        if is_masked_module(m):
            p = m.mask
            nz_count = (p != 0).type(torch.float).sum()
            total_count = p.numel()
            nonzero += nz_count
            total += total_count
            kernel_size = [0, 0]
            if hasattr(m, 'kernel_size'):
                kernel_size = m.kernel_size
            #layers.append(LayerStat(name, p.detach().cpu().numpy().tolist(), (nz_count/total_count).item(), total_count - nz_count.item(), p.data.shape))
            layerDict = list(masked_summary.values())[idx]
            layers.append(LayerStat(m.__class__.__name__, (nz_count/total_count).item(), total_count -
                                    nz_count.item(), layerDict['input_shape'][0], layerDict['output_shape'][0], kernel_size))
            idx += 1
    stats = PruningStats(nonzero.item(), total -
                         nonzero.item(), total, total / nonzero.item())
    return stats, layers


def get_masks_for_model(model):
    return model.get_masks()


def get_layer_out(network, dataset_slice, layer_num, seed):
    layerhook_output = None

    def hook(module, _input, output):
        nonlocal layerhook_output
        layerhook_output = output

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    network.eval()

    registeredHook = None
    counter = 0
    layers_output = []
    for m in network.modules():
        if is_masked_module(m):
            if counter == layer_num:
                print(m)
                registeredHook = m.register_forward_hook(hook)
                break
            counter += 1
    shape = None
    for i, (x, y) in enumerate(dataset_slice):
        x = torch.unsqueeze(x, 0).to(device)
        #x = x.cuda()
        with torch.no_grad():
            _ = network(x)
            untransformed = layerhook_output.detach().cpu().numpy()
            if shape == None:
                shape = untransformed.shape
            rgb_normalized = np.round(
                255 * (untransformed - untransformed.min()) / (untransformed.max() - untransformed.min()))
            layers_output.append(rgb_normalized.tolist()[0])

            _ = network(x)
            untransformed = layerhook_output.detach().cpu().numpy()
            if shape == None:
                shape = untransformed.shape
            rgb_normalized = np.round(
                255 * (untransformed - untransformed.min()) / (untransformed.max() - untransformed.min()))
            layers_output.append(rgb_normalized.tolist()[0])
    registeredHook.remove()
    return shape, layers_output
