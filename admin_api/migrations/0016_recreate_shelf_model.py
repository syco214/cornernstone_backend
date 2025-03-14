from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('admin_api', '0015_reset_shelf_model'),  # Reference the previous migration
    ]

    operations = [
        migrations.CreateModel(
            name='Shelf',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aisle', models.CharField(max_length=25)),
                ('shelf', models.CharField(max_length=25)),
                ('info', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('warehouse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shelves', to='admin_api.warehouse')),
            ],
            options={
                'verbose_name_plural': 'shelves',
                'ordering': ['aisle', 'shelf'],
                'unique_together': {('aisle', 'shelf', 'warehouse')},
            },
        ),
    ]