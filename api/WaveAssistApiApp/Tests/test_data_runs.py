from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
import json
from WaveAssistApiApp.manage_views import *  # Adjust the import according to your app structure
from WaveAssistApiApp.models import *  # Adjust the import according to your app structure
import WaveAssistApiApp.Utils.utils as utils  # Adjust the import according to your app structure
import uuid
from WaveAssistApiApp.Utils.constants import *


from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from unittest.mock import patch
import json
from WaveAssistApiApp.manage_views import create_data_run, update_data_run, delete_data_run  # Adjust the import according to your app structure
from WaveAssistApiApp.models import *  # Adjust the import according to your app structure
import WaveAssistApiApp.Utils.utils as utils  # Adjust the import according to your app structure

class DataRunTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(username='admin', can_create_projects=True)
        self.user.save()
        self.admin_uid = self.user.uid

        self.project = Project.objects.create(project_key='test_project_key')
        AccessProvided.objects.create(
            user_object=self.user,
            project_object=self.project,
            type=0,
            project_access_type=ADMIN_GTE
        )
        self.project.save()

    def test_create_data_run_success(self):
        request = self.factory.post('/create_data_run', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'name': 'test_data_run',
            'is_enabled': '1'
        })

        response = create_data_run(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])
        self.assertEqual(response_data['data']['name'], 'test_data_run')

    def test_create_data_run_duplicate_name(self):
        DataRuns.objects.create(
            name='test_data_run',
            data_run_key='test_project_key_test_data_run',
            project_object=self.project,
            is_enabled=True
        )

        request = self.factory.post('/create_data_run', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'name': 'test_data_run',
            'is_enabled': '1'
        })

        response = create_data_run(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertEqual(response_data['message'], 'Something went wrong while creating Data Run, make sure your data_run name is unique')

    def test_update_data_run_success(self):
        data_run = DataRuns.objects.create(
            name='test_data_run',
            data_run_key='test_project_key_test_data_run',
            project_object=self.project,
            is_enabled=True
        )

        request = self.factory.post('/update_data_run', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': data_run.data_run_key,
            'name': 'updated_data_run',
            'is_enabled': '0'
        })

        response = update_data_run(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])
        self.assertEqual(response_data['data']['name'], 'updated_data_run')
        self.assertEqual(response_data['data']['is_enabled'], False)

    def test_update_data_run_not_found(self):
        request = self.factory.post('/update_data_run', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'non_existent_key',
            'name': 'updated_data_run',
            'is_enabled': '0'
        })

        response = update_data_run(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertEqual(response_data['message'], 'Data Run not found')

    def test_delete_data_run_success(self):
        data_run = DataRuns.objects.create(
            name='test_data_run',
            data_run_key='test_project_key_test_data_run',
            project_object=self.project,
            is_enabled=True
        )

        request = self.factory.post('/delete_data_run', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': data_run.data_run_key
        })

        response = delete_data_run(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])

    def test_delete_data_run_not_found(self):
        request = self.factory.post('/delete_data_run', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'non_existent_key'
        })

        response = delete_data_run(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertEqual(response_data['message'], 'Data Run not found')
