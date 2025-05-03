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
    pass

@admin.register(ShareableLink)
class ShareableLinkAdmin(admin.ModelAdmin):
    pass

# @admin.register(DocumentTemplate)
# class DocumentTemplateAdmin(admin.ModelAdmin):
#     pass
#
# @admin.register(PrintingSize)
# class PrintingSizeAdmin(admin.ModelAdmin):
#     pass