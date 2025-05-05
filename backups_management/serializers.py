from rest_framework import serializers
from .models import Backup

class BackupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Backup
        fields = ['id', 'file', 'created_at']