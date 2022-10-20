from grove.settings.common import *

DEBUG = True
SECRET_KEY = 'django-insecure-g1g5j&s^n#2v)%+h&xph5(d09sjw!*brgps4_hbnq4pie*rh)t'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

M21_OUT_DIR = BASE_DIR / 'dev-m21-out'