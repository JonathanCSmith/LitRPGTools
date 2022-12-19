import re
from typing import TYPE_CHECKING, List

import pygsheets
from pygsheets import Worksheet, Spreadsheet, WorksheetNotFound, DataRange, Address
from pygsheets.exceptions import RangeNotFound

from new.data import Category, Output

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine


class OverviewSheet:
    def __init__(self, gsheets_handler: 'GSheetsHandler', worksheet_name: str):
        self.gsheets_handler = gsheets_handler
        self.current_write_index = 1

        try:
            self.worksheet = self.gsheets_handler.spreadsheet.worksheet_by_title(worksheet_name)
        except WorksheetNotFound:
            try:
                template_sheet = self.gsheets_handler.spreadsheet.worksheet_by_title("Template")
                self.worksheet = self.gsheets_handler.spreadsheet.add_worksheet(worksheet_name, src_worksheet=template_sheet)
            except:
                self.worksheet = self.gsheets_handler.spreadsheet.add_worksheet(worksheet_name)

    def write(self, engine: 'LitRPGToolsEngine', category: Category, view: List[str], current_index: int):
        data_to_write = [[category.name, ""]]
        for entry_id in view:
            entry = engine.get_entry_by_id(entry_id)
            if entry.is_disabled:
                continue

            # Build a data obj by looping through our values
            for i, content_header in enumerate(category.contents):
                entry_data = entry.data[i]
                if entry_data == "":
                    continue

                data_to_write.append([content_header, engine.translate_using_dynamic_data_at_index_for_character(entry.character_id, entry_data, current_index)])
            data_to_write.append(["", ""])
        self.write_block(data_to_write)

    def write_block(self, data_to_write):
        # Prealloc info
        row_count = len(data_to_write)
        while self.current_write_index + row_count > self.worksheet.rows:
            self.worksheet.add_rows(100)
            self.gsheets_handler.communicator.run_batch()

        # Cleanse our data
        for r_i in range(len(data_to_write)):
            for c_i in range(len(data_to_write[r_i])):
                data_to_write[r_i][c_i] = data_to_write[r_i][c_i].replace("\t", "    ")

        # Range pointers
        start = "A" + str(self.current_write_index)
        self.current_write_index += row_count
        end = "B" + str(self.current_write_index)

        # Output
        self.worksheet.update_values(start + ":" + end, data_to_write)

    def clear_all(self):
        self.worksheet.clear()


class HistorySheet:
    def __init__(self, gsheets_handler: 'GSheetsHandler'):
        self.gsheets_handler = gsheets_handler
        self.current_write_index = 1

        try:
            self.worksheet: Worksheet = self.gsheets_handler.spreadsheet.worksheet_by_title("History")
        except WorksheetNotFound:
            try:
                template_sheet = self.gsheets_handler.spreadsheet.worksheet_by_title("Template")
                self.worksheet: Worksheet = self.gsheets_handler.spreadsheet.add_worksheet("History", src_worksheet=template_sheet)
            except:
                self.worksheet: Worksheet = self.gsheets_handler.spreadsheet.add_worksheet("History")

    def clear_all(self):
        self.worksheet.clear()

    def write(self, engine: 'LitRPGToolsEngine', output: Output):
        named_range_pointers = list()
        output_counter = 0
        for entry_id in output.members:
            entry = engine.get_entry_by_id(entry_id)
            entry_index = engine.get_entry_index_in_history(entry_id)
            str_index = f"{entry_index:32}"
            str_counter = f"{output_counter:32}"
            category = engine.get_category_by_id(entry.category_id)
            character = engine.get_character_by_id(entry.character_id)

            # Create object header and write
            data_to_write = list()
            data_to_write.append(["History Index:", str_index])
            data_to_write.append(["Output Index:", str_counter])
            data_to_write.append([character.name, category.name])
            self.write_block(data_to_write)

            # Build a data obj by looping through our values
            data_to_write = list()
            for i, content_header in enumerate(category.contents):
                entry_data = entry.data[i]
                if entry_data == "":
                    continue

                data_to_write.append([content_header, engine.translate_using_dynamic_data_at_index_for_character(entry.character_id, entry_data, entry_index)])

            # Write data block with index and ensure we 'save' it as a named range to preserve sheet -> doc references
            named_range_pointer = self.write_named_range(entry_id, data_to_write)
            named_range_pointers.append(named_range_pointer)

            # Blank
            self.write_block(["", ""])
            output_counter += 1

        # Handle named ranges clean up - this can happen when an entry was deleted in the UI but printed previously to an output
        current_named_ranges = self.worksheet.get_named_ranges()
        for current_named_range in current_named_ranges:
            if current_named_range not in named_range_pointers:
                self.worksheet.delete_named_range(current_named_range)

    def write_named_range(self, entry_id: str, data_to_write: list[list[str]]):
        start, end = self.write_block(data_to_write)

        # Sanitize name
        name = re.sub(r'[^a-zA-Z0-9 \n\.]', '_', entry_id).replace(" ", "_")

        # Check to see if the named range already exists, if so, adjust
        try:
            nr: DataRange = self.worksheet.get_named_range(name)
            if nr.range == start + ":" + end:
                return

            # Cannot set both at the same time as it throws an error if the data range is 'inverted' so we basically just have to try both
            try:
                nr.start_addr = Address(start)
                nr.end_addr = Address(end)
            except AssertionError as ae:
                nr.end_addr = Address(end)
                nr.start_addr = Address(start)

        except RangeNotFound:
            nr = DataRange(start=start, end=end, worksheet=self.worksheet)
            nr.name = name

        return name

    def write_block(self, data_to_write):
        # Prealloc info
        row_count = len(data_to_write)
        while self.current_write_index + row_count > self.worksheet.rows:
            self.worksheet.add_rows(100)
            self.gsheets_handler.communicator.run_batch()

        # Cleanse our data
        for r_i in range(len(data_to_write)):
            for c_i in range(len(data_to_write[r_i])):
                data_to_write[r_i][c_i] = data_to_write[r_i][c_i].replace("\t", "    ")

        # Range pointers
        start = "A" + str(self.current_write_index)
        self.current_write_index += row_count
        end = "B" + str(self.current_write_index)

        # Output
        self.worksheet.update_values(start + ":" + end, data_to_write)
        return start, end


class GSheetsHandler:
    def __init__(self, engine: 'LitRPGToolsEngine', gui, credentials_path: str):
        self.__engine = engine
        self.__gui = gui
        self.__credentials_path = credentials_path
        self.communicator = None
        self.spreadsheet = None
        self.connect()

    def connect(self):
        self.communicator = pygsheets.authorize(service_file=self.__credentials_path)

    def get_sheets(self):
        try:
            if self.communicator is not None:
                return self.communicator.spreadsheet_titles()
            else:
                return list()

        # Sometimes our connection times out
        except ConnectionAbortedError:
            self.connect()
            return self.communicator.spreadsheet_titles()

    def open(self, target: str):
        self.spreadsheet = self.communicator.open(target)

    def create_overview_sheet(self, name: str) -> OverviewSheet:
        return OverviewSheet(self, name)

    def create_history_sheet(self) -> HistorySheet:
        return HistorySheet(self)
