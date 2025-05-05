from django.contrib import admin
from .models import Backup
from django.contrib import messages


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = ('file', 'created_at',)
    actions = ['create_backup', 'restore_selected']

    def create_backup(self, request, queryset):
        backup = Backup.objects.create()
        self.message_user(request, f"Backup '{backup.file.name}' created successfully.")

    create_backup.short_description = "Create new backup"

    def restore_selected(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request, "You can only restore one backup at a time.", level=messages.ERROR)
            return
        for backup in queryset:
            backup.restore()
            self.message_user(request, f"Backup '{backup.file.name}' restored successfully.")

    restore_selected.short_description = "Restore selected backups"

    def delete_queryset(self, request, queryset):
        for backup in queryset:
            backup.delete()