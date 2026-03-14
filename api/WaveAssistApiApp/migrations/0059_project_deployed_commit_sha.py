from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('WaveAssistApiApp', '0058_account_credits_check_interval_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='deployed_commit_sha',
            field=models.CharField(blank=True, default='', max_length=64, null=True),
        ),
    ]
