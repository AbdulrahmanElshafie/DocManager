from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Backup
from .permissions import IsStaffOrSuperuser
from .serializers import BackupSerializer

class BackupViewSet(viewsets.ModelViewSet):
    queryset = Backup.objects.all().order_by('-created_at')
    serializer_class = BackupSerializer
    permission_classes = [IsStaffOrSuperuser]

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        backup = get_object_or_404(Backup, pk=pk)
        backup.restore()
        return Response({"message": "Backup restored successfully."})

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
