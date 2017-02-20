import re
import six
import logging
import importlib

from django.conf.urls import url as make_url
from rest_framework import serializers, routers

from django_swagger_wrap.utils import Singleton, Template
from django_swagger_wrap.views import StubControllerMethods, SwaggerView
from django_swagger_wrap.params import SwaggerParameter

logger = logging.getLogger(__name__)

class SwaggerRouter(Singleton):
    # name of reference to controller in schema
    cextname = 'x-swagger-router-controller'

    # extract parameters from url path
    paramregex = re.compile('\{(\w?[\w\d]*)\}')

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
        self.router = routers.SimpleRouter()
        self.external = None
        self.stubsonly = False

        # try to import controller module first
        if controllers:
            try:
                self.external = importlib.import_module(controllers)
            except ImportError:
                self.stubsonly = True
                logger.info('Could not import controller module (%s), using stub handlers for all endpoints', str(controllers))
        else:
            self.stubsonly = True

        # construct urls
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
                        logger.info('Handler "%s" for path "%s" is not an instance of SwaggerController, using stub instead', str(controller), path)
                        stub = True
                except KeyError:
                    logger.info('Controller property for path "%s" is not defined, using stub handler', path)
                    stub = True
                except AttributeError:
                    logger.info('Could not find controller "%s" in module "%s", using stub handler', name, str(self.external))
                    stub = True
            else:
                stub = True

            # create stub view if needed, assign found controller otherwise
            if stub:
                view = SwaggerView()
            else:
                view = controller

            # pick only allowed methods
            methods = self.allowed_methods.intersection(set(child))

            # check for empty path
            # TODO: pretty errors
            if len(methods) == 0:
                raise ValueError('Path "%s" does not contain any supported methods' % path)

            # check/create missing controller methods
            for method in methods:
                missing = getattr(StubControllerMethods, method, None)
                handler = getattr(view, method, None)

                if not callable(handler):
                    setattr(view, method, six.create_bound_method(missing, view))

            # join basepath
            url = six.moves.urllib.parse.urljoin(self.base, path)

            # lets construct regex
            regex = None

            # search for parameters
            params = self.paramregex.findall(url)

            # if there are params in url, get corresponding regexes
            if(len(params)):
                # construct param
                #p = SwaggerParameter(path[])

                # create matching dict
                # TODO: polish this regex
                # rpdict = { z : r'([\d\D]+)' for z in params }
                # pregex = re.compile("(%s)" % "|".join(map(re.escape, rpdict.keys())))
                # create dict
                # for p in params:

                # interpret all params as text for now
                regex = re.sub(self.paramregex, '([\d\D]+)', url)

            else:
                # no params, just use the url
                regex = url

            # cast to list
            regex = list(regex)

            # make regex bounds
            regex[0] = '^'
            regex.append('$')

            # make django url
            u = ''.join(regex)

            print(path, u, view)

            # map to django's url()
            self.urls.append(make_url(u, view.as_view())) # TODO: add shortname

    def get_urls(self):
        return self.urls

