from django.urls import path
from .views import *


urlpatterns = [
    path('folder/', FolderView.as_view(
        {"get": "list", "post": "create"}
    )),
    path('folder/<str:pk>/', FolderView.as_view(
        {"get": "retrieve", "delete": "destroy"}
    )),
    path('document/', DocumentView.as_view(
        {"get": "list", "post": "create"}
    )),
    path('document/<str:pk>/', DocumentView.as_view(
        {"get": "retrieve", "delete": "destroy"}
    )),
    path('share/<str:token>/', ShareableLinkView.as_view(

    ))
]
