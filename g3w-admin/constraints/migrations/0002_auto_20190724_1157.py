# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-07-24 11:57
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0008_alter_user_username_max_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('constraints', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='constraintrule',
            unique_together=set([('constraint', 'group'), ('constraint', 'user')]),
        ),
    ]
