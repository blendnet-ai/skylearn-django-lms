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