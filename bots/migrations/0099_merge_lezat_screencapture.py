# Lezat: joins our 0096_botscreencapture branch with upstream's 0096-0098 chain.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("bots", "0096_botscreencapture"),
        ("bots", "0098_botlogentry_auto_leave_silence_pending"),
    ]

    operations = []
