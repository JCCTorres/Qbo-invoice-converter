import pandas as pd
from datetime import datetime, timedelta
import os
import re

def transform_data(file_path, start_invoice_number, invoice_date):
    """
    Transform the laundry service report to QuickBooks Online format
    
    Args:
        file_path (str): Path to the Excel file
        start_invoice_number (int): Starting invoice number
        invoice_date (datetime): Date for the invoice
        
    Returns:
        pd.DataFrame: Transformed dataframe ready for QBO import
    """
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)
        
        # Check if required columns exist
        required_columns = ['Id', 'Name', 'Cleaning Date', 'House', 'Code', 'Status', 'Price', 'Note']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Make a copy to avoid modifying the original dataframe
        qbo_df = df.copy()
        
        # Remove the last row if it's a total row (common in reports)
        if qbo_df.iloc[-1]['Name'] == '':
            qbo_df = qbo_df[:-1]
        
        # Filter out rows with missing essential data
        qbo_df = qbo_df.dropna(subset=['Name', 'Price'])
        
        # Only keep rows with status "Delivery" or "Production"
        qbo_df = qbo_df[qbo_df['Status'].isin(['Delivery', 'Production', 'Open'])]
        
        # Rename columns as specified
        column_mapping = {
            'Id': '*InvoiceNo',
            'Name': '*Customer',
            'Cleaning Date': 'Service Date',
            'Code': 'ItemDescription',
            'Price': '*ItemAmount',
            'House': 'House'  # Keep for reference, will modify later
        }
        qbo_df = qbo_df.rename(columns=column_mapping)
        
        # Create required new columns
        qbo_df['*InvoiceDate'] = invoice_date.strftime('%d/%m/%Y')
        qbo_df['*DueDate'] = (invoice_date + timedelta(days=4)).strftime('%d/%m/%Y')
        
        # Format ItemDescription: "Order Id: [ID] / [House]"
        qbo_df['ItemDescription'] = 'Order Id: ' + qbo_df['*InvoiceNo'].astype(str) + ' / ' + qbo_df['House'].fillna('')
        
        # Add Notes to ItemDescription if available
        mask = ~qbo_df['Note'].isna() & (qbo_df['Note'] != '')
        qbo_df.loc[mask, 'ItemDescription'] = qbo_df.loc[mask, 'ItemDescription'] + ' / Notes: ' + qbo_df.loc[mask, 'Note']
        
        # Set Item(Product/Service) column
        qbo_df['Item(Product/Service)'] = 'Linhas de Lavanderia:Services'
        
        # Set ItemQuantity to 1 for all rows
        qbo_df['ItemQuantity'] = 1
        
        # Now handle the sequential invoice numbers per customer
        # First, get unique customers in the order they appear
        unique_customers = qbo_df['*Customer'].drop_duplicates().tolist()
        
        # Create a mapping of customer to invoice number
        invoice_mapping = {}
        current_invoice = start_invoice_number
        
        for customer in unique_customers:
            invoice_mapping[customer] = current_invoice
            current_invoice += 1
        
        # Apply the invoice numbers
        qbo_df['*InvoiceNo'] = qbo_df['*Customer'].map(invoice_mapping)
        
        # Now we need to handle the customer name appearing only once per invoice
        # First, sort by invoice number to group by customer
        qbo_df = qbo_df.sort_values(by=['*InvoiceNo'])
        
        # For each invoice number (customer), keep only the first occurrence of customer name
        for inv_num in qbo_df['*InvoiceNo'].unique():
            mask = qbo_df['*InvoiceNo'] == inv_num
            indices = qbo_df[mask].index
            if len(indices) > 1:  # If there are multiple rows for this invoice
                qbo_df.loc[indices[1:], '*Customer'] = ''  # Clear customer name for all but first row
                qbo_df.loc[indices[1:], '*InvoiceDate'] = ''  # Clear invoice date for all but first row
                qbo_df.loc[indices[1:], '*DueDate'] = ''  # Clear due date for all but first row
        
        # Select and order columns as needed for QBO
        final_columns = [
            '*InvoiceNo', 
            '*Customer', 
            '*InvoiceDate', 
            '*DueDate', 
            'Item(Product/Service)', 
            'ItemDescription', 
            'ItemQuantity', 
            '*ItemAmount', 
            'Service Date'
        ]
        
        # Make sure we only keep columns we need
        qbo_df = qbo_df[final_columns]
        
        # Format dates properly
        qbo_df['Service Date'] = pd.to_datetime(qbo_df['Service Date']).dt.strftime('%d/%m/%Y')
        
        return qbo_df
    
    except Exception as e:
        raise Exception(f"Error transforming data: {str(e)}")

def save_to_csv(df, output_path):
    """
    Save the transformed dataframe to a CSV file
    
    Args:
        df (pd.DataFrame): Transformed dataframe
        output_path (str): Path to save the CSV file
        
    Returns:
        str: Path to the saved CSV file
    """
    try:
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        return output_path
    except Exception as e:
        raise Exception(f"Error saving CSV: {str(e)}")

def get_unique_customers(file_path):
    """
    Extract unique customer names from the input file
    
    Args:
        file_path (str): Path to the Excel file
        
    Returns:
        list: List of unique customer names
    """
    try:
        df = pd.read_excel(file_path)
        if 'Name' not in df.columns:
            raise ValueError("Column 'Name' not found in the file")
            
        # Filter out rows with missing names or total rows
        df = df.dropna(subset=['Name'])
        df = df[df['Name'] != '']
        
        # Only keep rows with status "Delivery" or "Production" or "Open"
        if 'Status' in df.columns:
            df = df[df['Status'].isin(['Delivery', 'Production', 'Open'])]
            
        # Get unique customer names
        unique_customers = df['Name'].unique().tolist()
        return unique_customers
    
    except Exception as e:
        raise Exception(f"Error extracting customer names: {str(e)}")

def validate_file(file_path):
    """
    Validate that the uploaded file is an Excel file with the expected format
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        bool: True if valid, raises Exception if not
    """
    # Check file extension
    if not file_path.lower().endswith(('.xlsx', '.xls')):
        raise ValueError("File must be an Excel file (.xlsx or .xls)")
    
    # Check if file exists and is readable
    if not os.path.isfile(file_path):
        raise ValueError("File does not exist or is not accessible")
    
    # Check if file name matches expected pattern
    file_name = os.path.basename(file_path)
    pattern = r"^Laundry Service - Financial Report - \d{4}-\d{2}-\d{2}.*\.(xlsx|xls)$"
    if not re.match(pattern, file_name):
        raise ValueError("File name does not match expected format 'Laundry Service - Financial Report - yyyy-mm-dd...'")
    
    # Check file content
    try:
        df = pd.read_excel(file_path)
        required_columns = ['Id', 'Name', 'Cleaning Date', 'House', 'Code', 'Status', 'Price']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        return True
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {str(e)}") 