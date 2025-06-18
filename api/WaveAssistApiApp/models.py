from django.db import models
from django.db.models.functions import Lower
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from django.core.exceptions import ValidationError
import uuid
from django.contrib.auth.hashers import make_password, is_password_usable
from django.db import transaction
import json

SCHEDULE_TYPE_CHOICES = [
        ('none', 'none'),
        ('interval', 'interval'),
        ('crontab', 'crontab')
]


class Account(models.Model):
    id = models.AutoField(primary_key=True)
    account_name = models.CharField(max_length=255, default="", null=True)
    account_uid = models.CharField(editable=False, unique=True,max_length=255)
    created_by_user = models.ForeignKey('User', on_delete=models.CASCADE)
    plan_name = models.CharField(max_length=255, default="free", null=True)
    mongo_db_url = models.CharField(max_length=255, default="", null=True)
    db_name = models.CharField(max_length=255, default="", null=True)
    celery_queue = models.CharField(max_length=255, default="", null=True)
    pip_requirements_array_json = models.TextField(default="[]")
    worker_service_arn = models.CharField(max_length=255, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    is_working_running = models.BooleanField(default=True)

    def __str__(self):
        return f"Account: {self.account_name} ({self.plan_name})"

    def get_dict(self):
        account_dict = {}
        account_dict['id'] = self.id
        account_dict['account_name'] = self.account_name
        account_dict['account_uid'] = self.account_uid
        account_dict['mongo_db_url'] = self.mongo_db_url
        account_dict['db_name'] = self.db_name
        account_dict['celery_queue'] = self.celery_queue
        account_dict['pip_requirements_array_json'] = json.loads(str(self.pip_requirements_array_json))
        account_dict['worker_service_arn'] = self.worker_service_arn
        account_dict['is_working_running'] = self.is_working_running
        return account_dict

    class Meta:
        db_table = "WaveAssist_Account"
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'



class User(models.Model):
    id = models.AutoField(primary_key=True)
    uid = models.CharField(editable=False, unique=True,max_length=255)
    name = models.CharField(max_length=255, default="", null=True)
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255, default="", null=True)
    can_create_projects = models.BooleanField(default=False)
    firebase_uid = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"User: {self.name} ({self.username})"

    def get_dict(self):
        user_dict = {}
        user_dict['id'] = self.id
        user_dict['name'] = self.name
        user_dict['username'] = self.username
        user_dict['uid'] = self.uid
        user_dict['can_create_projects'] = self.can_create_projects
        return user_dict

    def save(self, *args, **kwargs):
        if not self.pk:  # if creating a new instance
            self.password = make_password(self.password)
        elif not is_password_usable(self.password):  # if password needs to be hashed
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    class Meta:
        db_table = "WaveAssist_User"
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class AccessProvided(models.Model):
    id = models.BigAutoField(primary_key=True)
    type = models.IntegerField(default=0) ##0 is project, 1 is dataRun, 2 is dashboard
    user_object = models.ForeignKey('User', on_delete=models.CASCADE)
    project_object = models.ForeignKey('Project', on_delete=models.CASCADE, null=True)
    data_run_object = models.ForeignKey('DataRuns', on_delete=models.CASCADE, null=True)
    project_access_type = models.IntegerField(default=0) ##0 is nothing, 1 is read, 2 is write, 3 is admin  --> This is manage project from admin panel.
    data_run_access_type = models.IntegerField(default=0) ##0 is nothing, 1 is read, 2 is write, 3 is admin  --> This is manage dataRun from admin panel.
    dashboard_access_type = models.IntegerField(default=0) ##0 is nothing, 1 is read, 2 is edit  --> This is to view & edit dashboard
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AccessProvided: {self.id}"

    def get_dict(self):
        access_provided_dict = {}
        access_provided_dict['id'] = self.id
        access_provided_dict['type'] = self.type
        access_provided_dict['user_dict'] = self.user_object.get_dict()
        if self.type == 0:
            access_provided_dict['access_type'] = self.project_access_type
            access_provided_dict['project_id'] = self.project_object.id
        elif self.type == 1:
            access_provided_dict['access_type'] = self.data_run_access_type
            access_provided_dict['data_run_id'] = self.data_run_object.id
        elif self.type == 2:
            access_provided_dict['access_type'] = self.dashboard_access_type
            access_provided_dict['project_id'] = self.project_object.id
        return access_provided_dict

    class Meta:
        db_table = "WaveAssist_AccessProvided"
        verbose_name = 'AccessProvided'
        verbose_name_plural = 'AccessProvided'

class Integrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    integration_key = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, default="", null=True)
    import_code = models.TextField(default="")
    function_code = models.TextField(default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Integrations: {self.id} ({self.name})"

    def get_dict(self):
        integrations_dict = {}
        integrations_dict['id'] = self.id
        integrations_dict['integration_key'] = self.integration_key
        integrations_dict['name'] = self.name
        integrations_dict['import_code'] = self.import_code
        integrations_dict['function_code'] = self.function_code
        return integrations_dict
    class Meta:
        db_table = "WaveAssist_Integrations"
        verbose_name = 'Integration'
        verbose_name_plural = 'Integrations'

class DataKey(models.Model):
    id = models.BigAutoField(primary_key=True)
    key = models.CharField(max_length=255, unique=True)
    project_object = models.ForeignKey('Project', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DataKey: {self.key}"

    def get_dict(self):
        data_key_dict = {}
        data_key_dict['id'] = self.id
        data_key_dict['key'] = self.key
        return data_key_dict

    class Meta:
        db_table = "WaveAssist_DataKey"
        verbose_name = 'DataKey'
        verbose_name_plural = 'DataKeys'


class Project(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, default="", null=True)
    project_key = models.CharField(max_length=255, unique=True)
    integration_array = models.ManyToManyField('Integrations', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        ##Add all the fields
        return f"Project: {self.id} ({self.project_key})"

    def get_dict(self):
        project_dict = {}
        project_dict['id'] = self.id
        project_dict['name'] = self.name
        project_dict['project_key'] = self.project_key

        for integration_object in self.integration_array.all():
            project_dict['integration_array'] = integration_object.get_dict()

        return project_dict

    class Meta:
        db_table = "WaveAssist_Project"
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'


class DataRuns(models.Model):
    id = models.BigAutoField(primary_key=True)
    data_run_key = models.CharField(max_length=255, unique=True, null=True)
    name = models.CharField(max_length=255)
    project_object = models.ForeignKey('Project', on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


    ##Create data run key on save as project_key + "-" + id
    def save(self, *args, **kwargs):
        if not self.data_run_key:
            self.data_run_key = self.project_object.project_key + "-" + str(self.id)
        super(DataRuns, self).save(*args, **kwargs)

    def __str__(self):
        return f"DataRuns: {self.id}"

    def get_dict(self):
        data_run_dict = {}
        data_run_dict['id'] = self.id
        data_run_dict['name'] = self.name
        data_run_dict['key'] = self.data_run_key
        data_run_dict['project_id'] = self.project_object.id
        data_run_dict['is_enabled'] = self.is_enabled
        return data_run_dict

    class Meta:
        db_table = "WaveAssist_DataRuns"
        verbose_name = 'DataRun'
        verbose_name_plural = 'DataRuns'


class Nodes(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, default="", null=True)
    node_key = models.CharField(max_length=255, db_index=True)
    project_object = models.ForeignKey('Project', on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=False)

    ##Params
    python_code = models.TextField(default="")
    input_data_key_array = models.ManyToManyField("DataKey", related_name="input_data_array", blank=True)
    output_data_key_array = models.ManyToManyField("DataKey", related_name="output_data_array", blank=True)


    ##RunType
    is_starting_node = models.BooleanField(default=False)
    schedule_type = models.CharField(max_length=10, choices=SCHEDULE_TYPE_CHOICES, default='interval')
    interval_schedule = models.ForeignKey(IntervalSchedule, null=True, blank=True, on_delete=models.CASCADE)
    crontab_schedule = models.ForeignKey(CrontabSchedule, null=True, blank=True, on_delete=models.CASCADE)


    run_after_nodes_array = models.ManyToManyField("Nodes", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Node: {self.id} ({self.node_key})"

    def get_dict_info(self):
        node_dict = {}
        node_dict['id'] = self.id
        node_dict['name'] = self.name
        node_dict['node_key'] = self.node_key
        node_dict['python_code'] = self.python_code
        node_dict['is_starting_node'] = self.is_starting_node
        node_dict['is_enabled'] = self.is_enabled
        node_dict['schedule_type'] = self.schedule_type
        node_dict['interval_schedule'] = str(self.interval_schedule)
        node_dict['crontab_schedule'] = str(self.crontab_schedule)

        return node_dict


    def get_dict(self):
        node_dict = self.get_dict_info()

        input_data_key_array = []
        for input_data in self.input_data_key_array.all().order_by(Lower('key')):
            input_data_key_array.append(input_data.get_dict())
        node_dict['input_data_key_array'] = input_data_key_array

        output_data_key_array = []
        for output_data in self.output_data_key_array.all().order_by(Lower('key')):
            output_data_key_array.append(output_data.get_dict())
        node_dict['output_data_key_array'] = output_data_key_array

        run_after_nodes_array = []
        for run_after_node in self.run_after_nodes_array.all().order_by(Lower('node_key')):
            run_after_nodes_array.append(run_after_node.get_dict_info())
        node_dict['run_after_nodes_array'] = run_after_nodes_array

        return node_dict

    class Meta:
        db_table = "WaveAssist_Nodes"
        verbose_name = 'Nodes'
        verbose_name_plural = 'Nodes'

class DashboardSection(models.Model):
    id = models.BigAutoField(primary_key=True)
    dashboard_section_key = models.CharField(max_length=255, unique=True, null=True)
    project_object = models.ForeignKey('Project', on_delete=models.CASCADE)
    row = models.IntegerField(default=0)
    column = models.IntegerField(default=0)
    display_type = models.IntegerField(default=0) ##0 is Table, 1 is Numbers, 2 is Graph, 3 is HTML
    data_key_object = models.ForeignKey('DataKey', on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="", null=True)
    should_display_title = models.BooleanField(default=True)
    is_editable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.dashboard_section_key:
            self.dashboard_section_key = self.project_object.project_key + "-" + str(self.id)
        super(DashboardSection, self).save(*args, **kwargs)

    def __str__(self):
        return f"DashboardSection: {self.id} ({self.title})"

    def get_dict(self):
        dashboard_section_dict = {}
        dashboard_section_dict['id'] = self.id
        dashboard_section_dict['dashboard_section_key'] = self.dashboard_section_key
        dashboard_section_dict['row'] = self.row
        dashboard_section_dict['column'] = self.column
        dashboard_section_dict['display_type'] = self.display_type
        dashboard_section_dict['data_key'] = self.data_key_object.get_dict()
        dashboard_section_dict['title'] = self.title
        dashboard_section_dict['should_display_title'] = self.should_display_title
        dashboard_section_dict['is_editable'] = self.is_editable
        dashboard_section_dict['project_id'] = self.project_object.id
        return dashboard_section_dict

    class Meta:
        db_table = "WaveAssist_DashboardSection"
        verbose_name = 'DashboardSection'
        verbose_name_plural = 'DashboardSection'


class Deployments(models.Model):
    id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=255, unique=True, null=True)
    project_object = models.ForeignKey('Project', on_delete=models.CASCADE)
    data_run_object = models.ForeignKey('DataRuns', on_delete=models.CASCADE)
    version = models.CharField(max_length=100, default="1.0.0")
    is_running = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "WaveAssist_Deployments"
        verbose_name = 'Deployment'
        verbose_name_plural = 'Deployments'

    def __str__(self):
        return f"Deployments: {self.id} ({self.key}))"

    def get_dict(self):
        deployments_dict = {}
        deployments_dict['key'] = self.key
        deployments_dict['version'] = self.version
        deployments_dict['is_running'] = self.is_running
        return deployments_dict


class DAG(models.Model):
    id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=255, unique=True, null=True)
    parent_deployment = models.ForeignKey('Deployments', on_delete=models.CASCADE, null=True)
    periodic_task = models.ForeignKey('django_celery_beat.PeriodicTask', on_delete=models.CASCADE, null=True)
    is_running = models.BooleanField(default=True)
    start_node = models.ForeignKey('Nodes', on_delete=models.SET_NULL, related_name='start_node', null=True, blank=True)
    node_array = models.ManyToManyField('Nodes', blank=True)
    interval_schedule = models.ForeignKey('django_celery_beat.IntervalSchedule', on_delete=models.PROTECT, null=True)
    crontab_schedule = models.ForeignKey(CrontabSchedule, null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"DAG: ({self.id})"

    class Meta:
        db_table = "WaveAssist_DAG"
        verbose_name = 'DAG'
        verbose_name_plural = 'DAGs'

    def get_dict(self):
        dag_dict = {}
        dag_dict['key'] = self.key
        dag_dict['is_running'] = self.is_running
        return dag_dict



class DagRuns(models.Model):
    id = models.AutoField(primary_key=True)
    run_id = models.CharField(max_length=60, unique=True, null=True)            # Celery UUID
    dag_object = models.ForeignKey('DAG', on_delete=models.CASCADE, null=True)  # Which DAG definition
    project_object = models.ForeignKey('Project', on_delete=models.CASCADE)     # Tenant / workspace
    data_run_object = models.ForeignKey('DataRuns', on_delete=models.CASCADE, null=True)  # Data run associated with this DAG run
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "WaveAssist_DagRuns"
        verbose_name = 'DAG Run'
        verbose_name_plural = 'DAG Runs'

    def __str__(self):
        return f"DAG Run: {self.id} ({self.run_id})"

    def get_dict(self):
        return {
            'id':           self.id,
            'run_id':  self.run_id,
            'started_at':   self.started_at,
            'finished_at':  self.finished_at,
        }


RUN_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('STARTED', 'Started'),
        ('RETRY',   'Retry'),
        ('SUCCESS', 'Success'),
        ('FAILED',  'Failed'),
    ]
class NodeRuns(models.Model):
    id = models.AutoField(primary_key=True)
    task_id = models.CharField(max_length=50, unique=True, null=True)  # Celery UUID
    dag_run_object = models.ForeignKey('DagRuns', on_delete=models.CASCADE)
    node_object = models.ForeignKey('Nodes', on_delete=models.CASCADE)

    status = models.CharField(max_length=20, choices=RUN_STATUS_CHOICES, default='PENDING')

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    result = models.TextField(null=True, blank=True)
    traceback = models.TextField(null=True, blank=True)           # exc info for failures
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "WaveAssist_NodeRuns"
        verbose_name = 'Node Run'
        verbose_name_plural = 'Node Runs'
    def __str__(self):
        return f"Node Run: {self.id} ({self.task_id})"

    def get_dict(self):
        return {
            'task_id':      self.task_id,
            'status':       self.status,
            'started_at':   self.started_at,
            'finished_at':  self.finished_at,
            'result':       self.result,
        }
