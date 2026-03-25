from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("WaveAssistApiApp", "0061_account_open_router_key_hash"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_super_admin",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="account",
            name="plan_name",
            field=models.CharField(default="starter", max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="billingsubscription",
            name="plan_name",
            field=models.CharField(default="starter", max_length=255),
        )
    ]
