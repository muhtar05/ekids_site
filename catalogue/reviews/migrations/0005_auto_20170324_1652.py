# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-03-24 13:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0004_remove_productreview_title'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productreview',
            name='status',
            field=models.SmallIntegerField(choices=[(0, 'Requires moderation'), (1, 'Approved'), (2, 'Rejected')], default=0, verbose_name='Status'),
        ),
        migrations.AlterField(
            model_name='reviewcomment',
            name='status',
            field=models.SmallIntegerField(choices=[(0, 'Нуждается в модерации'), (1, 'Одобрен'), (2, 'Отклонен')], default=0, verbose_name='Статус'),
        ),
    ]
