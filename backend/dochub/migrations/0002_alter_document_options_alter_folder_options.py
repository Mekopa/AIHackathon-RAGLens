# Generated by Django 5.0.2 on 2025-03-12 23:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dochub', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='document',
            options={'ordering': ['-created_at'], 'verbose_name': 'Document', 'verbose_name_plural': 'Documents'},
        ),
        migrations.AlterModelOptions(
            name='folder',
            options={'ordering': ['name'], 'verbose_name': 'Folder', 'verbose_name_plural': 'Folders'},
        ),
    ]
