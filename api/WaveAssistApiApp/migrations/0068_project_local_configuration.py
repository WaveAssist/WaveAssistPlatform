from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("WaveAssistApiApp", "0067_deployments_consecutive_failures_usageledger")]
    operations = [migrations.AddField(
        model_name="project", name="local_configuration",
        field=models.JSONField(default=dict, blank=True),
    ), migrations.AddField(
        model_name="nodes", name="local_source_path",
        field=models.CharField(max_length=1024, default="", blank=True),
    )]
