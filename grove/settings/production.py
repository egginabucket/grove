import os
from grove.settings.common import *

DEBUG = False
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

MUSIC21_OUTPUT_DIR = os.environ['MUSIC21_OUTPUT_DIR']
