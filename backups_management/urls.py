from django.urls import path
from .views import *

urlpatterns = [
    path('', BackupViewSet.as_view(
        {"get": "list", "post": "create"}
    )),
    path('<str:pk>/', BackupViewSet.as_view(
        {"get": "retrieve", "delete": "destroy", "post": "restore"}
    )),
]