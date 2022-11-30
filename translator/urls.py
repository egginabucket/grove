from django.urls import path
from translator import views

urlpatterns = [path("langs/", views.supported_languages, name="langs")]
