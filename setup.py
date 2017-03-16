import sys
import contextlib
from distutils.core import setup

if (sys.version_info > (3, 0)):
    from urllib.request import urlopen as urlopen
else:
    from urllib2 import urlopen

txt = None
req = 'https://raw.githubusercontent.com/ErintLabs/django-openapi-gen/master/requirements.txt'

with contextlib.closing(urlopen(req)) as u:
    txt = [x.decode('utf-8') for x in u.read().splitlines()]

setup(
  name = 'djsw_wrapper',
  packages = ['djsw_wrapper'],
  version = '0.1.5',
  description = 'Allows to build REST API directly from Swagger schema',
  author = 'Alex Revin',
  author_email = 'lyssdod@gmail.com',
  url = 'https://github.com/ErintLabs/django-openapi-gen',
  download_url = 'https://github.com/ErintLabs/django-openapi-gen/archive/0.1.5.tar.gz',
  install_requires = txt,
  keywords = ['django', 'swagger', 'schema', 'django-rest-framework'],
  classifiers = [],
)
