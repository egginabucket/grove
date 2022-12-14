import os

from grove.settings.common import *

DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

M21_OUT_DIR = os.environ["M21_OUT_DIR"]
CORS_ALLOWED_ORIGINS = os.environ["CORS_ALLOWED_ORIGINS"].split()