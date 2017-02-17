from rest_framework import serializers, routers

from django_swagger_wrap.tools import Template
from django_swagger_wrap.views import StubControllerMethods, SwaggerView
from django_swagger_wrap.params import SwaggerParameter

import re
import six
import logging
import importlib

logger = logging.getLogger(__name__)

class SwaggerRouter():
    # name of reference to controller in schema
    cextname = 'x-swagger-router-controller'

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

            child = obj['paths'][path]

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

            # check/create missing controller methods
            for method in child:
                missing = getattr(StubControllerMethods, method, None)
                handler = getattr(view, method, None)

                if not callable(handler):
                    setattr(view, method, six.create_bound_method(missing, view)

            # join basepath
            regex = six.moves.urllib.parse.urljoin(self.base, self.path)

            # append to url list
            self.urls.append(self.makeraw(regex))

    def urls(self):
        return self.urls

