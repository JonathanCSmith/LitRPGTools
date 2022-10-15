import re

import pygsheets
from pygsheets import Spreadsheet, WorksheetNotFound, DataRange, Address
from pygsheets.exceptions import RangeNotFound

from utils.string_utils import number_to_letter


def check_rows(data):
    last_length = -1
    for row in data:
        length = len(row)
        if last_length != -1 and last_length != length:
            raise AttributeError("provided data rows were not all the same length!")
        else:
            last_length = length
    return last_length


def build_gsheets_communicator(file_path=None):
    if file_path is None:
        file_path = "./client-secret.json"
    return pygsheets.authorize(service_file=file_path)


class SystemSheetLayoutHandler:
    def __init__(self, gsheets_connector, target_spreadsheet, target_worksheet):
        self.gsheets_connector = gsheets_connector
        self.target_spreadsheet = target_spreadsheet
        self.target_worksheet = target_worksheet
        self.current_write_index = 1

        # Clear cache
        # self.gsheets_connector.run_batch()
        # self.gsheets_connector.set_batch_mode(False)

        try:
            self.worksheet = self.target_spreadsheet.worksheet_by_title(self.target_worksheet)
        except WorksheetNotFound:
            try:
                template_sheet = self.target_spreadsheet.worksheet_by_title("Template")
                self.worksheet = self.target_spreadsheet.add_worksheet(self.target_worksheet, src_worksheet=template_sheet)
            except:
                self.worksheet = self.target_spreadsheet.add_worksheet(self.target_worksheet)
        # self.gsheets_connector.set_batch_mode(True)

    def write_category_data(self, engine, category, category_data):
        for entry_key in category_data:
            entry = engine.get_entry(entry_key)
            if not entry.get_print_to_overview():
                continue

            items = entry.get_values()

            # Build data obj by looping through our values - skip lines where there is no user supplied data
            data_to_write = []
            properties = category.get_properties()
            for i in range(0, len(properties)):
                try:
                    item = items[i]
                except:
                    items.append("")
                    item = ""

                if item != "":
                    data_to_write.append([properties[i].get_property_name(), item])

            self.write_next(data_to_write)
            self.write_next([["", ""]])

    def write_next(self, data, name=None):
        # Dump the data
        row_count = len(data)

        # Cleanse the data
        for row_index in range(len(data)):
            for cell_index in range(len(data[row_index])):
                data[row_index][cell_index] = data[row_index][cell_index].replace("\t", "    ")

        # Preallocate rows
        while self.current_write_index + row_count > self.worksheet.rows:
            self.worksheet.add_rows(100)
            self.gsheets_connector.run_batch()

        # Create the range pointers
        start = "A" + str(self.current_write_index)
        self.current_write_index += row_count
        end = "B" + str(self.current_write_index)

        # Output
        self.worksheet.update_values(start + ":" + end, data)

        # Named ranges
        if name is not None:
            name = re.sub(r'[^a-zA-Z0-9 \n\.]', '_', name).replace(" ", "_")
            end = "B" + str(self.current_write_index - 1)
            try:
                dr = self.worksheet.get_named_range(name)
                if dr.range != start + ":" + end:

                    # It's possible for this to fuck up based on where the new range is moving to relative to the old range, so we should try both ways before allowing the error to crash
                    try:
                        dr.start_addr = Address(start)
                        dr.end_addr = Address(end)
                    except AssertionError as ae:
                        dr.end_addr = Address(end)
                        dr.start_addr = Address(start)

            except RangeNotFound:
                dr = DataRange(start=start, end=end, worksheet=self.worksheet)
                dr.name = name

    def clear_all(self):
        self.worksheet.clear()


