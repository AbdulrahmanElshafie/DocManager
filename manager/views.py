from django.db.models import Q
from django.http import FileResponse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from .permissions import *
from .serializers import *


class FolderView(ModelViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    permission_classes = [HasFolderDocumentPermission]

    def perform_create(self, serializer):
        serializer.validated_data['owner'] = self.request.user
        super().perform_create(serializer)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(
            Q(owner=self.request.user) |
            Q(id__in=Permission.objects.filter(user=request.user, folder__isnull=False).values('folder'))).distinct()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class DocumentView(ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [HasFolderDocumentPermission]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.validated_data['owner'] = self.request.user
        super().perform_create(serializer)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(
            Q(owner=self.request.user) |
            Q(id__in=Permission.objects.filter(user=request.user, document__isnull=False).values('document'))).distinct()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class PermissionView(ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsOwnerOrHasPermission]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(
            Q(user=request.user) |
            Q(document__owner=request.user) |
            Q(folder__owner=request.user)
        ).distinct()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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