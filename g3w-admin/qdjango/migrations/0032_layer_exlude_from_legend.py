# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-12-29 16:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('qdjango', '0031_layer_edittypes'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='exlude_from_legend',
            field=models.BooleanField(default=False, verbose_name='Exclude to legend'),
        ),
    ]
