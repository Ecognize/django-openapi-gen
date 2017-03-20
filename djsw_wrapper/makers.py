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

# TODO: make proper model mapping
class SwaggerDataSerializerMaker(LazyClass):
    def __init__(self, *args, **kwargs):
        super(SwaggerDataSerializerMaker, self).__init__(*args, **kwargs)