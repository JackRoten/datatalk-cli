# import openpyxl
import argparse
from re import S
from openpyxl import Workbook, load_workbook, workbook

def csv_file(path: str):
    """
    Offer ability to handle skip rows in .csv files 
    """
    # read in file and check for spaces in headers
    pass


def excel_file(path :str):
    """
    Interface for excel files
    1st if there are more than one sheet, ask user which sheet to use
    Allow for switching between different excel sheets in terminal
    Display sheets and top ten results in a visable view
    Prompt user to switch between different sheets and 
    select which sheet is needed
    """
    # Read in file and show items in excel file sheets
    
    wb = Workbook()
    wb = load_workbook(path)
    sheets = wb.sheetnames

    if len(sheets) > 1:
        print(f"More than one sheet: {sheets}")

    # sheet = workbook.active

    sheet = wb[sheets[0]] 
    

    # display top five rows
    num_top_rows = 5
    for row in sheet.iter_rows(min_row=1, max_row=num_top_rows):
        # Iterate over the cells in each row to print their values
        row_values = [cell.value for cell in row]
        print(row_values)
    
    pass

def pdf_file(path: str):
    """
    Function to interact with pdf files including tables
    Must present avaliable tables and give options to tune parameters

    """
    pass



def file_handler(args, printer):
    # Extension conditions
    file_object = None
    if args.extension == "csv" or "txt":
        file_object = csv_handler(args.file)
        pass
    elif args.extension == "xlsx":
        file_object = excel_handler(arg.file)
        # pass
    elif args.extension == "pdf":
        file_object = pdf_handler(arg.file)
        # pass
    else:
        print(f"{args.extension} file not supported: if you want to support this type of file raise an issue with datatalk-cli")

    return file_object

# path = "/Users/jackroten/Code/github.com/jackroten/datatalk-cli/tests/test_data_2_sheets_e2e.xlsx"
# path = "/Users/jackroten/Code/github.com/jackroten/datatalk-cli/tests/test_data_floating_table_e2e.xlsx"
# file_handler(path)