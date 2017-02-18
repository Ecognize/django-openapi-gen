from rest_framework import serializers
from six import iteritems

class InvalidParameterError(ValueError):
    pass

class ParameterType():
    String = 0
    Number = 1
    Integer = 2
    Boolean = 3
    Array = 4
    File = 5

    # TODO: add enum
    @staticmethod
    def fromString(string):
        if string.lower() == 'string':
            return ParameterType.String
        elif string.lower() == 'number':
            return ParameterType.Number
        elif string.lower() == 'integer':
            return ParameterType.Integer
        elif string.lower() == 'boolean':
            return ParameterType.Boolean
        elif string.lower() == 'array':
            return ParameterType.Array
        elif string.lower() == 'file':
            return ParameterType.File
        else:
            raise InvalidParameterError('Unknown parameter type: {0}'.format(string))

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
            raise InvalidParameterError('Unknown parameter location: {0}'.format(string))


class ProxySerializer(serializers.Serializer):
    @staticmethod
    def makeField(oftype, items = None):
        if oftype == ParameterType.String:
            return serializers.CharField(max_length = 255) # to be discussed
        elif oftype == ParameterType.Number:
            return serializers.DecimalField()
        elif oftype == ParameterType.Integer:
            return serializers.IntegerField()
        elif oftype == ParameterType.Boolean:
            return serializers.BooleanField()
        elif oftype == ParameterType.Array and items:
            return makeField(items)
        elif oftype == ParameterType.File:
            return serializers.FileField()


class SwaggerParameter():
    def __init__(self, schema):
        self.raw = None
        self.name = schema['name']
        self.oftype = ParameterType.fromString(schema['type'])
        self.location = ParameterLocation.fromString(schema['in'])
        self.required = schema['required']

        # quick check for array
        if self.oftype == ParameterType.Array and 'items' not in schema:
            raise InvalidParameterError('You should provide items dictionary for using array type')

        # quick check for file
        if self.oftype == ParameterType.File and self.location is not ParameterLocation.FormData:
            raise InvalidParameterError('You have to use formData location for using file type')

        # make serializer
        self.serializer = ProxySerializer
        setattr(self.serializer, 'param', ProxySerializer.makeField(self.oftype, schema.get('items')))

    # validate parameter against input data
    def process(self, rawdata):
        tmp = self.serializer(data = {'param' : rawdata})

        if tmp.is_valid(raise_exception = True):
            return tmp
        else:
            pass # 400 bad request exception should be already raised

    # regex representation for url matching
    def regex(self):
        regex = None

        # TODO: add enum
        if self.oftype == ParameterType.String:
            regex = '([\w\%\+\-]+)'
        elif self.oftype == ParameterType.Number:
            regex = '(\d+\.{1}\d+)'
        elif self.oftype == ParameterType.Integer:
            regex = '(\d+)'
        elif self.oftype == ParameterType.Boolean:
            regex = '(TRUE|True|true|FALSE|False|false)'
        # omit files and arrays for now

        # TODO: validate missing params
        return regex += '?'