import unittest
from Engine.ProjectManager import ProjectManager

import Utils.utils as utils


class TestUtils(unittest.TestCase):

    def setUp(self):
       pass

    def tearDown(self):
        pass


    def test_manage_data_update_function(self):
        ##Test function manage_data_update with specific data


        ##Test case 1: new_project_data_array is empty, managers_array is empty
        new_project_data_array = []
        managers_array = []
        utils.manage_data_update(new_project_data_array, managers_array)
        self.assertEqual(len(managers_array), 0)


        ##Test case 2: new_project_data_array is empty, managers_array is not empty
        new_project_data_array = []
        managers_array = [ProjectManager('project_key1'), ProjectManager('project_key2')]
        utils.manage_data_update(new_project_data_array, managers_array)

        ##Both should get deleted.
        self.assertEqual(len(managers_array), 0)


        ##Test case 5: new_project_data_array is not empty, managers_array is not empty, new_project_data_array has new project
        new_project_data_array = [{'project_key': 'test_project_1', 'should_refresh': '0'}, {'project_key': 'test_project_2', 'should_refresh': '0'}]
        managers_array = [ProjectManager('test_project_1')]
        utils.manage_data_update(new_project_data_array, managers_array)
        self.assertEqual(len(managers_array), 2)
        self.assertEqual(managers_array[0].project_key, 'test_project_1')
        self.assertEqual(managers_array[1].project_key, 'test_project_2')

        ##Cleanup
        for manager_object in managers_array:
            manager_object.delete_project()
