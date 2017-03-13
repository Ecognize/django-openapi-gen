from jinja2 import Environment, FileSystemLoader

class _Singleton(type):
    """ A metaclass that creates a Singleton base class when called. """
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Singleton(_Singleton('SingletonMeta', (object,), {})): pass

# creates class from dict on demand
class LazyClass(object):
    oftype = None

    def __init__(self, name = None):
        assert name is not None, ('You should provide a name for new class')
        assert self.oftype is not None, ('You should provide a type for new class')

        self.handle = None
        self.attrs = dict()
        self.ready = False
        self.name = name

    def setup(self):
        self.handle = type(self.name, (self.oftype,), dict(self.attrs))
        self.ready = True

    def set_attr(self, key, value):
        self.attrs[key] = value

    def as_class(self):
        if not self.ready:
            self.setup()

        return self.handle

class Template():
    def __init__(self):
        self.loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates'))
        self.env = Environment(loader = self.loader)

    def render(self, template_name, **kwargs):
        template = self.env.get_template(template_name)
        return template.render(**kwargs)
