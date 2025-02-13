import boto3
import json
from django.conf import settings
from constants import *

AWS_SUBNETS  = [
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
    "family": "waveassist-task",
    "networkMode": "awsvpc",
    "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
    "containerDefinitions": [
        {
            "name": "waveassist-container",
            "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/waveassist:latest",
            "memory": 512,
            "cpu": 256,
            "essential": True,
            "portMappings": [{"containerPort": 8080, "hostPort": 8080}]
        }
    ],
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "256",
    "memory": "512"
}


# Initialize the ECS client
ecs_client = boto3.client('ecs', region_name="us-east-1")  # Update region if needed

def register_task_definition(task_definition_json):
    """
    Registers a new ECS task definition using the provided JSON.
    """
    try:
        response = ecs_client.register_task_definition(**task_definition_json)
        return response["taskDefinition"]["taskDefinitionArn"]
    except Exception as e:
        print(f"Error registering task: {e}")
        return None




def create_fargate_service(service_name, task_definition_arn, subnet_ids=AWS_SUBNETS, security_group_ids=AWS_SECURITY_GROUPS, cluster_name=AWS_CLUSTER):
    """
    Creates an ECS service in Fargate mode running the specified task definition.
    """
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
                    "assignPublicIp": "DISABLED"
                }
            }
        )
        return response["service"]["serviceArn"]
    except Exception as e:
        print(f"Error creating service: {e}")
        return None

# # Sample Usage
# task_arn = register_task_definition(AWS_TASK_DEF_JSON)
# service_arn = create_fargate_service(service_name="WaveAssistService", task_definition_arn=task_arn)
# print(f"Service ARN: {service_arn}")
