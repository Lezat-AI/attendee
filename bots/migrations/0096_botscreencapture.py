# Lezat fork: screen captures taken on request while someone shares their screen.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bots', '0095_alter_participantevent_event_type_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BotScreenCapture',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.CharField(editable=False, max_length=32, unique=True)),
                ('timestamp_ms', models.BigIntegerField()),
                ('image', models.BinaryField()),
                ('content_type', models.CharField(default='image/jpeg', max_length=32)),
                ('width', models.IntegerField()),
                ('height', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('bot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screen_captures', to='bots.bot')),
            ],
            options={
                'ordering': ['timestamp_ms'],
            },
        ),
    ]
