from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('admin_api', '0014_customuser_admin_access'),  # Replace with your actual previous migration
    ]

    operations = [
        migrations.RemoveField(
            model_name='shelf',
            name='warehouse',
        ),
        migrations.DeleteModel(
            name='Shelf',
        ),
    ]