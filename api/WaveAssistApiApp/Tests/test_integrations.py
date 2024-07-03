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
from WaveAssistApiApp.manage_views import activate_integration, deactivate_integration  # Adjust the import according to your app structure
from WaveAssistApiApp.models import *  # Adjust the import according to your app structure
import WaveAssistApiApp.Utils.utils as utils  # Adjust the import according to your app structure

class IntegrationTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(username='admin', can_create_projects=True)
        self.user.save()
        self.admin_uid = self.user.uid

        self.project = Project.objects.create(project_key='test_project_key')
        self.integration = Integrations.objects.create(integration_key='test_integration_key')
        AccessProvided.objects.create(
            user_object=self.user,
            project_object=self.project,
            type=0,
            project_access_type=WRITE_GTE
        )
        self.project.save()
        self.integration.save()

    def test_activate_integration_success(self):
        request = self.factory.post('/activate_integration', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'integration_key': 'test_integration_key'
        })

        response = activate_integration(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])
        self.assertIn(self.integration, self.project.integration_array.all())

    def test_activate_integration_already_active(self):
        self.project.integration_array.add(self.integration)
        self.project.save()

        request = self.factory.post('/activate_integration', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'integration_key': 'test_integration_key'
        })

        response = activate_integration(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertEqual(response_data['message'], 'Integration already exist, and is active')

    def test_activate_integration_not_found(self):
        request = self.factory.post('/activate_integration', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'integration_key': 'non_existent_key'
        })

        response = activate_integration(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertEqual(response_data['message'], 'Integration not found')

    def test_deactivate_integration_success(self):
        self.project.integration_array.add(self.integration)
        self.project.save()

        request = self.factory.post('/deactivate_integration', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'integration_key': 'test_integration_key'
        })

        response = deactivate_integration(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])
        self.assertNotIn(self.integration, self.project.integration_array.all())

    def test_deactivate_integration_not_active(self):
        request = self.factory.post('/deactivate_integration', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'integration_key': 'test_integration_key'
        })

        response = deactivate_integration(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertEqual(response_data['message'], 'Integration not active for this project')

    def test_deactivate_integration_not_found(self):
        request = self.factory.post('/deactivate_integration', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'integration_key': 'non_existent_key'
        })

        response = deactivate_integration(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertEqual(response_data['message'], 'Integration not active for this project')
