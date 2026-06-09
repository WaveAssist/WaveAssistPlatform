"""Regression test for run_dag with MULTIPLE starting nodes and no start_node_key.

Before the fix, the no-key branch did Nodes.objects.get(is_starting_node=True), which raised
MultipleObjectsReturned ("get() returned more than one Nodes -- it returned 2!") for any project
with two starting nodes (e.g. GitZoid: review chain + brain). The fix resolves a LIST of starting
nodes and runs each as its own DAG.

Reuses BuildTestCase's fixtures (a project that already has TWO starting nodes: node_a + node_e),
patching out MongoManager so setUp never connects to the real cluster, and mocking the Celery
send so no broker/worker is needed.
"""
import json
import uuid
from unittest.mock import patch, MagicMock

from WaveAssistApiApp.Tests.test_worker import BuildTestCase
from WaveAssistApiApp.deployment_views import run_dag
from WaveAssistApiApp.models import DAG, Nodes, Account


class RunDagMultiStartTest(BuildTestCase):
    def setUp(self):
        # BuildTestCase.setUp() instantiates MongoManager() (connects to a real cluster).
        # This test never touches the worker/mongo, so patch it out for setUp.
        with patch("WaveAssistApiApp.Tests.test_worker.MongoManager", MagicMock()):
            super().setUp()
        # run_dag resolves the celery queue via the user's Account; create one.
        Account.objects.create(
            created_by_user=self.admin_user,
            account_uid=str(uuid.uuid4()),
            celery_queue="test_queue",
        )

    @patch("WaveAssistApiApp.deployment_views.utils.track_posthog", MagicMock())
    @patch("WaveAssistApiApp.deployment_views.app.send_task")
    def test_run_once_no_key_runs_all_starting_dags(self, mock_send_task):
        mock_send_task.return_value = MagicMock(id="fake-run-id")

        # The fixture project genuinely has two starting nodes.
        starts = Nodes.objects.filter(
            project_object=self.project, is_enabled=True, is_starting_node=True
        )
        self.assertEqual(starts.count(), 2)

        # No start_node_key — the exact case that used to raise MultipleObjectsReturned.
        request = self.factory.post("/run_dag", {
            "uid": self.admin_uid,
            "project_key": "test_project_key",
            "data_run_key": "test_data_run_django",
        })
        response = run_dag(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["message"], "Successfully started the DAG")
        # Both starting DAGs were launched (one send_task per DAG) and recorded.
        self.assertEqual(mock_send_task.call_count, 2)
        self.assertEqual(DAG.objects.filter(start_node__in=starts).count(), 2)

    @patch("WaveAssistApiApp.deployment_views.utils.track_posthog", MagicMock())
    @patch("WaveAssistApiApp.deployment_views.app.send_task")
    def test_run_once_with_key_still_runs_single_dag(self, mock_send_task):
        # Backward-compat: passing a key runs exactly that one DAG (unchanged behaviour).
        mock_send_task.return_value = MagicMock(id="fake-run-id")
        request = self.factory.post("/run_dag", {
            "uid": self.admin_uid,
            "project_key": "test_project_key",
            "data_run_key": "test_data_run_django",
            "start_node_key": "node_a",
        })
        response = run_dag(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_send_task.call_count, 1)
