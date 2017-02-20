from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from django_swagger_wrap.core import Swagger

import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

class DjangoOpenapiWrapConfig(AppConfig):
    name = 'django_swagger_wrap'
    schema = None
    swagger = None

    # startup
    def ready(self):
        self.schema = getattr(settings, 'SWAGGER_SCHEMA', None)

        if not self.schema:
            raise ImproperlyConfigured('You have to provide SWAGGER_SCHEMA setting pointing to desired schema')
        else:
            self.swagger = Swagger(self.schema)
