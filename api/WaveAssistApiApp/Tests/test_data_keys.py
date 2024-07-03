from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from unittest.mock import patch
import json
from WaveAssistApiApp.manage_views import create_data_key, delete_data_key  # Adjust the import according to your app structure
from WaveAssistApiApp.models import *  # Adjust the import according to your app structure
import WaveAssistApiApp.Utils.utils as utils  # Adjust the import according to your app structure
from WaveAssistApiApp.Utils.constants import *
class DataKeyTestCase(TestCase):

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

    def test_create_data_key_success(self):
        request = self.factory.post('/create_data_key', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'key': 'test_project_key_data_key',
        })

        response = create_data_key(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])
        self.assertIn('key', response_data['data'])
        self.assertEqual(response_data['data']['key'], 'test_project_key_data_key')

    def test_create_data_key_invalid_user(self):
        request = self.factory.post('/create_data_key', {
            'uid': 'non_admin_uid',
            'project_key': 'test_project_key',
            'key': 'test_project_key_data_key'
        })

        response = create_data_key(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])



    def test_delete_data_key_success(self):
        DataKey.objects.create(
            key='test_project_key_data_key',
            project_object=self.project
        )

        request = self.factory.post('/delete_io_data', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'key': 'test_project_key_data_key'
        })

        response = delete_data_key(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])

    def test_delete_data_key_not_found(self):
        request = self.factory.post('/delete_io_data', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'key': 'non_existent_data_key'
        })

        response = delete_data_key(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])

    def test_create_data_key_invalid_key(self):
        request = self.factory.post('/create_data_key', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'key': 'invalid_key'
        })

        response = create_data_key(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertEqual(response_data['message'], 'Key should start with project key + _')

    def test_create_data_key_duplicate_key(self):
        DataKey.objects.create(
            key='test_project_key_data_key',
            project_object=self.project
        )

        request = self.factory.post('/create_data_key', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'key': 'test_project_key_data_key',
        })

        response = create_data_key(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertEqual(response_data['message'], 'Something went wrong while creating Data Key')
