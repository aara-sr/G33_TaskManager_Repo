# Generated by Django 5.2 on 2025-04-10 19:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('TaskManagerPro', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='priority',
            field=models.IntegerField(choices=[(0, 'None'), (1, 'Low'), (2, 'Medium'), (3, 'High')], default=0),
        ),
    ]
