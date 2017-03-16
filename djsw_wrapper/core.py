from django.utils import six
from djsw_wrapper.router import SwaggerRouter
from djsw_wrapper.errors import SwaggerValidationError, SwaggerGenericError

import flex
import os
import re

class Swagger():
    # handle is local filename, file object, string or url
    def __init__(self, handle, module):
        self.schema = None
        self.module = None
        self.loaded = False
        self.handle = handle
        self.models = []
        self.router = None
        self.models = dict()

        # parse
        # TODO: proper errors
        try:
            self.schema = flex.load(self.handle)
            self.module = module
            self.loaded = True
        except:
            raise SwaggerGenericError('Cannot process schema {} : check resource availability'.format(self.handle))

        # make models for definitions
        if 'definitions' in self.schema:
            # make external models
            for name, data in six.iteritems(self.schema['definitions']):
                model = None

                if 'properties' in data:
                    model = list() #dict()

                    for prop, data in six.iteritems(data['properties']):
                        model.append(prop)

                if model:
                    self.models[name] = model

        # make routes
        if 'paths' in self.schema and 'basePath' in self.schema:
            self.router = SwaggerRouter(self.schema, self.module, self.models)
        else:
            raise SwaggerValidationError('Schema is missing paths and/or basePath values')

    # some advanced parsing techniques to be implemented
    def get_schema(self):
        if self.loaded:
            return self.schema
        else:
            raise SwaggerGenericError('You should load spec file first')

    def get_models(self):
        if self.loaded:
            return self.models
        else:
            raise SwaggerGenericError('You should load spec file first')
