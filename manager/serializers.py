from rest_framework import serializers
from .models import *


class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ('name', 'parent', 'id')


class DocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=True)

    class Meta:
        model = Document
        fields = ('name', 'folder', 'file', 'id')


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('user', 'document', 'folder', 'level', 'id')