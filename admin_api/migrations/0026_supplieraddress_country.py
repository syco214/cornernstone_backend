# Generated by Django 5.1.3 on 2025-05-22 16:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_api', '0025_alter_parentcompanypaymentterm_credit_limit'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplieraddress',
            name='country',
            field=models.TextField(default='China'),
            preserve_default=False,
        ),
    ]
