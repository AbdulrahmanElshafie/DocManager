from django.urls import path
from .views import *

urlpatterns = [
    path('template/', TemplateView.as_view(
        {"get": "list", "post": "create"}
    )),
    path('template/<str:pk>/', TemplateView.as_view(
        {"get": "retrieve", "delete": "destroy", "put": "update", "post": "insert"}
    )),
]