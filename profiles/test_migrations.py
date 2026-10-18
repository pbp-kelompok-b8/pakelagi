from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ProfileOwnershipMigrationTests(TransactionTestCase):
    def test_collision_stops_migration_without_deleting_either_identity(self):
        from django.contrib.contenttypes.models import ContentType

        executor = MigrationExecutor(connection)
        executor.migrate([("profiles", "0001_initial")])
        old, _ = ContentType.objects.get_or_create(app_label="main", model="profile")
        new, _ = ContentType.objects.get_or_create(app_label="profiles", model="profile")
        try:
            executor = MigrationExecutor(connection)
            with self.assertRaisesMessage(RuntimeError, "Both main.profile and profiles.profile"):
                executor.migrate([("profiles", "0002_profile_content_type")])
            self.assertTrue(ContentType.objects.filter(pk=old.pk, app_label="main").exists())
            self.assertTrue(ContentType.objects.filter(pk=new.pk, app_label="profiles").exists())
        finally:
            # Fixture cleanup only: neither identity has external references here.
            ContentType.objects.filter(pk=old.pk).delete()
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())

    def test_upgrade_preserves_profile_and_permission_assignments(self):
        executor = MigrationExecutor(connection)
        old_target = [("main", "0004_alter_profile_bio_alter_profile_city"), ("profiles", None)]
        executor.migrate(old_target)
        try:
            old_apps = executor.loader.project_state([
                ("main", "0004_alter_profile_bio_alter_profile_city"),
                ("auth", "0012_alter_user_first_name_max_length"),
            ]).apps
            User = old_apps.get_model("auth", "User")
            user = User.objects.create(username="migration-seller", email="private@example.com")
            profile = old_apps.get_model("main", "Profile").objects.create(
                user_id=user.pk, display_name="Penjual Lama", bio="Tetap ada",
                phone_number="+628123456789", avatar_url="https://example.com/avatar.png",
            )
            ContentType = old_apps.get_model("contenttypes", "ContentType")
            Permission = old_apps.get_model("auth", "Permission")
            content_type, _ = ContentType.objects.get_or_create(app_label="main", model="profile")
            permission, _ = Permission.objects.get_or_create(
                content_type=content_type, codename="change_profile", defaults={"name": "Can change profile"},
            )
            user.user_permissions.add(permission)
            group = old_apps.get_model("auth", "Group").objects.create(name="Profile editors")
            group.permissions.add(permission)
            user.groups.add(group)
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
            from profiles.models import Profile
            from django.contrib.auth.models import User as CurrentUser
            from django.contrib.contenttypes.models import ContentType as CurrentContentType
            from django.contrib.auth.models import Permission as CurrentPermission

            saved = Profile.objects.get(user_id=user.pk)
            self.assertEqual(saved.pk, profile.pk)
            self.assertEqual(saved.display_name, "Penjual Lama")
            self.assertEqual(saved.bio, "Tetap ada")
            self.assertEqual(saved.phone_number, "+628123456789")
            self.assertEqual(saved.avatar_url, "https://example.com/avatar.png")
            self.assertEqual(CurrentUser.objects.get(pk=user.pk).profile.pk, profile.pk)
            self.assertEqual(CurrentUser.objects.get(pk=user.pk).email, "private@example.com")
            self.assertEqual(Profile.objects.count(), 1)
            self.assertIn("main_profile", connection.introspection.table_names())
            self.assertNotIn("profiles_profile", connection.introspection.table_names())
            self.assertFalse(CurrentContentType.objects.filter(app_label="main", model="profile").exists())
            moved = CurrentContentType.objects.get(app_label="profiles", model="profile")
            self.assertEqual(moved.pk, content_type.pk)
            self.assertTrue(CurrentPermission.objects.filter(pk=permission.pk, content_type=moved).exists())
            self.assertTrue(CurrentUser.objects.get(pk=user.pk).has_perm("profiles.change_profile"))
            from django.contrib.auth.models import Group as CurrentGroup
            self.assertTrue(CurrentGroup.objects.get(pk=group.pk).permissions.filter(pk=permission.pk).exists())

            # Reverse and reapply with populated data, not merely an empty schema.
            executor = MigrationExecutor(connection)
            executor.migrate(old_target)
            restored_apps = executor.loader.project_state([
                ("main", "0004_alter_profile_bio_alter_profile_city"),
                ("auth", "0012_alter_user_first_name_max_length"),
            ]).apps
            restored = restored_apps.get_model("main", "Profile").objects.get(pk=profile.pk)
            self.assertEqual(restored.display_name, "Penjual Lama")
            self.assertEqual(restored.user_id, user.pk)
            self.assertTrue(CurrentContentType.objects.filter(pk=content_type.pk, app_label="main").exists())
            self.assertTrue(CurrentUser.objects.get(pk=user.pk).has_perm("main.change_profile"))
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
            self.assertEqual(Profile.objects.get(pk=profile.pk).phone_number, "+628123456789")
            self.assertTrue(CurrentUser.objects.get(pk=user.pk).has_perm("profiles.change_profile"))
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
