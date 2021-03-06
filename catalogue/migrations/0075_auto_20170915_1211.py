# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-09-15 09:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0074_merge_20170914_1042'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='driver_status',
            field=models.SmallIntegerField(choices=[(0, 'Нет'), (1, 'Забрал'), (2, 'Отменен'), (3, 'Перенесен'), (4, 'Удален')], default=0, verbose_name='Статус водителя'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_p',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В предложном падеже'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_r',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В родительном падеже'),
        ),
    ]
