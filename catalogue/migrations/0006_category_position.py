# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-11-11 20:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0005_menucategory'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='position',
            field=models.IntegerField(default=0),
        ),
    ]