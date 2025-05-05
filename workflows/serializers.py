from rest_framework import serializers
from workflows.models import Template


class TemplateSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=True)

    class Meta:
        model = Template
        fields = ('name', 'file', 'id')
