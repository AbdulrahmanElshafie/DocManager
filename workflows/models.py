import os
import shutil
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.db import models
from DocManager.settings import MEDIA_ROOT

User = get_user_model()


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.csv', '.docx', '.pdf']
    if not ext.lower() in valid_extensions:
        raise ValueError('Unsupported file extension.')

class Template(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100, default="New Template")
    file = models.FileField(upload_to='templates/', validators=[validate_file_extension], max_length=500)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Template'
        verbose_name_plural = 'Templates'

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        if os.path.exists(os.path.join(MEDIA_ROOT, f"{self.id}")):
            shutil.rmtree(os.path.join(MEDIA_ROOT, f"{self.id}"))

        super().delete(using, keep_parents)
