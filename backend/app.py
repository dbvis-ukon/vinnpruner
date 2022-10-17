from dataset import get_dataset, get_test_dataset
import sys
import threading
from lap import prune, load_base_network, evaluate
from hyperparameter import get_hyperparameters
from utils import get_sparsity_stats, get_layer_out, generate_network_id
import torch
import pytorch_model_summary as pms
import json
import numpy as np
import os
import uuid
import storage
import session
import base64
import io
import mosaic
from session_manager import Manager, network_dict
from flask import Flask, request, jsonify, send_file
from flask import session as flask_session
from flask_cors import CORS
app = Flask(__name__)
CORS(app, supports_credentials=True)
count_lock = threading.Lock()
eval_lock = threading.Lock()
evals_running = 0
sys.path.append(os.getcwd())
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

app.config["SECRET_KEY"] = 'iLww6wvQAPBT1NbCp6Le5g'
app.config["seed"] = 718


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


@app.route('/select_network', methods=['POST'])
def select_network_route():
    assert request.method == 'POST'
    req_body = request.get_json()
    network_name = req_body.get('network')
    network_dataset = req_body.get('dataset')
    sman = Manager(flask_session)

    if sman.session_active():
        print('cleared old session')
        sman.end_session()
    else:
        print('new session')
    sman.start_session()

    if network_name != None:
        try:
            network, prune_ratios, optimizer, pretrain_iteration, finetune_iteration, batch_size = get_hyperparameters(
                network_name)
            network_id = generate_network_id()
            load_base_network(network, network_dataset,
                              network_name, app.config['seed'])
            storage.save(network, network_name, 0,
                         sman.get_session_id(), network_id)
            sman.add_network(network_dict(
                network_name, network_dataset, 0, network_id), None)
            return sman.export_session_data()
        except ValueError:
            return jsonify("unknown network")


@app.route('/topology', methods=['POST'])
def get_topology():
    assert request.method == 'POST'
    req_body = request.get_json()
    network = req_body.get('network')
    if network == "mlp":
        try:
            network, prune_ratios, optimizer, pretrain_iteration, finetune_iteration, batch_size = get_hyperparameters(
                network)
        except ValueError:
            return jsonify("unknown network")
        layer_summary = pms.summary(
            network,
            torch.zeros((1, 1, 28, 28), device=(torch.device(device))),
            show_parent_layers=True,
            max_depth=None,
            print_summary=True)
        return jsonify(layer_summary)
    elif network != None:
        try:
            network, prune_ratios, optimizer, pretrain_iteration, finetune_iteration, batch_size = get_hyperparameters(
                network)
        except ValueError:
            return jsonify("unknown network")
        layer_summary = pms.summary(
            network,
            torch.zeros((1, 3, 32, 32), device=(torch.device(device))),
            show_parent_layers=True,
            max_depth=None,
            print_summary=True)
        return jsonify(layer_summary)
    return jsonify("")


@app.route('/prune_manual', methods=['POST'])
def prune_manual_route():
    assert request.method == 'POST'
    req_body = request.get_json()
    network_id = req_body.get('network_id')
    custom_masks = req_body.get('custom_masks')
    custom_channels = req_body.get('custom_channels')
    sman = Manager(flask_session)

    if not sman.session_active():
        return jsonify("no session present, start a session first"), 400
    else:
        print('session found')

    network_metadata = dotdict(sman.get_network(network_id))

    shape = None
    if network_metadata.name == "mlp":
        shape = torch.zeros((1, 1, 28, 28), device=(torch.device(device)))
    else:
        shape = torch.zeros((1, 3, 32, 32), device=(torch.device(device)))

    state_dict, _, network_type = storage.load(sman.get_session_id(), network_id)
    network, _, _, _, _, _ = get_hyperparameters(network_type)
    network.load_state_dict(state_dict)
    masks = network.get_masks()

    for layer in custom_masks:
        layer['channels'] = layer['channels'] = [x for x in range(layer['channels'][0], layer['channels'][1])]
        layer['kernels'] = layer['kernels'] = [x for x in range(layer['kernels'][0], layer['kernels'][1])]

    all_masks = custom_masks + custom_channels
    for custom_mask_dict in all_masks: 
        custom_mask = dotdict(custom_mask_dict)
        name = custom_mask.name
        channels = custom_mask.channels
        layer_id = custom_mask.maskedLayerId
        mask = masks[layer_id].cpu()
        kernels = custom_mask.kernels if custom_mask.kernels != None else [x for x in range(0, mask.shape[1])]
        prune = custom_mask.prune if custom_mask.prune != None else True
        if "Conv2d" in name:
            for channel in channels:
                for kernel in kernels:
                    if prune:
                        tmp_tensor = torch.zeros(mask[channel][kernel].shape[0], mask[channel][kernel].shape[1], dtype=torch.float32)
                    else:
                        tmp_tensor = torch.ones(mask[channel][kernel].shape[0], mask[channel][kernel].shape[1], dtype=torch.float32)
                    mask[channel][kernel] = tmp_tensor
        elif "Linear" in custom_mask.name:
            for channel in channels:
                for neuron in kernels:
                    tmp_tensor = torch.tensor(0.) if prune else torch.tensor(1.)
                    mask[channel][neuron] = tmp_tensor
        masks[layer_id] = mask

    history = sman.get_history()
    fresh_network, _, _, _, _, _ = get_hyperparameters(network_type)
    original_state_dict, _, _ = storage.load(sman.get_session_id(), history[0]['network_id'])
    fresh_network.load_state_dict(original_state_dict)
    fresh_network.set_masks(masks)

    prune_stats, layer_prune_stats = get_sparsity_stats(fresh_network, shape)
    network_uuid = generate_network_id()
    stats = {
        # 'current_loss': pre_train_loss.item(),
        # 'current_acc': pre_train_acc,
        'current_it': network_metadata.it,
        'id': network_uuid
    }

    storage.save(fresh_network, network_metadata.name, network_metadata.it,
                 sman.get_session_id(), network_uuid)

    sman.add_network(network_dict(
        network_metadata.name, network_metadata.dataset, network_metadata.it, stats['id']), 'manual')
    out = [sman.export_session_data(), stats, prune_stats.__dict__, [
        layer_stat.__dict__ for layer_stat in layer_prune_stats]]
    return json.dumps(out, cls=session.DictEncoder)

    

