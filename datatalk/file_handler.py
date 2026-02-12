# import openpyxl
import argparse
from openpyxl import Workbook, load_workbook

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

    pass

def pdf_file(path: str):
    """
    Function to interact with pdf files including tables
    Must present avaliable tables and give options to tune parameters

    """
    pass

path = "/Users/jackroten/Code/github.com/jackroten/datatalk-cli/tests/test_data_2_sheets_e2e.xlsx"
# path = "/Users/jackroten/Code/github.com/jackroten/datatalk-cli/tests/test_data_floating_table_e2e.xlsx"
excel_file(path)


def file_handler(args: argparse, )