from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock

import json

from WaveAssistApiApp.manage_views import create_user  # Adjust the import according to your app structure
from WaveAssistApiApp.models import *  # Adjust the import according to your app structure
import WaveAssistApiApp.Utils.utils as utils  # Adjust the import according to your app structure
import uuid


class CreateUserTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(username='admin', can_create_projects=True)
        self.user.save()
        self.admin_uid = self.user.uid

        self.non_admin_user = User.objects.create(username='non_admin')
        self.non_admin_user.save()
        self.non_admin_uid = self.non_admin_user.uid

    def test_create_user_success(self):
        request = self.factory.post('/create_user', {
            'uid': self.admin_uid,
            'name': 'Test User',
            'username': 'testuser',
            'password': 'password123',
            'company_name': 'Test Company'
        })

        response = create_user(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('1', response_data['success'])

        ##get uid from response_data
        uid = response_data['data']['user_object']['uid']

        # Check if the user was actually created in the database
        created_user = User.objects.get(uid=uid)
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.username, 'testuser')

    def test_create_user_no_admin_access(self):
        self.user.accessprovided_set.all().delete()
        request = self.factory.post('/create_user', {
            'uid': self.non_admin_uid
        })
        response = create_user(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])

    def test_create_user_user_not_found(self):
        request = self.factory.post('/create_user', {
            'uid': 'non_existent_uid'
        })
        response = create_user(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual('0', response_data['success'])
