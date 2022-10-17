import uuid
import json


class Store:
    def __init__(self, session_id):
        self.session_id = session_id
        self.history = []
        self.method = []

    def add_network(self, network):
        self.history.append(network)

    def remove_network(self, network):
        self.history.remove(network)
    
    def get_network(self, network_id):
        return next(n for n in self.history if n.network_id == network_id)

    def reprJSON(self):
        return self.__dict__


class Network:
    def __init__(self, name, dataset, it, network_id):
        self.network_id = network_id
        self.name = name
        self.dataset = dataset
        self.it = it

    def __eq__(self, obj):
        if isinstance(obj, Network) and obj.network_id == self.network_id:
            return True
        return False

    def reprJSON(self):
        return self.__dict__


class DictEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'reprJSON'):
            return obj.reprJSON()
        else:
            return json.JSONEncoder.default(self, obj)
