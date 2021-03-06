# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-11-08 09:31
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0091_merge_20171102_1728'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryAttributeSimilar',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.IntegerField(default=0)),
                ('weight', models.IntegerField(blank=True, null=True)),
                ('attribute_similar', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='catalogue.ProductAttribute')),
                ('category_similar', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='catalogue.Category')),
            ],
            options={
                'verbose_name': 'Атрибут/Категория',
                'verbose_name_plural': 'Атрибуты/Категории',
                'ordering': ('position',),
            },
        ),
        migrations.AlterField(
            model_name='product',
            name='attributes',
            field=models.ManyToManyField(through='catalogue.ProductAttributeValue', to='catalogue.ProductAttribute', verbose_name='Attributes'),
        ),
        migrations.AlterField(
            model_name='product',
            name='product_options',
            field=models.ManyToManyField(blank=True, to='catalogue.Option', verbose_name='Product options'),
        ),
        migrations.AlterField(
            model_name='product',
            name='recommended_products',
            field=models.ManyToManyField(blank=True, through='catalogue.ProductRecommendation', to='catalogue.Product', verbose_name='Recommended products'),
        ),
        migrations.AlterUniqueTogether(
            name='categoryattributesimilar',
            unique_together=set([('category_similar', 'attribute_similar')]),
        ),
    ]
