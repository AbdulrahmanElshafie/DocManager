import os
import shutil

from django.db import models
from django.contrib.auth import get_user_model
from uuid import uuid4

from django.shortcuts import get_object_or_404
from django.utils import timezone

from DocManager.settings import MEDIA_ROOT
from manager.helpers import get_folder_path

User = get_user_model()


class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100, default="New Folder")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    path = models.TextField(null=True, blank=True)


    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Folder'
        verbose_name_plural = 'Folders'

    def save(self, *args, **kwargs):
        new_path = get_folder_path(self)
        full_new_path = os.path.join(MEDIA_ROOT, self.owner.username, new_path)
        # Check if the folder already exists, i.e., is being updated
        try:
            old = Folder.objects.get(pk=self.pk)
            old_path = os.path.join(MEDIA_ROOT, self.owner.username, old.path)
            if old.path != new_path:
                # Rename the directory
                if os.path.exists(old_path):
                    os.makedirs(os.path.dirname(full_new_path), exist_ok=True)
                    shutil.move(old_path, full_new_path)
                else:
                    os.makedirs(full_new_path, exist_ok=True)

                self.path = new_path
                super().save(*args, **kwargs)
                # Update paths of all child folders
                for child in Folder.objects.filter(parent=old):
                    relative_subpath = child.path[len(old.path) + 1:]  # exclude "oldpath/"
                    child.path = os.path.join(new_path, relative_subpath)
                    child.save()

        except Folder.DoesNotExist:
            os.makedirs(full_new_path, exist_ok=True)

        self.path = new_path
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        if os.path.exists(os.path.join(MEDIA_ROOT, self.owner.username, self.path)):
            shutil.rmtree((os.path.join(MEDIA_ROOT, self.owner.username, self.path)))

        for child in Folder.objects.filter(parent=self):
            child.delete()

        super().delete(using, keep_parents)




def document_upload_path(instance, filename):
    username = instance.owner.username
    folder_path = get_folder_path(instance.folder) if instance.folder else ""

    if folder_path:
        return os.path.join(username, folder_path, filename)
    return os.path.join(username, filename)

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

class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100, default="New Document")
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to=document_upload_path, validators=[validate_file_extension])
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'

    def __str__(self):
        return self.name

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
        super().delete(using, keep_parents)
        if self.folder:
            for folder in Folder.objects.filter(parent=self.folder):
                Permission.objects.filter(user=self.user, folder=folder).delete()

            for document in Document.objects.filter(folder=self.folder):
                Permission.objects.filter(user=self.user, document=document).delete()

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


# class PrintingSize(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
#     name = models.CharField(max_length=100)
#     height = models.IntegerField(verbose_name="Height in CM")
#     width = models.IntegerField(verbose_name="Width in CM")
#
#     def __str__(self):
#         return self.name
#
#
# class DocumentTemplate(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
#     name = models.CharField(max_length=100)
#     printing_size = models.ForeignKey(PrintingSize, on_delete=models.CASCADE)
#     file = models.FileField(upload_to="templates/")
#     type = models.CharField(max_length=100, choices=TYPE, default="docx")
#
#     def __str__(self):
#         return self.name