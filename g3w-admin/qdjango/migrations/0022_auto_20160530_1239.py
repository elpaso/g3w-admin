# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-05-30 12:39
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('qdjango', '0021_auto_20160530_0852'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='baselayer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='qdjango_project_baselayer', to='core.BaseLayer', verbose_name='Base Layer'),
        ),
        migrations.AlterField(
            model_name='widget',
            name='widget_type',
            field=models.CharField(choices=[('law', 'Law'), ('tooltip', 'Tooltip'), ('search', 'Search')], max_length=255, verbose_name='Type'),
        ),
    ]
