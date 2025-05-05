from django.urls import path
from .views import *

urlpatterns = [
    path('backup/', BackupViewSet.as_view(
        {"get": "list", "post": "create"}
    )),
    path('backup/<str:pk>/', BackupViewSet.as_view(
        {"get": "retrieve", "delete": "destroy", "post": "restore"}
    )),
]