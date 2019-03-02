# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-12-09 13:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0019_auto_20161208_1433'),
    ]

    operations = [
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=255, verbose_name='Name')),
                ('image', models.ImageField(blank=True, max_length=255, null=True, upload_to='brands', verbose_name='Image')),
            ],
            options={
                'verbose_name_plural': 'Бренды',
                'verbose_name': 'Бренд',
            },
        ),
    ]
