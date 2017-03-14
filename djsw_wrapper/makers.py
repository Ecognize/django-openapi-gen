from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import serializers, status

from djsw_wrapper.utils import LazyClass

# make http handler
def SwaggerMethodMaker():
    def handler(self, request, *args, **kwargs):
        data = kwargs.get('data', None)

        return Response(status = status.HTTP_200_OK)

    return handler

# make named APIView class with specified methods
class SwaggerViewMaker(LazyClass):
    oftype = APIView

    def as_view(self):
        c = self.as_class()

        return c.as_view()

class SwaggerSerializerMaker(LazyClass):
    oftype = serializers.Serializer
