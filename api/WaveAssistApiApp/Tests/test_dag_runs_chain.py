"""fetch_dag_runs chain_label + is_idle + cadence (the dashboard contract).

LabelFallbackPureTest needs no DB/Mongo. FetchDagRunsChainTest reuses BuildTestCase's fixtures
(a project with starting nodes) and mocks _idle_run_ids so it never touches the real Mongo cluster.
"""
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase

from WaveAssistApiApp.Tests.test_worker import BuildTestCase
from WaveAssistApiApp.run_views import fetch_dag_runs, _label_for, _humanize_schedule
from WaveAssistApiApp.models import DagRuns, NodeRuns, Nodes, DataRuns


class LabelFallbackPureTest(TestCase):
    """The pure chain-label fallback rule — config label, else project name (+#index for multi)."""

    def test_config_label_wins(self):
        self.assertEqual(_label_for("PR Review", "GitZoid", 1, 3), "PR Review")

    def test_single_chain_uses_project_name(self):
        self.assertEqual(_label_for(None, "GitZoid", 1, 1), "GitZoid")

    def test_multi_chain_indexes(self):
        self.assertEqual(_label_for("", "GitZoid", 2, 3), "GitZoid #2")

    def test_blank_label_is_ignored(self):
        self.assertEqual(_label_for("   ", "GitZoid", 1, 3), "GitZoid #1")

    def test_no_project_name_falls_back_to_run(self):
        self.assertEqual(_label_for(None, None, 1, 1), "Run")

    def test_humanize_interval_schedule(self):
        class Iv:
            every, period = 2, "minutes"

        class Node:
            interval_schedule = Iv()
            crontab_schedule = None

        self.assertEqual(_humanize_schedule(Node()), "every 2 minutes")
        self.assertEqual(_humanize_schedule(None), "")


class FetchDagRunsChainTest(BuildTestCase):
    """DB integration: chain_label per run, idle batch flag, and status-wins for FAILED runs."""

    def setUp(self):
        with patch("WaveAssistApiApp.Tests.test_worker.MongoManager", MagicMock()):
            super().setUp()
        self.data_run = DataRuns.objects.filter(project_object=self.project).first()

    def _make_run(self, run_id, start_node, status="SUCCESS"):
        dr = DagRuns.objects.create(run_id=run_id, project_object=self.project,
                                    data_run_object=self.data_run)
        NodeRuns.objects.create(dag_run_object=dr, node_object=start_node, status=status)
        return dr

    def _fetch(self):
        request = self.factory.post("/fetch_dag_runs", {
            "uid": self.admin_uid, "project_key": "test_project_key",
            "data_run_key": self.data_run.data_run_key,
        })
        resp = fetch_dag_runs(request)
        return {d["run_id"]: d for d in json.loads(resp.content)["data"]["dag_run_array"]}

    @patch("WaveAssistApiApp.run_views._idle_run_ids")
    def test_chain_label_and_idle_flag(self, mock_idle):
        node = Nodes.objects.filter(project_object=self.project, is_starting_node=True).order_by("id").first()
        node.chain_label = "PR Review"
        node.save()
        self._make_run("run-idle-1", node)
        self._make_run("run-acted-1", node)
        mock_idle.return_value = {"run-idle-1"}

        by_id = self._fetch()
        self.assertEqual(by_id["run-idle-1"]["chain_label"], "PR Review")
        self.assertTrue(by_id["run-idle-1"]["is_idle"])
        self.assertFalse(by_id["run-acted-1"]["is_idle"])

    @patch("WaveAssistApiApp.run_views._idle_run_ids")
    def test_failed_run_never_idle(self, mock_idle):
        node = Nodes.objects.filter(project_object=self.project, is_starting_node=True).first()
        self._make_run("run-fail-1", node, status="FAILED")
        mock_idle.return_value = {"run-fail-1"}   # flagged idle, but the run FAILED
        run = self._fetch()["run-fail-1"]
        self.assertEqual(run["status"], "FAILED")
        self.assertFalse(run["is_idle"])          # status wins

    @patch("WaveAssistApiApp.run_views._idle_run_ids")
    def test_unlabeled_chain_falls_back_to_project_name(self, mock_idle):
        mock_idle.return_value = set()
        node = Nodes.objects.filter(project_object=self.project, is_starting_node=True).order_by("id").first()
        node.chain_label = None
        node.save()
        self._make_run("run-x", node)
        label = self._fetch()["run-x"]["chain_label"]
        # single-or-multi: must be the project name, optionally '#index' — never a raw node key.
        self.assertTrue(label.startswith(self.project.name))
