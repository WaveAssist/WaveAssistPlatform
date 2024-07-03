from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
import json
from WaveAssistApiApp.manage_views import *  # Adjust the import according to your app structure
from WaveAssistApiApp.build_views import *
from WaveAssistApiApp.models import *  # Adjust the import according to your app structure
import WaveAssistApiApp.Utils.utils as utils  # Adjust the import according to your app structure
import uuid
from WaveAssistApiApp.Utils.constants import *
from django.urls import reverse


##TODO: Check code added on run.
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


        ##Create interval object for node_a
        self.interval_object = IntervalSchedule.objects.create(
            every=10,
            period=IntervalSchedule.SECONDS
        )
        self.node_a.interval_schedule = self.interval_object
        self.node_a.save()


        self.input_data_key = DataKey.objects.create(key='valid_input_key', project_object=self.project)
        self.output_data_key = DataKey.objects.create(key='valid_output_key', project_object=self.project)
        self.input_data_key2 = DataKey.objects.create(key='valid_input_key2', project_object=self.project)

        # Set up the DAG relationships: a -> b, c -> d
        self.node_b.run_after_nodes_array.add(self.node_a)
        self.node_c.run_after_nodes_array.add(self.node_a)
        self.node_d.run_after_nodes_array.add(self.node_c)
        self.node_d.run_after_nodes_array.add(self.node_b)

    ##Build Project Tests
    def test_build_project_success(self):
        request = self.factory.post('/build_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key'
        })
        response = build_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Project built successfully.')
        self.assertEqual(response_data['data']['build_status'], 'build successful')

        # Assert that DAG objects are created/updated
        dag = DAG.objects.get(dag_key='test_project_key-node_a', is_enabled=True)
        self.assertEqual(dag.start_node, self.node_a)

    def test_build_project_update_success(self):
        request = self.factory.post('/build_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key'
        })
        response = build_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Project built successfully.')
        self.assertEqual(response_data['data']['build_status'], 'build successful')

        # Assert that DAG objects are created/updated
        dag = DAG.objects.get(dag_key='test_project_key-node_a', is_enabled=True)
        self.assertEqual(dag.start_node, self.node_a)

        ##Update the DAG
        self.node_d.run_after_nodes_array.add(self.node_a)
        node_e = Nodes.objects.create(
            node_key='node_e',
            project_object=self.project,
            is_enabled=True,
            is_starting_node=False
        )
        node_e.save()

        ##Add node_e to the DAG
        node_e.run_after_nodes_array.add(self.node_d)

        ##BUILD AGAIN
        request = self.factory.post('/build_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key'
        })
        response = build_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Project built successfully.')
        self.assertEqual(response_data['data']['build_status'], 'build successful')

        # Assert that DAG objects are created/updated
        dag = DAG.objects.get(dag_key='test_project_key-node_a', is_enabled=True)
        self.assertEqual(dag.start_node, self.node_a)

        ##Asset that node_e is added to the DAG
        self.assertEqual(dag.node_array.all().count(), 5)
        self.assertIn(node_e, dag.node_array.all())


    def test_build_project_failure_invalid_dag(self):
        # Manually create an invalid DAG setup
        self.node_b.run_after_nodes_array.add(self.node_d)  # This would create a cycle

        request = self.factory.post('/build_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key'
        })
        response = build_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('Invalid DAG', response_data['message'])


    def test_build_project_failure_no_write_access(self):
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

        request = self.factory.post('/build_project', {
            'uid': non_admin_uid,
            'project_key': 'test_project_key'
        })
        response = build_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('You do not have access to this project', response_data['message'])



    def test_build_inactive_success(self):
        request = self.factory.post('/build_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key'
        })
        response = build_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Project built successfully.')
        self.assertEqual(response_data['data']['build_status'], 'build successful')

        # Assert that DAG objects are created/updated
        dag = DAG.objects.get(dag_key='test_project_key-node_a', is_enabled=True)
        self.assertEqual(dag.start_node, self.node_a)

        ##Update the DAG

        ##Disable node_a
        self.node_a.is_enabled = False
        self.node_a.save()

        ##Check if DAG is still active
        dag_array = DAG.objects.filter(dag_key='test_project_key-node_a')
        self.assertEqual(len(dag_array), 1)
        self.assertTrue(dag_array[0].is_enabled)


        ##BUILD AGAIN
        ##BUILD AGAIN
        request = self.factory.post('/build_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key'
        })
        response = build_project(request)
        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        ##No enabled starting nodes found in the project to build
        self.assertIn('No enabled starting nodes found in the project to build', response_data['message'])


        dag_array = DAG.objects.filter(dag_key='test_project_key-node_a')
        self.assertEqual(len(dag_array), 1)


    def test_build_delete_node(self):
        request = self.factory.post('/build_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key'
        })
        response = build_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Project built successfully.')
        self.assertEqual(response_data['data']['build_status'], 'build successful')

        # Assert that DAG objects are created/updated
        dag = DAG.objects.get(dag_key='test_project_key-node_a', is_enabled=True)
        self.assertEqual(dag.start_node, self.node_a)

        ##Update the DAG
        dag_array = DAG.objects.filter(dag_key='test_project_key-node_a')
        self.assertEqual(len(dag_array), 1)

        ##Delete node_a
        self.node_a.delete()

        dag_array = DAG.objects.filter(dag_key='test_project_key-node_a')
        self.assertEqual(len(dag_array), 0)



    def test_build_extra_dags(self):
        request = self.factory.post('/build_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key'
        })
        response = build_project(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Project built successfully.')
        self.assertEqual(response_data['data']['build_status'], 'build successful')

        # Assert that DAG objects are created/updated
        dag = DAG.objects.get(dag_key='test_project_key-node_a', is_enabled=True)
        self.assertEqual(dag.start_node, self.node_a)

        ##Update the DAG
        self.node_a.is_enabled = False
        self.node_a.save()

        ##Add a new starting node
        node_e = Nodes.objects.create(
            node_key='node_e',
            project_object=self.project,
            is_enabled=True,
            is_starting_node=True,
            interval_schedule = self.interval_object
        )
        node_e.save()

        ##Add node e to the node_b run_after
        self.node_b.run_after_nodes_array.add(node_e)
        self.node_b.save()

        ##BUILD AGAIN
        request = self.factory.post('/build_project', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key'
        })
        response = build_project(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Project built successfully.')

        ##Check if the new DAG is created
        dag = DAG.objects.get(dag_key='test_project_key-node_e', is_enabled=True)
        self.assertEqual(dag.start_node, node_e)
        self.assertEqual(dag.node_array.all().count(), 4)
        self.assertIn(node_e, dag.node_array.all())
        self.assertIn(self.node_b, dag.node_array.all())

        ##Check if the original dag is marked inactive
        dag_array = DAG.objects.filter(dag_key='test_project_key-node_a')
        self.assertEqual(len(dag_array), 1)
        self.assertFalse(dag_array[0].is_enabled)



    ##DataRuns
    def test_start_dag_for_data_run_success(self):
        # Create a data run object associated with the project
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

        # Create a DAG object associated with the project
        dag = DAG.objects.create(
            dag_key='test_project_key-node_a',
            project_object=self.project,
            start_node=self.node_a,
            interval_schedule=self.interval_object,
            is_enabled=True
        )
        node_array = [self.node_a, self.node_b, self.node_c, self.node_d]
        dag.node_array.set(node_array)
        dag.save()

        request = self.factory.post('/start_project_for_data_run', {
            'uid': self.admin_uid,
            'data_run_key': 'data_run_1'
        })
        response = start_project_for_data_run(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully started the data run for your project.')

        # Assert that the DAGRun and PeriodicTask objects are created
        dag_run = DAGRun.objects.get(dag_run_key='test_project_key-node_a-data_run_1')
        self.assertTrue(dag_run.is_running)
        self.assertTrue(dag_run.periodic_task.enabled)

    def test_start_dag_for_data_run_failure_no_access(self):
        # Create a data run object associated with the project
        data_run = DataRuns.objects.create(data_run_key='data_run_1', project_object=self.project, is_enabled=True)
        data_run.save()

        ##Provide access to user
        access_provided_object = AccessProvided.objects.create(
            user_object=self.admin_user,
            data_run_object=data_run,
            type=1,
            data_run_access_type=READ_GTE
        )
        access_provided_object.save()

        # Create a DAG object associated with the project
        dag = DAG.objects.create(
            dag_key='test_project_key-node_a',
            project_object=self.project,
            start_node=self.node_a,
            interval_schedule=self.interval_object,
            is_enabled=True
        )
        node_array = [self.node_a, self.node_b, self.node_c, self.node_d]
        dag.node_array.set(node_array)
        dag.save()

        request = self.factory.post('/start_project_for_data_run', {
            'uid': self.admin_uid,
            'data_run_key': 'data_run_1'
        })
        response = start_project_for_data_run(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'You do not have access to this data run')

        # Assert that the DAGRun and PeriodicTask objects are not created
        dag_run_array = DAGRun.objects.filter(dag_run_key='test_project_key-node_a-data_run_1')
        self.assertEqual(len(dag_run_array), 0)


    def test_stop_dag_run_success(self):
        # Create a data run object associated with the project
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

        # Create a DAG object associated with the project
        dag = DAG.objects.create(
            dag_key='test_project_key-node_a',
            project_object=self.project,
            start_node=self.node_a,
            interval_schedule=self.interval_object,
            is_enabled=True
        )
        node_array = [self.node_a, self.node_b, self.node_c, self.node_d]
        dag.node_array.set(node_array)
        dag.save()

        request = self.factory.post('/start_project_for_data_run', {
            'uid': self.admin_uid,
            'data_run_key': 'data_run_1'
        })
        response = start_project_for_data_run(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully started the data run for your project.')

        # Assert that the DAGRun and PeriodicTask objects are created
        dag_run = DAGRun.objects.get(dag_run_key='test_project_key-node_a-data_run_1')
        self.assertTrue(dag_run.is_running)
        self.assertTrue(dag_run.periodic_task.enabled)


        request = self.factory.post('/stop_dag_run', {
            'uid': self.admin_uid,
            'data_run_key': 'data_run_1'
        })
        response = stop_project_for_data_run(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully stopped the data run for your project.')

        ##Check if DAGS are stopped
        dag_run = DAGRun.objects.get(dag_run_key='test_project_key-node_a-data_run_1')
        self.assertFalse(dag_run.is_running)
        self.assertFalse(dag_run.periodic_task.enabled)


    def test_start_dag_for_data_run_update_existing(self):
        # Create a data run object associated with the project
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

        # Create a DAG object associated with the project
        dag = DAG.objects.create(
            dag_key='test_project_key-node_a',
            project_object=self.project,
            start_node=self.node_a,
            interval_schedule=self.interval_object,
            is_enabled=True
        )
        node_array = [self.node_a, self.node_b, self.node_c, self.node_d]
        dag.node_array.set(node_array)
        dag.save()

        # Create an existing DAGRun and PeriodicTask
        periodic_task = PeriodicTask.objects.create(
            interval=self.interval_object,
            name='test_project_key-node_a-data_run_1',
            task='celery_worker.run_dag',
            kwargs=json.dumps({
                'dependencies_dict': {},
                'data_dict': {},
                'collection_key': 'data_run_1'
            }),
            one_off=False,
            enabled=False
        )
        periodic_task.save()

        dag_run = DAGRun.objects.create(
            dag_run_key='test_project_key-node_a-data_run_1',
            dag_object=dag,
            data_run_object=data_run,
            is_running=False,
            periodic_task=periodic_task,
            is_enabled=True
        )
        dag_run.save()

        request = self.factory.post('/start_project_for_data_run', {
            'uid': self.admin_uid,
            'data_run_key': 'data_run_1'
        })
        response = start_project_for_data_run(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully started the data run for your project.')

        # Assert that the DAGRun and PeriodicTask objects are updated
        dag_run.refresh_from_db()
        self.assertTrue(dag_run.is_running)
        self.assertTrue(dag_run.periodic_task.enabled)
        self.assertEqual(dag_run.periodic_task.interval, self.interval_object)


    def test_start_dag_for_data_run_disable_existing(self):
        # Create a data run object associated with the project
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

        # Create a DAG object associated with the project
        dag = DAG.objects.create(
            dag_key='test_project_key-node_a',
            project_object=self.project,
            start_node=self.node_a,
            interval_schedule=self.interval_object,
            is_enabled=False  # Disable this DAG to trigger disable loop
        )
        node_array = [self.node_a, self.node_b, self.node_c, self.node_d]
        dag.node_array.set(node_array)
        dag.save()

        # Create an existing DAGRun and PeriodicTask
        periodic_task = PeriodicTask.objects.create(
            interval=self.interval_object,
            name='test_project_key-node_a-data_run_1',
            task='celery_worker.run_dag',
            kwargs=json.dumps({
                'dependencies_dict': {},
                'data_dict': {},
                'collection_key': 'data_run_1'
            }),
            one_off=False,
            enabled=True
        )
        periodic_task.save()

        dag_run = DAGRun.objects.create(
            dag_run_key='test_project_key-node_a-data_run_1',
            dag_object=dag,
            data_run_object=data_run,
            is_running=True,
            periodic_task=periodic_task,
            is_enabled=True
        )
        dag_run.save()

        request = self.factory.post('/start_project_for_data_run', {
            'uid': self.admin_uid,
            'data_run_key': 'data_run_1'
        })
        response = start_project_for_data_run(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully started the data run for your project.')

        # Assert that the DAGRun and PeriodicTask objects are disabled
        dag_run.refresh_from_db()
        self.assertFalse(dag_run.is_enabled)
        self.assertFalse(dag_run.periodic_task.enabled)
