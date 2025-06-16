import io
import shutil
import zipfile
from datetime import datetime
from uuid import uuid4

from django.core.files.base import ContentFile, File
from django.core.management import call_command
from django.db import models
import os
# Create your models here.

class Backup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    file = models.FileField(upload_to='backups/', null=True, blank=True)
    media_archive = models.FileField(upload_to='backups/media/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return os.path.basename(self.file.name)

    def save(self, *args, **kwargs):
        # First, save the object so we have an ID and file path is valid
        new_backup = not Backup.objects.filter(id=self.id).exists()
        super().save(*args, **kwargs)
        # Only generate and attach backup file for new objects
        if new_backup and not self.file and not self.media_archive:
        # if self._state.adding:
            buffer = io.StringIO()
            call_command("dumpdata", stdout=buffer)
            filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            content = buffer.getvalue()

            self.file.save(filename, ContentFile(content), save=True)

            # Create media archive
            media_dir = os.path.join(os.getcwd(), 'media')
            if os.path.exists(media_dir):
                archive_base = f"media_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                archive_path = shutil.make_archive(archive_base, 'zip', media_dir)
                with open(archive_path, 'rb') as archive_file:
                    self.media_archive.save(os.path.basename(archive_path), File(archive_file), save=True)
                os.remove(archive_path)  # Clean up temporary zip file


    def delete(self, using=None, keep_parents=False):
        if self.file and os.path.exists(self.file.path):
            os.remove(self.file.path)
        if self.media_archive and os.path.exists(self.file.path):
            os.remove(self.media_archive.path)

        super().delete(using, keep_parents)

    def restore(self):
        # Restore the database
        # Cache file references before loaddata wipes them from memory
        file_path = self.file.name
        media_path = self.media_archive.name

        if self.file:
            call_command('loaddata', self.file.path)

        # Restore media files
        if self.media_archive and os.path.exists(self.media_archive.path):
            with zipfile.ZipFile(self.media_archive.path, 'r') as zip_ref:
                zip_ref.extractall(os.path.join(os.getcwd(), 'media'))

        # Reassign the restored paths to current instance
        self.file.name = file_path
        self.media_archive.name = media_path
        self.save()

    class Meta:
        verbose_name = "Backup"
        verbose_name_plural = "Backups"