from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.views import APIView
from djsw_wrapper.utils import LazyClass

SwaggerViewClass = APIView

# make http handler
# TODO: rewrite to class?
def SwaggerRequestMethodMaker(model = None):
    def model_handler(self, request, *args, **kwargs):
        data = kwargs.get('data', None)
        resp = model

        return Response(resp, status = status.HTTP_200_OK)

    def empty_handler(self, request, *args, **kwargs):
        data = kwargs.get('data', None)
        resp = None

        return Response(resp, status = status.HTTP_200_OK)

    if model:
        return model_handler
    else:
        return empty_handler

# make named APIView class with specified methods
class SwaggerViewMaker(LazyClass):
    oftype = SwaggerViewClass

    def as_view(self):
        c = self.as_class()

        return c.as_view()

class SwaggerRequestSerializerMaker(LazyClass):
    oftype = serializers.Serializer

class SwaggerSerializerMaker():
    def __init__(self, oftype = None, fields = ['__all__'], model = None):
        assert oftype is not None, ('You should specify a type for the serializer')
        assert type(fields) is list, ('Serializer fields should be listed')
        assert len(fields) > 0, ('Serializer fields should not be an empty list')

        self.fields = fields
        self.oftype = oftype
        self.model = model
        self.serializer = LazyClass('SwaggerDefaultSerializer', self.oftype)

        self.serializer.set_attr('Meta', self.make_meta())

    # construct metaclass (actually DRF uses it as a dict, but let's create class for safety)
    def make_meta(self):
        meta = LazyClass('Meta', type)

        # set fields
        meta.set_attr('fields', tuple(self.fields))

        if self.model:
            meta.set_attr('model', self.model)

        return meta.as_class()

    def as_class(self):
        return self.serializer.as_class()
