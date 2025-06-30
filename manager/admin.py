from django.contrib import admin
from reversion.admin import VersionAdmin
from .models import *


@admin.register(Folder)
class FolderAdmin(VersionAdmin):
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('id', 'owner', 'created_at', 'updated_at')
        return ()

    list_display = ('name', 'parent', 'owner', 'created_at', 'updated_at')

@admin.register(Document)
class DocumentAdmin(VersionAdmin):
    list_display = ('name', 'folder', 'owner', 'created_at', 'updated_at')
    actions = ['create_shareable_link']
    
    def create_shareable_link(self, request, queryset):
        """Create shareable links for selected documents"""
        from .models import ShareableLink
        
        created_count = 0
        for document in queryset:
            # Check if a shareable link already exists for this document
            existing_link = ShareableLink.objects.filter(document=document, is_active=True).first()
            
            if not existing_link:
                ShareableLink.objects.create(
                    document=document,
                    created_by=request.user,
                    is_active=True
                )
                created_count += 1
        
        if created_count > 0:
            self.message_user(request, f"Created {created_count} shareable link(s).")
        else:
            self.message_user(request, "All selected documents already have active shareable links.")
    
    create_shareable_link.short_description = "Create shareable links for selected documents"

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
    readonly_fields = ('token', 'url')
    
    def url(self, obj):
        """Display the shareable URL"""
        return f"api/manager/share/{obj.token}/"
    url.short_description = 'Shareable URL'

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


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('document', 'user', 'content', 'created_at', 'parent')
    list_filter = ('created_at', 'document', 'user')
    search_fields = ('document__name', 'user__username', 'content')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
