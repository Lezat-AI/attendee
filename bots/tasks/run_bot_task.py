import logging
import os
import signal
from datetime import timedelta

from celery import shared_task
from celery.signals import worker_shutting_down

from bots.bot_controller import BotController

logger = logging.getLogger(__name__)


def skip_reason(bot, *, redelivered, now):
    """Lezat: why a run_bot task should not run this bot, or None to run it.

    On Railway the bot task runs on a shared celery worker, so a task that ran
    past the broker's visibility timeout is handed out again (bot 63 kept every
    worker busy for days this way). Only a bot that still has to join is run.
    """
    from bots.models import BotStates

    if bot.state in (BotStates.FATAL_ERROR, BotStates.ENDED, BotStates.DATA_DELETED):
        return f"bot is already {BotStates(bot.state).label}"
    if redelivered and bot.state not in (BotStates.JOINING, BotStates.STAGED):
        return f"task was redelivered and the bot is {BotStates(bot.state).label}, so another worker already ran it"
    if bot.state == BotStates.JOINING and (bot.join_at or bot.created_at) < now - timedelta(hours=1):
        return "bot has been joining for more than an hour"
    return None


@shared_task(bind=True, soft_time_limit=3600)
def run_bot(self, bot_id):
    from django.utils import timezone

    from bots.models import Bot

    bot = Bot.objects.get(id=bot_id)
    redelivered = bool((self.request.delivery_info or {}).get("redelivered"))
    reason = skip_reason(bot, redelivered=redelivered, now=timezone.now())
    if reason:
        logger.info(f"Not running bot {bot_id}: {reason}")
        return

    logger.info(f"Running bot {bot_id}")
    bot_controller = BotController(bot_id)
    bot_controller.run()


def kill_child_processes():
    # Get the process group ID (PGID) of the current process
    pgid = os.getpgid(os.getpid())

    try:
        # Send SIGTERM to all processes in the process group
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass  # Process group may no longer exist


@worker_shutting_down.connect
def shutting_down_handler(sig, how, exitcode, **kwargs):
    # Just adding this code so we can see how to shut down all the tasks
    # when the main process is terminated.
    # It's likely overkill.
    logger.info("Celery worker shutting down, sending SIGTERM to all child processes")
    kill_child_processes()
