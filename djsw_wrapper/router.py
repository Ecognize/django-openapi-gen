import re
import logging
import importlib

from django.utils import six
from django.conf.urls import url

from djsw_wrapper.utils import Singleton, Template, Resolver
from djsw_wrapper.makers import SwaggerViewMaker, SwaggerRequestMethodMaker, SwaggerViewClass
from djsw_wrapper.params import SwaggerParameter, SwaggerRequestHandler
from djsw_wrapper.errors import SwaggerValidationError, SwaggerGenericError

from rest_framework import status
from rest_framework.response import Response
from rest_framework.routers import SimpleRouter
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin

logger = logging.getLogger(__name__)

#: name of swagger view reference in schema
SCHEMA_VIEW_NAME = 'x-swagger-router-view'

#: what param to use as key when quering single obj
SCHEMA_OBJECT_KEY = 'x-swagger-object-key'

#: django url param substitution
DJANGO_PARAMS_STRING = r'(?P<\1>[^/.]+)'

#: complete django url
DJANGO_URL_SUBSTRING = r'^\1/?$'

#: removes heading and trailing slashes
URL_SLASHES_REGEX = re.compile(r'^\/?(.*)\/?')

#: extracts parameters from swagger url path
SWAGGER_PARAMS_REGEX = re.compile(r'\{(\w?[\w\d]*)\}')

#: allowed by Swagger 2.0
SWAGGER_METHODS = set(['get', 'put', 'post', 'head', 'patch', 'options', 'delete'])

#: borrowed from DRF
VIEWSET_MAPPING = { 'list': {'post': 'create', 'get': 'list'}, 
                    'detail': {'delete': 'destroy', 'patch': 'partial_update', 'get': 'retrieve', 'put': 'update'} }

#: name of apiroot view
APIROOT_NAME = 'SwaggerAPIRoot'

