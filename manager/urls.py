from django.urls import path
from .views import *

urlpatterns = [
    path('folder/', FolderView.as_view(
        {"get": "list", "post": "create"}
    )),
    path('folder/<str:pk>/', FolderView.as_view(
        {"get": "retrieve", "delete": "destroy", "put": "update"}
    )),
    path('document/', DocumentView.as_view(
        {"get": "list", "post": "create"}
    )),
    path('document/<str:pk>/', DocumentView.as_view(
        {"get": "retrieve", "delete": "destroy", "put": "update"}
    )),
    path('document/revision/<str:doc_id>/', RevisionView.as_view(
        {"get": "list"}
    )),
    path('document/revision/<str:doc_id>/<str:version_id>/', RevisionView.as_view(
        {"get": "retrieve", "post": "create"}
    )),
    path('permission/', PermissionView.as_view(
        {"get": "list", "post": "create"}
    )),
    path('permission/<str:pk>/', PermissionView.as_view(
        {"get": "retrieve", "delete": "destroy", "put": "update"}
    )),
    path('share/<str:token>/', ShareableLinkView.as_view(

    ))
]
