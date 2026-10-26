"""Remove only Django's old model state; the physical table is retained."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("main", "0004_alter_profile_bio_alter_profile_city")]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.DeleteModel(name="Profile")],
            database_operations=[],
        ),
    ]
