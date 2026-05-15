from django.db import migrations


def create_initial_data(apps, schema_editor):
    """Create admin user, user groups (roles), and site settings."""
    User = apps.get_model("auth", "User")
    Group = apps.get_model("auth", "Group")
    SiteSettings = apps.get_model("shopapp", "SiteSettings")

    # Groups / Roles
    admin_group, _ = Group.objects.get_or_create(name="Администратор")
    buyer_group, _ = Group.objects.get_or_create(name="Покупатель")

    # Superuser admin
    if not User.objects.filter(username="admin").exists():
        admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@megano.ru",
            password="admin",
        )
        admin_user.groups.add(admin_group)

    # Site settings (singleton)
    SiteSettings.objects.get_or_create(
        pk=1,
        defaults={
            "express_delivery_cost": 500,
            "ordinary_delivery_cost": 200,
            "free_delivery_threshold": 2000,
        },
    )


def reverse_initial_data(apps, schema_editor):
    """Reverse: remove initial data."""
    User = apps.get_model("auth", "User")
    Group = apps.get_model("auth", "Group")
    SiteSettings = apps.get_model("shopapp", "SiteSettings")

    User.objects.filter(username="admin").delete()
    Group.objects.filter(name__in=["Администратор", "Покупатель"]).delete()
    SiteSettings.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("shopapp", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_initial_data, reverse_initial_data),
    ]
