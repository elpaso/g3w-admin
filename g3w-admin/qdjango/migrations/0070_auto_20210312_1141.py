# Generated by Django 2.2.16 on 2021-03-12 11:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('qdjango', '0069_auto_20210310_0838'),
    ]

    operations = [
        migrations.AlterField(
            model_name='singlelayerconstraint',
            name='name',
            field=models.CharField(default='title', max_length=255, verbose_name='Name'),
            preserve_default=False,
        ),
    ]
