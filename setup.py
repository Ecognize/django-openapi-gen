from distutils.core import setup

with open('requirements.txt') as req:
    content = req.readlines()

setup(
  name = 'djsw_wrapper',
  packages = ['djsw_wrapper'],
  version = '0.2.2.1',
  description = 'Allows to build REST API directly from Swagger schema',
  author = 'Alex Revin',
  author_email = 'lyssdod@gmail.com',
  url = 'https://github.com/ErintLabs/django-openapi-gen',
  download_url = 'https://github.com/ErintLabs/django-openapi-gen/archive/0.2.2.1.tar.gz',
  install_requires = [x.strip() for x in content],
  keywords = ['django', 'swagger', 'schema', 'django-rest-framework'],
  classifiers = [],
)
