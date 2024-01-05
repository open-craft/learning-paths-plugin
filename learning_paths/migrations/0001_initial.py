# Generated by Django 3.2.23 on 2024-01-23 12:16

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import opaque_keys.edx.django.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='LearningPath',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('slug', models.SlugField(help_text='Custom unique code identifying this Learning Path.', unique=True)),
                ('display_name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('image_url', models.CharField(blank=True, help_text='URL to an image representing this Learning Path.', max_length=200, verbose_name='Image URL')),
                ('level', models.CharField(blank=True, choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')], max_length=255)),
                ('duration_in_days', models.PositiveIntegerField(blank=True, help_text='Approximate time (in days) it should take to complete this Learning Path.', null=True, verbose_name='Duration (days)')),
                ('sequential', models.BooleanField(help_text='Whether the courses in this Learning Path are meant to be taken sequentially.', verbose_name='Is sequential')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('display_name', models.CharField(max_length=255)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RequiredSkill',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('level', models.PositiveIntegerField(help_text='The skill level associated with this course.')),
                ('learning_path', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='learning_paths.learningpath')),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='learning_paths.skill')),
            ],
            options={
                'abstract': False,
                'unique_together': {('learning_path', 'skill')},
            },
        ),
        migrations.CreateModel(
            name='LearningPathStep',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('course_key', opaque_keys.edx.django.models.CourseKeyField(max_length=255)),
                ('relative_due_date_in_days', models.PositiveIntegerField(blank=True, help_text='Used to calculate the due date from the starting date of the course.', null=True, verbose_name='Due date (days)')),
                ('order', models.PositiveIntegerField(blank=True, help_text='Ordinal position of this step in the sequence of the Learning Path, if applicable.', null=True, verbose_name='Sequential order')),
                ('learning_path', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='learning_paths.learningpath')),
            ],
            options={
                'unique_together': {('learning_path', 'course_key')},
            },
        ),
        migrations.CreateModel(
            name='AcquiredSkill',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('level', models.PositiveIntegerField(help_text='The skill level associated with this course.')),
                ('learning_path', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='learning_paths.learningpath')),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='learning_paths.skill')),
            ],
            options={
                'abstract': False,
                'unique_together': {('learning_path', 'skill')},
            },
        ),
    ]