@app.route('/prune', methods=['POST'])
def prune_route():
    assert request.method == 'POST'
    req_body = request.get_json()
    # dataset = req_body.get('dataset')
    method = req_body.get('method')
    # network = req_body.get('network')
    # pruning_iteration_end = req_body.get('pruning_iteration_end')
    iterations = req_body.get('iterations')
    pruning_type = req_body.get('pruning_type')
    network_id = req_body.get('network_id')
    pruning_ratios = req_body.get('ratios')
    sman = Manager(flask_session)

    if not sman.session_active():
        return jsonify("no session present, start a session first")
    else:
        print('session found')

    network_metadata = dotdict(sman.get_network(network_id))
    args = {
        'dataset': network_metadata.dataset,
        'method': method,
        'network': network_metadata.name,
        'pruning_iteration_end': network_metadata.it + iterations,
        'pruning_iteration_start': network_metadata.it + 1,
        'pruning_type': pruning_type,
        'seed': app.config['seed'],
        'session_id': sman.get_session_id(),
        'network_id': network_id,
        'ratios': pruning_ratios
    }
    shape = None
    if network_metadata.name == "mlp":
        shape = torch.zeros((1, 1, 28, 28), device=(torch.device(device)))
    else:
        shape = torch.zeros((1, 3, 32, 32), device=(torch.device(device)))

    original, network, stats = prune(dotdict(args))
    prune_stats, layer_prune_stats = get_sparsity_stats(network, shape)
    sman.add_network(network_dict(
        args['network'], args['dataset'], stats['current_it'], stats['id']), args['method'])
    out = [sman.export_session_data(), stats, prune_stats.__dict__, [
        layer_stat.__dict__ for layer_stat in layer_prune_stats]]
    return json.dumps(out, cls=session.DictEncoder)


@app.route('/evaluate', methods=['POST'])
def eval_route():
    assert request.method == 'POST'
    req_body = request.get_json()
    network_id = req_body.get('network_id')
    dataset = req_body.get('dataset')
    sman = Manager(flask_session)
    result = None
    try:
        global evals_running
        with count_lock:
            evals_running += 1
        if evals_running < 2:
            print("concurrent eval allowed")
            result = jsonify(
                evaluate(network_id, sman.get_session_id(), dataset))
        else:
            print(f"sequential eval allowed, queue: {evals_running}")
            with eval_lock:
                print(f"eval concurrency lock acquired for {evals_running}")
                result = jsonify(
                    evaluate(network_id, sman.get_session_id(), dataset))
    finally:
        with count_lock:
            evals_running -= 1
    return result


@app.route("/layer_stat", methods=['POST'])
def layer_stat_route():
    assert request.method == 'POST'
    sman = Manager(flask_session)
    req_body = request.get_json()
    network_id = req_body.get('network_id')
    layer_num = req_body.get('layer_num')
    requested_width = req_body.get('requested_width')
    dark = req_body.get('dark')
    state_dict, _, network_type = storage.load(
        sman.get_session_id(), network_id)
    network, _, _, _, _, _ = get_hyperparameters(network_type)
    network.load_state_dict(state_dict)
    masks = network.get_masks()

    if layer_num == None:
        return json.dumps("nodata"), 400
    if dark == None:
        dark = False
    #print("transforming using mosaic")
    transform_layer = masks[layer_num].numpy()
    imsize = None

    is_conv2d = True if len(transform_layer.shape) > 3 else False
    # if not is_conv2d:
    #    if transform_layer.shape[1] > requested_width:
    #        transform_layer = np.moveaxis(transform_layer, 0, 1)
    mosaics = []
    settings = mosaic.Settings()
    if dark:
        settings.nonzeroed_color = [40, 35, 37, 140]
        settings.filler_color = [20, 15, 17, 200]
    if is_conv2d:
        settings.hspacing = 1
        settings.scale = 2
        settings.vspacing = 1
        mosaics, img_height, img_width, chunk_width, chunks_per_slice = mosaic.transform_mt(
            transform_layer, settings, "conv2d", requested_width)
    else:
        settings.hspacing = 0
        settings.scale = 2
        mosaics, img_height, img_width, chunk_width, chunks_per_slice = mosaic.transform_mt(
            transform_layer, settings, "linear", requested_width)

    layer = {
        'shape': masks[layer_num].shape,
        'mask': masks[layer_num].numpy().tolist(),
        'mosaics': mosaics,
        'img_height': img_height,
        'img_width': img_width,
        'chunk_width': chunk_width,
        'chunks_per_slice': chunks_per_slice
    }
    return json.dumps(layer)


