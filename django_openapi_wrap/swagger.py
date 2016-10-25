import yaml
import codecs

try:
    import simplejson as json
except ImportError:
    import json

class Swagger
    def __init__(self, name):
        self.raw = None
        self.loaded = False
        self.filename = name

        parse()

    def parse(self):
        filename = self.filename

        if filename.endswith('.json'):
            loader = json.load
        elif filename.endswith('.yml') or filename.endswith('.yaml'):
            loader = yaml.load
        else:
            with codecs.open(filename, 'r', 'utf-8') as f:
                contents = f.read()
                contents = contents.strip()
                if contents[0] in ['{', '[']:
                    loader = json.load
                else:
                    loader = yaml.load
        with codecs.open(filename, 'r', 'utf-8') as f:
            self.raw = loader(f)
            self.loaded = True

    # some advanced parsing techniques to be implemented
    def get_object(self):
        if self.loaded:
            return self.raw
        else raise ValueError('You should load spec file first')
