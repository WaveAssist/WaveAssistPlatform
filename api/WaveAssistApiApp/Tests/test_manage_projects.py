from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
import json
from WaveAssistApiApp.manage_views import *  # Adjust the import according to your app structure
from WaveAssistApiApp.models import *  # Adjust the import according to your app structure
import WaveAssistApiApp.Utils.utils as utils  # Adjust the import according to your app structure
import uuid
from WaveAssistApiApp.Utils.constants import *



class UpdateProjectTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(username='read_username')
        self.user.save()
        self.uid = self.user.uid

        self.admin_user = User.objects.create(username='admin_username')
        self.admin_user.save()
        self.admin_uid = self.admin_user.uid


        self.project = Project.objects.create(
            project_key='test_project_key'
        )
        AccessProvided.objects.create(
            user_object=self.user,
            project_object=self.project,
            type=0,
            project_access_type=READ_GTE
        )
        AccessProvided.objects.create(
            user_object=self.admin_user,
            project_object=self.project,
            type=0,
            project_access_type=ADMIN_GTE
        )

    def test_05_fetch_all_projects_success(self):
        request = self.factory.post('/fetch_all_projects', {'uid': self.uid})
        response = fetch_all_projects(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])
        self.assertIn('project_array', response_data['data'])
        project_array = response_data['data']['project_array']
        self.assertEqual(1, len(project_array))
        project = project_array[0]
        self.assertEqual('test_project_key', project['project_key'])



