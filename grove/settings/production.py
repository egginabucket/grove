import os
from grove.settings.common import *

DEBUG = False
SECRET_KEY = os.environ['DJANGO+SECRET_KEY']