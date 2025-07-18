# Generated by Django 4.2.16 on 2024-11-10 14:07

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigMap',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date created')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='Unique ID for this config map.', primary_key=True, serialize=False)),
                ('tag', models.CharField(help_text='The tag to identify the config.', max_length=30)),
                ('config', models.JSONField(help_text='Config corresponding to the tag.')),
                ('is_active', models.BooleanField(default=False, help_text='Is the config active')),
            ],
            options={
                'verbose_name': 'Config Map',
                'verbose_name_plural': 'Config Maps',
            },
        ),
        migrations.CreateModel(
            name='InstituteData',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('institute_name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='QuestionBank',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date created')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('question', models.TextField(blank=True, help_text='Practice question', max_length=1000, null=True)),
                ('hints', models.TextField(blank=True, help_text='Practice question hints', max_length=1000, null=True)),
                ('type', models.CharField(choices=[('IL', 'IELTS'), ('IP', 'Interview Prep'), ('CQ', 'Custom question entered by the user')], default='IL', help_text='Practice question type', max_length=2)),
                ('response_timelimit', models.SmallIntegerField(blank=True, default=60, help_text='Practice question attempt response time limit in secs', null=True)),
                ('is_active', models.BooleanField(default=True, help_text='Is practice question active')),
            ],
            options={
                'verbose_name': 'Question Bank',
                'verbose_name_plural': 'Bank Questions',
            },
        ),
        migrations.AddConstraint(
            model_name='configmap',
            constraint=models.UniqueConstraint(condition=models.Q(('is_active', True)), fields=('tag',), name='one_active_config_per_tag'),
        ),
    ]
