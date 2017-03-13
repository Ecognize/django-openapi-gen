from django.utils.six import iteritems
from rest_framework import serializers

from djsw_wrapper.errors import SwaggerParameterError
from djsw_wrapper.makers import SwaggerSerializerMaker


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
    mapping = {
        ParameterType.String : serializers.CharField,
        ParameterType.Number : serializers.DecimalField,
        ParameterType.Integer : serializers.IntegerField,
        ParameterType.Boolean : serializers.BooleanField,
        ParameterType.File : serializers.FileField
    }

    # TODO: properly handle array and enums
    def __init__(self, schema):
        self._name = schema['name']
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

    @property
    def name(self):
        return self._name

    @property
    def location(self):
        return self._location

    @property
    def required(self):
        return self._required


    def __repr__(self):
        return "{} ({},{})".format(self._name, self._oftype, self._required)

    # TODO: properly handle array and enums
    def as_field(self):
        items = None

        if self._oftype == ParameterType.String:
            self._params['max_length'] = 255 # to be discussed
        elif self._oftype == ParameterType.Enum:
            pass
        elif self._oftype == ParameterType.Array and items:
            pass

        field = self.mapping.get(self._oftype, None)

        # maybe exception?
        return field(**self._params) if field is not None else None

# automatically validates the data
def SwaggerRequestHandler(handler, params, *args, **kwargs):

    # wrapped request handler
    class SwaggerValidator(object):
        def __init__(self, serializer = None, func = None, params = None):
            self.serializer = serializer
            self.params = params
            self.func = func

        # extract params with respect to their location
        def extract(self, request, uparams):
            data = dict()


            for param in self.params:
                p = None
                n = param.name
                l = param.location

                # TODO: clarify different location combination
                #if request.method == 'GET':
                if l is ParameterLocation.Query:
                    p = request.query_params.get(n, None)
                elif l is ParameterLocation.Path:
                    p = uparams.get(n, None)
                #elif request.method in ['POST', 'PUT', 'DELETE']:
                elif l is ParameterLocation.FormData or l is ParameterLocation.Body:
                    p = request.data.get(n, None)

                if p is not None:
                    data[n] = p

            return data

        # validate request data
        def process(self, request, *args, **kwargs):
            s_object = self.serializer.as_class()
            serializer = s_object(data = self.extract(request, kwargs))

            if serializer.is_valid(raise_exception = True):
                return self.func(*args, **kwargs)
            else:
                pass # s.errors contain detailed error

    # validate or not
    if params is None:
        return handler
    else:
        serializer = SwaggerSerializerMaker('AutoSerializer')

        for param in params:
            serializer.set_attr(param.name, param.as_field())

        validator = SwaggerValidator(serializer, handler, params)

        return validator.process

