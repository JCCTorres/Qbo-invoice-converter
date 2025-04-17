import pandas as pd
from datetime import datetime, timedelta
import os
import re

def transform_data(file_path, start_invoice_number, invoice_date):
    """
    Transform the laundry service report to QuickBooks Online format
    
    Args:
        file_path (str): Path to the Excel or CSV file
        start_invoice_number (int): Starting invoice number
        invoice_date (datetime): Date for the invoice
        
    Returns:
        pd.DataFrame: Transformed dataframe ready for QBO import
    """
    try:
        # Determine file type based on extension
        file_extension = file_path.lower().split('.')[-1] if '.' in file_path else ''
        
        # Read the file based on its extension
        if file_extension == 'csv':
            print("Reading CSV file for transformation...")
            df = pd.read_csv(file_path)
        else:
            # Try multiple Excel reading engines if it's an Excel file
            try:
                print("Attempting to read Excel file with default engine for transformation...")
                df = pd.read_excel(file_path)
            except Exception as e1:
                print(f"Error with default engine: {str(e1)}")
                try:
                    print("Trying with engine='openpyxl'...")
                    df = pd.read_excel(file_path, engine='openpyxl')
                except Exception as e2:
                    print(f"Error with openpyxl engine: {str(e2)}")
                    try:
                        print("Trying with engine='xlrd'...")
                        df = pd.read_excel(file_path, engine='xlrd')
                    except Exception as e3:
                        print(f"Error with xlrd engine: {str(e3)}")
                        # If Excel reading fails completely, try CSV as last resort
                        try:
                            print("Trying to read as CSV...")
                            df = pd.read_csv(file_path)
                        except Exception as e4:
                            print(f"Error reading as CSV: {str(e4)}")
                            raise ValueError(f"Could not read file with any available method. Last error: {str(e3)}")
        
        print(f"File contents loaded. Columns: {df.columns.tolist()}")
        print(f"First few rows: {df.head(2).to_dict()}")
        
        # Add fallback columns if the CSV doesn't have all required columns
        # These are the minimum required columns for QuickBooks Online import
        required_qbo_columns = [
            '*InvoiceNo', '*Customer', '*InvoiceDate', '*DueDate',
            'Item(Product/Service)', 'ItemDescription', 'ItemQuantity', '*ItemAmount'
        ]
        
        # Create a new DataFrame with the required structure
        qbo_df = pd.DataFrame(columns=required_qbo_columns)
        
        # Try to identify needed columns from the input file
        name_col = None
        price_col = None
        date_col = None
        id_col = None
        house_col = None
        note_col = None
        
        # Look for customer name column
        for possible_name in ['Name', 'Customer', 'Client', 'Account']:
            if possible_name in df.columns:
                name_col = possible_name
                break
                
        if not name_col:
            # Try case-insensitive search
            for col in df.columns:
                if 'name' in col.lower() or 'customer' in col.lower():
                    name_col = col
                    break
                    
        if not name_col and len(df.columns) > 1:
            # If still not found, use second column as fallback
            name_col = df.columns[1]
        
        # Look for price/amount column
        for possible_price in ['Price', 'Amount', 'Total', 'Value', 'Cost']:
            if possible_price in df.columns:
                price_col = possible_price
                break
                
        if not price_col:
            # Try case-insensitive search
            for col in df.columns:
                if 'price' in col.lower() or 'amount' in col.lower() or 'total' in col.lower() or 'value' in col.lower():
                    price_col = col
                    break
        
        # Look for date column
        for possible_date in ['Date', 'Service Date', 'Cleaning Date', 'Invoice Date']:
            if possible_date in df.columns:
                date_col = possible_date
                break
                
        if not date_col:
            # Try case-insensitive search
            for col in df.columns:
                if 'date' in col.lower():
                    date_col = col
                    break
        
        # Look for ID column
        for possible_id in ['ID', 'Id', 'Order', 'Order ID', 'Invoice', 'Ref']:
            if possible_id in df.columns:
                id_col = possible_id
                break
                
        if not id_col:
            # Try case-insensitive search
            for col in df.columns:
                if 'id' in col.lower() or 'order' in col.lower() or 'ref' in col.lower():
                    id_col = col
                    break
                    
        if not id_col and len(df.columns) > 0:
            # If still not found, use first column as fallback
            id_col = df.columns[0]
            
        # Look for House/Address column
        for possible_house in ['House', 'Address', 'Location', 'Property', 'Apartment']:
            if possible_house in df.columns:
                house_col = possible_house
                break
                
        if not house_col:
            # Try case-insensitive search
            for col in df.columns:
                if 'house' in col.lower() or 'address' in col.lower() or 'location' in col.lower() or 'property' in col.lower():
                    house_col = col
                    break
        
        # Look for Note column
        for possible_note in ['Note', 'Notes', 'Comment', 'Comments', 'Description']:
            if possible_note in df.columns:
                note_col = possible_note
                break
                
        if not note_col:
            # Try case-insensitive search
            for col in df.columns:
                if 'note' in col.lower() or 'comment' in col.lower() or 'description' in col.lower():
                    note_col = col
                    break
        
        # Make sure we have the minimally required columns
        if not name_col:
            raise ValueError("Could not find customer name column in the file")
        if not price_col:
            raise ValueError("Could not find price/amount column in the file")
        
        print(f"Using {name_col} as customer name column")
        print(f"Using {price_col} as price column")
        if date_col:
            print(f"Using {date_col} as date column")
        if id_col:
            print(f"Using {id_col} as ID column")
        if house_col:
            print(f"Using {house_col} as house/address column")
        if note_col:
            print(f"Using {note_col} as note column")
        
        # Create a basic transformation - copy needed columns to the QBO format
        # Filter for valid rows - non-empty customer names
        df = df.dropna(subset=[name_col])
        df = df[df[name_col] != '']
        
        # Get unique customers
        unique_customers = df[name_col].drop_duplicates().tolist()
        
        # Create invoice numbers sequence
        invoice_mapping = {}
        current_invoice = start_invoice_number
        
        for customer in unique_customers:
            invoice_mapping[customer] = current_invoice
            current_invoice += 1
        
        # Build the QBO dataframe row by row
        rows = []
        
        for _, row in df.iterrows():
            customer = row[name_col]
            # Check if price can be converted to float
            try:
                price = float(row[price_col])
            except:
                # Try to extract numeric part
                price_str = str(row[price_col])
                price_str = ''.join(c for c in price_str if c.isdigit() or c == '.' or c == ',')
                price_str = price_str.replace(',', '.')
                try:
                    price = float(price_str)
                except:
                    price = 0
            
            # Create a description with the requested format
            description = ""
            
            # Add house/address if available
            if house_col and house_col in row and pd.notna(row[house_col]) and row[house_col] != '':
                description = f"{row[house_col]}, "
            
            # Add order ID
            if id_col and id_col in row and pd.notna(row[id_col]) and row[id_col] != '':
                order_id = row[id_col]
            else:
                order_id = invoice_mapping[customer]  # Use invoice number as fallback
                
            description += f"/ order id: {order_id}"
            
            # Add note if available
            if note_col and note_col in row and pd.notna(row[note_col]) and row[note_col] != '':
                description += f" / Notes: {row[note_col]}"
            
            # Add date if available
            if date_col and date_col in row and pd.notna(row[date_col]):
                try:
                    service_date = pd.to_datetime(row[date_col]).strftime('%d/%m/%Y')
                except:
                    service_date = invoice_date.strftime('%d/%m/%Y')
            else:
                service_date = invoice_date.strftime('%d/%m/%Y')
            
            # Create a QBO row
            qbo_row = {
                '*InvoiceNo': invoice_mapping[customer],
                '*Customer': customer,
                '*InvoiceDate': invoice_date.strftime('%d/%m/%Y'),
                '*DueDate': (invoice_date + timedelta(days=4)).strftime('%d/%m/%Y'),
                'Item(Product/Service)': 'Linhas de Lavanderia:Services',
                'ItemDescription': description,
                'ItemQuantity': 1,
                '*ItemAmount': price,
                'Service Date': service_date
            }
            
            rows.append(qbo_row)
        
        # Convert list of rows to DataFrame
        if not rows:
            raise ValueError("No valid invoice data found in the file after processing")
            
        qbo_df = pd.DataFrame(rows)
        
        # Set blank customer names for all but first occurrence of each invoice
        for inv_num in qbo_df['*InvoiceNo'].unique():
            mask = qbo_df['*InvoiceNo'] == inv_num
            indices = qbo_df[mask].index
            if len(indices) > 1:  # If there are multiple rows for this invoice
                qbo_df.loc[indices[1:], '*Customer'] = ''  # Clear customer name for all but first row
                qbo_df.loc[indices[1:], '*InvoiceDate'] = ''  # Clear invoice date for all but first row
                qbo_df.loc[indices[1:], '*DueDate'] = ''  # Clear due date for all but first row
                
        print(f"Created {len(qbo_df)} invoice rows for QuickBooks Online import")
        
        return qbo_df
    
    except Exception as e:
        print(f"Error in transform_data: {str(e)}")
        import traceback
        traceback.print_exc()
        raise ValueError(f"Error transforming data: {str(e)}")

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
        file_path (str): Path to the Excel or CSV file
        
    Returns:
        list: List of unique customer names
    """
    try:
        # Determine file type based on extension
        file_extension = file_path.lower().split('.')[-1] if '.' in file_path else ''
        
        # Read the file based on its extension
        if file_extension == 'csv':
            print("Reading CSV file for customer extraction...")
            df = pd.read_csv(file_path)
        else:
            # Try multiple Excel reading engines if it's an Excel file
            try:
                print("Attempting to read Excel file with default engine for customer extraction...")
                df = pd.read_excel(file_path)
            except Exception as e1:
                print(f"Error with default engine: {str(e1)}")
                try:
                    print("Trying with engine='openpyxl'...")
                    df = pd.read_excel(file_path, engine='openpyxl')
                except Exception as e2:
                    print(f"Error with openpyxl engine: {str(e2)}")
                    try:
                        print("Trying with engine='xlrd'...")
                        df = pd.read_excel(file_path, engine='xlrd')
                    except Exception as e3:
                        print(f"Error with xlrd engine: {str(e3)}")
                        # If Excel reading fails completely, try CSV as last resort
                        try:
                            print("Trying to read as CSV...")
                            df = pd.read_csv(file_path)
                        except Exception as e4:
                            print(f"Error reading as CSV: {str(e4)}")
                            print(f"Could not read file with any available method. Returning empty customer list.")
                            return []
        
        # Log the column names to help with debugging
        print(f"Columns in file: {df.columns.tolist()}")
        
        # Check if 'Name' column exists - try case-insensitive match if not
        if 'Name' not in df.columns:
            # Try to find a column that might contain customer names
            name_cols = [col for col in df.columns if 'name' in col.lower()]
            if name_cols:
                name_col = name_cols[0]
                print(f"Using '{name_col}' as the customer name column")
            else:
                # If can't find a name column, check if the first column might contain names
                if len(df.columns) > 0:
                    if len(df.columns) > 1:
                        name_col = df.columns[1]  # Often the second column is for names
                    else:
                        name_col = df.columns[0]  # Use first column as fallback
                    print(f"Using column '{name_col}' as a fallback for customer names")
                else:
                    raise ValueError("Could not identify a suitable customer name column")
        else:
            name_col = 'Name'
        
        # Filter out rows with missing names or total rows
        df = df.dropna(subset=[name_col])
        df = df[df[name_col] != '']
        
        # Filter rows by Status if the column exists
        if 'Status' in df.columns:
            valid_statuses = ['Delivery', 'Production', 'Open']
            df = df[df['Status'].isin(valid_statuses)]
            print(f"Filtered to {len(df)} rows with status in {valid_statuses}")
        else:
            print("No 'Status' column found, not filtering by status")
        
        # Get unique customer names
        unique_customers = df[name_col].unique().tolist()
        print(f"Found {len(unique_customers)} unique customers")
        
        return unique_customers
    
    except Exception as e:
        print(f"Error in get_unique_customers: {str(e)}")
        # Return an empty list as a fallback to allow the app to continue
        return []

def validate_file(file_path):
    """
    Validate that the uploaded file is an Excel file or CSV with the expected format
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        bool: True if valid, raises Exception if not
    """
    # Check file extension
    file_extension = file_path.lower().split('.')[-1] if '.' in file_path else ''
    if file_extension not in ['xlsx', 'xls', 'csv']:
        raise ValueError("File must be an Excel file (.xlsx or .xls) or CSV file (.csv)")
    
    # Check if file exists and is readable
    if not os.path.isfile(file_path):
        raise ValueError("File does not exist or is not accessible")
    
    # Try to read the file
    try:
        if file_extension == 'csv':
            print("Reading CSV file...")
            df = pd.read_csv(file_path)
        else:
            # Try multiple Excel reading engines if it's an Excel file
            try:
                print("Attempting to read Excel file with default engine...")
                df = pd.read_excel(file_path)
            except Exception as e1:
                print(f"Error with default engine: {str(e1)}")
                try:
                    print("Trying with engine='openpyxl'...")
                    df = pd.read_excel(file_path, engine='openpyxl')
                except Exception as e2:
                    print(f"Error with openpyxl engine: {str(e2)}")
                    try:
                        print("Trying with engine='xlrd'...")
                        df = pd.read_excel(file_path, engine='xlrd')
                    except Exception as e3:
                        print(f"Error with xlrd engine: {str(e3)}")
                        # If CSV with xlsx extension, try reading as CSV
                        try:
                            print("Trying to read as CSV...")
                            df = pd.read_csv(file_path)
                        except Exception as e4:
                            print(f"Error reading as CSV: {str(e4)}")
                            raise ValueError(f"Could not read file with any available method. Last error: {str(e3)}")
        
        print(f"File loaded successfully with {len(df)} rows and columns: {df.columns.tolist()}")
        
        # Check for minimum required columns for functionality
        required_columns = ['Name', 'Price']
        
        # Look for variations of required column names
        name_columns = [col for col in df.columns if 'name' in col.lower()]
        price_columns = [col for col in df.columns if any(x in col.lower() for x in ['price', 'amount', 'value', 'cost'])]
        
        if not name_columns:
            print("Warning: No 'Name' column found. Looking for a suitable column to use as customer name.")
            # We'll handle this in get_unique_customers
        
        if not price_columns:
            raise ValueError("No column found for price/amount information. This is required for invoicing.")
            
        return True
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}")