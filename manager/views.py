from django.db.models import Q
from django.http import FileResponse, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from reversion.models import Version
import os
import tempfile
import json
import zipfile
from django.utils import timezone
from datetime import datetime
from django.contrib.auth import get_user_model
import reversion
from django.core.files.base import ContentFile

from .permissions import (
    HasFolderDocumentPermission, HasActivityTrackingPermission, has_permission
)
from .models import Folder, Document, ActivityLog, ShareableLink, ACTIVITY_TYPES, Permission, Comment
from .serializers import (
    FolderSerializer, DocumentSerializer, ActivityLogSerializer, ShareableLinkSerializer, CommentSerializer
)
from .document_converter import DocumentConverter
from reversion.views import RevisionMixin

User = get_user_model()

class FolderView(ModelViewSet, RevisionMixin):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated, HasFolderDocumentPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_context(self):
        return {'request': self.request}

    def perform_create(self, serializer):
        with reversion.create_revision():
            folder = serializer.save(owner=self.request.user)
            reversion.set_user(self.request.user)
            reversion.set_comment(f"Created folder: {folder.name}")
            
            # Log folder creation activity
            ActivityLog.log_activity(
                document=None,
                user=self.request.user,
                activity_type='create',
                request=self.request,
                resource_type='folder',
                resource_name=folder.name
            )

    def perform_update(self, serializer):
        old_name = serializer.instance.name
        old_parent = serializer.instance.parent
        
        with reversion.create_revision():
            folder = serializer.save()
            reversion.set_user(self.request.user)
            reversion.set_comment(f"Updated folder: {folder.name}")
            
            # Log folder update activity
            metadata = {}
            if old_name != folder.name:
                metadata['old_name'] = old_name
                metadata['new_name'] = folder.name
            if old_parent != folder.parent:
                metadata['old_parent'] = old_parent.name if old_parent else None
                metadata['new_parent'] = folder.parent.name if folder.parent else None
            
            ActivityLog.log_activity(
                document=None,
                user=self.request.user,
                activity_type='edit',
                request=self.request,
                resource_type='folder',
                resource_name=folder.name,
                **metadata
            )

    def perform_destroy(self, instance):
        with reversion.create_revision():
            folder_name = instance.name
            instance.delete()
            reversion.set_user(self.request.user)
            reversion.set_comment(f"Deleted folder: {folder_name}")
            
            # Log folder deletion activity
            ActivityLog.log_activity(
                document=None,
                user=self.request.user,
                activity_type='delete',
                request=self.request,
                resource_type='folder',
                resource_name=folder_name
            )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(
            Q(owner=self.request.user) |
            Q(id__in=Permission.objects.filter(user=request.user, folder__isnull=False).values('folder'))).distinct()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def upload_folder(self, request):
        """
        Upload a folder as a zip file and extract its contents
        """
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No zip file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        zip_file = request.FILES['file']
        parent_folder_id = request.data.get('parent')
        
        # Validate zip file
        if not zip_file.name.endswith('.zip'):
            return Response(
                {'error': 'File must be a zip archive'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create parent folder if specified
            parent_folder = None
            if parent_folder_id:
                try:
                    parent_folder = Folder.objects.get(id=parent_folder_id, owner=request.user)
                except Folder.DoesNotExist:
                    return Response(
                        {'error': 'Parent folder not found'}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Create main folder with zip file name (without extension)
            folder_name = os.path.splitext(zip_file.name)[0]
            main_folder = Folder.objects.create(
                name=folder_name,
                parent=parent_folder,
                owner=request.user
            )
            
            # Extract zip file
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, 'upload.zip')
                
                # Save uploaded zip to temporary location
                with open(zip_path, 'wb') as f:
                    for chunk in zip_file.chunks():
                        f.write(chunk)
                
                # Extract and process zip contents
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Get all file paths
                    file_list = zip_ref.namelist()
                    
                    # Create folder structure
                    folder_mapping = {'/': main_folder}  # Root maps to main folder
                    
                    # First pass: create all folders
                    for file_path in file_list:
                        if file_path.endswith('/'):  # It's a directory
                            self._create_folder_structure(file_path, folder_mapping, request.user, main_folder)
                    
                    # Second pass: create documents
                    for file_path in file_list:
                        if not file_path.endswith('/'):  # It's a file
                            self._create_document_from_zip(zip_ref, file_path, folder_mapping, request.user, main_folder)
            
            # Log folder upload activity
            ActivityLog.log_activity(
                document=None,
                user=request.user,
                activity_type='upload',
                request=request,
                resource_type='folder',
                resource_name=main_folder.name,
                zip_file_name=zip_file.name
            )
            
            # Return the created folder
            serializer = self.get_serializer(main_folder)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except zipfile.BadZipFile:
            return Response(
                {'error': 'Invalid zip file'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error processing zip file: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _create_folder_structure(self, folder_path, folder_mapping, owner, root_folder):
        """
        Create folder structure recursively
        """
        # Remove trailing slash
        folder_path = folder_path.rstrip('/')
        if not folder_path:
            return
        
        # Split path into components
        path_parts = folder_path.split('/')
        current_path = ''
        current_parent = root_folder
        
        for part in path_parts:
            if not part:  # Skip empty parts
                continue
                
            current_path = current_path + '/' + part if current_path else part
            
            if current_path not in folder_mapping:
                # Create new folder
                folder = Folder.objects.create(
                    name=part,
                    parent=current_parent,
                    owner=owner
                )
                folder_mapping[current_path] = folder
                current_parent = folder
            else:
                current_parent = folder_mapping[current_path]
    
    def _create_document_from_zip(self, zip_ref, file_path, folder_mapping, owner, root_folder):
        """
        Create document from zip file entry
        """
        # Get the folder for this file
        folder_path = '/'.join(file_path.split('/')[:-1])
        if folder_path and folder_path in folder_mapping:
            parent_folder = folder_mapping[folder_path]
        else:
            parent_folder = root_folder
        
        # Get file name
        file_name = os.path.basename(file_path)
        
        # Skip hidden files and system files
        if file_name.startswith('.') or file_name.startswith('__'):
            return
        
        # Check if file extension is supported
        valid_extensions = ['.csv', '.docx', '.pdf']
        file_ext = os.path.splitext(file_name)[1].lower()
        if file_ext not in valid_extensions:
            return  # Skip unsupported files
        
        try:
            # Extract file content
            file_content = zip_ref.read(file_path)
            
            # Create document
            document = Document.objects.create(
                name=file_name,
                folder=parent_folder,
                owner=owner
            )
            
            # Save file
            file_obj = ContentFile(file_content, name=f"{document.id}{file_ext}")
            document.file.save(f"{document.id}{file_ext}", file_obj)
            document.save()
            
        except Exception as e:
            # Log error but continue processing other files
            print(f"Error creating document {file_name}: {str(e)}")


class DocumentView(ModelViewSet, RevisionMixin):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, HasFolderDocumentPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_context(self):
        return {'request': self.request}

    def perform_create(self, serializer):
        serializer.validated_data['owner'] = self.request.user
        document = serializer.save()
        
        # Log document creation activity
        ActivityLog.log_activity(
            document=document,
            user=self.request.user,
            activity_type='create',
            request=self.request,
            file_type=document.file.name.split('.')[-1].lower() if document.file else 'empty',
            folder=document.folder.name if document.folder else 'Root'
        )

    def perform_update(self, serializer):
        old_name = serializer.instance.name
        old_folder = serializer.instance.folder
        document = serializer.save()
        
        # Log document rename activity
        if old_name != document.name:
            ActivityLog.log_activity(
                document=document,
                user=self.request.user,
                activity_type='rename',
                request=self.request,
                old_name=old_name,
                new_name=document.name
            )
        
        # Log document move activity
        if old_folder != document.folder:
            ActivityLog.log_activity(
                document=document,
                user=self.request.user,
                activity_type='move',
                request=self.request,
                old_folder=old_folder.name if old_folder else 'Root',
                new_folder=document.folder.name if document.folder else 'Root'
            )

    def perform_destroy(self, instance):
        # Log document deletion activity
        ActivityLog.log_activity(
            document=instance,
            user=self.request.user,
            activity_type='delete',
            request=self.request,
            file_type=instance.file.name.split('.')[-1].lower() if instance.file else 'empty'
        )
        instance.delete()

    def retrieve(self, request, *args, **kwargs):
        document = self.get_object()
        
        # Log document view activity
        ActivityLog.log_activity(
            document=document,
            user=request.user,
            activity_type='view',
            request=request,
            action='retrieve_metadata'
        )
        
        return super().retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        # Get base queryset with permissions
        queryset = self.get_queryset().filter(
            Q(owner=self.request.user) |
            Q(id__in=Permission.objects.filter(user=request.user, document__isnull=False).values('document'))).distinct()
        
        # Filter by folder if specified
        folder_id = request.query_params.get('folder')
        if folder_id:
            queryset = queryset.filter(folder__id=folder_id)
        
        # Filter by search query if specified
        search_query = request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def annotations(self, request, pk=None):
        """Get PDF annotations"""
        document = self.get_object()
        
        # For now, store annotations as JSON in a separate field or file
        # In production, you might want a separate Annotation model
        annotations_file = os.path.join(
            os.path.dirname(document.file.path),
            f"{document.id}_annotations.json"
        )
        
        if request.method == 'GET':
            # Log annotation view activity
            ActivityLog.log_activity(
                document=document,
                user=request.user,
                activity_type='view',
                request=request,
                action='view_annotations'
            )
            
            try:
                if os.path.exists(annotations_file):
                    with open(annotations_file, 'r', encoding='utf-8') as f:
                        annotations = json.load(f)
                else:
                    annotations = {'drawings': [], 'notes': []}
                return Response(annotations)
            except Exception as e:
                return Response({'error': f'Error loading annotations: {str(e)}'}, 
                              status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        elif request.method == 'PUT':
            # Log annotation edit activity
            ActivityLog.log_activity(
                document=document,
                user=request.user,
                activity_type='edit',
                request=request,
                action='update_annotations',
                drawings_count=len(request.data.get('drawings', [])),
                notes_count=len(request.data.get('notes', []))
            )
            
            try:
                annotations = {
                    'drawings': request.data.get('drawings', []),
                    'notes': request.data.get('notes', []),
                    'updated_at': timezone.now().isoformat(),
                }
                
                os.makedirs(os.path.dirname(annotations_file), exist_ok=True)
                with open(annotations_file, 'w', encoding='utf-8') as f:
                    json.dump(annotations, f, indent=2)
                
                return Response({'message': 'Annotations saved successfully'})
            except Exception as e:
                return Response({'error': f'Error saving annotations: {str(e)}'}, 
                              status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download document file"""
        document = self.get_object()
        
        # Log document download activity
        ActivityLog.log_activity(
            document=document,
            user=request.user,
            activity_type='download',
            request=request,
            file_type=document.file.name.split('.')[-1].lower() if document.file else 'empty'
        )
        
        if not document.file or not os.path.exists(document.file.path):
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return FileResponse(
            open(document.file.path, 'rb'),
            as_attachment=True,
            filename=document.name + os.path.splitext(document.file.name)[1]
        )

    @action(detail=True, methods=['get'])
    def convert_docx_to_pdf(self, request, pk=None):
        import logging
        import traceback

        logger = logging.getLogger(__name__)
        """Convert DOCX document to PDF and return the PDF file"""
        document = self.get_object()
        
        # Check if document is DOCX
        if not document.file or not document.file.name.lower().endswith('.docx'):
            return Response(
                {'error': 'Document is not a DOCX file'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Log conversion activity
        ActivityLog.log_activity(
            document=document,
            user=request.user,
            activity_type='view',
            request=request,
            action='convert_docx_to_pdf'
        )
        
        if not document.file or not os.path.exists(document.file.path):
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Create temporary PDF file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
            # Convert DOCX to PDF
            success = DocumentConverter.docx_to_pdf(document.file.path, temp_pdf_path)
            
            if not success:
                os.unlink(temp_pdf_path)
                return Response(
                    {'error': 'Failed to convert document to PDF'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Read the converted PDF
            with open(temp_pdf_path, 'rb') as f:
                pdf_content = f.read()
            
            # Clean up temporary file
            os.unlink(temp_pdf_path)
            
            # Return PDF file response
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{document.name.replace(".docx", ".pdf")}"'
            response['Content-Length'] = len(pdf_content)
            
            return response
            
        except Exception as e:
            logger.exception("Error converting DOCX to PDF")  # <-- prints full traceback
            print(f"Error converting DOCX to PDF: {e}")       # <-- still goes to stdout
            traceback.print_exc() 
            return Response(
                {'error': f'Conversion failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ActivityLogView(ModelViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated, HasActivityTrackingPermission]
    
    def get_queryset(self):
        """Filter activity logs based on user permissions"""
        user = self.request.user
        
        if user.is_superuser:
            return self.queryset
        
            
        # # 1) IDs of docs the user owns
        # owned_ids = Document.objects.filter(owner=user) \
        #                             .values_list('id', flat=True)

        # # 2) IDs of docs the user has track/delete perms on
        # permitted_ids = Permission.objects.filter(
        #     user=user,
        #     level__in=['track', 'delete'],
        #     document__isnull=False
        # ).values_list('document_id', flat=True)

        # # 3) Union those two sets of IDs
        # accessible_ids = owned_ids.union(permitted_ids)

        # # 4) Filter ActivityLog by document_id IN that single-column subquery
        # return self.queryset.filter(
        #     Q(document__id__in=accessible_ids) |
        #     Q(user=user, document__isnull=True)
        # )
        return self.queryset.filter(
            Q(document__owner=user) |
            Q(document__permission__user=user,
            document__permission__level__in=['track','delete']) |
            Q(user=user, document__isnull=True)
        ).distinct()
    
    def list(self, request, *args, **kwargs):
        """List activity logs with filtering options"""
        queryset = self.get_queryset()
        
        # Apply filters
        document_id = request.query_params.get('document_id')
        if document_id:
            queryset = queryset.filter(document__id=document_id)
        
        activity_type = request.query_params.get('activity_type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        user_filter = request.query_params.get('user')
        if user_filter:
            try:
                # Try to filter by user ID first, then by username
                queryset = queryset.filter(
                    Q(user__id=user_filter) | Q(user__username__icontains=user_filter)
                )
            except ValueError:
                queryset = queryset.filter(user__username__icontains=user_filter)
        
        start_date = request.query_params.get('start_date')
        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date)
                queryset = queryset.filter(timestamp__gte=start_datetime)
            except ValueError:
                pass
        
        end_date = request.query_params.get('end_date')
        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date)
                queryset = queryset.filter(timestamp__lte=end_datetime)
            except ValueError:
                pass
        
        ip_address = request.query_params.get('ip_address')
        if ip_address:
            queryset = queryset.filter(ip_address=ip_address)
        
        # Filter by resource type
        resource_type = request.query_params.get('resource_type')
        if resource_type == 'document':
            queryset = queryset.filter(document__isnull=False)
        elif resource_type == 'folder':
            queryset = queryset.filter(document__isnull=True, metadata__resource_type='folder')
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def document_activity(self, request):
        """Get activity logs for a specific document"""
        document_id = request.query_params.get('document_id')
        if not document_id:
            return Response(
                {'error': 'document_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            document = Document.objects.get(id=document_id)
            
            # Check if user has permission to view this document's activity logs
            # Document owners should automatically have access
            if document.owner != request.user and not has_permission(request.user, document=document, required_level='track'):
                raise PermissionDenied("You don't have permission to view activity logs for this document.")
            
            queryset = self.get_queryset().filter(document=document)
            
            # Apply additional filters
            activity_type = request.query_params.get('activity_type')
            if activity_type:
                queryset = queryset.filter(activity_type=activity_type)
            
            limit = request.query_params.get('limit')
            if limit:
                try:
                    limit_int = int(limit)
                    queryset = queryset[:limit_int]
                except ValueError:
                    pass
            
            # Pagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
            
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def folder_activity(self, request):
        """Get activity logs for folder operations by the current user"""
        queryset = self.get_queryset().filter(document__isnull=True, user=request.user)
        
        # Apply additional filters
        activity_type = request.query_params.get('activity_type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        folder_id = request.query_params.get('folder_id')
        if folder_id:
            queryset = queryset.filter(metadata__resource_id=folder_id)
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def user_activity(self, request):
        """Get activity logs for a specific user (admin only)"""
        if not request.user.is_superuser:
            raise PermissionDenied("Only administrators can view user activity logs.")
        
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            queryset = self.queryset.filter(user=user)
            
            # Pagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get activity statistics"""
        queryset = self.get_queryset()
        
        # Filter by document if specified
        document_id = request.query_params.get('document_id')
        if document_id:
            try:
                document = Document.objects.get(id=document_id)
                
                # Check if user has permission to view this document's activity stats
                # Document owners should automatically have access
                if document.owner != request.user and not has_permission(request.user, document=document, required_level='track'):
                    raise PermissionDenied("You don't have permission to view activity stats for this document.")
                
                queryset = queryset.filter(document__id=document_id)
            except Document.DoesNotExist:
                return Response(
                    {'error': 'Document not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Filter by resource type if specified
        resource_type = request.query_params.get('resource_type')
        if resource_type == 'document':
            queryset = queryset.filter(document__isnull=False)
        elif resource_type == 'folder':
            queryset = queryset.filter(document__isnull=True, metadata__resource_type='folder')
        
        # Calculate statistics
        total_activities = queryset.count()
        activity_counts = {}
        
        for activity_type, _ in ACTIVITY_TYPES:
            count = queryset.filter(activity_type=activity_type).count()
            activity_counts[activity_type] = count
        
        # Most active users
        from django.db.models import Count
        top_users = queryset.values('user__username').annotate(
            activity_count=Count('id')
        ).order_by('-activity_count')[:10]
        
        # Recent activities (last 24 hours)
        from django.utils import timezone
        from datetime import timedelta
        
        yesterday = timezone.now() - timedelta(days=1)
        recent_activities = queryset.filter(timestamp__gte=yesterday).count()
        
        return Response({
            'total_activities': total_activities,
            'recent_activities_24h': recent_activities,
            'activity_counts': activity_counts,
            'top_users': list(top_users)
        })
    
    def create(self, request, *args, **kwargs):
        """Disable manual creation of activity logs"""
        return Response(
            {'error': 'Activity logs are created automatically and cannot be manually created.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def update(self, request, *args, **kwargs):
        """Disable updating of activity logs"""
        return Response(
            {'error': 'Activity logs cannot be modified.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        """Only allow superusers to delete activity logs"""
        if not request.user.is_superuser:
            raise PermissionDenied("Only administrators can delete activity logs.")
        return super().destroy(request, *args, **kwargs)


class RevisionView(ModelViewSet):
    queryset = Version.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, HasFolderDocumentPermission]

    def get_document(self, doc_id):
        document = get_object_or_404(
            Document.objects.filter(
                Q(owner=self.request.user) |
                Q(id__in=Permission.objects.filter(
                    user=self.request.user, document__isnull=False
                ).values('document'))
            ).distinct(),
            pk=doc_id
        )
        return document

    def create(self, request, *args, **kwargs):
        document = self.get_document(request.query_params.get('doc_id'))
        versions = Version.objects.get_for_object(document)
        version = get_object_or_404(versions, pk=request.query_params.get('version_id'))
        version.revision.revert()

        # Log document restore activity
        ActivityLog.log_activity(
            document=document,
            user=request.user,
            activity_type='restore',
            request=request,
            version_id=str(version.id),
            version_date=version.revision.date_created.isoformat() if version.revision.date_created else None
        )

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




class ShareableLinkView(ModelViewSet):
    queryset = ShareableLink.objects.all()
    serializer_class = ShareableLinkSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        # DRF sets self.action to the name of the handler ("retrieve_by_token")
        if self.action == 'retrieve_by_token':
            return [AllowAny()]
        return [perm() for perm in self.permission_classes]

    def perform_create(self, serializer):
        link = serializer.save(created_by=self.request.user)
        
        # Log share activity for document only
        ActivityLog.log_activity(
            document=link.document,
            user=self.request.user,
            activity_type='share',
            request=self.request,
            share_token=str(link.token),
            expires_at=link.expires_at.isoformat() if link.expires_at else None
        )
    
    @action(detail=False, methods=["get"])
    def retrieve_by_token(self, request, token):
        """Retrieve shared document by token for public access"""
        try:
            link = get_object_or_404(ShareableLink, token=token, is_active=True)
            
            # Check if link is still valid
            if not link.is_valid():
                return Response({'error': 'Link has expired or is inactive'}, 
                              status=status.HTTP_403_FORBIDDEN)
            
            # Log view activity (anonymous access allowed for shared links)
            ActivityLog.log_activity(
                document=link.document,
                user=request.user if request.user.is_authenticated else None,
                activity_type='view',
                request=request,
                share_token=str(link.token)
            )
            
            # Return file if document has one, otherwise document data
            if link.document.file and os.path.exists(link.document.file.path):
                return FileResponse(
                    open(link.document.file.path, 'rb'),
                    as_attachment=True,
                    filename=link.document.name
                )
            else:
                # Fallback to document data if no file
                from .serializers import DocumentSerializer
                return Response(DocumentSerializer(link.document).data)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CommentView(ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Filter comments based on document permissions
        user = self.request.user
        # Get documents the user has access to
        accessible_documents = Document.objects.filter(
            Q(owner=user) |
            Q(id__in=Permission.objects.filter(user=user, document__isnull=False).values('document'))
        ).distinct()
        
        # Return comments for accessible documents only
        return Comment.objects.filter(document__in=accessible_documents)
    
    def perform_create(self, serializer):
        comment = serializer.save(user=self.request.user)
        
        # Log comment creation activity
        ActivityLog.log_activity(
            document=comment.document,
            user=self.request.user,
            activity_type='create',
            request=self.request,
            resource_type='comment',
            resource_name=f"Comment on {comment.document.name}"
        )
    
    def perform_update(self, serializer):
        comment = serializer.save()
        
        # Log comment update activity
        ActivityLog.log_activity(
            document=comment.document,
            user=self.request.user,
            activity_type='edit',
            request=self.request,
            resource_type='comment',
            resource_name=f"Comment on {comment.document.name}"
        )
    
    def perform_destroy(self, instance):
        document = instance.document
        comment_info = f"Comment on {document.name}"
        
        # Log comment deletion activity
        ActivityLog.log_activity(
            document=document,
            user=self.request.user,
            activity_type='delete',
            request=self.request,
            resource_type='comment',
            resource_name=comment_info
        )
        
        instance.delete()
    
    @action(detail=False, methods=['get'])
    def document_comments(self, request):
        """
        Get all comments for a specific document
        """
        document_id = request.query_params.get('document_id')
        if not document_id:
            return Response(
                {'error': 'document_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Check if user has access to the document
            document = Document.objects.get(id=document_id)
            if not has_permission(request.user, document=document, required_level='read'):
                raise PermissionDenied("You don't have permission to view comments for this document")
            
            # Get top-level comments for the document (comments without parent)
            comments = Comment.objects.filter(document=document, parent__isnull=True)
            serializer = self.get_serializer(comments, many=True)
            return Response(serializer.data)
            
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )