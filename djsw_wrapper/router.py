import re
import logging
import importlib

from django.utils import six
from django.conf.urls import url

from djsw_wrapper.utils import Singleton, Template, Resolver
from djsw_wrapper.makers import SwaggerViewMaker, SwaggerRequestMethodMaker, SwaggerViewClass
from djsw_wrapper.params import SwaggerParameter, SwaggerRequestHandler
from djsw_wrapper.errors import SwaggerValidationError, SwaggerGenericError

from rest_framework.routers import SimpleRouter
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin

logger = logging.getLogger(__name__)

#: name of swagger view reference in schema
SCHEMA_VIEW_NAME = 'x-swagger-router-view'

#: indicates whether it's a detailed obj view
SCHEMA_VIEW_ITEM = 'x-swagger-object-item'

#: django url param substitution
DJANGO_PARAMS_REGEX = r'(?P<\1>[^/.]+)'

#: removes heading and trailing slashes
URL_SLASHES_REGEX = re.compile(r'^\/?(.*)\/?')

#: extracts parameters from swagger url path
SWAGGER_PARAMS_REGEX = re.compile(r'\{(\w?[\w\d]*)\}')

#: allowed by Swagger 2.0
SWAGGER_METHODS = set(['get', 'put', 'post', 'head', 'patch', 'options', 'delete'])

class SwaggerRouter(Singleton):
    def __init__(self, schema, controllers = None, models = None):
        self.base = schema['basePath']
        self.enum = None
        self.links = []
        self.paths = schema['paths']
        self.schema = schema
        self.create = False
        self.models = models
        self.handlers = {}
        self.external = None
        self.stubonly = False
        self.controllers = controllers

        self.process()

    def update(self, create = False):
        self.create = create

    def log(self, *args, **kwargs):
        if self.create:
            print(*args, **kwargs)
        else:
            logger.info(*args, **kwargs)

    # detachable constructor
    def process(self):
        self.stubonly = True

        # try to import controller module first
        if self.controllers:
            try:
                self.external = importlib.import_module(self.controllers)
                self.stubonly = False
            except ImportError:
                self.log('Could not import controller module ({}), using stub handlers for all endpoints'.format(str(self.controllers)))

        # enumerate all methods for gen
        self.enum = dict()

        # determine parsers and renderers
        # TODO: do we really need this?
        #
        # APIView.parser_classes = (XMLParser, )
        # self.schema['consumes'] = ...
        # self.schema['produces'] = ...

        # iterate over all paths
        for path in self.paths:
            view = None
            stub = False
            name = None
            controller = None
            child = self.paths[path]

            # get name from schema
            name = child[self.cextname]

            # if we have module, check for controller property and try to use it
            if not self.stubonly:
                try:
                    controller = getattr(self.external, name)

                except KeyError:
                    stub = True
                    self.log('Controller property for path "{}" is not defined, using stub handler'.format(path))

                except AttributeError:
                    stub = True
                    self.log('Could not find controller "{}" for path "{}", using stub handler'.format(name, path))

            else:
                stub = True

            # pick only allowed methods and make dict of them
            methods = { m : None for m in SWAGGER_METHODS.intersection(set(child)) }

            # check for empty path
            if len(methods) == 0:
                raise SwaggerValidationError('Path "{}" does not contain any supported methods'.format(path))

            # gather all params and wrap them for matching methods
            allparams = set()

            # process methods and responses
            for method in methods:
                responses = child[method].get('responses', None)
                parameters = child[method].get('parameters', None)
                methoddata = { 'params' : None, 'model' : None }

                if parameters:
                    wrapped = list(map(lambda p : SwaggerParameter(p), parameters))
                    methoddata['params'] = wrapped
                    allparams.update([x.name for x in wrapped])

                # TODO: simplify
                if responses:
                    successful = responses[200]
                    schema = successful.get('schema', None)

                    if schema and schema.get('type', None) == 'array':
                        model = Resolver(self.schema, schema['items']['$ref'])
                        mdict = { x : None for x in self.models[model] }
                        methoddata['model'] = [mdict]

                methods[method] = methoddata

            # enumerate named parameters and construct endpoint url
            reg = None
            endpoint = six.moves.urllib.parse.urljoin(self.base, path)
            named = set(self.paramregex.findall(endpoint))

            # if there are any named params, convert 'em to django's format; otherwise just use url
            if len(named):
                reg = re.sub(self.paramregex, self.paramsub, endpoint) # TODO: make matching length tuneable

                # check if schema missing params described in url
                if not named.issubset(allparams):
                    raise SwaggerValidationError('Path "{}" lacks parameters schema'.format(path))
            else:
                reg = endpoint

            # make regex bounds
            reg = re.sub(self.wrapregex, r'^\1/?$', reg)

            # get documentation (if present)
            doc = child.get('description', None)

            # create fallback name
            tempname = re.sub(self.paramregex, r'', str().join(map(str.capitalize, path.split('/')))) + '_' + str(len(path))

            # create stub view object or use existing controller
            if not self.create:
                if stub:
                    name = tempname
                    view = SwaggerViewMaker(name)
                else:
                    view = controller
            else:
                if not name:
                    name = tempname

                self.enum[name] = { 'methods' : [], 'doc' : doc.splitlines() if doc else None }

            # determine if we've got a viewset
            viewset = issubclass(view, GenericViewSet)

            # create serializers
            for method, data in six.iteritems(methods):
                handler = getattr(view, method, None) if not stub else None

                # TODO: refactor for viewsets
                if handler is None:
                    handler = SwaggerRequestMethodMaker(data['model'])

                    if self.create:
                        self.enum[name]['methods'].append({ 'method' : method, 'model' : data['model'] })

                if not self.create:
                    # return validation wrapper if there are some params
                    # or clean (stub) method otherwise
                    wrapped = SwaggerRequestHandler(view, handler, data['params'])

                    # write back to view
                    if stub:
                        view.set_attr(method, wrapped)
                    else:
                        setattr(view, method, wrapped)

            # create doc
            if doc and stub and not self.create:
                view.set_attr('__doc__', doc)

            if not self.create:
                as_view = getattr(view, 'as_view', None)
                

                # use method views if possible
                if not viewset:
                    if as_view:
                        view = as_view()

                    self.handlers.update({ reg : [view, name] })

                else:
                    # hello viewset
                    # TODO: MAJOR rewrite of viewset method breakup logic
                    # TODO: check if swagger allows certain methods for this path
                    # object key for certain mixins
                    lookup_field = getattr(view, 'lookup_field', None)

                    # viewset needs some love
                    for method in methods:
                        if method == 'get':
                            # just GET with(out) params
                            if issubclass(view, ListModelMixin):
                                pass

                            # GET with <pk>
                            if issubclass(view, RetrieveModelMixin):
                                pass

                        elif method in ['put', 'post', 'patch']:
                            # PUT/POST/PATCH request
                            if issubclass(view, CreateModelMixin):
                                pass

                            # PUT/POST/PATCH request
                            if issubclass(view, UpdateModelMixin):
                                pass

                        elif method == 'delete':
                            # DELETE request
                            if issubclass(view, DestroyModelMixin):
                                pass

        # make sorted list and map to django's url()
        if not self.create:
            self.links = [ url(regex, details[0], name = details[1]) for regex, details in sorted(six.iteritems(self.handlers)) ]

    def get_enum(self):
        return self.enum

    @property
    def urls(self):
        return self.links

