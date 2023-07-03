from django.db import models

class Client(models.Model):
    id = models.AutoField(primary_key=True)
    client_key = models.CharField(unique=True)
    name = models.CharField(max_length=255, default="", null=True)
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


class IOData(models.Model):
    id = models.BigAutoField(primary_key=True)
    key = models.CharField(max_length=255, unique=True)
    type = models.IntegerField(default=0) ## 0 = RedisCache, 1 = S3, 2 = Other
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Project(models.Model):
    id = models.BigAutoField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    node_list = models.ManyToManyField('Nodes')

    creation_status = models.IntegerField(default=0) ##0 = Default, 1 = Ready to create, 2 = Creating, 3 = Created, 4 = Running, 5 = Failed
    payment_status = models.IntegerField(default=0) ##0 = Default, 1 = Paid, 2 = Unpaid


    created_at = models.DateTimeField(auto_now_add=True)


class Nodes(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    type = models.IntegerField(default = 0) ## 0 = Worker

    start_frequency_in_seconds = models.IntegerField(default=0) ##0 is always

    input_data_list = models.ManyToManyField("IOData", related_name="input_data_list")
    output_data_list = models.ManyToManyField("IOData", related_name="output_data_list")

    python_code = models.TextField(default="")

    running_status = models.IntegerField(default=0) ##0 = Default, 1 = Ready to run, 2 = Running, 3 = Failed
    server_status = models.IntegerField(default=0) ##0 = Default, 1 = Ready to run, 2 = Running, 3 = Failed

    last_logs = models.TextField(default="")

    created_at = models.DateTimeField(auto_now_add=True)
