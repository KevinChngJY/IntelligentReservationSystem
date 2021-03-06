# Generated by Django 3.1.2 on 2020-10-26 13:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nus', '0016_auto_20201026_2139'),
    ]

    operations = [
        migrations.AlterField(
            model_name='establishments',
            name='close_time',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='company',
            field=models.TextField(default='-', max_length=100),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='contact',
            field=models.TextField(default='-', max_length=50),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='days_in_advance',
            field=models.IntegerField(default='-', max_length=50),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='default_duration',
            field=models.IntegerField(max_length=50),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='email',
            field=models.TextField(default='-', max_length=50),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='location',
            field=models.TextField(default='-', max_length=100),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='max_cap',
            field=models.IntegerField(max_length=50),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='max_group_size',
            field=models.IntegerField(max_length=50),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='open_days',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='open_time',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='report_period',
            field=models.IntegerField(default='14', max_length=10),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='sublocs',
            field=models.TextField(default='-', max_length=100),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='type_business',
            field=models.TextField(default='-', max_length=50),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='username',
            field=models.TextField(default='-', max_length=50),
        ),
        migrations.AlterField(
            model_name='queries',
            name='action',
            field=models.TextField(default='-', max_length=50),
        ),
        migrations.AlterField(
            model_name='queries',
            name='establishment',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='queries',
            name='intent',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='queries',
            name='n_person',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='queries',
            name='patron',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='queries',
            name='selection',
            field=models.TextField(default='-', max_length=50),
        ),
        migrations.AlterField(
            model_name='queries',
            name='session',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='queries',
            name='step',
            field=models.TextField(default='-', max_length=50),
        ),
        migrations.AlterField(
            model_name='queries',
            name='time_in',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='queries',
            name='time_out',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='queries',
            name='timestamp',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='reservations',
            name='establishment',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='reservations',
            name='intent',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='reservations',
            name='loc',
            field=models.TextField(default='-', max_length=50),
        ),
        migrations.AlterField(
            model_name='reservations',
            name='n_person',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='reservations',
            name='patron',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='reservations',
            name='session',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='reservations',
            name='status',
            field=models.TextField(default='-', max_length=50),
        ),
        migrations.AlterField(
            model_name='reservations',
            name='time_in',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='reservations',
            name='time_out',
            field=models.TextField(max_length=50),
        ),
        migrations.AlterField(
            model_name='reservations',
            name='timestamp',
            field=models.TextField(max_length=50),
        ),
    ]
