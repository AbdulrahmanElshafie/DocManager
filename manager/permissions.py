from rest_framework.permissions import BasePermission
from .models import *


def has_permission(user, document=None, folder=None, required_level='read'):
    levels = ['read', 'write', 'delete']

    if document:
        perm = Permission.objects.filter(user=user, document=document).first()
    elif folder:
        perm = Permission.objects.filter(user=user, folder=folder).first()
    else:
        perm = None

    return (
            (perm and levels.index(perm.level) >= levels.index(required_level))
            or (document and document.owner == user)
            or (folder and folder.owner == user)
    )


class HasFolderPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        method = request.method

        if method in ['GET', 'HEAD']:
            required = 'read'
        elif method in ['POST', 'PUT', 'PATCH']:
            required = 'write'
        elif method == 'DELETE':
            required = 'delete'
        else:
            return False

        if type(obj) == Document:
            return has_permission(request.user, document=obj, required_level=required)
        return has_permission(request.user, folder=obj, required_level=required)

