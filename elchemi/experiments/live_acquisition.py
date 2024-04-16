import yaml


class LiveAcquisition:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = {}

    def load_config(self):
        with open(self.config_file, 'r') as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)