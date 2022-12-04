# Generated by Django 3.2 on 2022-12-03 10:09

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_message_created_time'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='message',
            name='created_time',
        ),
        migrations.AddField(
            model_name='message',
            name='date',
            field=models.DateField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='message',
            name='timestamp',
            field=models.TimeField(auto_now_add=True),
        ),
    ]