from django.contrib import admin

# Register your models here.
from .models import *

from django.contrib import admin
from .models import Client, IOData, Project, Nodes


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'client_key', 'name', 'username', 'company_name', 'firebase_uid', 'created_at')
    search_fields = ('name', 'username', 'company_name', 'firebase_uid')
    list_filter = ('created_at',)
    readonly_fields = ('id', 'created_at')


@admin.register(IOData)
class IODataAdmin(admin.ModelAdmin):
    list_display = ('id', 'key', 'type', 'output_type', 'project', 'created_at', 'description')
    search_fields = ('key', 'project__project_key', 'description')
    list_filter = ('type', 'output_type', 'project__project_key')
    readonly_fields = ('id', 'created_at')
    list_per_page = 25


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'project_key', 'client', 'running_status', 'payment_status', 'created_at')
    search_fields = ('project_key', 'client__name')
    list_filter = ('running_status', 'payment_status', 'created_at')
    autocomplete_fields = ('client',)
    readonly_fields = ('id', 'created_at')
    ##Make client field optional
    optional_fields = ('node_array',)

@admin.register(Nodes)
class NodesAdmin(admin.ModelAdmin):
    list_display = ('id', 'node_key', 'name', 'description', 'type', 'start_frequency_in_seconds',
                    'running_status', 'server_status', 'created_at')
    search_fields = ('node_key', 'name', 'description')
    list_filter = ('type', 'running_status', 'server_status', 'created_at')
    autocomplete_fields = ('input_data_array', 'output_data_array')
    readonly_fields = ('id', 'created_at')
    optional_fields = ('python_code','input_data_array', 'output_data_array')


