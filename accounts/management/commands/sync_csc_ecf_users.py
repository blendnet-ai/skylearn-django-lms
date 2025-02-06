from django.core.management.base import BaseCommand
from accounts.csc_ecf_reg import main

class Command(BaseCommand):
    help = "Syncs users from CSC and ECF APIs"

    def handle(self, *args, **options):
        self.stdout.write("Starting CSC and ECF user sync...")
        try:
            main()
            self.stdout.write(self.style.SUCCESS("Successfully synced users from CSC and ECF"))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error syncing users from CSC and ECF: {str(e)}")
            ) 