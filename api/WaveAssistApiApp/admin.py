from django.contrib import admin
from .models import User, AccessProvided, Integrations, DataKey, Project, DataRuns, Nodes, DashboardSection, DAG, \
    Deployments, Account


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'username', 'company_name', 'uid', 'created_at')
    search_fields = ('name', 'username', 'company_name')
    list_filter = ('created_at', 'company_name')
    readonly_fields = ('id', 'created_at')

@admin.register(AccessProvided)
class AccessProvidedAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'user_object', 'project_object', 'data_run_object', 'project_access_type', 'data_run_access_type', 'created_at')
    search_fields = ('user_object__username', 'project_object__project_key', 'data_run_object__data_run_key')
    list_filter = ('type', 'project_access_type', 'data_run_access_type', 'created_at')
    readonly_fields = ('id', 'created_at')

@admin.register(Integrations)
class IntegrationsAdmin(admin.ModelAdmin):
    list_display = ('id', 'integration_key', 'name', 'created_at')
    search_fields = ('integration_key', 'name')
    list_filter = ('created_at',)
    readonly_fields = ('id', 'created_at')

@admin.register(DataKey)
class DataKeyAdmin(admin.ModelAdmin):
    list_display = ('id', 'key', 'project_object', 'created_at')
    search_fields = ('key',)
    list_filter = ( 'created_at',)
    readonly_fields = ('id', 'created_at')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'project_key', 'created_at')
    search_fields = ('project_key',)
    list_filter = ('created_at',)
    readonly_fields = ('id', 'created_at')

@admin.register(DataRuns)
class DataRunsAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_run_key', 'name', 'project_object', 'is_enabled', 'created_at')
    search_fields = ('data_run_key', 'name', 'project_object__project_key')
    list_filter = ('is_enabled', 'created_at')
    readonly_fields = ('id', 'created_at')

@admin.register(Nodes)
class NodesAdmin(admin.ModelAdmin):
    list_display = ('id', 'node_key', 'project_object', 'is_enabled', 'is_starting_node', 'schedule_type', 'created_at')
    search_fields = ('node_key', 'project_object__project_key')
    list_filter = ('is_enabled', 'is_starting_node', 'schedule_type', 'created_at')
    readonly_fields = ('id', 'created_at')

@admin.register(DashboardSection)
class DashboardSectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'dashboard_section_key', 'project_object', 'row', 'column', 'display_type', 'title', 'should_display_title', 'is_editable', 'created_at')
    search_fields = ('dashboard_section_key', 'title', 'project_object__project_key')
    list_filter = ('display_type', 'should_display_title', 'is_editable', 'created_at')
    readonly_fields = ('id', 'created_at')


@admin.register(Deployments)
class DeploymentsAdmin(admin.ModelAdmin):
    list_display = ('id', 'key', 'project_object', 'data_run_object', 'version', 'is_running', 'created_at')
    search_fields = ('key', 'version', 'project_object__name', 'data_run_object__name')
    list_filter = ('is_running', 'created_at')
    readonly_fields = ('id', 'created_at')

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('project_object', 'data_run_object', 'key')
        return self.readonly_fields

@admin.register(DAG)
class DAGAdmin(admin.ModelAdmin):
    list_display = ('id', 'key', 'parent_deployment', 'periodic_task', 'is_running', 'start_node', 'created_at')
    search_fields = ('key', 'periodic_task__name', 'start_node__name')
    list_filter = ('is_running', 'created_at')
    readonly_fields = ('id', 'created_at')

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('parent_deployment', 'key')
        return self.readonly_fields

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'account_name', 'created_at')
    search_fields = ('account_name',)
    list_filter = ('created_at',)
    readonly_fields = ('id', 'created_at')