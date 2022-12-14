from grove.settings.common import *

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True
SECRET_KEY = (
    "django-insecure-g1g5j&s^n#2v)%+h&xph5(d09sjw!*brgps4_hbnq4pie*rh)t"
)

STATICFILES_DIRS = [BASE_DIR / "static"]

M21_OUT_DIR = BASE_DIR / "dev-m21-out"
