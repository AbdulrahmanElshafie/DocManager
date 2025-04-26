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


class HasFolderDocumentPermission(BasePermission):
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

        if isinstance(obj, Document):
            return has_permission(request.user, document=obj, required_level=required)
        return has_permission(request.user, folder=obj, required_level=required)

class IsOwnerOrHasPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        method = request.method

        """
        Permissions are granted based on the following conditions:
        
        For GET/HEAD requests:
        - The user is the object owner
        - The user is a superuser
        - The user has explicit permission
        
        For create/update/delete requests:
        - The user is the object owner
        - The user is a superuser
        """

        if request.user.is_superuser:
            return True

        if request.user == obj.user and method in ['GET', 'HEAD']:
            return True

        if obj.document and obj.document.owner == request.user:
            return True

        if obj.folder and obj.folder.owner == request.user:
            return True

        return False