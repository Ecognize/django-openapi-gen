from distutils.core import setup

setup(
  name = 'djsw_wrapper',
  packages = ['djsw_wrapper'],
  version = '0.1.4',
  description = 'Allows to build REST API directly from Swagger schema',
  author = 'Alex Revin',
  author_email = 'lyssdod@gmail.com',
  url = 'https://github.com/ErintLabs/django-openapi-gen',
  download_url = 'https://github.com/ErintLabs/django-openapi-gen/archive/0.1.4.tar.gz',
  install_requires = ['django', 'djangorestframework', 'jinja2', 'flex'],
  keywords = ['django', 'swagger', 'schema', 'django-rest-framework'],
  classifiers = [],
)
