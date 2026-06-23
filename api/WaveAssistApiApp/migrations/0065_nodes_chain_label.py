from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("WaveAssistApiApp", "0064_alter_noderuns_node_object"),
    ]

    operations = [
        migrations.AddField(
            model_name="nodes",
            name="chain_label",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
    ]
