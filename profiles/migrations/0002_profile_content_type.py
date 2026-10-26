"""Move the existing content-type identity, retaining all references to its PK."""
from django.db import migrations


def transfer_content_type(apps, schema_editor, source, destination):
    content_types = apps.get_model("contenttypes", "ContentType").objects.using(
        schema_editor.connection.alias,
    )
    old = content_types.filter(app_label=source, model="profile").first()
    if old is None:
        # Fresh installs have no old identity; post_migrate creates the new one.
        return
    if content_types.filter(app_label=destination, model="profile").exists():
        # Never delete/merge an identity with potentially unknown generic or
        # admin-log references. Resolve the collision explicitly before retrying.
        raise RuntimeError(
            "Both main.profile and profiles.profile content types exist. "
            "Reconcile their permissions and content-type references before retrying; "
            "no automatic merge or deletion is performed."
        )
    old.app_label = destination
    old.save(using=schema_editor.connection.alias, update_fields=["app_label"])


def forward(apps, schema_editor):
    transfer_content_type(apps, schema_editor, "main", "profiles")


def backward(apps, schema_editor):
    transfer_content_type(apps, schema_editor, "profiles", "main")


class Migration(migrations.Migration):
    dependencies = [("profiles", "0001_initial")]
    operations = [migrations.RunPython(forward, backward)]
