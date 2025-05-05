import os
import shutil

from django.db import models
from django.contrib.auth import get_user_model
from uuid import uuid4
from django.utils import timezone

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
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.csv', '.docx', '.pdf']
    if not ext.lower() in valid_extensions:
        raise ValueError('Unsupported file extension.')

@reversion.register(ignore_duplicates=True)
class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100, default="New Document")
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to=document_upload_path, validators=[validate_file_extension], max_length=500)
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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.folder:
            for folder in Folder.objects.filter(parent=self.folder):
                Permission.objects.update_or_create(
                    user=self.user,
                    folder=folder,
                    level=self.level
                )

            for document in Document.objects.filter(folder=self.folder):
                Permission.objects.update_or_create(
                    user=self.user,
                    document=document,
                    level=self.level
                )

    def delete(self, using=None, keep_parents=False):
        if self.folder:
            for folder in Folder.objects.filter(parent=self.folder):
                Permission.objects.filter(user=self.user, folder=folder).delete()

            for document in Document.objects.filter(folder=self.folder):
                Permission.objects.filter(user=self.user, document=document).delete()

        super().delete(using, keep_parents)

class ShareableLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    document = models.ForeignKey('Document', on_delete=models.CASCADE, related_name='share_links')
    token = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    # access_level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='read')  # Extend if needed
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

    def __str__(self):
        return f"Shared link for {self.document.name}"
