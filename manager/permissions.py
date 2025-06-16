from rest_framework.permissions import BasePermission
from .models import *
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


def has_permission(user, document=None, folder=None, required_level='read'):
    """
    Check if user has the required permission level for a document or folder
    
    Args:
        user: User instance
        document: Document instance (optional)
        folder: Folder instance (optional)
        required_level: 'read', 'write', 'delete', or 'track'
    
    Returns:
        bool: True if user has permission, False otherwise
    """
    # Check document permissions
    if document:
        # Check if user is the owner
        if document.owner == user:
            return True
        
        
        # Check direct document permissions
        try:
            permission = Permission.objects.get(
                user=user,
                document=document
            )
            
            if required_level == 'read':
                return permission.level in ['read', 'write', 'delete', 'track']
            elif required_level == 'write':
                return permission.level in ['write', 'delete']
            elif required_level == 'delete':
                return permission.level == 'delete'
            elif required_level == 'track':
                return permission.level in ['track', 'delete']  # Owners and those with track permission
            else:
                return False
                
        except Permission.DoesNotExist:
            pass
    
    # Check folder permissions
    if folder:
        # Check if user is the owner
        if folder.owner == user:
            return True
        
        # Check direct folder permissions
        try:
            permission = Permission.objects.get(
                user=user,
                folder=folder
            )
            
            if required_level == 'read':
                return permission.level in ['read', 'write', 'delete', 'track']
            elif required_level == 'write':
                return permission.level in ['write', 'delete']
            elif required_level == 'delete':
                return permission.level == 'delete'
            elif required_level == 'track':
                return permission.level in ['track', 'delete']
            else:
                return False
                
        except Permission.DoesNotExist:
            pass
        
    return False

class HasFolderDocumentPermission(BasePermission):
    """
    Global permission class for both FolderViewSet and DocumentViewSet.
    - GET/HEAD: requires read.
    - POST/PUT/PATCH: requires write.
    - DELETE: requires delete.
    Additionally: for any create/update that specifies a parent folder,
    the user must have write/delete on that folder (not just read).
    """

    def _required_level_for_method(self, method):
        if method in ['GET', 'HEAD']:
            return 'read'
        if method in ['POST', 'PUT', 'PATCH']:
            return 'write'
        if method == 'DELETE':
            return 'delete'
        return None

    def has_permission(self, request, view):
        # superusers bypass everything
        if request.user.is_superuser:
            return True

        required = self._required_level_for_method(request.method)
        if not required:
            return False  # unsupported HTTP verb

        # For creation or moving (POST / PUT / PATCH), enforce on parent folder:
        if request.method in ['POST', 'PUT', 'PATCH']:
            # the payload field name for the parent folder on both Document and Folder
            folder_id = request.query_params.get('folder') if request.method == 'GET' else request.data.get('folder')
            # if there's no folder specified, we let other parts of your logic decide
            if folder_id and folder_id.strip():
                try:
                    parent = Folder.objects.get(id=folder_id)
                except (Folder.DoesNotExist, ValidationError):
                    return False
                # must have at least write on this parent folder
                try:
                    return has_permission(request.user, folder=parent, required_level='write')
                except (Permission.DoesNotExist, ValidationError):
                    return False

        return True
    
    def has_object_permission(self, request, view, obj):
        # superusers bypass everything
        if request.user.is_superuser:
            return True

        required = self._required_level_for_method(request.method)
        if not required:
            return False  # unsupported HTTP verb

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
        - The user is the object owner (document/folder owner)
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

class HasActivityTrackingPermission(BasePermission):
    """
    Permission class for activity log access.
    Users can access activity logs if:
    - They are the document owner
    - They are a superuser
    - They have 'track' permission for the document
    """
    
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        # For ActivityLog objects, check permission on the associated document
        if hasattr(obj, 'document'):
            document = obj.document
        else:
            document = obj
        
        # Check if user has track permission or is the owner
        return has_permission(request.user, document=document, required_level='track')