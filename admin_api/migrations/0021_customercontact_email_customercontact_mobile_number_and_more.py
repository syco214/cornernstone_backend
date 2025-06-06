# Generated by Django 5.1.3 on 2025-04-09 16:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_api', '0020_alter_customuser_admin_access_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customercontact',
            name='email',
            field=models.TextField(default='hello@gmail.com'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customercontact',
            name='mobile_number',
            field=models.TextField(default='09081238238'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customercontact',
            name='office_number',
            field=models.TextField(default='0918182818238'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='suppliercontact',
            name='email',
            field=models.TextField(default='hello@gmail.com'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='suppliercontact',
            name='mobile_number',
            field=models.TextField(default='09023910293091'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='suppliercontact',
            name='office_number',
            field=models.TextField(default='012930912903'),
            preserve_default=False,
        ),
    ]
