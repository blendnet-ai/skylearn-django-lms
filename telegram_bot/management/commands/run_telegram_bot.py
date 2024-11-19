from django.core.management.base import BaseCommand
from telegram_bot.bot import run_bot

class Command(BaseCommand):
    help = 'Runs the Telegram bot'

    def handle(self, *args, **options):
        self.stdout.write('Starting Telegram bot...')
        run_bot("7292221420:AAG1mm1YUXXi0arBIHCAjDMPrX-hIfK4DtA")