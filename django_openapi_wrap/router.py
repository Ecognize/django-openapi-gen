from rest_framework import routers
from django_openapi_gen import Swagger
from django_openapi_gen.views import StubMethods, DefaultAPIView

import six

class SwaggerRouter:
    def __init__(self, spec):
        self.router = routers.SimpleRouter()
        self.swagger = Swagger(self.spec)

    def create_view(self, root, path):
        view = DefaultAPIView()

        for method in root[path]:
            handler = getattr(StubMethods, method, None)

            if callable(handler):
                setattr(view, method, six.create_bound_method(handler, view)

        # setup validators here

        return view

    def generate(self):
        obj = self.swagger.get_object()

        for path in obj['paths']:
            view = create_view(obj['paths'], path)