class SwaggerRouter(Singleton):
    def __init__(self, schema, module = None, models = None):
        self.base = schema['basePath']
        self.gen = None
        self.links = []
        self.paths = schema['paths']
        self.schema = schema
        self.create = False
        self.models = models
        self.module = module
        self.handlers = {}

        self.process()

    def update(self, create = False):
        self.create = create

    def log(self, *args, **kwargs):
        if self.create:
            print(*args, **kwargs)
        else:
            logger.info(*args, **kwargs)

    #: import views module or return None
    def get_module(self):
        module = None

        try:
            module = importlib.import_module(self.module)
        except ImportError:
            self.log('Could not import controller module ({}), using stub handlers for all endpoints'.format(str(self.module)))

        return module

    #: get obj key if present
    def get_object_key(self, schemapart):
        return schemapart.get(SCHEMA_OBJECT_KEY, None)

    #: get view name from schema or construct temporary one
    def get_view_name(self, path, schemapart):
        name = None

        try:
            name = schemapart[SCHEMA_VIEW_NAME]
        except KeyError:
            name = str().join(map(str.capitalize, path.split('/')))

        return name

    #: get method group and name
    def get_viewset_method(self, method, key = None):
        return VIEWSET_MAPPING['detail'][method] if key else VIEWSET_MAPPING['list'][method]

    #: return dict of all methods for current path
    def enumerate_methods(self, schemapart, fullpath):
        allparams = set()
        namedparams = set(SWAGGER_PARAMS_REGEX.findall(fullpath))

        # initial dict
        methods = { m : None for m in SWAGGER_METHODS.intersection(set(schemapart)) }

        # process methods and responses
        for method in methods:
            responses = schemapart[method].get('responses', None)
            parameters = schemapart[method].get('parameters', None)
            description = schemapart[method].get('description', None)

            methoddata = { 'params' : None, 'model' : None, 'doc' : None }

            if description:
                methoddata['doc'] = description

            if parameters:
                wrapped = list(map(lambda p : SwaggerParameter(p), parameters))
                methoddata['params'] = wrapped
                allparams.update([x.name for x in wrapped])

            # TODO: simplify
            # TODO: does anybody really needs this?
            if responses:
                successful = responses[200]
                default = responses['default']

                schema = successful.get('schema', None)

                if schema and schema.get('type', None) == 'array':
                    model = Resolver(self.schema, schema['items']['$ref'])
                    mdict = { x : None for x in self.models[model] }
                    methoddata['model'] = [mdict]

            methods[method] = methoddata

        return not namedparams.issubset(allparams), namedparams, methods

    #: create root api view
    def get_root_apiview(self):
        handlers = self.handlers

        class SwaggerAPIRootView(SwaggerViewClass):
            """
            Enumerates all available endpoints for current schema
            """

            def get(self, request, *args, **kwargs):
                prefix = request.scheme + '://' + request.get_host()
                resp = dict()
                root = dict()

                # get all names
                for regex, data in six.iteritems(handlers):
                    if data['name'] != APIROOT_NAME:
                        root.update(data['root'])

                # assign regexless urls
                for name, url in six.iteritems(root):
                    regex = url.strip('/').split('/')
                    resp[name] = six.moves.urllib.parse.urljoin(prefix, regex[0])

                return Response(resp, status = status.HTTP_200_OK)

        return SwaggerAPIRootView.as_view()

    #: main schema processing function
    def process(self):
        # try to import controller module first
        module = self.get_module()

        # enumerate all methods for gen
        self.gen = dict()

        # determine parsers and renderers
        # TODO: do we really need this?
        #
        # APIView.parser_classes = (XMLParser, )
        # self.schema['consumes'] = ...
        # self.schema['produces'] = ...

        # iterate over all paths
        for path, tree in six.iteritems(self.paths):
            doc = []
            view = None
            stub = True
            name = None
            regex = None
            viewdoc = None
            controller = None

            # get view name from schema
            name = self.get_view_name(path, tree)

            # try to get this view from module
            try:
                controller = getattr(module, name)
                stub = False
            except KeyError:
                self.log('Controller property for path "{}" is not defined, using stub handler'.format(path))
            except AttributeError:
                self.log('Could not find controller "{}" for path "{}", using stub handler'.format(name, path))

            # construct full url
            fullpath = six.moves.urllib.parse.urljoin(self.base, path)

            # get all methods for this path and check for named params
            mismatch, namedparams, methods = self.enumerate_methods(tree, fullpath)

            # check for empty path
            if len(methods) == 0:
                raise SwaggerValidationError('Path "{}" does not contain any supported methods'.format(path))

            if mismatch:
                raise SwaggerValidationError('Path "{}" lacks parameters schema'.format(path))

            # and make bounded regex of it
            regex = re.sub(SWAGGER_PARAMS_REGEX, DJANGO_PARAMS_STRING, fullpath) if len(namedparams) > 0 else fullpath
            regex = re.sub(URL_SLASHES_REGEX, DJANGO_URL_SUBSTRING, regex)

            # create stub view object or use existing controller
            if not self.create:
                view = controller if controller else SwaggerViewMaker(name)()
            else:
                self.gen[name] = { 'methods' : [], 'doc' : doc.splitlines() if doc else None }

            viewset = issubclass(view, GenericViewSet)

            # TODO: delete/forbid methods undefined in schema and notify user
            if viewset:
                pass

            # for all defined methods, get their handlers from view
            for method, data in six.iteritems(methods):
                key = self.get_object_key(tree)
                inner = self.get_viewset_method(method, key)
                objname = inner if viewset else method
                handler = getattr(view, objname, None) if not stub else None

                if handler is None:
                    handler = SwaggerRequestMethodMaker(data['model'])

                    """
                    if self.create:
                        self.gen[name]['methods'].append({ 'method' : method, 'model' : data['model'] })
                        if not self.create:
                    """
                # update <pk> name if path has single queries
                if viewset:
                    if key:
                        if key not in namedparams:
                            raise SwaggerValidationError('Path {} requires param `{}` to be defined for single object operations'.format(path, key))
                        setattr(view, 'lookup_field', key)

                    elif stub:
                        raise SwaggerValidationError('There is no object key property ({}) for single queries for path {}'.format(SCHEMA_OBJECT_KEY, path))

                # validation itself
                wrapped = SwaggerRequestHandler(view, handler, data['params'])

                # write back to view
                setattr(view, objname, wrapped)

                # doc gathering
                if data['doc']:
                    doc.append(objname + ':\n' + data['doc'])

            # create doc
            old = getattr(view, '__doc__', None)

            if len(doc) and not self.create:
                setattr(view, '__doc__', str(old if old else '') + '\n' + str('\n').join(doc))

            if not self.create:
                as_view = getattr(view, 'as_view', None)
                
            # use method views if possible
            final = None

            if viewset:
                group = 'detail' if key else 'list'
                av_args = { method : mapping for method, mapping in six.iteritems(VIEWSET_MAPPING[group]) if method in methods }

                final = view.as_view(av_args)
            else:
                final = view.as_view()

            self.handlers.update({ regex : { 'view': final, 'name': (name + 'Item' if key else name), 'root': { name : path } } })

            """
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
            """
        # create API root view
        self.handlers.update({ '^$' : { 'view' : self.get_root_apiview(), 'name': APIROOT_NAME, 'root': dict() } })

        # make sorted list and map to django's url()
        if not self.create:
            self.links = [ url(regex, details['view'], name = details['name']) for regex, details in sorted(six.iteritems(self.handlers)) ]

    @property
    def enum(self):
        return self.gen

    @property
    def urls(self):
        return self.links

