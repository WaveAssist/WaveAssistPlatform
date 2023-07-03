from django.db import models

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


class IOData(models.Model):
    id = models.BigAutoField(primary_key=True)
    key = models.CharField(max_length=255, unique=True)
    type = models.IntegerField(default=0)
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"IOData: {self.id} ({self.key})"

    def get_dict(self):
        iodata_dict = {}
        iodata_dict['id'] = self.id
        iodata_dict['key'] = self.key
        iodata_dict['type'] = self.type
        return iodata_dict

    class Meta:
        db_table = "WaveAssist_IOData"


class Project(models.Model):
    id = models.BigAutoField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    node_list = models.ManyToManyField('Nodes')

    creation_status = models.IntegerField(default=0)
    payment_status = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        ##Add all the fields
        return f"Project: {self.id} ({self.client})"

    def get_dict(self):
        project_dict = {}
        project_dict['id'] = self.id
        project_dict['client'] = self.client.get_dict()
        project_dict['creation_status'] = self.creation_status
        project_dict['payment_status'] = self.payment_status
        return project_dict

    class Meta:
        db_table = "WaveAssist_Project"


class Nodes(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    type = models.IntegerField(default=0)

    start_frequency_in_seconds = models.IntegerField(default=0)

    input_data_list = models.ManyToManyField("IOData", related_name="input_data_list")
    output_data_list = models.ManyToManyField("IOData", related_name="output_data_list")

    python_code = models.TextField(default="")

    running_status = models.IntegerField(default=0)
    server_status = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Node: {self.id} ({self.name})"

    def get_dict(self):
        node_dict = {}
        node_dict['id'] = self.id
        node_dict['name'] = self.name
        node_dict['description'] = self.description
        node_dict['type'] = self.type
        node_dict['start_frequency_in_seconds'] = self.start_frequency_in_seconds
        node_dict['python_code'] = self.python_code
        node_dict['running_status'] = self.running_status
        node_dict['server_status'] = self.server_status
        return node_dict

    class Meta:
        db_table = "WaveAssist_Nodes"
