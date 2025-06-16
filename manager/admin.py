from django.contrib import admin
from reversion.admin import VersionAdmin
from .models import *


@admin.register(Folder)
class FolderAdmin(VersionAdmin):
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return 'id', 'owner', 'created_at', 'updated_at'
        return ('path', )

    list_display = ('name', 'parent', 'owner', 'created_at', 'updated_at')

@admin.register(Document)
class DocumentAdmin(VersionAdmin):
    list_display = ('name', 'folder', 'owner', 'created_at', 'updated_at')

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'document', 'folder', 'level')
    list_filter = ('level', 'user', 'document', 'folder')
    search_fields = ('user__username', 'user__email', 'document__name', 'folder__name')

@admin.register(ShareableLink)
class ShareableLinkAdmin(admin.ModelAdmin):
    list_display = ('document', 'token', 'created_by', 'created_at', 'expires_at', 'is_active')
    list_filter = ('is_active', 'created_at', 'expires_at')
    search_fields = ('document__name', 'created_by__username')
    readonly_fields = ('token',)

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('document', 'user', 'activity_type', 'timestamp', 'ip_address')
    list_filter = ('activity_type', 'timestamp', 'document', 'user')
    search_fields = ('document__name', 'user__username', 'user__email', 'description')
    readonly_fields = ('id', 'timestamp', 'ip_address', 'user_agent', 'session_id')
    ordering = ('-timestamp',)
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('document', 'user', 'activity_type')
        return self.readonly_fields
