import uuid
from collections import OrderedDict

class Manager:
    def __init__(self, flask_session):
        self.flask_session = flask_session

    def start_session(self):
        self.flask_session['session_id'] = str(uuid.uuid4())
        self.flask_session['history'] = []

    def end_session(self):
        self.flask_session.clear()

    def get_session_id(self):
        return self.flask_session['session_id']

    def get_history(self):
        return self.flask_session['history']

    def export_session_data(self):
        return {
            "session_id": self.get_session_id(),
            "history": self.get_history()
        }

    def session_active(self):
        if 'session_id' in self.flask_session:
            return True
        return False

    def add_network(self, network_dict, method):
        if 'history' in self.flask_session:
            self.flask_session['history'].append(network_dict)
            self.flask_session.modified = True

    def get_network(self, network_id):
        if 'history' in self.flask_session:
            for network_dict in self.flask_session['history']:
                if network_dict['network_id'] == network_id:
                    return network_dict

    def remove_network(self, network_id):
        if 'history' in self.flask_session:
            to_remove = None
            for network_dict in self.flask_session['history']:
                if network_dict['network_id'] == network_id:
                    to_remove = network_dict
                    break
            if to_remove is not None:
                self.flask_session['history'].remove(to_remove)
                self.flask_session.modified = True
                return True
        return False


def network_dict(name, dataset, it, network_id):
    return {
        'network_id': network_id,
        'name': name,
        'dataset': dataset,
        'it': it
    }