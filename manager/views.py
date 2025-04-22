import shutil

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from DocManager.settings import MEDIA_ROOT
from .helpers import get_folder_path
from .permissions import HasFolderPermission
from .serializers import *


class FolderView(ModelViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    permission_classes = [HasFolderPermission]

    def perform_create(self, serializer):
        folder_path = get_folder_path(serializer.instance)
        serializer.validated_data['owner'] = self.request.user
        serializer.validated_data['path'] = folder_path
        super().perform_create(serializer)
        os.makedirs(os.path.join(MEDIA_ROOT, serializer.instance.owner.username, folder_path), exist_ok=True)

    def perform_destroy(self, instance):
        if os.path.exists(os.path.join(MEDIA_ROOT, instance.owner.username, instance.path)):
            shutil.rmtree((os.path.join(MEDIA_ROOT, instance.owner.username, instance.path)))

        super().perform_destroy(instance)



class DocumentView(ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [HasFolderPermission]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.validated_data['owner'] = self.request.user
        super().perform_create(serializer)

class ShareableLinkView(APIView):
    def get(self, request, token):
        link = get_object_or_404(ShareableLink, token=token, is_active=True, expires_at__gte=timezone.now())

        if not link.is_valid():
            return Response(
                {"error": "Invalid or expired shareable link."},
                status=status.HTTP_404_NOT_FOUND)

        document = link.document
        if not document:
            return Response(
                {"error": "Invalid shareable link."},
                status=status.HTTP_404_NOT_FOUND)

        file_path = document.file.path
        if not os.path.exists(file_path):
            return Response(
                {"error": "File not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        return FileResponse(open(file_path, 'rb'), as_attachment=True)