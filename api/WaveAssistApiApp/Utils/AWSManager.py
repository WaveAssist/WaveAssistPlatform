import boto3
import json
from django.conf import settings
from constants import *

UID = '9088b203-66a6-4c0d-a57a-31b33963a6c8'

AWS_SUBNETS = [
    "subnet-03cccfff54a6e3773",
    "subnet-0533f695b991c48a6",
    "subnet-0b17fa83bd1c04057",
    "subnet-0d08d90cec1b37c5c",
    "subnet-0b5550e4d4513f556",
    "subnet-0ed494a15183076af"
]

AWS_SECURITY_GROUPS = ['sg-0bea94ea56d183f43']
AWS_CLUSTER = 'WaveAssistFargateCluster'

AWS_TASK_DEF_JSON = {
    "containerDefinitions": [
        {
            "name": "worker",
            "image": "713358430452.dkr.ecr.us-east-1.amazonaws.com/waveassist_celery_worker:latest",
            "cpu": 0,
            "portMappings": [],
            "essential": True,
            "environment": [
                {
                    "name": "ACCOUNT_ID",
                    "value": f"{UID}"
                }
            ],
            "mountPoints": [],
            "volumesFrom": [],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/WaveAssistWorkerTasks",
                    "mode": "non-blocking",
                    "awslogs-create-group": "true",
                    "max-buffer-size": "25m",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "ecs"
                },
                "secretOptions": []
            },
            "systemControls": []
        }
    ],
    "family": f"WaveAssistWorkerTasks__{UID}",
    "taskRoleArn": "arn:aws:iam::713358430452:role/ecsTaskExecutionRole",
    "executionRoleArn": "arn:aws:iam::713358430452:role/ecsTaskExecutionRole",
    "networkMode": "awsvpc",
    "volumes": [],
    "placementConstraints": [],

    "requiresCompatibilities": [
        "FARGATE"
    ],
    "cpu": "512",
    "memory": "2048",
    "runtimePlatform": {
        "cpuArchitecture": "X86_64",
        "operatingSystemFamily": "LINUX"
    },

}

# Initialize the ECS client
ecs_client = boto3.client('ecs', region_name="us-east-1", aws_access_key_id=AWSS3_ACCESS_KEY_VALUE,
                          aws_secret_access_key=AWSS3_SECRET_KEY_VALUE)


def register_task_definition(task_definition_json):
    """
    Registers a new ECS task definition using the provided JSON.
    """
    print("This is register_task_definition")
    try:
        response = ecs_client.register_task_definition(**task_definition_json)
        return response["taskDefinition"]["taskDefinitionArn"]
    except Exception as e:
        print(f"Error registering task: {e}")
        return None


def create_fargate_service(service_name, task_definition_arn, subnet_ids=AWS_SUBNETS,
                           security_group_ids=AWS_SECURITY_GROUPS, cluster_name=AWS_CLUSTER):
    """
    Creates an ECS service in Fargate mode running the specified task definition.
    """
    print("This is create_fargate_service")
    try:
        response = ecs_client.create_service(
            cluster=cluster_name,
            serviceName=service_name,
            taskDefinition=task_definition_arn,
            launchType="FARGATE",
            desiredCount=1,  # Adjust as needed
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": subnet_ids,
                    "securityGroups": security_group_ids,
                    "assignPublicIp": "ENABLED"
                }
            }
        )
        return response["service"]["serviceArn"]
    except Exception as e:
        print(f"Error creating service: {e}")
        return None


# # Sample Usage
task_arn = register_task_definition(AWS_TASK_DEF_JSON)
service_name = "WaveAssistWorkerService_{}".format(UID)
service_arn = create_fargate_service(service_name=service_name,
                                     task_definition_arn=task_arn)
print(f"Service ARN: {service_arn}")
