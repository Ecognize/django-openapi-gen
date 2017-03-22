from django.utils.six import iteritems
from rest_framework import serializers

from djsw_wrapper.errors import SwaggerParameterError
from djsw_wrapper.makers import SwaggerRequestSerializerMaker


# TODO: rewrite to proper enum
class ParameterType():
    String = 0
    Number = 1
    Integer = 2
    Boolean = 3
    Array = 4
    Enum = 5
    File = 6

    typeset = {
        'string' : String,
        'number' : Number,
        'integer' : Integer,
        'boolean' : Boolean,
        'array' : Array,
        'enum' : Enum,
        'file' : File
    }

    oftype = None

    def get_type(self):
        return self.oftype

    def __init__(self, initial = None):
        if type(initial) is None:
            self.oftype = self.typeset.string
        elif type(initial) is str and initial.lower() in self.typeset.keys():
            self.oftype = self.typeset[initial.lower()]
        elif isinstance(initial, ParameterType):
            self.oftype = initial.get_type()
        else:
            raise SwaggerParameterError('Unknown parameter type: {0}'.format(string))

    def __repr__(self):
        return next(x for x, y in iteritems(self.typeset) if y == self.oftype)

class ParameterLocation():
    Query = 0
    Header = 1
    Path = 2
    FormData = 3
    Body = 4

    @staticmethod
    def fromString(string):
        if string.lower() == 'query':
            return ParameterLocation.Query
        elif string.lower() == 'header':
            return ParameterLocation.Header
        elif string.lower() == 'path':
            return ParameterLocation.Path
        elif string.lower() == 'formdata':
            return ParameterLocation.FormData
        elif string.lower() == 'body':
            return ParameterLocation.Body
        else:
            raise SwaggerParameterError('Unknown parameter location: {0}'.format(string))

class SwaggerParameter():

    def typemap(self, p):
        mapping = {
            ParameterType.String : serializers.CharField,
            ParameterType.Number : serializers.FloatField,
            ParameterType.Integer : serializers.IntegerField,
            ParameterType.Boolean : serializers.BooleanField,
            ParameterType.Array : serializers.ListField,
            ParameterType.Enum : serializers.ChoiceField,
            ParameterType.File : serializers.FileField
        }

        return mapping.get(p, None)

    # TODO: properly handle array and enums
    def __init__(self, schema):
        self._name = schema['name']
        self._enum = schema.get('enum', None)
        self._items = schema.get('items', None)
        self._oftype = ParameterType(schema['type']).get_type()
        self._location = ParameterLocation.fromString(schema['in'])
        self._required = schema.get('required', False)

        # default params
        self._params = { 'required' : self.required }

        # quick check for array
        if self._oftype == ParameterType.Array and 'items' not in schema:
            raise SwaggerParameterError('You should provide items dictionary for using array type')

        # quick check for file
        if self._oftype == ParameterType.File and self._location is not ParameterLocation.FormData:
            raise SwaggerParameterError('You have to use formData location for using file type')

        if self._oftype == ParameterType.Array:
            child = self.typemap(ParameterType(self._items['type']).get_type())
            self._params = { 'child': child() }

        if self._enum:
            self._oftype = ParameterType.Enum
            self._params = { 'choices' : self._enum }


    @property
    def name(self):
        return self._name

    @property
    def oftype(self):
        return self._oftype

    @property
    def location(self):
        return self._location

    @property
    def required(self):
        return self._required


    def __repr__(self):
        return "{} ({},{})".format(self._name, self._oftype, self._required)

    # TODO: properly handle array and enums
    # TODO: store serializer params in settings
    def as_field(self):
        items = None

        if self._oftype is ParameterType.String:
            self._params['max_length'] = 255 # to be discussed
        elif self._oftype is ParameterType.Enum:
            pass
        elif self._oftype is ParameterType.Number:
            #self._params['max_digits'] = 16
            #self._params['decimal_places'] = 4
            pass
        elif self._oftype is ParameterType.Array and items:
            pass

        field = self.typemap(self._oftype)

        # maybe exception?
        return field(**self._params) if field is not None else None

# automatically validates the data
def SwaggerRequestHandler(view, handler, params, *args, **kwargs):

    # wrapped request handler
    class SwaggerValidator(object):
        def __init__(self, view = None, serializer = None, func = None, params = None):
            self.serializer = serializer
            self.params = params
            self.func = func
            self.view = view

        # extract params with respect to their location
        def extract(self, request, uparams):
            data = dict()

            for param in self.params:
                store = None
                value = None

                p = None
                n = param.name
                t = param.oftype

                if param.location == ParameterLocation.Query:
                    store = request.query_params
                elif param.location == ParameterLocation.Path:
                    store = uparams
                elif param.location in [ParameterLocation.FormData, ParameterLocation.Body]:
                    store = request.data

                if param.oftype == ParameterType.Array:
                    value = store.getlist(param.name, None)
                else:
                    value = store.get(param.name, None)

                if value:
                    data[param.name] = value

            return data

        # validate request data
        @staticmethod
        def process(self, request, *args, **kwargs):
            print(self)
            # wrong self!
            s_object = self.serializer() # returned obj is already another obj
            serializer = s_object(data = self.extract(request, kwargs))

            if serializer.is_valid(raise_exception = True):
                print('here!', self.func, self.view)
                r= self.func(self.view, request=request, data = serializer.data, *args, **kwargs)
                print('after')
                return r
            else:
                pass # s.errors contain detailed error

    # validate or not
    if not params:
        print('no params')
        return handler
    else:
        serializer = SwaggerRequestSerializerMaker('SwaggerRequestSerializer')

        for param in params:
            serializer.set_attr(param.name, param.as_field())

        print('validation construct')
        validator = SwaggerValidator(view, serializer, handler, params)

        print('returning .process')
        return validator.process

