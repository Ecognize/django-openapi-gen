from django_swagger_wrap.router import SwaggerRouter

import flex
import six
import os

class Swagger():
    # handle is local filename, file object, string or url
    def __init__(self, handle):
        self.schema = None
        self.loaded = False
        self.handle = handle
        self.models = []
        self.router = None

        # parse
        # TODO: proper errors
        try:
            self.schema = flex.load(self.handle)
            self.loaded = True
        except:
            raise ValueError('Cannot process this schema')

        # make models for definitions
        if 'definitions' in self.schema:
            # make external models
            for name, data in six.iteritems(self.schema['definitions']):
                #self.models.append()
                pass

        # make routes
        if 'paths' in self.schema and 'basePath' in self.schema:
            self.router = SwaggerRouter(self.schema['basePath'], self.schema['paths'])
            print('Startup completed')
        else:
            raise ValueError('Schema is missing paths and/or basePath values')
    
    # some advanced parsing techniques to be implemented
    def get_schema(self):
        if self.loaded:
            return self.schema
        else:
            raise ValueError('You should load spec file first')
