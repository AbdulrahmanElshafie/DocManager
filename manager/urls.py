from django.urls import path
from .views import (
    FolderView, DocumentView, RevisionView, ActivityLogView, ShareableLinkView, CommentView
)

urlpatterns = [
    path('folder/', FolderView.as_view(
        {"get": "list", "post": "create"}
    )),
    path('folder/upload/', FolderView.as_view(
        {"post": "upload_folder"}
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
    path('document/<str:pk>/annotations/', DocumentView.as_view(
        {"get": "annotations"}
    )),
    path('document/<str:pk>/download/', DocumentView.as_view(
        {"get": "download"}
    )),

    # Revision endpoints
    path('document/revision/<str:doc_id>/', RevisionView.as_view(
        {"get": "list", "post": "create"}
    )),
    path('document/revision/<str:doc_id>/<str:version_id>/', RevisionView.as_view(
        {"get": "retrieve"}
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
        {"get": "retrieve_by_token"}
    )),
    path('share/', ShareableLinkView.as_view(
        {"post": "create", "get": "list"}
    )),
    path('share/<str:pk>/', ShareableLinkView.as_view(
        {"delete": "destroy", "put": "update"}
    )),
    
    # Comment endpoints
    path('comment/', CommentView.as_view(
        {"get": "list", "post": "create"}
    )),
    path('comment/<str:pk>/', CommentView.as_view(
        {"get": "retrieve", "delete": "destroy", "put": "update"}
    )),
    path('comment/document/', CommentView.as_view(
        {"get": "document_comments"}
    )),
]
