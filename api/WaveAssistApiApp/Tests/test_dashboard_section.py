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
from WaveAssistApiApp.manage_views import create_dashboard_section, update_dashboard_section, delete_dashboard_section  # Adjust the import according to your app structure
from WaveAssistApiApp.models import *  # Adjust the import according to your app structure
import WaveAssistApiApp.Utils.utils as utils  # Adjust the import according to your app structure

class DashboardSectionTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(username='admin', can_create_projects=True)
        self.user.save()
        self.admin_uid = self.user.uid

        self.project = Project.objects.create(project_key='test_project_key')
        self.data_key = DataKey.objects.create(
            key='test_project_key_data_key',
            project_object=self.project
        )
        AccessProvided.objects.create(
            user_object=self.user,
            project_object=self.project,
            type=0,
            project_access_type=WRITE_GTE
        )
        self.user.save()
        self.project.save()
        self.data_key.save()

    def test_create_dashboard_section_success(self):
        request = self.factory.post('/create_dashboard_section', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'row': 0,
            'column': 0,
            'display_type': 0,
            'data_key': 'test_project_key_data_key',
            'title': 'Test Title',
            'should_display_title': '1',
            'is_editable': '0'
        })

        response = create_dashboard_section(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])
        self.assertIn('row', response_data['data'])
        self.assertEqual(response_data['data']['title'], 'Test Title')

    def test_create_dashboard_section_data_key_not_found(self):
        request = self.factory.post('/create_dashboard_section', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'row': 0,
            'column': 0,
            'display_type': 0,
            'data_key': 'non_existent_data_key',
            'title': 'Test Title',
            'should_display_title': '1',
            'is_editable': '0'
        })

        response = create_dashboard_section(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertEqual(response_data['message'], 'Data Key not found')

    def test_update_dashboard_section_success(self):
        dashboard_section = DashboardSection.objects.create(
            row=0,
            column=0,
            display_type=0,
            data_key_object=self.data_key,
            title='Old Title',
            should_display_title=True,
            is_editable=False,
            project_object=self.project,
            dashboard_section_key = 'test_dashboard_section_key'
        )
        dashboard_section.save()

        request = self.factory.post('/update_dashboard_section', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'dashboard_section_key': dashboard_section.dashboard_section_key,
            'row': 1,
            'column': 1,
            'display_type': 1,
            'data_key': 'test_project_key_data_key',
            'title': 'New Title',
            'should_display_title': '0',
            'is_editable': '1'
        })

        response = update_dashboard_section(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])
        self.assertEqual(response_data['data']['title'], 'New Title')
        self.assertEqual(response_data['data']['row'], '1')

    def test_update_dashboard_section_not_found(self):
        request = self.factory.post('/update_dashboard_section', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'dashboard_section_key': 'non_existent_key',
            'row': 1,
            'column': 1,
            'display_type': 1,
            'data_key': 'test_project_key_data_key',
            'title': 'New Title',
            'should_display_title': '0',
            'is_editable': '1'
        })

        response = update_dashboard_section(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertEqual(response_data['message'], 'Dashboard Section not found')

    def test_delete_dashboard_section_success(self):
        dashboard_section = DashboardSection.objects.create(
            row=0,
            column=0,
            display_type=0,
            data_key_object=self.data_key,
            title='Test Title',
            should_display_title=True,
            is_editable=False,
            project_object=self.project,
            dashboard_section_key='test_dashboard_section_key'
        )
        dashboard_section.save()

        request = self.factory.post('/delete_dashboard_section', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'dashboard_section_key': dashboard_section.dashboard_section_key
        })

        response = delete_dashboard_section(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])

    def test_delete_dashboard_section_not_found(self):
        request = self.factory.post('/delete_dashboard_section', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'dashboard_section_key': 'non_existent_key'
        })

        response = delete_dashboard_section(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
        self.assertEqual(response_data['message'], 'Dashboard Section not found')
