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
        self.raw = None
        self.name = schema['name']
        self.oftype = ParameterType(schema['type'])
        self.location = ParameterLocation.fromString(schema['in'])
        self.required = schema.get('required', False)

        # default params
        self.params = { 'required' : self.required }

        # quick check for array
        if self.oftype == ParameterType.Array and 'items' not in schema:
            raise SwaggerParameterError('You should provide items dictionary for using array type')

        # quick check for file
        if self.oftype == ParameterType.File and self.location is not ParameterLocation.FormData:
            raise SwaggerParameterError('You have to use formData location for using file type')

    def get_name(self):
        return self.name

    def __repr__(self):
        return "{} ({},{})".format(self.name, self.oftype, self.required)

    # TODO: properly handle array and enums
    def as_field(self):
        items = None

        if self.oftype == ParameterType.String:
            self.params['max_length'] = 255 # to be discussed
        elif self.oftype == ParameterType.Enum:
            pass
        elif self.oftype == ParameterType.Array and items:
            pass

        field = self.mapping.get(self.oftype, None)

        # maybe exception?
        return field(self.params) if field is not None else None

# automatically validates the data
def SwaggerRequestHandler(handler, params, *args, **kwargs):

    # wrapped request handler
    class SwaggerValidator(object):
        def __init__(self, serializer = None, func = None):
            self.serializer = serializer
            self.func = func

        def process(self, request, *args, **kwargs):
            print('VALIDATION')
            print('R:',request)
            print('params:', kwargs)

            # map kwargs request to serializer
            # TODO: POST data!
            s_object = self.serializer.as_class()
            serializer = s_object(data = kwargs)

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
            serializer.set_attr(param.get_name(), param.as_field())

        validator = SwaggerValidator(serializer, handler)

        return validator.process

