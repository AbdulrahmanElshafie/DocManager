from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from reversion.models import Version

from .permissions import *
from .serializers import *
from reversion.views import RevisionMixin

class FolderView(ModelViewSet, RevisionMixin):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated, HasFolderDocumentPermission]


    def perform_create(self, serializer):
        serializer.validated_data['owner'] = self.request.user
        super().perform_create(serializer)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(
            Q(owner=self.request.user) |
            Q(id__in=Permission.objects.filter(user=request.user, folder__isnull=False).values('folder'))).distinct()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class DocumentView(ModelViewSet, RevisionMixin):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, HasFolderDocumentPermission]
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


class RevisionView(ModelViewSet):
    queryset = Version.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, HasFolderDocumentPermission]

    def get_document(self, doc_id):
        return get_object_or_404(
            Document.objects.filter(
                Q(owner=self.request.user) |
                Q(id__in=Permission.objects.filter(
                    user=self.request.user, document__isnull=False
                ).values('document'))
            ).distinct(),
            pk=doc_id
        )

    def create(self, request, *args, **kwargs):
        document = self.get_document(request.query_params.get('doc_id'))
        versions = Version.objects.get_for_object(document)
        version = get_object_or_404(versions, pk=request.query_params.get('version_id'))
        version.revision.revert()

        serializer = self.get_serializer(version.object)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        document = self.get_document(request.query_params.get('doc_id'))
        versions = Version.objects.get_for_object(document)

        docs = [version.object for version in versions]
        serializer = self.get_serializer(docs, many=True)
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        document = self.get_document(request.query_params.get('doc_id'))
        versions = Version.objects.get_for_object(document)
        version = get_object_or_404(versions, pk=request.query_params.get('version_id'))

        serializer = self.get_serializer(version.object)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

class GetRevisionDocumentView(APIView):
    permission_classes = [IsAuthenticated, HasFolderDocumentPermission]

    def get(self, request, *args, **kwargs):
        doc = Document.objects.get(pk=kwargs['pk'])
        versions = Version.objects.get_for_object(doc)

        # Filter revisions where the file changed
        revision_objs = [
            version.object
            for version in versions
            if 'File' in version.revision.get_comment()
        ]

        serializer = DocumentSerializer(revision_objs, many=True)
        return Response(serializer.data)

class PermissionView(ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrHasPermission]

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