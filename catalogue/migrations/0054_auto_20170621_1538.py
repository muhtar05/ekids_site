# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-06-21 12:38
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0053_auto_20170620_1622'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='AttributeOption',
            new_name='ProductAttributeOption',
        ),
        migrations.RenameModel(
            old_name='AttributeOptionGroup',
            new_name='ProductAttributeOptionGroup',
        ),
    ]