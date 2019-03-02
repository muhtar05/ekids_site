# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-10-13 09:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0081_auto_20171012_1322'),
    ]

    operations = [
        migrations.AddField(
            model_name='productattributeoption',
            name='case_d_g',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В дательном падеже в женском роде'),
        ),
        migrations.AddField(
            model_name='productattributeoption',
            name='case_i_g',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В именительном падеже в женском роде'),
        ),
        migrations.AddField(
            model_name='productattributeoption',
            name='case_p_g',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В предложном падеже в женском роде'),
        ),
        migrations.AddField(
            model_name='productattributeoption',
            name='case_r_g',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В родительном падеже в женском роде'),
        ),
        migrations.AddField(
            model_name='productattributeoption',
            name='case_t_g',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В творительном падеже в женском роде'),
        ),
        migrations.AddField(
            model_name='productattributeoption',
            name='case_v_g',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В винительном падеже в женском роде'),
        ),
        migrations.AlterField(
            model_name='category',
            name='name_plural_r',
            field=models.CharField(db_index=True, max_length=255, null=True, verbose_name='Название во множественном числе в род. падеже'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_d',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В дательном падеже в мужском роде'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_i',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В именительном падеже в мужском роде'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_p',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В предложном падеже в мужском роде'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_r',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В родительном падеже в мужском роде'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_t',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В творительном падеже в мужском роде'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_v',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В винительном падеже в мужском роде'),
        ),
    ]