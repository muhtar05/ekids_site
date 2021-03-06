# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-09-08 11:36
from __future__ import unicode_literals

import core.validators
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0072_auto_20170829_2032'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='productattributeoption',
            options={'ordering': ('option',), 'verbose_name': 'Опция атрибута', 'verbose_name_plural': 'Опции для атрибутов'},
        ),
        migrations.AlterField(
            model_name='productattribute',
            name='code',
            field=models.SlugField(max_length=128, validators=[django.core.validators.RegexValidator(message="Code can only contain the letters a-z, A-Z, digits, and underscores, and can't start with a digit.", regex='^[a-zA-Z_][0-9a-zA-Z_-]*$'), core.validators.non_python_keyword], verbose_name='Code'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_i',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В именительном падеже'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_mi',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Во множественном числе им. падеже'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_mr',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Во множественном числе род. падеже'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_p',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В дательном падеже'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_r',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В  родительном падеже'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_v',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В винительном падеже'),
        ),
    ]
