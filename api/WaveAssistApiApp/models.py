from django.db import models
from django.db.models.functions import Lower

class Client(models.Model):
    id = models.AutoField(primary_key=True)
    client_key = models.CharField(unique=True, max_length=255)
    name = models.CharField(max_length=255, default="", null=True)
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    firebase_uid = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Client: {self.name} ({self.client_key})"

    def get_dict(self):
        client_dict = {}
        client_dict['id'] = self.id
        client_dict['client_key'] = self.client_key
        client_dict['name'] = self.name
        client_dict['username'] = self.username
        client_dict['company_name'] = self.company_name
        client_dict['firebase_uid'] = self.firebase_uid
        return client_dict

    class Meta:
        db_table = "WaveAssist_Client"
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'


class Integrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, default="", null=True)
    import_code = models.TextField(default="")
    function_code = models.TextField(default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Integrations: {self.id} ({self.name})"

    def get_dict(self):
        integrations_dict = {}
        integrations_dict['id'] = self.id
        integrations_dict['name'] = self.name

        return integrations_dict

    class Meta:
        db_table = "WaveAssist_Integrations"
        verbose_name = 'Integrations'
        verbose_name_plural = 'Integrations'


class IOData(models.Model):
    id = models.BigAutoField(primary_key=True)
    key = models.CharField(max_length=255, unique=True)
    output_type = models.IntegerField(default=0) ## 0 is default, 1 is needed for output, 2 is final_output_format, 3 is Integrations
    action_type = models.IntegerField(default=0) ## 0 is replace, 1 is add
    description = models.CharField(max_length=255, default="", null=True)
    name = models.CharField(max_length=255, default="", null=True)

    project = models.ForeignKey('Project', on_delete=models.CASCADE)


    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"IOData: {self.id} ({self.key}) ({self.name})"

    def get_dict(self):
        iodata_dict = {}
        iodata_dict['id'] = self.id
        iodata_dict['key'] = self.key
        iodata_dict['output_type'] = self.output_type
        iodata_dict['action_type'] = self.action_type
        return iodata_dict

    class Meta:
        db_table = "WaveAssist_IOData"
        verbose_name = 'IOData'
        verbose_name_plural = 'IOData'

class Project(models.Model):
    id = models.BigAutoField(primary_key=True)
    project_key = models.CharField(unique=True, max_length=255)

    client_array = models.ManyToManyField('Client', blank=True)
    node_array = models.ManyToManyField('Nodes', blank=True)
    integration_array = models.ManyToManyField('Integrations', blank=True)


    running_status = models.IntegerField(default=0) ##0 is not running, 1 is running
    payment_status = models.IntegerField(default=0) ##0 is unpaid, 1 is paid

    refresh_status = models.IntegerField(default=0) ##0 is no, 1 is yes

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        ##Add all the fields
        return f"Project: {self.id} ({self.project_key})"

    def get_dict(self):
        project_dict = {}
        project_dict['id'] = self.id
        project_dict['project_key'] = self.project_key
        project_dict['running_status'] = self.running_status
        project_dict['payment_status'] = self.payment_status
        project_dict['refresh_status'] = self.refresh_status
        return project_dict

    class Meta:
        db_table = "WaveAssist_Project"
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'


class Nodes(models.Model):
    id = models.BigAutoField(primary_key=True)

    node_key = models.CharField(unique=True, max_length=255)

    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)

    start_frequency_in_seconds = models.IntegerField(default=0)

    input_data_array = models.ManyToManyField("IOData", related_name="input_data_array", blank=True)
    output_data_array = models.ManyToManyField("IOData", related_name="output_data_array", blank=True)

    python_code = models.TextField(default="")

    running_status = models.IntegerField(default=0) ##0 is not running, 1 is running, 2 is restart

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Node: {self.id} ({self.name})"

    def get_dict(self):
        node_dict = {}
        node_dict['id'] = self.id
        node_dict['node_key'] = self.node_key
        node_dict['name'] = self.name
        node_dict['description'] = self.description
        node_dict['start_frequency_in_seconds'] = self.start_frequency_in_seconds
        node_dict['sleep_duration'] = self.start_frequency_in_seconds
        node_dict['running_status'] = self.running_status
        node_dict['python_code'] = self.python_code

        ##Also optimially load and pass the input and output data list
        input_data_array = []
        for input_data in self.input_data_array.all().order_by(Lower('key')):
            input_data_array.append(input_data.get_dict())
        node_dict['input_data_array'] = input_data_array

        output_data_array = []
        for output_data in self.output_data_array.all().order_by(Lower('key')):
            output_data_array.append(output_data.get_dict())
        node_dict['output_data_array'] = output_data_array

        return node_dict

    class Meta:
        db_table = "WaveAssist_Nodes"
        verbose_name = 'Nodes'
        verbose_name_plural = 'Nodes'
