from django.core.management.base import BaseCommand
from accounts.repositories import UserConfigMappingRepository
from evaluation.management.generate_status_sheet.gd_wrapper import GDWrapper
from accounts.models import UserConfigMapping

class Command(BaseCommand):
    help = 'Sync user configurations from Google Sheet'

    def add_arguments(self, parser):
        parser.add_argument('spreadsheet_id', type=str)

    def handle(self, *args, **options):
        spreadsheet_id = options['spreadsheet_id']
        gd_wrapper = GDWrapper(spreadsheet_id)
        
        # Read user configs from sheet
        sheet_data = gd_wrapper.get_sheet_as_json("sheet1")
        
        config_mappings = []
        existing_emails = set(UserConfigMapping.objects.values_list('email', flat=True))
        
        for row in sheet_data:
            # Skip if email already exists
            if row['Email'] in existing_emails:
                self.stdout.write(f"Skipping existing config for email: {row['Email']}")
                continue
                
            role = row['Role']
            if role == 'lecturer':
                config = {
                    'role': role,
                    'first_name': row.get('First Name', ''),
                    'last_name': row.get('Last Name', ''),
                    'course_provider_id': row.get('Course Provider ID'),
                    'course_code': row.get('Course Code'),
                    'batch_id':row.get('Batch ID')
                }
            elif role == 'student':
                config = {
                    'role': role,
                    'first_name': row.get('First Name', ''),
                    'last_name': row.get('Last Name', ''),
                    'batch_id':row.get('Batch ID'),
                    'course_code':row.get('Course Code')
                }
            elif role == 'course_provider_admin':
                config = {
                    'role': role,
                    'first_name': row.get('First Name', ''),
                    'last_name': row.get('Last Name', ''),
                    'course_provider_id': row.get('Course Provider ID')
                }
                
            config_mappings.append(
                UserConfigMapping(
                    email=row['Email'],
                    config=config
                )
            )
        
        # Bulk create config mappings
        if config_mappings:
            UserConfigMappingRepository.bulk_create_user_config_mappings(config_mappings)
            self.stdout.write(self.style.SUCCESS(f'Successfully synced {len(config_mappings)} new user configs'))
        else:
            self.stdout.write(self.style.SUCCESS('No new user configs to sync')) 