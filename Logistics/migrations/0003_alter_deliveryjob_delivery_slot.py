# Generated by Django 4.2.10 on 2024-02-24 11:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Logistics', '0002_alter_deliveryjob_vehicle'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deliveryjob',
            name='delivery_slot',
            field=models.DateTimeField(null=True),
        ),
    ]
