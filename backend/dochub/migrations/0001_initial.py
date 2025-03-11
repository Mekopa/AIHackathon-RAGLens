# Generated by Django 5.0.2 on 2025-03-11 10:13

import django.db.models.deletion
import dochub.models
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Folder',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subfolders', to='dochub.folder')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('file', models.FileField(upload_to=dochub.models.document_upload_path)),
                ('file_type', models.CharField(blank=True, max_length=100)),
                ('size', models.PositiveIntegerField(default=0)),
                ('status', models.CharField(choices=[('processing', 'Processing'), ('ready', 'Ready'), ('error', 'Error')], default='processing', max_length=20)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('folder', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='dochub.folder')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
