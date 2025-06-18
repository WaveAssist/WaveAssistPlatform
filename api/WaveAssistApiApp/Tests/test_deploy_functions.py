from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
import json
from WaveAssistApiApp.manage_views import *  # Adjust the import according to your app structure
from WaveAssistApiApp.deployment_views import *
from WaveAssistApiApp.models import *  # Adjust the import according to your app structure
import WaveAssistApiApp.Utils.utils as utils  # Adjust the import according to your app structure
import uuid
from WaveAssistApiApp.Utils.constants import *
from django.urls import reverse


class BuildTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create(username='admin_username')
        self.admin_user.save()
        self.admin_uid = self.admin_user.uid
        self.project = Project.objects.create(
            project_key='test_project_key'
        )
        AccessProvided.objects.create(
            user_object=self.admin_user,
            project_object=self.project,
            type=0,
            project_access_type=ADMIN_GTE
        )

        # Create nodes for the project
        self.node_a = Nodes.objects.create(
            node_key='node_a',
            project_object=self.project,
            is_enabled=True,
            is_starting_node=True
        )
        self.node_b = Nodes.objects.create(
            node_key='node_b',
            project_object=self.project,
            is_enabled=True
        )
        self.node_c = Nodes.objects.create(
            node_key='node_c',
            project_object=self.project,
            is_enabled=True
        )
        self.node_d = Nodes.objects.create(
            node_key='node_d',
            project_object=self.project,
            is_enabled=True
        )

        self.node_e = Nodes.objects.create(
            node_key='node_e',
            project_object=self.project,
            is_enabled=True,
            is_starting_node=True
        )

        self.node_f = Nodes.objects.create(
            node_key='node_f',
            project_object=self.project,
            is_enabled=True
        )

        data_run = DataRuns.objects.create(data_run_key='data_run_1', project_object=self.project, is_enabled=True)
        data_run.save()

        ##Provide access to user
        access_provided_object = AccessProvided.objects.create(
            user_object=self.admin_user,
            data_run_object=data_run,
            type=1,
            data_run_access_type=ADMIN_GTE
        )
        access_provided_object.save()


        ##Create interval object for node_a
        self.interval_object = IntervalSchedule.objects.create(
            every=10,
            period=IntervalSchedule.SECONDS
        )
        self.node_a.interval_schedule = self.interval_object
        self.node_a.save()

        self.cron_object = CrontabSchedule.objects.create(
            minute='0',
            hour='0',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*'
        )
        self.node_e.crontab_schedule = self.cron_object
        self.node_e.save()

        self.input_data_key = DataKey.objects.create(key='valid_input_key', project_object=self.project)
        self.output_data_key = DataKey.objects.create(key='valid_output_key', project_object=self.project)
        self.input_data_key2 = DataKey.objects.create(key='valid_input_key2', project_object=self.project)

        # Set up the DAG relationships: a -> b, c -> d && e -> f
        self.node_b.run_after_nodes_array.add(self.node_a)
        self.node_c.run_after_nodes_array.add(self.node_a)
        self.node_d.run_after_nodes_array.add(self.node_c)
        self.node_d.run_after_nodes_array.add(self.node_b)
        self.node_f.run_after_nodes_array.add(self.node_e)

    ##Build Project Tests
    def test_deploy_project(self):
        request = self.factory.post('/deploy_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'data_run_1',
        })
        response = deploy_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully deployed the project')

        deployment_key = response_data['data']['deployment']['key']

        ##Assert if the Deployment is created
        deployment = Deployments.objects.get(key=deployment_key)
        self.assertEqual(deployment.project_object, self.project)
        self.assertEqual(deployment.data_run_object.data_run_key, 'data_run_1')
        self.assertTrue(deployment.is_running)

        ##Assert of the DAGs are also created
        dags = DAG.objects.filter(parent_deployment=deployment)
        self.assertEqual(dags.count(), 2)
        self.assertEqual(dags[0].start_node, self.node_a)
        self.assertEqual(dags[1].start_node, self.node_e)

        ##Assert that the PeriodicTask is created properly.
        periodic_task = dags[0].periodic_task
        self.assertEqual(periodic_task.interval, self.interval_object)
        # self.assertEqual(periodic_task.task, 'celery_worker.run_dag')


        ##Assert that the PeriodicTask is created properly for the second DAG
        periodic_task2 = dags[1].periodic_task
        self.assertEqual(periodic_task2.crontab, self.cron_object)
        # self.assertEqual(periodic_task2.task, 'celery_worker.run_dag')


        ##Assert kwargs has collection_key as data_run_1
        kwargs_json = json.loads(periodic_task.kwargs)
        self.assertEqual(kwargs_json['collection_key'], 'data_run_1')

        ##Assert kwargs has data_dict with 4 nodes.
        self.assertEqual(len(kwargs_json['data_dict']), 4)

        ##Assert kwargs has dependencies_dict with 4 nodes.
        self.assertEqual(len(kwargs_json['dependencies_dict']), 4)

        ##Assert kwargs has dependencies_dict has node_d, and that has node_b and node_c
        self.assertIn('node_d', kwargs_json['dependencies_dict'])
        self.assertIn('node_b', kwargs_json['dependencies_dict']['node_d'])
        self.assertIn('node_c', kwargs_json['dependencies_dict']['node_d'])



    def test_deploy_again_project(self):
        request = self.factory.post('/deploy_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'data_run_1',
            'version' : '1.0.0'
        })
        response = deploy_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully deployed the project')

        deployment_key = response_data['data']['deployment']['key']

        ##Assert if the Deployment is created
        deployment = Deployments.objects.get(key=deployment_key)
        self.assertEqual(deployment.project_object, self.project)
        self.assertEqual(deployment.data_run_object.data_run_key, 'data_run_1')
        self.assertTrue(deployment.is_running)

        ##Deploy again
        request = self.factory.post('/deploy_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'data_run_1',
            'version' : '2.0.0'
        })
        response = deploy_project(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully deployed the project')
        new_deployment_key = response_data['data']['deployment']['key']

        ##Assert if the Deployment is created
        deployment_new = Deployments.objects.get(key=new_deployment_key)
        self.assertEqual(deployment_new.project_object, self.project)
        self.assertEqual(deployment_new.data_run_object.data_run_key, 'data_run_1')
        self.assertTrue(deployment_new.is_running)

        ##Assert if the old deployment is stopped
        deployment = Deployments.objects.get(key=deployment_key)
        self.assertFalse(deployment.is_running)

        ##Assert if the DAG's of the old deployment are stopped
        dags = DAG.objects.filter(parent_deployment=deployment)
        self.assertEqual(dags.count(), 2)
        self.assertFalse(dags[0].is_running)
        self.assertFalse(dags[1].is_running)

        ##Assert if the PeriodicTask of old deployment is stopped
        self.assertFalse(dags[0].periodic_task.enabled)
        self.assertFalse(dags[1].periodic_task.enabled)




    def test_deploy_with_same_version_error_project(self):
        request = self.factory.post('/deploy_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'data_run_1',
            'version' : '1.0.0'
        })
        response = deploy_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully deployed the project')

        deployment_key = response_data['data']['deployment']['key']

        ##Assert if the deployment is created
        deployment = Deployments.objects.get(key=deployment_key)
        self.assertEqual(deployment.project_object, self.project)
        self.assertEqual(deployment.data_run_object.data_run_key, 'data_run_1')
        self.assertTrue(deployment.is_running)

        ##Deploy again
        request = self.factory.post('/deploy_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'data_run_1',
            'version' : '1.0.0'
        })
        response = deploy_project(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('Version already exists for the project. Please provide a unique version.', response_data['message'])

        ##Assert no new deployment is created
        deployments = Deployments.objects.filter(project_object=self.project, data_run_object__data_run_key='data_run_1', is_running=True)
        self.assertEqual(deployments.count(), 1)

        ##Assert if the old deployment is still running
        deployment = Deployments.objects.get(key=deployment_key)
        self.assertTrue(deployment.is_running)


    def test_deploy_project_failure_invalid_dag(self):
        # Manually create an invalid DAG setup
        self.node_b.run_after_nodes_array.add(self.node_d)  # This would create a cycle


        request = self.factory.post('/deploy_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'data_run_1',
            'version': '1.0.0'
        })
        response = deploy_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        ##Invalid DAG
        self.assertIn('Invalid DAG', response_data['message'])


    def test_deploy_project_failure_no_write_access(self):
        # Create a non-admin user
        non_admin_user = User.objects.create(username='non_admin_user')
        non_admin_user.save()
        non_admin_uid = non_admin_user.uid
        AccessProvided.objects.create(
            user_object=non_admin_user,
            project_object=self.project,
            type=0,
            project_access_type=READ_GTE
        )

        request = self.factory.post('/deploy_project', {
            'uid': non_admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'data_run_1',
            'version': '1.0.0'
        })
        response = deploy_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('You do not have access to this project', response_data['message'])



    def test_deploy_inactive_success(self):
        request = self.factory.post('/deploy_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'data_run_1',
        })
        response = deploy_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully deployed the project')
        deployment_key = response_data['data']['deployment']['key']


        ##Disable node_a
        self.node_a.is_enabled = False
        self.node_a.save()

        ##Disable node_e
        self.node_e.is_enabled = False
        self.node_e.save()

        ##Check if Deployments are still active
        deployment = Deployments.objects.get(key=deployment_key)
        self.assertTrue(deployment.is_running)

        ##Check if the DAGs are still active
        dags = DAG.objects.filter(parent_deployment=deployment)
        self.assertEqual(dags.count(), 2)
        self.assertTrue(dags[0].is_running)
        self.assertTrue(dags[1].is_running)

        ##Assert starting node of the DAGs
        self.assertEqual(dags[0].start_node, self.node_a)
        self.assertEqual(dags[1].start_node, self.node_e)



        ##BUILD AGAIN
        request = self.factory.post('/deploy_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'data_run_1',
        })
        response = deploy_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        ##No enabled starting nodes found in the project to build
        self.assertIn('No enabled starting nodes found in the project to Deploy', response_data['message'])

        ##Assert only one deployment is active
        deployments = Deployments.objects.filter(project_object=self.project, data_run_object__data_run_key='data_run_1', is_running=True)
        self.assertEqual(deployments.count(), 1)

        ##Assert if the old deployment is still running
        deployment = Deployments.objects.get(key=deployment_key)
        self.assertTrue(deployment.is_running)



    def test_build_delete_node(self):
        request = self.factory.post('/deploy_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'data_run_1',
        })
        response = deploy_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully deployed the project')
        deployment_key = response_data['data']['deployment']['key']

        ##Delete node_a
        self.node_a.delete()

        ##Check status of the deployment
        deployment = Deployments.objects.get(key=deployment_key)
        self.assertTrue(deployment.is_running)

        ##Check status of the DAGs
        dags = DAG.objects.filter(parent_deployment=deployment)
        self.assertEqual(dags.count(), 2)
        self.assertTrue(dags[0].is_running)
        self.assertTrue(dags[1].is_running)


        ##Assert that the PeriodicTask is created properly.
        periodic_task = dags[0].periodic_task
        self.assertEqual(periodic_task.interval, self.interval_object)
        self.assertEqual(periodic_task.task, 'celery_worker.run_dag')

        ##Assert kwargs has collection_key as data_run_1
        kwargs_json = json.loads(periodic_task.kwargs)
        self.assertEqual(kwargs_json['collection_key'], 'data_run_1')

        ##Assert kwargs has data_dict with 4 nodes.
        self.assertEqual(len(kwargs_json['data_dict']), 4)

        ##Assert kwargs has dependencies_dict with 4 nodes.
        self.assertEqual(len(kwargs_json['dependencies_dict']), 4)

        ##Assert kwargs has dependencies_dict has node_d, and that has node_b and node_c
        self.assertIn('node_d', kwargs_json['dependencies_dict'])
        self.assertIn('node_b', kwargs_json['dependencies_dict']['node_d'])
        self.assertIn('node_c', kwargs_json['dependencies_dict']['node_d'])

        self.assertIn('node_a', kwargs_json['dependencies_dict'])

    def test_stop_deployment(self):
        request = self.factory.post('/deploy_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'data_run_1',
        })
        response = deploy_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully deployed the project')
        deployment_key = response_data['data']['deployment']['key']

        ##Stop the deployment
        request = self.factory.post('/stop_deployment', {
            'uid': self.admin_uid,
            'deployment_key': deployment_key
        })
        response = stop_deployment(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully stopped the deployment.')

        ##Check if the deployment is stopped
        deployment = Deployments.objects.get(key=deployment_key)
        self.assertFalse(deployment.is_running)

        ##Check if the DAGs are stopped
        dags = DAG.objects.filter(parent_deployment=deployment)
        self.assertEqual(dags.count(), 2)
        self.assertFalse(dags[0].is_running)
        self.assertFalse(dags[1].is_running)

        ##Check if the PeriodicTask is stopped
        self.assertFalse(dags[0].periodic_task.enabled)
        self.assertFalse(dags[1].periodic_task.enabled)

    def test_run_dag_function(self):
        request = self.factory.post('/run_dag', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'data_run_1',
            'start_node_key':'node_a'
        })
        response = run_dag(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully started the DAG')

