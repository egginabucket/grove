from django.urls import path
from translator import views

urlpatterns = [
    path("", views.index, name="index"),
    path("mxl/<slug:filename>/", views.mxl, name="mxl"),
]
