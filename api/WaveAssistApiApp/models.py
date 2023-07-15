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
    type = models.IntegerField(default=0) ## 0 is default, 1 is final_output
    output_type = models.IntegerField(default=0) ##0 is replace, 1 is update, 2 is append, 3 is delete


    project = models.ForeignKey('Project', on_delete=models.CASCADE)


    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"IOData: {self.id} ({self.key})"

    def get_dict(self):
        iodata_dict = {}
        iodata_dict['id'] = self.id
        iodata_dict['key'] = self.key
        iodata_dict['type'] = self.type
        iodata_dict['output_type'] = self.output_type
        return iodata_dict

    class Meta:
        db_table = "WaveAssist_IOData"


class Project(models.Model):
    id = models.BigAutoField(primary_key=True)
    project_key = models.CharField(unique=True, max_length=255)

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    node_list = models.ManyToManyField('Nodes')

    running_status = models.IntegerField(default=0) ##0 is not running, 1 is start to run, 2 is restart
    payment_status = models.IntegerField(default=0)


    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        ##Add all the fields
        return f"Project: {self.id} ({self.client})"

    def get_dict(self):
        project_dict = {}
        project_dict['id'] = self.id
        project_dict['project_key'] = self.project_key
        project_dict['creation_status'] = self.running_status
        project_dict['payment_status'] = self.payment_status
        if self.running_status == 2:
            project_dict['should_refresh'] = '1'
        else:
            project_dict['should_refresh'] = '0'
        return project_dict

    class Meta:
        db_table = "WaveAssist_Project"


class Nodes(models.Model):
    id = models.BigAutoField(primary_key=True)

    node_key = models.CharField(unique=True, max_length=255)

    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    type = models.IntegerField(default=0)

    start_frequency_in_seconds = models.IntegerField(default=0)

    input_data_array = models.ManyToManyField("IOData", related_name="input_data_array")
    output_data_array = models.ManyToManyField("IOData", related_name="output_data_array")

    python_code = models.TextField(default="")

    running_status = models.IntegerField(default=0)
    server_status = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Node: {self.id} ({self.name})"

    def get_dict(self):
        node_dict = {}
        node_dict['id'] = self.id
        node_dict['node_key'] = self.node_key
        node_dict['name'] = self.name
        node_dict['description'] = self.description
        node_dict['type'] = self.type
        node_dict['start_frequency_in_seconds'] = self.start_frequency_in_seconds
        node_dict['sleep_duration'] = self.start_frequency_in_seconds
        node_dict['python_code'] = self.python_code
        node_dict['running_status'] = self.running_status
        node_dict['server_status'] = self.server_status

        ##Also optimially load and pass the input and output data list
        input_data_array = []
        for input_data in self.input_data_array.all():
            input_data_array.append(input_data.get_dict())
        node_dict['input_data_array'] = input_data_array

        output_data_array = []
        for output_data in self.output_data_array.all():
            output_data_array.append(output_data.get_dict())
        node_dict['output_data_array'] = output_data_array

        return node_dict

    class Meta:
        db_table = "WaveAssist_Nodes"
