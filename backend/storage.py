import torch
import os
import shutil
sessions_path = "./session_storage"

def save(network, name, it, session_id, network_id):
    session_path = os.path.join(sessions_path, session_id)
    if not os.path.exists(session_path):
        os.makedirs(session_path)
    torch.save({
        'model_state_dict': network.state_dict(),
        'iteration': it,
        'name': name
    }, os.path.join(session_path, f'{network_id}.pth'))


def load(session_id, network_id):
    session_path = os.path.join(sessions_path, session_id)
    checkpoint = torch.load(os.path.join(
        session_path, f'{network_id}.pth'), map_location='cpu')
    state_dict = checkpoint['model_state_dict']
    iteration = checkpoint['iteration']
    name = checkpoint['name']
    return state_dict, iteration, name


def clear(session_id):
    session_path = os.path.join(sessions_path, session_id)
    for item in os.listdir(session_path):
        if os.path.isfile(os.path.join(os.path.abspath(session_path), item)):
            os.remove(os.path.join(os.path.abspath(session_path), item))
    os.rmdir(os.path.abspath(session_path))
