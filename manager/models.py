import os
import shutil

from django.db import models, transaction
from django.contrib.auth import get_user_model
from uuid import uuid4
from django.utils import timezone
from django.core.exceptions import ValidationError

from DocManager.settings import MEDIA_ROOT
import reversion

User = get_user_model()

@reversion.register(ignore_duplicates=True)
class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100, default="New Folder")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Folder'
        verbose_name_plural = 'Folders'




def document_upload_path(instance, filename):
    # Always use the document ID as the folder and file name
    return os.path.join(
        str(instance.id),  # Folder name is the document ID
        f"{instance.id}{os.path.splitext(filename)[1]}"  # File name is also the document ID with original extension
    )


TYPE = (
    ("csv", "CSV"),
    ("docx", "Docx"),
    ("pdf", "PDF"),
)

def validate_file_extension(value):
    if value:  # Only validate if file is provided
        ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
        valid_extensions = ['.csv', '.docx', '.pdf']
        if not ext.lower() in valid_extensions:
            raise ValidationError('Unsupported file extension.')

@reversion.register(ignore_duplicates=True)
class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100, default="New Document")
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(
        upload_to=document_upload_path, 
        validators=[validate_file_extension], 
        max_length=500,
        blank=True,
        null=True
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        if os.path.exists(os.path.join(MEDIA_ROOT, f"{self.id}")):
            shutil.rmtree(os.path.join(MEDIA_ROOT, f"{self.id}"))

        super().delete(using, keep_parents)

LEVEL_CHOICES = (
    ('read', 'Read'),
    ('write', 'Write'),
    ('delete', 'Delete'),
    ('track', 'Track'),  # New permission level for viewing activity logs
)

class Permission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    document = models.ForeignKey(Document, null=True, blank=True, on_delete=models.CASCADE)
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.CASCADE)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)

    class Meta:
        unique_together = ('user', 'document', 'folder')

    def __str__(self):
        target = self.document.name if self.document else (self.folder.name if self.folder else "Unknown")
        return f"{self.user.username} - {target} - {self.level}"

    def clean(self):
        # Must specify exactly one of document or folder
        if bool(self.document) == bool(self.folder):
            raise ValidationError("Specify either `document` or `folder`, but not both.")

    def save(self, *args, **kwargs):
        self.clean()
        # Only propagate permissions if this is a folder permission
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.folder:
                # Propagate to child folders
                for folder in Folder.objects.filter(parent=self.folder):
                    Permission.objects.update_or_create(
                        user=self.user,
                        folder=folder,
                        defaults={'level': self.level, 'document': None}
                    )
                # Propagate to documents in this folder
                for document in Document.objects.filter(folder=self.folder):
                    Permission.objects.update_or_create(
                        user=self.user,
                        document=document,
                        defaults={'level': self.level, 'folder': None}
                    )

    def delete(self, using=None, keep_parents=False):
        with transaction.atomic():
            if self.folder:
                # Remove permissions from child folders
                for permission in Permission.objects.filter(user=self.user, folder__parent=self.folder):
                    permission.delete()
                # Remove permissions from documents in this folder
                for permission in Permission.objects.filter(user=self.user, document__folder=self.folder):
                    permission.delete()

            super().delete(using, keep_parents)

class ShareableLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    document = models.ForeignKey('Document', on_delete=models.CASCADE, related_name='share_links')
    token = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('shared-document-view', args=[str(self.token)])

    def clean(self):
        # Document is required
        if not self.document:
            raise ValidationError("Document is required for shareable links.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Shared link for document: {self.document.name}"


ACTIVITY_TYPES = (
    ('view', 'Document Viewed'),
    ('edit', 'Document Edited'),
    ('create', 'Document Created'),
    ('delete', 'Document Deleted'),
    ('download', 'Document Downloaded'),
    ('upload', 'Document Uploaded'),
    ('share', 'Document Shared'),
    ('permission_change', 'Permission Changed'),
    ('restore', 'Document Restored'),
    ('rename', 'Document Renamed'),
    ('move', 'Document Moved'),
    ('websocket_connect', 'Real-time Edit Connected'),
    ('websocket_disconnect', 'Real-time Edit Disconnected'),
    ('auto_save', 'Auto Save'),
    ('manual_save', 'Manual Save'),
)


class ActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='activity_logs', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Null for anonymous access
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Additional tracking data
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Metadata for storing additional information
    metadata = models.JSONField(default=dict, blank=True)
    
    # Description for human-readable activity description
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['document', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['activity_type', '-timestamp']),
        ]

    def __str__(self):
        user_display = self.user.username if self.user else 'Anonymous'
        resource = self.document.name if self.document else self.metadata.get('resource_name', 'Unknown Resource')
        return f"{user_display} - {self.get_activity_type_display()} - {resource} - {self.timestamp}"

    @classmethod
    def log_activity(cls, document=None, user=None, activity_type='view', request=None, **kwargs):
        """
        Convenience method to log document and folder activities
        
        Args:
            document: Document instance (optional for folder activities)
            user: User instance (optional)
            activity_type: Type of activity from ACTIVITY_TYPES
            request: HTTP request object (optional)
            **kwargs: Additional metadata
        """
        log_data = {
            'document': document,
            'user': user,
            'activity_type': activity_type,
        }
        
        # Extract request information if available
        if request:
            log_data['ip_address'] = cls._get_client_ip(request)
            log_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
            log_data['session_id'] = request.session.session_key
        
        # Add metadata
        if kwargs:
            log_data['metadata'] = kwargs
            
        # Generate description
        log_data['description'] = cls._generate_description(
            document, user, activity_type, kwargs
        )
        
        return cls.objects.create(**log_data)
    
    @staticmethod
    def _get_client_ip(request):
        """Extract the real client IP address from the request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def _generate_description(document, user, activity_type, metadata):
        """Generate a human-readable description of the activity"""
        user_display = user.username if user else 'Anonymous user'
        
        # Determine the resource being operated on
        if document:
            resource_name = document.name
            resource_type = 'document'
        elif metadata.get('resource_type') == 'folder':
            resource_name = metadata.get('resource_name', 'Unknown Folder')
            resource_type = 'folder'
        else:
            resource_name = 'Unknown Resource'
            resource_type = 'resource'
        
        descriptions = {
            'view': f"{user_display} viewed {resource_type} {resource_name}",
            'edit': f"{user_display} edited {resource_type} {resource_name}",
            'create': f"{user_display} created {resource_type} {resource_name}",
            'delete': f"{user_display} deleted {resource_type} {resource_name}",
            'download': f"{user_display} downloaded {resource_name}",
            'upload': f"{user_display} uploaded {resource_name}",
            'share': f"{user_display} shared {resource_name}",
            'permission_change': f"{user_display} changed permissions for {resource_name}",
            'restore': f"{user_display} restored {resource_name}",
            'rename': f"{user_display} renamed {resource_name}",
            'move': f"{user_display} moved {resource_name}",
            'websocket_connect': f"{user_display} connected for real-time editing of {resource_name}",
            'websocket_disconnect': f"{user_display} disconnected from real-time editing of {resource_name}",
            'auto_save': f"Auto-saved changes to {resource_name} by {user_display}",
            'manual_save': f"{user_display} manually saved {resource_name}",
        }
        
        base_description = descriptions.get(activity_type, f"{user_display} performed {activity_type} on {resource_name}")
        
        # Add metadata details if available
        if metadata:
            if 'old_name' in metadata and 'new_name' in metadata:
                base_description += f" (from '{metadata['old_name']}' to '{metadata['new_name']}')"
            elif 'old_folder' in metadata and 'new_folder' in metadata:
                base_description += f" (from folder '{metadata['old_folder']}' to '{metadata['new_folder']}')"
        
        return base_description


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    attachment = models.FileField(upload_to='comment_attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For nested comments (replies)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='replies')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'

    def __str__(self):
        return f"Comment by {self.user.username} on {self.document.name}"
