from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import *
import os
import tempfile

User = get_user_model()


class FolderSerializer(serializers.ModelSerializer):
    folders = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()

    def get_folders(self, obj):
        folders = Folder.objects.filter(parent=obj)
        return FolderSerializer(folders, many=True).data

    def get_documents(self, obj):
        documents = Document.objects.filter(folder=obj)
        return DocumentSerializer(documents, many=True).data
    
    def get_owner(self, obj):
        """Return the owner ID as an integer"""
        return obj.owner.id if obj.owner else None

    def get_fields(self):
        fields = super().get_fields()
        fields['documents'] = serializers.SerializerMethodField()
        fields['folders'] = serializers.SerializerMethodField()
        return fields

    class Meta:
        model = Folder
        fields = ('name', 'parent', 'id', 'owner', 'folders', 'documents', 'created_at', 'updated_at')


class DocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=False, allow_null=True)
    document_type = serializers.ChoiceField(choices=[('docx', 'DOCX'), ('csv', 'CSV'), ('pdf', 'PDF')], required=False, write_only=True)
    owner = serializers.SerializerMethodField()

    def get_owner(self, obj):
        """Return the owner ID as an integer"""
        return obj.owner.id if obj.owner else None

    class Meta:
        model = Document
        fields = ('id', 'name', 'folder', 'file', 'owner', 'document_type', 'created_at', 'updated_at')

    def create(self, validated_data):
        # Handle empty document creation
        document_type = validated_data.pop('document_type', None)
        file = validated_data.get('file')
        
        # If no file is provided but document_type is specified, create an empty file
        if not file and document_type:
            validated_data['file'] = self._create_empty_file(document_type)
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Handle document_type for existing documents that don't have a file yet
        document_type = validated_data.pop('document_type', None)
        
        # If instance doesn't have a file and document_type is provided, create empty file
        if (not instance.file or not instance.file.name) and document_type:
            validated_data['file'] = self._create_empty_file(document_type)
        
        return super().update(instance, validated_data)
    
    def _create_empty_file(self, document_type):
        """Create an empty file based on document type"""
        from django.core.files.base import ContentFile
        
        if document_type == 'docx':
            # Create empty DOCX file
            from docx import Document as DocxDocument
            doc = DocxDocument()
            doc.add_paragraph("This is an empty document. Start typing here...")
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
            doc.save(temp_file.name)
            
            with open(temp_file.name, 'rb') as f:
                content = f.read()
            
            os.unlink(temp_file.name)
            return ContentFile(content, name='empty_document.docx')
            
        elif document_type == 'csv':
            # Create empty CSV file
            csv_content = "Column1,Column2,Column3\n"
            return ContentFile(csv_content.encode('utf-8'), name='empty_document.csv')
            
        elif document_type == 'pdf':
            # For PDF, we'll create a simple text file for now
            # In production, you might want to create an actual PDF
            pdf_content = "This is an empty PDF document placeholder."
            return ContentFile(pdf_content.encode('utf-8'), name='empty_document.pdf')
        
        return None

    def validate_file(self, value):
        """Validate uploaded file"""
        if value:
            # Check file size (limit to 50MB)
            if value.size > 50 * 1024 * 1024:
                raise serializers.ValidationError("File size cannot exceed 50MB.")
            
            # Check file extension
            ext = os.path.splitext(value.name)[1].lower()
            valid_extensions = ['.csv', '.docx', '.pdf']
            if ext not in valid_extensions:
                raise serializers.ValidationError(f"Unsupported file extension. Allowed: {', '.join(valid_extensions)}")
        
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')




class ShareableLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareableLink
        fields = ('document', 'token', 'created_at', 'expires_at', 'is_active', 'created_by', 'id')


class ActivityLogSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    document_name = serializers.CharField(source='document.name', read_only=True)
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = (
            'id', 'document', 'document_name', 'user', 'user_details', 
            'activity_type', 'activity_type_display', 'timestamp',
            'ip_address', 'user_agent', 'session_id', 'metadata', 'description'
        )
        read_only_fields = (
            'id', 'timestamp', 'ip_address', 'user_agent', 'session_id', 'description'
        )


class ActivityLogFilterSerializer(serializers.Serializer):
    """Serializer for activity log filtering parameters"""
    activity_type = serializers.ChoiceField(
        choices=ACTIVITY_TYPES, 
        required=False,
        help_text="Filter by activity type"
    )
    user = serializers.CharField(
        required=False,
        help_text="Filter by user ID or username"
    )
    start_date = serializers.DateTimeField(
        required=False,
        help_text="Filter activities from this date (ISO format)"
    )
    end_date = serializers.DateTimeField(
        required=False,
        help_text="Filter activities until this date (ISO format)"
    )
    ip_address = serializers.IPAddressField(
        required=False,
        help_text="Filter by IP address"
    )