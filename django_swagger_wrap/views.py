from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import logging

logger = logging.getLogger(__name__)

class StubControllerMethods():
    def get(self, request, *args, **kwargs):
        logger.info('stub GET request for %s', request.path)
        return Response(status = status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        logger.info('stub PUT request for %s', request.path)
        return Response(status = status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        logger.info('stub POST request for %s', request.path)
        return Response(status = status.HTTP_200_OK)

    def head(self, request, *args, **kwargs):
        logger.info('stub HEAD request for %s', request.path)
        return Response(status = status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        logger.info('stub PATCH request for %s', request.path)
        return Response(status = status.HTTP_200_OK)

    def options(self, request, *args, **kwargs):
        logger.info('stub OPTIONS request for %s', request.path)
        return Response(status = status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        logger.info('stub DELETE request for %s', request.path)
        return Response(status = status.HTTP_204_NO_CONTENT)


class SwaggerView(APIView):
    pass
