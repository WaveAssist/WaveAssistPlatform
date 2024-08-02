from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
import json
from WaveAssistApiApp.manage_views import *  # Adjust the import according to your app structure
from WaveAssistApiApp.deployment_views import *
from WaveAssistApiApp.models import *  # Adjust the import according to your app structure
import WaveAssistApiApp.Utils.utils as utils  # Adjust the import according to your app structure
import uuid
from WaveAssistApiApp.Utils.constants import *
from django.urls import reverse
import time
from WaveAssistApiApp.Utils.MongoManager import MongoManager

class BuildTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create(username='admin_username')
        self.mongo_manager = MongoManager()
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

        # Node A: Create the DataFrame
        node_a_python_code = """
        import pandas as pd
        # Create a sample DataFrame
        data = {
            'Name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
            'Age': [25, 30, 35, 40, 45],
            'City': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']
        }
        df = pd.DataFrame(data)
        return df
        """

        # Node B: Add a Salary column
        node_b_python_code = """
        # Add a new column to the DataFrame
        df['Salary'] = [50000, 60000, 70000, 80000, 90000]
        return df
        """

        # Node C: Add a Bonus column
        node_c_python_code = """
        # Add a new column to the DataFrame
        df['Bonus'] = [5000, 6000, 7000, 8000, 9000]
        return df
        """

        # Node D: Add a Department column
        node_d_python_code = """
        # Add a new column to the DataFrame
        df['Department'] = ['HR', 'Finance', 'IT', 'Marketing', 'Sales']
        return df
        """

        # Node E: Add a Performance Score column
        node_e_python_code = """
        import pandas as pd
        # Create a sample DataFrame
        data = {
            'E': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
            'Age': [25, 30, 35, 40, 45],
        }
        df = pd.DataFrame(data)
        return df
        """
        # Node F: Add an Email column
        node_f_python_code = """
        # Add a new column to the DataFrame
        df_e['Email'] = ['alice@example.com', 'bob@example.com', 'charlie@example.com', 'david@example.com', 'eve@example.com']
        return df_e
        """

        self.data_key = DataKey.objects.create(key='df', project_object=self.project)
        self.data_key_e = DataKey.objects.create(key='df_e', project_object=self.project)
        input_array = [self.data_key]
        input_array_e = [self.data_key_e]
        # Create nodes for the project
        self.node_a = Nodes.objects.create(
            node_key='node_a',
            project_object=self.project,
            is_enabled=True,
            is_starting_node=True,
            python_code = node_a_python_code,
        )
        self.node_a.input_data_key_array.set(input_array)
        self.node_a.output_data_key_array.set(input_array)

        self.node_b = Nodes.objects.create(
            node_key='node_b',
            project_object=self.project,
            is_enabled=True,
            python_code=node_b_python_code,
        )

        self.node_b.input_data_key_array.set(input_array)
        self.node_b.output_data_key_array.set(input_array)


        self.node_c = Nodes.objects.create(
            node_key='node_c',
            project_object=self.project,
            is_enabled=True,
            python_code=node_c_python_code,
        )
        self.node_c.input_data_key_array.set(input_array)
        self.node_c.output_data_key_array.set(input_array)

        self.node_d = Nodes.objects.create(
            node_key='node_d',
            project_object=self.project,
            is_enabled=True,
            python_code=node_d_python_code,

        )

        self.node_d.input_data_key_array.set(input_array)
        self.node_d.output_data_key_array.set(input_array)

        self.node_e = Nodes.objects.create(
            node_key='node_e',
            project_object=self.project,
            is_enabled=True,
            is_starting_node=True,
            python_code=node_e_python_code,
        )

        self.node_e.input_data_key_array.set(input_array_e)
        self.node_e.output_data_key_array.set(input_array_e)

        self.node_f = Nodes.objects.create(
            node_key='node_f',
            project_object=self.project,
            is_enabled=True,
            python_code=node_f_python_code,
        )
        self.node_f.input_data_key_array.set(input_array_e)
        self.node_f.output_data_key_array.set(input_array_e)


        data_run = DataRuns.objects.create(data_run_key='test_data_run_django', project_object=self.project, is_enabled=True)
        data_run.save()
        self.mongo_manager.collection = self.mongo_manager.database['test_data_run_django']

        ##Provide access to user
        access_provided_object = AccessProvided.objects.create(
            user_object=self.admin_user,
            data_run_object=data_run,
            type=1,
            data_run_access_type=ADMIN_GTE
        )
        access_provided_object.save()


        ##Create interval object for node_a
        self.interval_object = IntervalSchedule.objects.create(
            every=10,
            period=IntervalSchedule.SECONDS
        )
        self.node_a.interval_schedule = self.interval_object
        self.node_a.save()

        self.cron_object = CrontabSchedule.objects.create(
            minute='*',
            hour='*',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='Asia/Kolkata'
        )
        self.node_e.crontab_schedule = self.cron_object
        self.node_e.save()



        # Set up the DAG relationships: a -> b, c -> d && e -> f
        self.node_b.run_after_nodes_array.add(self.node_a)
        self.node_c.run_after_nodes_array.add(self.node_a)
        self.node_d.run_after_nodes_array.add(self.node_c)
        self.node_d.run_after_nodes_array.add(self.node_b)
        self.node_f.run_after_nodes_array.add(self.node_e)


    def test_run_dag_function(self):
        request = self.factory.post('/run_dag', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'test_data_run_django',
            'start_node_key':'node_a',
            'should_wait': '1'
        })
        response = run_dag(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully started the DAG')

        ##Check mongo
        df = self.mongo_manager.fetch_data_as_dataframe('df')

        ##Assert df is like above
        self.assertEqual(df.shape, (5, 5))
        self.assertEqual(df['Name'].tolist(), ['Alice', 'Bob', 'Charlie', 'David', 'Eve'])
        self.assertEqual(df['Age'].tolist(), [25, 30, 35, 40, 45])
        self.assertEqual(df['City'].tolist(), ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'])
        self.assertEqual(df['Bonus'].tolist(), [5000, 6000, 7000, 8000, 9000])

    def test_run_dag_function_e(self):
        request = self.factory.post('/run_dag', {
            'uid': self.admin_uid,
            'project_key': 'test_project_key',
            'data_run_key': 'test_data_run_django',
            'start_node_key': 'node_e',
            'should_wait': '1'
        })
        response = run_dag(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Successfully started the DAG')

        ##Check mongo
        df = self.mongo_manager.fetch_data_as_dataframe('df_e')

        ##Assert df is like above
        self.assertEqual(df.shape, (5, 3))
        self.assertEqual(df['E'].tolist(), ['Alice', 'Bob', 'Charlie', 'David', 'Eve'])
        self.assertEqual(df['Age'].tolist(), [25, 30, 35, 40, 45])
        self.assertEqual('Email' in df.columns, True)

    def tearDown(self):
        ##Delete the mongo collection called test_data_run_django
        self.mongo_manager.collection.drop()








