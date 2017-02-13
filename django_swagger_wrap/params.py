from rest_framework import serializers
from six import iteritems


# make virtual models according to the schema

class BasicSerializer(serializers.Serializer):
	pass

# make parameter after model
class BasicModel(object):
	def __init__(self):
		self.fields = [];
		self.serializer = BasicSerializer

	def make_serializer(self):
		# set attrs according to fields
		self.serializer
