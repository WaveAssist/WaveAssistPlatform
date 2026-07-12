"""Trial / deployment-lifecycle tests for the GitZoid metering changes.

Covers the behavior we deliberately built (see CLAUDE.md → "Deployment lifecycle policy"):
  * NO circuit breaker — repeated failures never auto-pause a deployment.
  * GitZoid trial exhaustion → stop_trial_deployments disables the schedule.
  * Upgrade → resume_account_deployments re-enables it.
  * Deliverable nodes meter the trial (idempotently); gate nodes and WaveAssist don't.

The deployment graph (Deployment → DAG → PeriodicTask) is built directly so the test is
fully isolated from the HTTP deploy flow. Runs on sqlite localtest — never touches prod:

  DJANGO_SETTINGS_MODULE=WaveAssistApi.settings_localtest \
    python manage.py test WaveAssistApiApp.Tests.test_trial_lifecycle
"""

from django.test import TestCase
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from WaveAssistApiApp.models import (
    Account,
    AccessProvided,
    DAG,
    DataRuns,
    Deployments,
    Nodes,
    Project,
    User,
)
from WaveAssistApiApp.Utils import metering, utils
from WaveAssistApiApp.Utils.constants import ADMIN_GTE


class TrialLifecycleTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create(username="owner")
        self.project = Project.objects.create(project_key="trial_project")
        AccessProvided.objects.create(
            user_object=self.owner,
            project_object=self.project,
            type=0,
            project_access_type=ADMIN_GTE,
        )
        self.data_run = DataRuns.objects.create(
            data_run_key="dr", project_object=self.project, is_enabled=True
        )
        self.interval = IntervalSchedule.objects.create(
            every=120, period=IntervalSchedule.SECONDS
        )
        # One deployment with one running DAG whose celery-beat task is enabled.
        self.deployment = Deployments.objects.create(
            key="dep-1",
            project_object=self.project,
            data_run_object=self.data_run,
            is_running=True,
        )
        self.periodic_task = PeriodicTask.objects.create(
            name="dep-1-dag", task="celery_worker.run_dag", interval=self.interval, enabled=True
        )
        self.dag = DAG.objects.create(
            key="dag-1",
            parent_deployment=self.deployment,
            periodic_task=self.periodic_task,
            is_running=True,
            interval_schedule=self.interval,
        )

    # ---- helpers -------------------------------------------------------------
    def _account(self, *, product="gitzoid", plan="starter", used=0, limit=30):
        return Account.objects.create(
            created_by_user=self.owner,
            product=product,
            plan_name=plan,
            trial_credits_used=used,
            trial_credits_limit=limit,
            open_router_key="sk-test",
        )

    def _reload(self):
        self.deployment.refresh_from_db()
        self.dag.refresh_from_db()
        self.periodic_task.refresh_from_db()

    def _assert_stopped(self):
        self._reload()
        self.assertFalse(self.deployment.is_running)
        self.assertFalse(self.dag.is_running)
        self.assertFalse(self.periodic_task.enabled)

    def _assert_running(self):
        self._reload()
        self.assertTrue(self.deployment.is_running)
        self.assertTrue(self.dag.is_running)
        self.assertTrue(self.periodic_task.enabled)

    # ---- tests ---------------------------------------------------------------
    def test_trial_exhaustion_stops_deployment(self):
        self._account(used=30, limit=30)  # trialling GitZoid, budget spent
        metering.stop_trial_deployments(self.project)
        self._assert_stopped()

    def test_stop_trial_deployments_is_idempotent(self):
        self._account(used=30, limit=30)
        metering.stop_trial_deployments(self.project)
        metering.stop_trial_deployments(self.project)  # second call is a no-op
        self._assert_stopped()

    def test_resume_account_deployments_on_upgrade(self):
        # Simulate the trial-exhaustion pause, then upgrade to Pro.
        utils.stop_deployment(self.deployment)
        self._assert_stopped()
        account = self._account(plan="gitzoid_pro", used=30, limit=30)
        metering.resume_account_deployments(account)
        self._assert_running()

    def test_failures_never_pause_deployment(self):
        """No circuit breaker: repeated failed runs must not stop the deployment."""
        self._account(used=0, limit=30)  # healthy trial
        for i in range(5):
            metering.handle_run_terminal(
                self.project, Nodes.objects.create(node_key=f"n{i}", project_object=self.project),
                self.data_run, run_id=f"fail-{i}", did_succeed=False,
            )
        self._assert_running()

    def test_deliverable_node_meters_trial_idempotently(self):
        account = self._account(used=0, limit=30)
        deliverable = Nodes.objects.create(node_key="post_comment", project_object=self.project)
        # is_idle=False = a run that actually shipped a review (production reads this from the
        # absence of the run's run_idle flag).
        metering.handle_run_terminal(
            self.project, deliverable, self.data_run,
            run_id="deliver-1", did_succeed=True, is_idle=False,
        )
        account.refresh_from_db()
        self.assertEqual(account.trial_credits_used, 1, "post_comment should charge 1 (pr_review)")
        # Same run replayed → no double charge.
        metering.handle_run_terminal(
            self.project, deliverable, self.data_run,
            run_id="deliver-1", did_succeed=True, is_idle=False,
        )
        account.refresh_from_db()
        self.assertEqual(account.trial_credits_used, 1, "re-delivery must be idempotent")

    def test_idle_deliverable_node_does_not_meter(self):
        """A deliverable node that RAN but delivered nothing (idle) must not charge — even though
        the run 'succeeded' (did_succeed=True means the code didn't raise, NOT that work shipped).
        This is the every-2-min idle-repo case: post_comment runs, finds no PR to post, calls
        waveassist.mark_run_idle(), and returns normally. Idle is passed explicitly here; in
        production handle_run_terminal reads it from the run's run_idle flag."""
        account = self._account(used=0, limit=30)
        deliverable = Nodes.objects.create(node_key="post_comment", project_object=self.project)
        metering.handle_run_terminal(
            self.project, deliverable, self.data_run,
            run_id="idle-1", did_succeed=True, is_idle=True,
        )
        account.refresh_from_db()
        self.assertEqual(account.trial_credits_used, 0,
                         "an idle deliverable run must not charge the trial")

    def test_idle_flag_is_read_from_store_when_not_passed(self):
        """Production path: with is_idle left unset, handle_run_terminal reads the run's run_idle
        flag from the per-user store. Present flag (idle) → no charge; absent (delivered) → charge.
        _mongo is faked (like tests/unit/test_skip_flag_parsing.py) so no real Mongo is needed."""

        class _FakeStore:
            """db[name] and coll[name] both return self; find_one reports whether the flag exists."""
            def __init__(self, has_flag):
                self._has = has_flag

            def __getitem__(self, name):
                return self

            def find_one(self, *a, **k):
                return {"IODataKey": "x"} if self._has else None

        account = self._account(used=0, limit=30)
        deliverable = Nodes.objects.create(node_key="post_comment", project_object=self.project)
        orig_mongo = metering._mongo
        try:
            # run_idle flag present → treated as idle → not charged.
            metering._mongo = lambda: _FakeStore(True)
            metering.handle_run_terminal(
                self.project, deliverable, self.data_run, run_id="store-idle", did_succeed=True
            )
            account.refresh_from_db()
            self.assertEqual(account.trial_credits_used, 0, "flag present → idle → no charge")

            # run_idle flag absent → real delivery → charged.
            metering._mongo = lambda: _FakeStore(False)
            metering.handle_run_terminal(
                self.project, deliverable, self.data_run, run_id="store-live", did_succeed=True
            )
            account.refresh_from_db()
            self.assertEqual(account.trial_credits_used, 1, "flag absent → delivered → charge")
        finally:
            metering._mongo = orig_mongo

    def test_gate_node_does_not_meter(self):
        account = self._account(used=0, limit=30)
        gate = Nodes.objects.create(node_key="gate_check", project_object=self.project)
        metering.handle_run_terminal(
            self.project, gate, self.data_run, run_id="gate-1", did_succeed=True
        )
        account.refresh_from_db()
        self.assertEqual(account.trial_credits_used, 0, "non-deliverable nodes must not charge")

    def test_waveassist_account_untouched(self):
        self._account(product="waveassist")  # not GitZoid
        node = Nodes.objects.create(node_key="post_comment", project_object=self.project)
        # A failure on a WaveAssist deployment must not stop it (metering bails on product).
        metering.handle_run_terminal(self.project, node, self.data_run, did_succeed=False)
        self._assert_running()
        # And a deliverable success must not meter a WaveAssist account.
        metering.handle_run_terminal(self.project, node, self.data_run, run_id="wa-1", did_succeed=True)
        account = Account.objects.get(created_by_user=self.owner)
        self.assertEqual(account.trial_credits_used, 0, "WaveAssist must never be metered")
