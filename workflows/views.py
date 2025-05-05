from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from manager.models import Document
from manager.serializers import DocumentSerializer
from workflows.permissions import TemplatePermission
from workflows.serializers import TemplateSerializer
from workflows.models import Template

class TemplateView(ModelViewSet):
    queryset = Template.objects.all()
    # serializer_class = TemplateSerializer
    permission_classes = [IsAuthenticated, TemplatePermission]
    parser_classes = [MultiPartParser, FormParser]  # Needed for file upload

    def get_serializer_class(self, *args, **kwargs):
        if self.action == 'insert':
            return None
        return TemplateSerializer

    def perform_create(self, serializer):
        serializer.validated_data['owner'] = self.request.user
        super().perform_create(serializer)

    @swagger_auto_schema(operation_id="workflows_template_insert", responses={200: DocumentSerializer},)
    @action(detail=True, methods=['post'])
    def insert(self, request, *args, **kwargs):
        template = self.get_object()
        document = Document.objects.create(
            name=template.name,
            file=template.file,
            owner=request.user
        )

        return Response(DocumentSerializer(document).data)