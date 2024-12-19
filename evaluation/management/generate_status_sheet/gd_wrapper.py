from asyncio.log import logger
import json
import os
from django.conf import settings
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials


class GDWrapper:
    def __init__(self, speadsheet_id) -> None:
        scopes = [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/spreadsheets",
        ]

        self.speadsheet_id = speadsheet_id

        current_directory = os.getcwd()
        config_file_path = os.path.join(current_directory, "gd_config.json")
        credentials = Credentials.from_service_account_file(
            config_file_path, scopes=scopes
        )

        self.sheets_service = build("sheets", "v4", credentials=credentials)

    
    def update_sheet(self, sheet_name, data):
        fieldnames = data[0].keys()
        values = [list(fieldnames)]
        for entry in data:
            row = []
            for field in fieldnames:
                value = entry.get(field, "")
                if isinstance(value, dict):
                    value = json.dumps(value)
                row.append(str(value))
            values.append(row)

        self.sheets_service.spreadsheets().values().clear(
            spreadsheetId=self.speadsheet_id, range=sheet_name
        ).execute()

        body = {"values": values}
        result = (
            self.sheets_service.spreadsheets()
            .values()
            .update(
                spreadsheetId=self.speadsheet_id,
                range=sheet_name,
                valueInputOption="RAW",
                body=body,
            )
            .execute()
        )

        logger.info(f"Cells updated in the sheet {sheet_name}.")

    def get_sheet_as_json(self, sheet_name):
        # Fetch the data from the sheet
        result = (
            self.sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=self.speadsheet_id, range=sheet_name)
            .execute()
        )

        values = result.get("values", [])

        if not values:
            return []

        # The first row contains the headers/fieldnames
        fieldnames = values[0]

        # Convert rows to a list of dictionaries
        data = []
        for row in values[1:]:
            entry = {}
            for i, field in enumerate(fieldnames):
                # Handle missing values by filling with an empty string
                entry[field] = row[i] if i < len(row) else ""
            data.append(entry)

        return data

    def rename_spreadsheet(self, new_spreadsheet_name):
        requests = [
            {
                "updateSpreadsheetProperties": {
                    "properties": {"title": new_spreadsheet_name},
                    "fields": "title",
                }
            }
        ]

        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=self.speadsheet_id, body={"requests": requests}
        ).execute()

        logger.info(f"Spreadsheet renamed to {new_spreadsheet_name}.")

    def get_existing_data(self, sheet_name):
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=self.speadsheet_id,
            range=sheet_name
        ).execute()
        values = result.get('values', [])
        return values
    

    def is_row_in_existing_data(self,new_row, existing_data):
        new_row_sorted = sorted(new_row)
        for row in existing_data:
            row_sorted = sorted(row)
            if new_row_sorted == row_sorted:
                return True
        return False

    def update_sheet_for_new_data(self, sheet_name, data, unique_key_index=None):
        logger.info(f"Updating sheet {sheet_name} with new data...")

        # Read existing data
        existing_data = self.get_existing_data(sheet_name)

        # Get fieldnames from the new data
        fieldnames = data[0].keys()

        # If existing data is empty, add fieldnames as the first row
        if not existing_data:
            existing_data = [list(fieldnames)]
            logger.info("Existing data was empty, adding fieldnames as the first row.")

        # If unique_key_index is not provided, add new data without checking for duplicates
        if unique_key_index is None:
            for entry in data:
                new_row = [str(entry[field]) for field in entry.keys()]
                if not self.is_row_in_existing_data(new_row, existing_data):
                    existing_data.append(new_row)
        else:
            # Create a dictionary to store existing data with the unique key as the key
            existing_data_dict = {row[unique_key_index]: row for row in existing_data}
            
            # Iterate through new data
            for entry in data:
                key_value = str(entry[list(entry.keys())[unique_key_index]])
                
                if key_value in existing_data_dict:
                    logger.info(f"Updating existing row for key value: {key_value}")
                    # Update existing row
                    existing_row = existing_data_dict[key_value]
                    for i, field in enumerate(entry.keys()):
                        existing_row[i] = str(entry[field])
                else:
                    logger.info(f"Adding new row for key value: {key_value}")
                    # Add new row
                    new_row = [str(entry[field]) for field in entry.keys()]
                    if not self.is_row_in_existing_data(new_row, existing_data):
                        existing_data.append(new_row)

        # Write updated data back to the sheet
        body = {"values": existing_data}
        result = (
            self.sheets_service.spreadsheets()
            .values()
            .update(
                spreadsheetId=self.speadsheet_id,
                range=sheet_name,
                valueInputOption="RAW",
                body=body,
            )
            .execute()
        )
        logger.info(f"Data updated in the sheet {sheet_name}.")

    
    def get_or_create_sheet(self, sheet_name):
        spreadsheet_id = self.speadsheet_id
        worksheets = self.sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for worksheet in worksheets.get('sheets', []):
            if worksheet.get('properties', {}).get('title') == sheet_name:
                return worksheet
        body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name,
                        'gridProperties': {
                            'rowCount': 100,
                            'columnCount': 20
                        }
                    }
                }
            }]
        }
        response = self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        return response

    def find_row_by_value(self, sheet_name, column_name, value):
        logger.info(f"Searching for value '{value}' in column '{column_name}' of sheet '{sheet_name}'.")

        # Fetch existing data from the sheet
        existing_data = self.get_existing_data(sheet_name)

        # Get the index of the specified column
        column_index = None
        for i, field in enumerate(existing_data[0]):
            if field == column_name:
                column_index = i
                break

        if column_index is None:
            logger.error(f"Column '{column_name}' not found in the sheet '{sheet_name}'.")
            return None

        # Iterate through the existing data to find the row with the specified value
        for row in existing_data:
            if row[column_index] == value:
                # Convert row data to key-value pair
                row_data = {existing_data[0][i]: row[i] for i in range(len(row))}
                return row_data

        logger.info(f"Value '{value}' not found in column '{column_name}' of sheet '{sheet_name}'.")
        return None
    

    def smart_update_sheet(self, sheet_name, new_data, key_fields):
        """
        Updates sheet by comparing existing data with new data based on key fields.
        
        Args:
            sheet_name (str): Name of the sheet to update
            new_data (list): List of dictionaries containing new data
            key_fields (list): List of field names to use as unique identifiers
        """
        logger.info(f"Smart updating sheet {sheet_name} using keys: {key_fields}")

        # Get existing data
        existing_data = self.get_sheet_as_json(sheet_name)
        
        # Create a dictionary of existing data using key fields as composite key
        existing_data_dict = {}
        for row in existing_data:
            composite_key = tuple(str(row.get(key, '')) for key in key_fields)
            existing_data_dict[composite_key] = row

        # Process new data
        updated_data = existing_data.copy()  # Start with existing data
        for new_row in new_data:
            # Create composite key for new row
            composite_key = tuple(str(new_row.get(key, '')) for key in key_fields)
            
            if composite_key in existing_data_dict:
                # Row exists - check if update needed
                existing_row = existing_data_dict[composite_key]
                if self._row_needs_update(existing_row, new_row):
                    logger.info(f"Updating existing row with key: {composite_key}")
                    # Find and update the row in updated_data
                    for i, row in enumerate(updated_data):
                        if all(str(row.get(key, '')) == str(new_row.get(key, '')) for key in key_fields):
                            updated_data[i] = new_row
                            break
            else:
                # New row - append to data
                logger.info(f"Adding new row with key: {composite_key}")
                updated_data.append(new_row)

        # Update sheet with final data
        self.update_sheet(sheet_name, updated_data)

    def _row_needs_update(self, existing_row, new_row):
        """
        Compare existing and new row to determine if update is needed.
        Returns True if rows are different, False if they're the same.
        """
        return any(
            str(existing_row.get(key, '')) != str(new_row.get(key, ''))
            for key in set(existing_row.keys()) | set(new_row.keys())
        )
    
