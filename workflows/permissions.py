from rest_framework.permissions import BasePermission
from .models import *


class TemplatePermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_staff:
            return True

        if obj.owner == request.user:
            return True

        if obj.owner is None:
            return True

        return False