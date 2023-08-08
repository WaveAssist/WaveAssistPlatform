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
    list_display = ('id', 'name', 'key', 'action_type', 'output_type', 'project', 'created_at', 'description')
    search_fields = ('key', 'project__project_key', 'description', 'name')
    list_filter = ('output_type', 'project__project_key')
    readonly_fields = ('id', 'created_at')
    list_per_page = 25


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'project_key', 'running_status','refresh_status', 'payment_status', 'created_at')
    search_fields = ['project_key']
    list_filter = ('running_status', 'payment_status', 'created_at')
    readonly_fields = ('id', 'created_at')
    ##Make client field optional
    optional_fields = ('node_array','client_array')

@admin.register(Nodes)
class NodesAdmin(admin.ModelAdmin):
    list_display = ('id', 'node_key', 'name', 'description', 'start_frequency_in_seconds',
                    'running_status', 'created_at')
    search_fields = ('node_key', 'name', 'description')
    list_filter = ('running_status', 'created_at')
    autocomplete_fields = ('input_data_array', 'output_data_array')
    readonly_fields = ('id', 'created_at')
    optional_fields = ('python_code','input_data_array', 'output_data_array')