class CategorySheetLayoutHandler:
    def __init__(self, gsheets_connector, target_spreadsheet, category, existing_pointers):
        self.gsheets_connector = gsheets_connector
        self.target_spreadsheet = target_spreadsheet
        self.category = category
        self.pointers = existing_pointers

        # Clear cache
        self.gsheets_connector.run_batch()
        self.gsheets_connector.set_batch_mode(False)

        # Grab our worksheet
        try:
            self.worksheet = self.target_spreadsheet.worksheet_by_title(self.category.get_name())
        except WorksheetNotFound:
            try:
                template_sheet = self.target_spreadsheet.worksheet_by_title("Template")
                self.worksheet = self.target_spreadsheet.add_worksheet(self.category.get_name(), src_worksheet=template_sheet)
            except:
                self.worksheet = self.target_spreadsheet.add_worksheet(self.category.get_name())
        self.gsheets_connector.set_batch_mode(False)

        # Handle our pointers
        self.next_column = 1
        if len(self.pointers) != 0:
            self.next_column = max(self.pointers.values()) + 3

    def write_historical_category_data(self, category_data, last_seen, all_entries, history):
        for entry in category_data:
            # Recurse through this entry's history and output all items that haven't ever been output before
            last_sheet_tail = False
            while True:
                unique_key = entry.get_unique_key()
                items = entry.get_values()

                # Build data obj by looping through our values - skip lines where there is no user supplied data
                history_index = history.index(unique_key)
                data_to_write = [["History index: ", str(history_index)]]
                properties = self.category.get_properties()
                for i in range(0, len(properties)):
                    item = items[i]
                    if item != "":
                        data_to_write.append([properties[i].get_property_name(), item])
                self.write_next(unique_key, data_to_write)

                # Add self to last seen
                last_seen.append(unique_key)

                # Get historical parent
                parent_key = entry.get_parent_key()

                # If there is a parent that hasnt been output before we work through it like normal
                if parent_key is not None and parent_key not in last_seen:
                    entry = all_entries[parent_key]

                # Sometimes we will need to reference the last 'observed' data before we added new data. So put the last observed data from previous outputs into this sheet
                elif parent_key in last_seen and not last_sheet_tail:
                    entry = all_entries[parent_key]
                    last_sheet_tail = True
                elif parent_key in last_seen and last_sheet_tail:
                    break

                # Safe to escape from this historical dive
                else:
                    break

    def write_category_data(self, entries, last_seen, history: list, minimum_index):
        for entry in entries:
            unique_key = entry.get_unique_key()
            if unique_key in last_seen:
                continue  # Bit of a design choice here - there may be a case for not doing this?
            history_index = history.index(unique_key)

            # We are only interested in entries that were generated in this tag region
            if history_index < minimum_index:
                continue

            # Write
            items = entry.get_values()
            data_to_write = [["History index: ", str(history_index)]]
            properties = self.category.get_properties()
            for i in range(0, len(properties)):
                item = items[i]
                if item != "":
                    data_to_write.append([properties[i].get_property_name(), item])
            self.write_next(unique_key, data_to_write)
            last_seen.append(entry)

    def write_next(self, pointer, payload):
        row_count = len(payload)

        # Cleanse the data
        for row_index in range(len(payload)):
            for cell_index in range(len(payload[row_index])):
                payload[row_index][cell_index] = payload[row_index][cell_index].replace("\t", "    ")

        # Use remembered position if required
        if pointer in self.pointers:
            target = self.pointers[pointer]
        else:
            target = self.next_column
            self.pointers[pointer] = target
            self.next_column += 3

        # Extend the sheet if required
        while target + 1 > self.worksheet.cols:
            self.worksheet.add_cols(26)

        # Create our data range
        start = number_to_letter(target) + "1"
        end = number_to_letter(target + 1) + str(row_count)

        # Output
        dr = DataRange(start=start, end=end, worksheet=self.worksheet)
        dr.update_values(payload)

        # Handle the boldening
        for row in range(row_count):
            current_cell = dr.cells[row][0]
            current_cell.set_text_format("bold", True)

    def clear_all(self):
        self.worksheet.clear()


class HistorySheetLayoutHandler(SystemSheetLayoutHandler):
    def __init__(self, gsheets_connector, target_spreadsheet, target_worksheet):
        super().__init__(gsheets_connector, target_spreadsheet, target_worksheet)

    def write_historical_data(self, history, entries, categorites, characters, start_inclusive, end_exclusive):
        # Loop through the given part of the history
        counter = start_inclusive
        for unique_key in history[start_inclusive:end_exclusive + 1]:
            entry = entries[unique_key]
            category = categorites[entry.get_category()]

            # Do not output notes only items or items that should no longer be seen by the 'user'
            if not category.print_to_history or not entry.print_to_history:
                continue

            # Basic writable values
            date_headers = category.get_properties()
            data_values = entry.get_values()

            # Build a data matrix
            payload = []
            for i in range(len(date_headers)):
                header = date_headers[i].get_property_name()
                value = data_values[i]

                # Skip empty items
                if value == "":
                    continue

                payload.append([header, value])

            # Write out with a buffer line
            str_counter = f"{counter:03}"
            self.write_next(([[characters[entry.character], str_counter]]))
            self.write_next(payload, name="id_" + unique_key)
            self.write_next([["", ""]])
            counter += 1

    def clear_all(self):
        self.worksheet.clear()
