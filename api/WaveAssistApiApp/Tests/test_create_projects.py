from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
import json
from WaveAssistApiApp.manage_views import *  # Adjust the import according to your app structure
from WaveAssistApiApp.models import *  # Adjust the import according to your app structure
import WaveAssistApiApp.Utils.utils as utils  # Adjust the import according to your app structure
import uuid
from WaveAssistApiApp.Utils.constants import *

class CreateProjectTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(username='admin', can_create_projects=True)
        self.user.save()
        self.admin_uid = self.user.uid
        self.non_admin_user = User.objects.create(username='non_admin', can_create_projects=False)
        self.non_admin_user.save()
        self.non_admin_uid = self.non_admin_user.uid
        self.user.save()
        self.project_key = 'test_project_key'

    def test_01_create_project_success(self):
        request = self.factory.post('/create_project', {
            'uid': self.admin_uid,
            'project_key': self.project_key,
            'project_name': self.project_key
        })

        response = create_project(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])

        ##Check in db if project created
        try:
            project = Project.objects.get(project_key=self.project_key)
        except:
            pass
        self.assertIsNotNone(project)

    def test_02_create_project_no_access(self):
        request = self.factory.post('/create_project', {
            'uid': self.non_admin_uid,
            'project_key': 'test_project_key'
        })

        response = create_project(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])

    def test_03_create_project_key_already_exists(self):
        Project.objects.create(
            project_key=self.project_key,
        ).save()

        request = self.factory.post('/create_project', {
            'uid': self.admin_uid,
            'project_key': self.project_key
        })
        response = create_project(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])


    def test_04_create_project_missing_project_key(self):
        request = self.factory.post('/create_project', {
            'uid': self.admin_uid,
            'project_key': ''
        })
        response = create_project(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])


