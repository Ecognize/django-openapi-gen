from rest_framework import routers
from django_openapi_gen.tools import Swagger, Template
from django_openapi_gen.views import StubMethods, SwaggerController

import six
import logging
import importlib

logger = logging.getLogger(__name__)

class SwaggerRouter(object):
    def __init__(self, spec, controllers = None):
        self.external = None
        self.router = routers.SimpleRouter()
        self.swagger = Swagger(self.spec)
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

    def generate(self):
        obj = self.swagger.get_object()

        urls = []

        for path in obj['paths']:
            view = None
            stub = False
            name = None
            controller = None

            child = obj['paths'][path]

            # if we have module, check for controller property and try to use it
            if not self.stubsonly:
                try:
                    name = child['x-swagger-router-controller']
                    controller = getattr(self.external, name)

                    if not isinstance(controller, SwaggerController):
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
                view = SwaggerController()
            else:
                view = controller

            # check/create missing controller methods
            for method in child:
                missing = getattr(StubControllerMethods, method, None)
                handler = getattr(view, method, None)

                if not callable(handler):
                    setattr(view, method, six.create_bound_method(missing, view)

            # create regex path
            regex = 'stub'

            # append to list
            urls.append(None)

        return urls
