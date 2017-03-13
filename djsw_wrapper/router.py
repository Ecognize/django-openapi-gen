import re
import logging
import importlib

from django.utils import six
from django.conf.urls import url as make_url

from .utils import Singleton, Template
from .views import SwaggerViewMaker, SwaggerMethodMaker
from .params import SwaggerParameter, SwaggerRequestHandler
from .errors import SwaggerValidationError, SwaggerGenericError

logger = logging.getLogger(__name__)

class SwaggerRouter(Singleton):
    # name of reference to controller in schema
    cextname = 'x-swagger-router-controller'

    # extract parameters from url path
    paramregex = re.compile(r'\{(\w?[\w\d]*)\}')

    # remove heading and trailing slashes
    wrapregex = re.compile(r'^\/?(.*)\/?')

    # allowed
    allowed_methods = set(['get', 'put', 'post', 'head', 'patch', 'options', 'delete'])

    # return a raw string for url regex
    def makeraw(self, string):
        if six.PY3:
            return string.encode('unicode-escape')
        else:
            return string.encode('string-escape')

    def __init__(self, base, paths, controllers = None):
        self.base = base
        self.urls = []
        self.paths = paths
        self.handlers = {}
        self.external = None
        self.stubsonly = False

        # try to import controller module first
        if controllers:
            try:
                self.external = importlib.import_module(controllers)
            except ImportError:
                self.stubsonly = True
                logger.info('Could not import controller module ({}), using stub handlers for all endpoints'.format(str(controllers)))
        else:
            self.stubsonly = True

        self.process()

    def process(self):
        for path in self.paths:
            view = None
            stub = False
            name = None
            controller = None

            child = self.paths[path]

            # if we have module, check for controller property and try to use it
            if not self.stubsonly:
                try:
                    name = child[self.cextname]
                    controller = getattr(self.external, name)

                    if not isinstance(controller, SwaggerView):
                        logger.info('Handler "{}" for path "{}" is not an instance of SwaggerController, using stub instead'.format(str(controller), path))
                        stub = True
                except KeyError:
                    logger.info('Controller property for path "{}" is not defined, using stub handler'.format(path))
                    stub = True
                except AttributeError:
                    logger.info('Could not find controller "{}" in module "{}", using stub handler'.format(name, str(self.external)))
                    stub = True
            else:
                stub = True

            # pick only allowed methods and make dict of them
            methods = { m : None for m in self.allowed_methods.intersection(set(child)) }

            # check for empty path
            if len(methods) == 0:
                raise SwaggerValidationError('Path "{}" does not contain any supported methods'.format(path))

            # gather all params and wrap them for matching methods
            allparams = set()

            for method in methods:
                parameters = child[method].get('parameters')

                if parameters:
                    wrapped = list(map(lambda p : SwaggerParameter(p), parameters))
                    methods[method] = wrapped
                    allparams.update([x.get_name() for x in wrapped])

            # enumerate named parameters and construct endpoint url
            reg = None
            url = six.moves.urllib.parse.urljoin(self.base, path)
            named = set(self.paramregex.findall(url))

            # if there are any named params, convert 'em to django's format; otherwise just use url
            if len(named):
                reg = re.sub(self.paramregex, r'(?P<\1>[\d\D]+)', url) # TODO: make matching length tuneable

                # check if schema missing params described in url
                if not named.issubset(allparams):
                    raise SwaggerValidationError('Path "{}" lacks parameters schema'.format(path))
            else:
                reg = url

            # make regex bounds
            reg = re.sub(self.wrapregex, r'^\1', reg)

            # create stub view object or use existing controller
            if stub:
                name = re.sub(self.paramregex, r'', str().join(map(str.capitalize, path.split('/')))) + '_' + str(len(path))
                view = SwaggerViewMaker(name)
            else:
                view = controller

            # create serializers
            for method, params in six.iteritems(methods):
                handler = getattr(view, method, None) if not stub else None

                if handler is None:
                    handler = SwaggerMethodMaker()

                # return validation wrapper if there are some params
                # or clean (stub) method otherwise
                wrapped = SwaggerRequestHandler(handler, params)

                # write back to view
                if stub:
                    view.update_method(method, wrapped)
                else:
                    setattr(view, method, wrapped)

            # ensure that view is callable
            if view is not callable:
                view = view.as_view()

            # push to dict
            self.handlers.update({ reg : view })

        # make sorted list and map to django's url()

        self.urls = [ make_url(rv[0], rv[1]) for rv in sorted(six.iteritems(self.handlers)) ]


    def get_urls(self):
        return self.urls

