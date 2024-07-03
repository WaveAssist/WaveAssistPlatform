import json
from django.test import TestCase, RequestFactory
from django.contrib.auth.hashers import make_password
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from WaveAssistApiApp.dashboard_views import login
from WaveAssistApiApp.Utils.constants import *

import json

from WaveAssistApiApp.manage_views import create_user  # Adjust the import according to your app structure
from WaveAssistApiApp.models import *  # Adjust the import according to your app structure
import WaveAssistApiApp.Utils.utils as utils  # Adjust the import according to your app structure
import uuid

class LoginTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user_password = 'password123'
        self.user = User.objects.create(
            username='testuser',
            password=self.user_password
        )
        self.user.save()

        self.project1 = Project.objects.create(project_key='Project 1')
        self.project2 = Project.objects.create(project_key='Project 2')

        self.data_run1 = DataRuns.objects.create(data_run_key='Data Run 1', project_object=self.project1)
        self.data_run2 = DataRuns.objects.create(data_run_key='Data Run 2', project_object=self.project2)

        AccessProvided.objects.create(
            user_object=self.user,
            project_object=self.project1,
            type=0,
            project_access_type=READ_GTE
        )
        AccessProvided.objects.create(
            user_object=self.user,
            project_object=self.project2,
            type=0,
            project_access_type=READ_GTE
        )
        AccessProvided.objects.create(
            user_object=self.user,
            data_run_object=self.data_run1,
            type=1,
            data_run_access_type=READ_GTE
        )
        AccessProvided.objects.create(
            user_object=self.user,
            data_run_object=self.data_run2,
            type=1,
            data_run_access_type=READ_GTE
        )

    def test_login_success(self):
        request = self.factory.post('/login', {
            'username': 'testuser',
            'password': self.user_password
        })




        response = login(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])
        self.assertEqual('Login successful.', response_data['message'])

        # Check user data in the response
        user_data = response_data['data']['user_data']
        self.assertEqual(user_data['username'], 'testuser')

        # Check project array in the response
        project_array = response_data['data']['project_array']
        self.assertEqual(len(project_array), 2)

        project_names = {project['project_key'] for project in project_array}
        self.assertIn('Project 1', project_names)
        self.assertIn('Project 2', project_names)

        # Check data runs within projects
        for project in project_array:
            if project['project_key'] == 'Project 1':
                self.assertEqual(len(project['data_run_array']), 1)
                self.assertEqual(project['data_run_array'][0]['data_run_key'], 'Data Run 1')
            elif project['project_key'] == 'Project 2':
                self.assertEqual(len(project['data_run_array']), 1)
                self.assertEqual(project['data_run_array'][0]['data_run_key'], 'Data Run 2')

    def test_login_invalid_password(self):
        request = self.factory.post('/login', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })

        response = login(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertIn('Username or Password invalid.', response_data['message'])

    def test_login_invalid_username(self):
        request = self.factory.post('/login', {
            'username': 'nonexistentuser',
            'password': 'password123'
        })

        response = login(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertIn('Username or Password invalid.', response_data['message'])

