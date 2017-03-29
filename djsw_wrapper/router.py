import re
import logging
import importlib

from collections import OrderedDict
from django.utils import six
from django.conf.urls import url as make_url, include

from djsw_wrapper.utils import Singleton, Template, Resolver, LazyClass
from djsw_wrapper.makers import SwaggerViewMaker, SwaggerRequestMethodMaker, SwaggerViewClass
from djsw_wrapper.params import SwaggerParameter, SwaggerRequestHandler
from djsw_wrapper.errors import SwaggerValidationError, SwaggerGenericError

from rest_framework import status
from rest_framework.response import Response
from rest_framework.routers import SimpleRouter
from rest_framework.viewsets import GenericViewSet
from rest_framework.relations import ManyRelatedField, HyperlinkedRelatedField

from rest_framework.reverse import reverse
from rest_framework.compat import NoReverseMatch

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

#: request kwarg parameter describing object primary key (usually `pk` in Django)
LOOKUP_FIELD_NAME = 'lookup_url_kwarg'

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

    #: construct full url
    def make_fullpath(self, path):
        return six.moves.urllib.parse.urljoin(self.base.rstrip('/') + '/', path.lstrip('/'))

    #: convert swagger path to django url regex (with params if present)
    def make_regex(self, path, named = False):
        regex = re.sub(SWAGGER_PARAMS_REGEX, DJANGO_PARAMS_STRING, path) if named else path
        regex = re.sub(URL_SLASHES_REGEX, DJANGO_URL_SUBSTRING, regex)

        return regex

    #: create handler ready for urlization
    def store_handler(self, path, view, linkname, displayname, named = False):
        fullpath = self.make_fullpath(path)
        regex = self.make_regex(fullpath, named)

        self.handlers.update({ regex : { 'view': view, 'name': linkname, 'display': displayname } })

    #: DRF only allows lookup_url_kwarg specified during __init__,
    #: which's not always possible. If it's not specified there,
    #: variable defaults to lookup_field attribute. It's too risky
    #: to overwrite it also, so the only way to ensure we are using
    #: right url kwarg is to substitute the whole method with the
    #: right argument provided. more info:
    #: https://github.com/tomchristie/django-rest-framework/issues/5034
    def properly_kwarged_get_object(self, kwarg_lookup):
        def get_object(self, view_name, view_args, view_kwargs):
            """
            Return the object corresponding to a matched URL.
            Takes the matched URL conf arguments, and should return an
            object instance, or raise an `ObjectDoesNotExist` exception.
            """
            lookup_value = view_kwargs[kwarg_lookup]
            lookup_kwargs = {self.lookup_field: lookup_value}
            print('DEBUG GET_OBJECT: ', lookup_kwargs)
            return self.get_queryset().get(**lookup_kwargs)

        return get_object

    #: the same for get_url
    def properly_kwarged_get_url(self, kwarg_lookup):
        def get_url(self, obj, view_name, request, format):
            """
            Given an object, return the URL that hyperlinks to the object.
            May raise a `NoReverseMatch` if the `view_name` and `lookup_field`
            attributes are not configured to correctly match the URL conf.
            """
            # Unsaved objects will not yet have a valid URL.
            if hasattr(obj, 'pk') and obj.pk in (None, ''):
                return None

            lookup_value = getattr(obj, self.lookup_field)
            kwargs = {kwarg_lookup: lookup_value}
            print('DEBUG_GET_URL: ', kwargs)
            return self.reverse(view_name, kwargs=kwargs, request=request, format=format)

        return get_url

    #: method binding helper
    def bind(self, obj, name, func):
        setattr(obj, name, six.create_bound_method(func, obj))

    #: create root api view
    def get_root_apiview(self):
        handlers = sorted(self.handlers.items(), key = lambda x : x[1]['display'])

        def list_handlers(self, request, *args, **kwargs):
            resp = OrderedDict()

            # get all names
            for regex, data in handlers:
                name = data['name']
                alias = data['display']

                if alias != APIROOT_NAME:
                    try:
                        resp[alias] = reverse(name, args = args, kwargs = kwargs, request = request, format = kwargs.get('format', None))
                    except NoReverseMatch:
                        # here we've got a path with defined params which are not specified in request
                        continue

            return Response(resp, status = status.HTTP_200_OK)

        # get available info from schema
        info = self.schema.get('info', None)
        name = info.get('title', APIROOT_NAME).strip(' ').replace(' ', '_')
        vers = info.get('version', 'unknown')
        desc = info.get('description', 'Enumerates all available endpoints for current schema')

        # construct class
        apiroot = LazyClass(name, SwaggerViewClass)

        apiroot.set_attr('get', list_handlers)
        apiroot.set_attr('__doc__', 'v.' + vers + '\n\n' + desc)

        return apiroot().as_view()

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

            # remove trailing slash from path
            path = path.rstrip('/')

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

            # get all methods for this path and check for named params
            mismatch, namedparams, methods = self.enumerate_methods(tree, path)
            named = len(namedparams) > 0

            # check for empty path
            if len(methods) == 0:
                raise SwaggerValidationError('Path "{}" does not contain any supported methods'.format(path))

            if mismatch:
                raise SwaggerValidationError('Path "{}" lacks parameters schema'.format(path))

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

                        setattr(view, LOOKUP_FIELD_NAME, key)

                        # if we have fancy serializers, update them as well
                        if hasattr(view, 'serializer_class'):
                            # thanks to default metaclass, we can iterate serializer class
                            # without creating an instance of it
                            for sn, sf in six.iteritems(view.serializer_class._declared_fields):
                                # have to substitute the whole method instead of one attribute
                                # https://github.com/tomchristie/django-rest-framework/issues/5034
                                if isinstance(sf, HyperlinkedRelatedField): # many == False
                                    self.bind(view.serializer_class._declared_fields[sn], 'get_object', self.properly_kwarged_get_object(key))
                                    self.bind(view.serializer_class._declared_fields[sn], 'get_url', self.properly_kwarged_get_url(key))
                                elif isinstance(sf, ManyRelatedField): # many == True
                                    self.bind(view.serializer_class._declared_fields[sn].child_relation, 'get_object', self.properly_kwarged_get_object(key))
                                    self.bind(view.serializer_class._declared_fields[sn].child_relation, 'get_url', self.properly_kwarged_get_url(key))
                                # more fancy serializer classes to be added here
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

            # properly format name for viewsets
            linkname = None

            if viewset:
                temp = None
                queryset = getattr(view, 'queryset', None)

                if queryset is not None:
                    temp = queryset.model._meta.object_name.lower()
                else:
                    temp = name.lower()

                linkname = temp + ('-detail' if key else '-list')
            else:
                linkname = name.lower()

            # special case for path params — we need to create individual endpoints for each param
            if not viewset and not key and named:
                url = str('/')

                # break url by parts and append by one
                for part in path.strip('/').split('/'):
                    url += (part + '/')

                    self.store_handler(url.rstrip('/'), final, linkname, name, True)
            else:
                self.store_handler(path, final, linkname, name, named)


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
        if not self.create:
            # make sorted list and map to django's url()
            self.links = [ make_url(regex, details['view'], name = details['name']) for regex, details in six.iteritems(self.handlers) ]

            # create API root view
            self.links.append(make_url(self.make_regex(self.base), self.get_root_apiview(), name = APIROOT_NAME))

    @property
    def enum(self):
        return self.gen

    @property
    def urls(self):
        return self.links

