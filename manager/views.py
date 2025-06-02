from django.db.models import Q
from django.http import FileResponse, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from reversion.models import Version
import os
import tempfile

from .permissions import *
from .serializers import *
from .document_converter import DocumentConverter
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

    @action(detail=True, methods=['get'])
    def content(self, request, pk=None):
        """Get document content as HTML or Markdown for editing"""
        document = self.get_object()
        
        if not document.file:
            return Response({'error': 'No file associated with document'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        file_path = document.file.path
        if not os.path.exists(file_path):
            return Response({'error': 'File not found'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        # Get the requested format (default to html)
        format_type = request.query_params.get('format', 'html').lower()
        
        try:
            if document.file.name.endswith('.docx'):
                html_content, markdown_content = DocumentConverter.convert_for_editor(file_path)
                
                if format_type == 'markdown':
                    return Response({
                        'content': markdown_content,
                        'format': 'markdown',
                        'original_format': 'docx'
                    })
                else:
                    return Response({
                        'content': html_content,
                        'format': 'html',
                        'original_format': 'docx'
                    })
            else:
                # For non-DOCX files, return raw content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return Response({
                    'content': content,
                    'format': 'raw',
                    'original_format': document.file.name.split('.')[-1].lower()
                })
                
        except Exception as e:
            return Response({'error': f'Error reading document: {str(e)}'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['put'])
    def update_content(self, request, pk=None):
        """Update document content from editor"""
        document = self.get_object()
        
        content = request.data.get('content', '')
        content_type = request.data.get('content_type', 'html')
        
        if not document.file:
            return Response({'error': 'No file associated with document'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        file_path = document.file.path
        
        try:
            if document.file.name.endswith('.docx'):
                # Convert content back to DOCX
                success = DocumentConverter.convert_from_editor(content, content_type, file_path)
                if not success:
                    return Response({'error': 'Failed to convert content to DOCX'}, 
                                  status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                # For other file types, save content directly
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Update the document's updated_at timestamp
            document.save()
            
            return Response({'message': 'Document updated successfully'})
            
        except Exception as e:
            return Response({'error': f'Error updating document: {str(e)}'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

class ShareableLinkView(ModelViewSet):
    queryset = ShareableLink.objects.all()
    serializer_class = ShareableLinkSerializer
    permission_classes = [IsAuthenticated]

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