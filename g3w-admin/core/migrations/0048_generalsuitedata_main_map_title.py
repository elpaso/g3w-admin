# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2018-04-19 13:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0047_generalsuitedata_url_suite_logo'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalsuitedata',
            name='main_map_title',
            field=models.CharField(blank=True, max_length=400, null=True, verbose_name='Main map title'),
        ),
    ]
