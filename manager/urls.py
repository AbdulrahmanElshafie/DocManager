from django.urls import path
from .views import (
    FolderView, DocumentView, RevisionView, ActivityLogView, ShareableLinkView
)

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
    path('document/<str:pk>/content/', DocumentView.as_view(
        {"get": "content", "put": "update_content"}
    )),
    path('document/<str:pk>/annotations/', DocumentView.as_view(
        {"get": "annotations", "put": "annotations"}
    )),
    path('document/<str:pk>/download/', DocumentView.as_view(
        {"get": "download"}
    )),
    path('document/revision/<str:doc_id>/', RevisionView.as_view(
        {"get": "list"}
    )),
    path('document/revision/<str:doc_id>/<str:version_id>/', RevisionView.as_view(
        {"get": "retrieve", "post": "create"}
    )),

    
    # Activity tracking endpoints
    path('activity/document/', ActivityLogView.as_view(
        {"get": "document_activity"}
    )),
    path('activity/folder/', ActivityLogView.as_view(
        {"get": "folder_activity"}
    )),
    path('activity/user/', ActivityLogView.as_view(
        {"get": "user_activity"}
    )),
    path('activity/stats/', ActivityLogView.as_view(
        {"get": "stats"}
    )),
    path('activity/', ActivityLogView.as_view(
        {"get": "list"}
    )),
    path('activity/<str:pk>/', ActivityLogView.as_view(
        {"get": "retrieve", "delete": "destroy"}
    )),
    
    path('share/<str:token>/', ShareableLinkView.as_view(
        {"get": "retrieve"}
    )),
    path('share/', ShareableLinkView.as_view(
        {"post": "create", "get": "list"}
    )),
    path('share/<str:pk>/', ShareableLinkView.as_view(
        {"delete": "destroy", "put": "update"}
    )),
]
