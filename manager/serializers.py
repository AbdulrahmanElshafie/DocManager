from rest_framework import serializers
from .models import *


class FolderSerializer(serializers.ModelSerializer):
    folders = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()

    def get_folders(self, obj):
        folders = Folder.objects.filter(parent=obj)
        return FolderSerializer(folders, many=True).data

    def get_documents(self, obj):
        documents = Document.objects.filter(folder=obj)
        return DocumentSerializer(documents, many=True).data

    def get_fields(self):
        fields = super().get_fields()
        fields['documents'] = serializers.SerializerMethodField()
        fields['folders'] = serializers.SerializerMethodField()
        return fields

    class Meta:
        model = Folder
        fields = ('name', 'parent', 'id', 'folders', 'documents')


class DocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=True)

    class Meta:
        model = Document
        fields = ('id', 'name', 'folder', 'file', 'created_at', 'updated_at')


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('user', 'document', 'folder', 'level', 'id')


class ShareableLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareableLink
        fields = ('document', 'token', 'created_at', 'expires_at', 'is_active', 'created_by', 'id')