# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-02-28 17:39
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0017_auto_20170227_0547'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='paymenttype',
            options={'verbose_name': 'Типы оплаты', 'verbose_name_plural': 'Типы оплаты'},
        ),
    ]
