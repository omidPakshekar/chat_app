# Generated by Django 3.2 on 2022-12-24 16:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0006_auto_20221224_1221'),
    ]

    operations = [
        migrations.AddField(
            model_name='chat',
            name='hide',
            field=models.BooleanField(default=False),
        ),
    ]
