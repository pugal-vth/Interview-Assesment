# Generated by Django 2.2.6 on 2019-10-31 16:38

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pathways', '0003_application_benefits_photo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='account_number',
            field=models.CharField(blank=True, max_length=30, validators=[django.core.validators.RegexValidator(message='Please enter only digits', regex='^\\d+$')]),
        ),
    ]
