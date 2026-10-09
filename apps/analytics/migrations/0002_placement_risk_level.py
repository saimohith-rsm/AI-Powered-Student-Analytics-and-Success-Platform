from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("analytics", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="studentsuccesssnapshot",
            name="placement_risk_level",
            field=models.CharField(
                choices=[
                    ("UNKNOWN", "Not Assessed"),
                    ("LOW", "Low Placement Risk"),
                    ("MEDIUM", "Medium Placement Risk"),
                    ("HIGH", "High Placement Risk"),
                    ("CRITICAL", "Critical Placement Risk"),
                ],
                default="UNKNOWN",
                max_length=20,
            ),
        ),
    ]
