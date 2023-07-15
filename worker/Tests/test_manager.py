# import unittest
# from Engine.ProjectManager import ProjectManager
# from unittest.mock import patch, MagicMock
# import os
# import Utils.utils as utils
# class ProjectManagerTest(unittest.TestCase):
#
#     def setUp(self):
#         print("Started Setup")
#
#         self.project_key = 'test_project_1'
#         self.manager = ProjectManager(self.project_key)
#
#         self.project_key2 = 'test_project_2'
#         self.manager2 = ProjectManager(self.project_key2)
#
#         self.managers_array = []
#         self.managers_array.append(self.manager)
#         self.managers_array.append(self.manager2)
#
#         for manager in self.managers_array:
#             manager.get_started()
#
#
#     def tearDown(self):
#         print("Started tear down")
#         for manager in self.managers_array:
#             manager.delete_project()
#
#
#
#     def test_project_manager_initialization(self):
#         self.assertEqual(self.manager.project_key, self.project_key)
#         self.assertIn(self.manager, self.managers_array)
#
#
#     def test_nodes_created(self):
#         for manager in self.managers_array:
#             ##Check if the nodes are created and alive
#             for node_key, node in manager.nodes_dict.items():
#                 self.assertTrue(node.is_alive())
#
#
#     def test_delete_project(self):
#         for manager in self.managers_array:
#
#             manager.delete_project()
#
#             ##Assert if the nodes of the manager are not running
#             for node_key, node in manager.nodes_dict.items():
#                 self.assertFalse(node.is_alive())
#
#             ##Assert if the file created by utils is deleted
#             self.assertFalse(os.path.exists(utils.get_project_file_path(manager.project_key)))
#
#
#     def test_is_healthy(self):
#         for manager in self.managers_array:
#             ##Assert if is healthy
#             self.assertTrue(manager.is_healthy())
#
#             ##Stop one node and then assert if not healthy
#             for node_key, node in manager.nodes_dict.items():
#                 manager.stop_node(node_key)
#                 break
#             self.assertFalse(manager.is_healthy())
#
#
#     def test_fix_things(self):
#         for manager in self.managers_array:
#             ##Assert if is healthy
#             self.assertTrue(manager.is_healthy())
#
#             ##Stop one node and then assert if not healthy
#             for node_key, node in manager.nodes_dict.items():
#                 manager.stop_node(node_key)
#                 break
#             self.assertFalse(manager.is_healthy())
#
#             manager.fix_things()
#
#             self.assertTrue(manager.is_healthy())
#
