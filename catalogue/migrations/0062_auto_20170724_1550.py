# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-07-24 12:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0061_productattributevalue_id_attribute_value'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productattribute',
            name='product_class',
        ),
        migrations.RemoveField(
            model_name='productattribute',
            name='category',
        ),
        migrations.AddField(
            model_name='productattribute',
            name='category',
            field=models.ManyToManyField(blank=True, null=True, related_name='attributes', through='catalogue.ProductAttributeCategory', to='catalogue.Category'),
        ),
    ]
