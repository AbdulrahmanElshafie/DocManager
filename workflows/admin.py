from django.contrib import admin
from workflows.models import Template

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('name','owner', 'created_at', 'updated_at')