@app.route("/layer_stat_mosaic", methods=['POST'])
def layer_stat_mosaic_route():
    assert request.method == 'POST'
    sman = Manager(flask_session)
    req_body = request.get_json()
    network_id = req_body.get('network_id')
    layer_num = req_body.get('layer_num')
    requested_width = req_body.get('requested_width')
    state_dict, _, network_type = storage.load(
        sman.get_session_id(), network_id)
    network, _, _, _, _, _ = get_hyperparameters(network_type)
    network.load_state_dict(state_dict)
    masks = network.get_masks()

    #print("transforming using mosaic")
    transform_layer = masks[layer_num].numpy()
    img_out = None
    if len(transform_layer.shape) > 3:
        settings = mosaic.Settings()
        settings.hspacing = 1
        settings.scale = 2
        settings.vspacing = 1
        (img_out, img_height) = mosaic.transform_conv2d_full(transform_layer, settings, [
            settings.zeroed_color, settings.nonzeroed_color])
    else:
        settings = mosaic.Settings()
        settings.hspacing = 0
        settings.scale = 2
        (img_out, img_height) = mosaic.transform_linear_full(transform_layer, settings, [
            settings.zeroed_color, settings.nonzeroed_color])

    #mosaics = []
    # for layer in transform_layer:
    #    mosaics.append(mosaic.transform(layer, settings, "linear"))
    return send_file(img_out, mimetype='image/png')


@app.route("/reset", methods=['POST'])
def reset_route():
    assert request.method == 'POST'
    storage.clear(Manager(flask_session).get_session_id())
    flask_session.clear()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return jsonify("cleared session")


@app.route("/remove", methods=['POST'])
def remove_route():
    assert request.method == 'POST'
    req_body = request.get_json()
    network_id = req_body.get('network_id')
    sman = Manager(flask_session)
    if network_id is not None:
        sman.remove_network(network_id)
    out = sman.export_session_data()
    return json.dumps(out, cls=session.DictEncoder)


@app.route("/layer_out", methods=['POST'])
def layer_out_route():
    assert request.method == 'POST'
    sman = Manager(flask_session)
    req_body = request.get_json()
    network_id = req_body.get('network_id')
    layer_num = req_body.get('layer_num')
    image_num = req_body.get('image_num')
    dataset_type = req_body.get('dataset')
    if layer_num == None or image_num == None:
        return json.dumps("nodata"), 400
    net_state_dict, _, network_type = storage.load(
        sman.get_session_id(), network_id)
    network, _, _, _, _, _ = get_hyperparameters(network_type)
    network.load_state_dict(net_state_dict)
    dataset_subset = torch.utils.data.Subset(
        get_test_dataset(dataset_type, transform=True), [image_num])
    shape, output = get_layer_out(
        network, dataset_subset, layer_num, app.config['seed'])
    result = {
        "shape": shape,
        "output": output
    }
    return json.dumps(result)


@app.route("/get_dataset_image", methods=['POST'])
def get_dataset_image():
    assert request.method == 'POST'
    req_body = request.get_json()
    dataset_type = req_body.get('dataset')
    start_idx = req_body.get('start_idx')
    end_idx = req_body.get('end_idx')
    if dataset_type == None or start_idx == None or end_idx == None:
        print("invalid values for get_dataset_image")
        return json.dumps("type, start or end idx undefined"), 400
    dataset = get_test_dataset(dataset_type)
    sequence = [x for x in range(start_idx, end_idx)]
    subset = torch.utils.data.Subset(dataset, sequence)
    loader = torch.utils.data.DataLoader(subset)
    images = []
    idx_to_class = {}
    for key, value in dataset.class_to_idx.items():
        idx_to_class[value] = key

    for i, (x, y) in enumerate(subset):
        img_bytes = io.BytesIO()
        x.save(img_bytes, format="png")
        entry = {
            "img_data": base64.encodebytes(img_bytes.getvalue()).decode('ascii'),
            "class": idx_to_class[y]
        }
        images.append(entry)

    return json.dumps(images)
