from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
import json
from WaveAssistApiApp.manage_views import *  # Adjust the import according to your app structure
from WaveAssistApiApp.models import *  # Adjust the import according to your app structure
import WaveAssistApiApp.Utils.utils as utils  # Adjust the import according to your app structure
import uuid
from WaveAssistApiApp.Utils.constants import *
from django.urls import reverse

class NodeTestCase(TestCase):
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

        self.input_data_key = DataKey.objects.create(key='valid_input_key', project_object=self.project)
        self.output_data_key = DataKey.objects.create(key='valid_output_key', project_object=self.project)
        self.input_data_key2 = DataKey.objects.create(key='valid_input_key2', project_object=self.project)




        # Set up the DAG relationships: a -> b, c -> d
        self.node_b.run_after_nodes_array.add(self.node_a)
        self.node_c.run_after_nodes_array.add(self.node_a)
        self.node_d.run_after_nodes_array.add(self.node_c)
        self.node_d.run_after_nodes_array.add(self.node_b)



    ##Delete Tests
    def test_delete_node_success_end(self):
        request = self.factory.post('/delete_node', {
            'node_key': 'node_d',
            'uid': self.admin_uid,
            'project_key': 'test_project_key'
        })
        response = delete_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Node deleted successfully.')

        ##Asset if node is actually deleted from DB
        with self.assertRaises(Nodes.DoesNotExist):
            Nodes.objects.get(node_key='node_d')


    def test_delete_node_success_middle(self):
        request = self.factory.post('/delete_node', {
            'node_key': 'node_b',
            'uid': self.admin_uid,
            'project_key': 'test_project_key'
        })
        response = delete_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Node deleted successfully.')

        ##Asset if node is actually deleted from DB
        with self.assertRaises(Nodes.DoesNotExist):
            Nodes.objects.get(node_key='node_b')


    def test_delete_node_failure_starting_node(self):
        request = self.factory.post('/delete_node', {
            'node_key': 'node_a',
            'uid': self.admin_uid,
            'project_key': 'test_project_key'
        })
        response = delete_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Something went wrong while deleting Node, error: No starting node found in project, ensure you have at least one starting node.')

        ##Asset if node is actually not deleted from DB
        self.assertTrue(Nodes.objects.filter(node_key='node_a').exists())



    ##Update code tests:
    def test_update_code_success(self):
        request = self.factory.post('/update_code', {
            'node_key': 'node_a',
            'python_code': 'print("New code")',
            'uid': self.admin_uid
        })
        response = update_code(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Code updated successfully.')
        self.node_a.refresh_from_db()
        self.assertEqual(self.node_a.python_code, 'print("New code")')

    def test_update_code_node_not_found(self):
        request = self.factory.post('/update_code', {
            'node_key': 'nonexistent_node',
            'python_code': 'print("New code")',
            'uid': self.admin_uid
        })
        response = update_code(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Node not found')



    ##Test create nodes
    def test_create_node_success_starting_node(self):
        request = self.factory.post('/create_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'test_project_key_node_e',
            'is_enabled': '1',
            'is_starting_node': '1',
            'schedule_type': 'interval',
            'interval_every': '10',
            'interval_type': 'seconds',
            'input_data_key_csv': '',
            'output_data_key_csv': '',
            'run_after_nodes_csv': ''
        })
        response = create_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Node updated successfully.')

        # Assert if node is actually created in the DB
        node = Nodes.objects.get(node_key='test_project_key_node_e')
        self.assertEqual(node.node_key, 'test_project_key_node_e')
        self.assertEqual(node.is_enabled, True)
        self.assertEqual(node.is_starting_node, True)
        self.assertEqual(node.schedule_type, 'interval')

    def test_create_node_success_non_starting_node(self):
        request = self.factory.post('/create_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'test_project_key_node_f',
            'is_enabled': '1',
            'is_starting_node': '0',
            'schedule_type': 'none',
            'input_data_key_csv': '',
            'output_data_key_csv': '',
            'run_after_nodes_csv': 'node_a'
        })
        response = create_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Node updated successfully.')

        # Assert if node is actually created in the DB
        node = Nodes.objects.get(node_key='test_project_key_node_f')
        self.assertEqual(node.node_key, 'test_project_key_node_f')
        self.assertEqual(node.is_enabled, True)
        self.assertEqual(node.is_starting_node, False)
        self.assertEqual(node.schedule_type, 'none')
        self.assertIn(self.node_a, node.run_after_nodes_array.all())

    def test_create_node_key_validation_failure(self):
        request = self.factory.post('/create_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'invalid_node_key',
            'is_enabled': '1',
            'is_starting_node': '1',
            'schedule_type': 'interval',
            'interval_every': '10',
            'interval_type': 'seconds',
            'input_data_key_csv': '',
            'output_data_key_csv': '',
            'run_after_nodes_csv': ''
        })
        response = create_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Key should start with project key + _')


    def test_create_node_missing_run_after_nodes(self):
        # Attempt to create a non-starting node without specifying run_after_nodes
        request = self.factory.post('/create_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'test_project_key_missing_run_after',
            'is_enabled': '1',
            'is_starting_node': '0',
            'schedule_type': 'none',
            'input_data_key_csv': '',
            'output_data_key_csv': '',
            'run_after_nodes_csv': ''
        })
        response = create_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'],
                         'Invalid/Not found run after nodes. Please provide valid run after nodes as this is not a starting node')

    def test_create_node_invalid_input_keys(self):
        # Attempt to create a node with invalid input keys
        request = self.factory.post('/create_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'test_project_key_invalid_input_keys',
            'is_enabled': '1',
            'is_starting_node': '1',
            'schedule_type': 'interval',
            'interval_every': '10',
            'interval_type': 'seconds',
            'input_data_key_csv': 'invalid_key',
            'output_data_key_csv': '',
            'run_after_nodes_csv': ''
        })
        response = create_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Input data keys should belong to this project: Data Key invalid_key not found in project')



    def test_create_node_valid_keys(self):
        # Create valid input and output data keys for the project

        request = self.factory.post('/create_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'test_project_key_valid_keys',
            'is_enabled': '1',
            'is_starting_node': '1',
            'schedule_type': 'interval',
            'interval_every': '10',
            'interval_type': 'seconds',
            'input_data_key_csv': 'valid_input_key, valid_input_key2',
            'output_data_key_csv': 'valid_output_key',
            'run_after_nodes_csv': ''
        })
        response = create_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Node updated successfully.')

        # Assert if node is actually created in the DB
        node = Nodes.objects.get(node_key='test_project_key_valid_keys')
        self.assertEqual(node.node_key, 'test_project_key_valid_keys')
        self.assertEqual(node.is_enabled, True)
        self.assertEqual(node.is_starting_node, True)
        self.assertEqual(node.schedule_type, 'interval')

        # Check if the input and output keys are correctly associated
        self.assertIn(self.input_data_key, node.input_data_key_array.all())
        self.assertIn(self.input_data_key2, node.input_data_key_array.all())
        self.assertIn(self.output_data_key, node.output_data_key_array.all())


    ##Update node test cases

    def test_update_node_failure_start_node_interval(self):
        # Update node with valid input and output data keys
        request = self.factory.post('/update_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'node_a',
            'is_enabled': '1',
            'input_data_key_csv': 'valid_input_key',
            'output_data_key_csv': 'valid_output_key',
            'schedule_type': 'interval',
            'interval_type': 'seconds'
        })
        response = update_node(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('Something went wrong while updating Node: All schedule params are required',
                      response_data['message'])
    def test_update_node_success_start_node(self):
        # Update node with valid input and output data keys
        request = self.factory.post('/update_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'node_a',
            'is_enabled': '1',
            'input_data_key_csv': 'valid_input_key',
            'output_data_key_csv': 'valid_output_key',
            'schedule_type': 'interval',
            'interval_every': '30',
            'interval_type': 'seconds'
        })
        response = update_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Node updated successfully.')

        # Assert if node is actually updated in the DB
        node = Nodes.objects.get(node_key='node_a')
        self.assertEqual(node.is_enabled, True)
        self.assertIn(self.input_data_key, node.input_data_key_array.all())
        self.assertIn(self.output_data_key, node.output_data_key_array.all())
        self.assertEqual(node.schedule_type, 'interval')
        self.assertEqual(node.interval_schedule.every, 30)

    def test_update_node_failure_start_node_crontab(self):
        # Attempt to update a starting node with an incomplete crontab schedule
        request = self.factory.post('/update_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'node_a',
            'is_enabled': '1',
            'input_data_key_csv': 'valid_input_key',
            'output_data_key_csv': 'valid_output_key',
            'schedule_type': 'crontab',
            'crontab_minutes': '*',
            'crontab_hours': '*',
            'crontab_days_of_month': '*',
            # Missing 'crontab_months_of_year', 'crontab_days_of_week', 'crontab_timezone'
        })
        response = update_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('Something went wrong while updating Node: All schedule params are required',
                      response_data['message'])

    def test_update_node_success_start_node_crontab(self):
        # Update a starting node with a valid crontab schedule
        request = self.factory.post('/update_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'node_a',
            'is_enabled': '1',
            'input_data_key_csv': 'valid_input_key',
            'output_data_key_csv': 'valid_output_key',
            'schedule_type': 'crontab',
            'crontab_minutes': '*',
            'crontab_hours': '0',
            'crontab_days_of_month': '*',
            'crontab_months_of_year': '*',
            'crontab_days_of_week': '1',
            'crontab_timezone': 'UTC'
        })
        response = update_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Node updated successfully.')

        # Assert if node is actually updated in the DB
        node = Nodes.objects.get(node_key='node_a')
        self.assertEqual(node.is_enabled, True)
        self.assertIn(self.input_data_key, node.input_data_key_array.all())
        self.assertIn(self.output_data_key, node.output_data_key_array.all())
        self.assertEqual(node.schedule_type, 'crontab')
        self.assertEqual(node.crontab_schedule.minute, '*')
        self.assertEqual(node.crontab_schedule.hour, '0')
        self.assertEqual(node.crontab_schedule.day_of_month, '*')
        self.assertEqual(node.crontab_schedule.month_of_year, '*')
        self.assertEqual(node.crontab_schedule.day_of_week, '1')

    def test_update_node_invalid_crontab_format(self):
        # Attempt to update a starting node with an invalid crontab schedule format
        request = self.factory.post('/update_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'node_a',
            'is_enabled': '1',
            'input_data_key_csv': 'valid_input_key',
            'output_data_key_csv': 'valid_output_key',
            'schedule_type': 'crontab',
            'crontab_minutes': 'invalid',  # Invalid format
            'crontab_hours': '0',
            'crontab_days_of_month': '*',
            'crontab_months_of_year': '*',
            'crontab_days_of_week': '1',
            'crontab_timezone': 'UTC'
        })
        response = update_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('Something went wrong while updating Node: Invalid value for minute:', response_data['message'])

    def test_update_node_not_found(self):
        # Attempt to update a non-existent node
        request = self.factory.post('/update_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'nonexistent_node'
        })
        response = update_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Node not found.')

    def test_update_node_invalid_input_keys(self):
        # Attempt to update node with invalid input keys
        request = self.factory.post('/update_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'node_a',
            'input_data_key_csv': 'invalid_key'
        })
        response = update_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('Something went wrong while updating Node: Input data keys should belong to this project:',response_data['message'])

    def test_update_node_valid_input_keys(self):
        # Attempt to update the node with valid input keys
        request = self.factory.post('/update_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'node_a',
            'input_data_key_csv': 'valid_input_key,valid_input_key2'
        })
        response = update_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Node updated successfully.')

        # Assert if the node is actually updated in the DB with the valid input key
        node = Nodes.objects.get(node_key='node_a')
        self.assertIn(self.input_data_key, node.input_data_key_array.all())
        self.assertIn(self.input_data_key2, node.input_data_key_array.all())



    def test_update_node_invalid_dag(self):
        # Update node in a way that creates an invalid DAG
        request = self.factory.post('/update_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'node_c',
            'run_after_nodes_csv': 'node_d'
        })
        response = update_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('Invalid DAG', response_data['message'])
        ##Check if the node is not updated, by checking the run_after_nodes_array for node_c
        node = Nodes.objects.get(node_key='node_c')
        self.assertNotIn(self.node_d, node.run_after_nodes_array.all())


    def test_update_node_success_middle_node(self):
        # Update node_b with valid input and output data keys and new run_after_nodes_csv
        request = self.factory.post('/update_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'node_d',
            'is_enabled': '1',
            'input_data_key_csv': 'valid_input_key',
            'output_data_key_csv': 'valid_output_key',
            'run_after_nodes_csv': 'node_a,node_b,node_c'
        })
        response = update_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Node updated successfully.')

        # Assert if node is actually updated in the DB
        node = Nodes.objects.get(node_key='node_d')
        self.assertEqual(node.is_enabled, True)
        self.assertIn(self.input_data_key, node.input_data_key_array.all())
        self.assertIn(self.output_data_key, node.output_data_key_array.all())
        self.assertIn(self.node_a, node.run_after_nodes_array.all())
        self.assertIn(self.node_b, node.run_after_nodes_array.all())
        self.assertIn(self.node_c, node.run_after_nodes_array.all())


    def test_update_node_failure_middle_node_invalid_run_after(self):
        # Attempt to update node_d with invalid run_after_nodes_csv
        request = self.factory.post('/update_node', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'node_key': 'node_d',
            'is_enabled': '1',
            'input_data_key_csv': 'valid_input_key',
            'output_data_key_csv': 'valid_output_key',
            'run_after_nodes_csv': 'invalid_node'
        })
        response = update_node(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('Something went wrong while updating Node: Invalid/Not found run after nodes.', response_data['message'])
