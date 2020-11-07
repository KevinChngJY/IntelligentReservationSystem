# Generated by Django 3.1.2 on 2020-10-21 11:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nus', '0006_establishments_patrons_queries_reservations'),
    ]

    operations = [
        migrations.AddField(
            model_name='establishments',
            name='email',
            field=models.CharField(default='-', max_length=50),
        ),
        migrations.AddField(
            model_name='establishments',
            name='location',
            field=models.CharField(default='-', max_length=100),
        ),
        migrations.AddField(
            model_name='establishments',
            name='type_business',
            field=models.CharField(default='-', max_length=50),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='sublocs',
            field=models.TextField(default='-', max_length=100),
        ),
        migrations.AlterField(
            model_name='establishments',
            name='username',
            field=models.CharField(default='-', max_length=50),
        ),
    ]