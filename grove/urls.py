import os

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
]

if os.environ.get("MAAS_LOADED", False):
    urlpatterns.append(path("", include("translator.urls"), name="translator"))
