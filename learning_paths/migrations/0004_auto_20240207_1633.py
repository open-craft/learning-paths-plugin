# Generated by Django 3.2.21 on 2024-02-07 16:33

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('learning_paths', '0003_learningpath_subtitle'),
    ]

    operations = [
        migrations.CreateModel(
            name='LearningPathEnrollment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('learning_path', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='learning_paths.learningpath')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'learning_path')},
            },
        ),
        migrations.AddField(
            model_name='learningpath',
            name='enrolled_users',
            field=models.ManyToManyField(through='learning_paths.LearningPathEnrollment', to=settings.AUTH_USER_MODEL),
        ),
    ]
