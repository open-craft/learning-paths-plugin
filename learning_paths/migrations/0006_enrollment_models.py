# Generated by Django 4.2.16 on 2025-03-28 09:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('learning_paths', '0005_learningpathstep_weight_learningpathgradingcriteria'),
    ]

    operations = [
        migrations.AddField(
            model_name='learningpathenrollment',
            name='enrolled_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, help_text='Timestamp of enrollment or un-enrollment. To be explicitly set when performing a learner enrollment.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='learningpathenrollment',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Indicates if the learner is enrolled or not in the Learning Path'),
        ),
        migrations.CreateModel(
            name='HistoricalLearningPathEnrollment',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_active', models.BooleanField(default=True, help_text='Indicates if the learner is enrolled or not in the Learning Path')),
                ('enrolled_at', models.DateTimeField(blank=True, editable=False, help_text='Timestamp of enrollment or un-enrollment. To be explicitly set when performing a learner enrollment.')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('learning_path', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='learning_paths.learningpath')),
                ('user', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical learning path enrollment',
                'verbose_name_plural': 'historical learning path enrollments',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='LearningPathEnrollmentAllowed',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('learning_path', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='learning_paths.learningpath')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('email', 'learning_path')},
            },
        ),
    ]
