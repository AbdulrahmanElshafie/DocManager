from django.contrib import admin

from .models import *


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    pass


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    pass

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