import logging

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

# make http handler
def SwaggerMethodMaker():
    def handler(*args, **kwargs):
        return Response(status = status.HTTP_200_OK)

    return handler

# make named APIView class with specified methods
class SwaggerViewMaker(object):

    # methods: name : serializer
    # if methods is list, no decorators will be used
    def __init__(self, name = 'SwaggerView'):
        self.methods = dict()
        self.ready = False
        self.view = None
        self.name = name

        #super(SwaggerViewMaker, self).__init__()

    # make class with methods
    def setup(self):
        self.view = type(self.name, (APIView,), dict(self.methods))
        self.ready = True

    def update_method(self, name, func):
        self.methods[name] = func

    def as_view(self):
        if not self.ready:
            self.setup()

        return self.view.as_view()

    def as_class(self):
        if not self.ready:
            self.setup()

        return self.view


