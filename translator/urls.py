from django.urls import path
from translator import views

urlpatterns = [path("", views.index, name="index")]
