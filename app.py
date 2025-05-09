import os
import json
from datetime import datetime
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import pandas as pd
from werkzeug.utils import secure_filename
from transformer import transform_data, save_to_csv, get_unique_customers, validate_file
import tempfile
import uuid
import pickle

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['DOWNLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls', 'csv'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SESSION_DATA_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'session_data')

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SESSION_DATA_FOLDER'], exist_ok=True)

# Helper functions for storing large session data in files
def save_session_data(key, data):
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_id = session['session_id']
    session_dir = os.path.join(app.config['SESSION_DATA_FOLDER'], session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    file_path = os.path.join(session_dir, f"{key}.pickle")
    with open(file_path, 'wb') as f:
        pickle.dump(data, f)
    
    return file_path

def load_session_data(key, default=None):
    if 'session_id' not in session:
        return default
    
    session_id = session['session_id']
    file_path = os.path.join(app.config['SESSION_DATA_FOLDER'], session_id, f"{key}.pickle")
    
    if not os.path.exists(file_path):
        return default
    
    try:
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        logger.error(f"Error loading session data for {key}: {str(e)}")
        return default

def clear_session_data():
    if 'session_id' in session:
        session_id = session['session_id']
        session_dir = os.path.join(app.config['SESSION_DATA_FOLDER'], session_id)
        if os.path.exists(session_dir):
            for file in os.listdir(session_dir):
                file_path = os.path.join(session_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    logger.error(f"Error removing file {file_path}: {str(e)}")
            try:
                os.rmdir(session_dir)
            except Exception as e:
                logger.error(f"Error removing directory {session_dir}: {str(e)}")
        session.clear()

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    # Clear session data when starting fresh
    clear_session_data()
    logger.debug("Index page loaded")
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    logger.debug("Upload endpoint called")
    # Check if a file was uploaded
    if 'file' not in request.files:
        flash('No file part')
        logger.error("No file part in request")
        return redirect(request.url)
        
    file = request.files['file']
    
    # Check if the file is empty
    if file.filename == '':
        flash('No selected file')
        logger.error("No selected file")
        return redirect(request.url)
        
    # Check if the file is allowed
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        logger.debug(f"File saved to {file_path}")
        
        # Display success message for the file upload
        flash(f'File "{filename}" uploaded successfully!', 'success')
        
        try:
            # For CSV files with xlsx/xls extension, try to fix the extension
            if file_path.lower().endswith(('.xlsx', '.xls')):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline()
                        if ',' in first_line and first_line.count(',') > 3:
                            logger.debug(f"File appears to be a CSV file with Excel extension. First line: {first_line}")
                            # Rename to CSV
                            csv_path = file_path.rsplit('.', 1)[0] + '.csv'
                            os.rename(file_path, csv_path)
                            file_path = csv_path
                            logger.debug(f"Renamed file to {file_path}")
                            flash(f"Detected CSV file format. Renamed to {os.path.basename(csv_path)}", 'success')
                except Exception as e:
                    logger.debug(f"Error checking for CSV: {str(e)}")
            
            # Validate the file
            validate_file(file_path)
            logger.debug("File validation passed")
            
            # Extract unique customers
            logger.debug(f"Attempting to extract unique customers from {file_path}")
            try:
                df = pd.read_excel(file_path)
                logger.debug(f"Excel file read successfully. Columns: {list(df.columns)}")
                logger.debug(f"First few rows: {df.head().to_dict()}")
            except Exception as e:
                logger.error(f"Error reading Excel file directly: {str(e)}")
                try:
                    # Try reading as CSV if Excel reading failed
                    df = pd.read_csv(file_path)
                    logger.debug(f"CSV file read successfully. Columns: {list(df.columns)}")
                except Exception as e2:
                    logger.error(f"Error reading as CSV: {str(e2)}")
            
            unique_customers = get_unique_customers(file_path)
            
            if not unique_customers:
                logger.warning("No customers found in the file")
                flash("Warning: No customers were found in the file. Please check the file format and try again.", "warning")
                return redirect(url_for('index'))
                
            logger.debug(f"Extracted {len(unique_customers)} unique customers: {unique_customers}")
            
            # Store file path and customers in session
            session['file_path'] = file_path
            session['unique_customers'] = unique_customers
            
            flash(f"Found {len(unique_customers)} customers in the file. Proceed to confirm them.", 'success')
            return redirect(url_for('confirm_customers'))
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error processing file: {error_message}")
            
            # Provide more user-friendly error messages
            if "expected <class 'openpyxl.styles.fills.Fill'>" in error_message:
                flash("The Excel file format is not compatible. Try saving it as CSV and uploading again.")
            elif "No column found for price/amount information" in error_message:
                flash("Could not find price information in the file. Please ensure the file has a column for prices or amounts.")
            else:
                flash(f"Error processing file: {error_message}")
                
            return redirect(url_for('index'))
    else:
        flash('File type not allowed. Please upload an Excel file (.xlsx or .xls)')
        logger.error(f"Invalid file type: {file.filename}")
        return redirect(url_for('index'))

@app.route('/confirm_customers', methods=['GET', 'POST'])
def confirm_customers():
    logger.debug("Confirm customers endpoint called")
    if request.method == 'GET':
        if 'unique_customers' not in session:
            flash('No customers found. Please upload a file first.')
            logger.error("No customers in session")
            return redirect(url_for('index'))
            
        return render_template('confirm_customers.html', customers=session['unique_customers'])
    else:
        # Process form submission
        confirmed_customers = {}
        for i, original_customer in enumerate(session['unique_customers']):
            input_name = f'customer_{i}'
            checkbox_name = f'confirm_{i}'
            
            if input_name in request.form and checkbox_name in request.form:
                confirmed_customers[original_customer] = request.form[input_name]
                
        # Check if any customers are confirmed
        if not confirmed_customers:
            flash('Please confirm at least one customer')
            logger.error("No customers confirmed")
            return redirect(url_for('confirm_customers'))
            
        # Store confirmed customers in session
        session['confirmed_customers'] = confirmed_customers
        logger.debug(f"Confirmed {len(confirmed_customers)} customers")
        
        return redirect(url_for('invoice_details'))

@app.route('/invoice_details', methods=['GET', 'POST'])
def invoice_details():
    logger.debug("Invoice details endpoint called")
    if request.method == 'GET':
        if 'confirmed_customers' not in session:
            flash('No confirmed customers. Please confirm customers first.')
            logger.error("No confirmed customers in session")
            return redirect(url_for('confirm_customers'))
        
        # Pass the current date to the template
        current_date = datetime.now()
        return render_template('invoice_details.html', now=current_date)
    else:
        # Process form submission
        try:
            start_invoice_number = int(request.form['start_invoice_number'])
            invoice_date_str = request.form['invoice_date']
            invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d')
            logger.debug(f"Invoice details: start={start_invoice_number}, date={invoice_date}")
            
            # Store invoice details in session
            session['start_invoice_number'] = start_invoice_number
            session['invoice_date'] = invoice_date_str
            
            # Transform the data
            file_path = session['file_path']
            transformed_df = transform_data(file_path, start_invoice_number, invoice_date)
            logger.debug(f"Data transformed: {transformed_df.shape[0]} rows")
            
            # Replace customer names with confirmed names if any
            if 'confirmed_customers' in session:
                name_mapping = session['confirmed_customers']
                transformed_df['*Customer'] = transformed_df['*Customer'].map(
                    lambda x: name_mapping.get(x, x) if x else ''
                )
            
            # Save transformed data to file instead of session cookie
            save_session_data('transformed_df', transformed_df)
            
            return redirect(url_for('review'))
        except Exception as e:
            flash(f'Error processing invoice details: {str(e)}')
            logger.error(f"Error processing invoice details: {str(e)}")
            return redirect(url_for('invoice_details'))

@app.route('/review', methods=['GET', 'POST'])
def review():
    logger.debug("Review endpoint called")
    if request.method == 'GET':
        # Load transformed data from file
        transformed_df = load_session_data('transformed_df')
        if transformed_df is None:
            flash('No transformed data. Please process invoice details first.')
            logger.error("No transformed data in session files")
            return redirect(url_for('invoice_details'))
            
        logger.debug(f"Review data loaded: {transformed_df.shape[0]} rows")
        
        return render_template('review.html', 
                              data=transformed_df.to_dict('records'),
                              columns=transformed_df.columns.tolist())
    else:
        # Handle any edits from the review page
        try:
            # Get edited data from form
            edited_data = json.loads(request.form['edited_data'])
            logger.debug(f"Received edited data with {len(edited_data)} rows")
            
            # Convert to DataFrame
            edited_df = pd.DataFrame(edited_data)
            
            # Save transformed data to CSV
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            output_filename = f'quickbooks_import_{timestamp}.csv'
            output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], output_filename)
            
            save_to_csv(edited_df, output_path)
            logger.debug(f"CSV saved to {output_path}")
            
            # Store download path in session
            session['download_path'] = output_path
            session['download_filename'] = output_filename
            
            return redirect(url_for('download'))
        except Exception as e:
            flash(f'Error processing review: {str(e)}')
            logger.error(f"Error processing review: {str(e)}")
            return redirect(url_for('review'))

@app.route('/download')
def download():
    logger.debug("Download page endpoint called")
    if 'download_path' not in session or 'download_filename' not in session:
        flash('No file to download. Please complete the process first.')
        logger.error("No download path in session")
        return redirect(url_for('index'))
        
    return render_template('download.html', filename=session['download_filename'])

@app.route('/get_file')
def get_file():
    logger.debug("Get file endpoint called")
    if 'download_path' not in session:
        flash('No file to download. Please complete the process first.')
        logger.error("No download path in session")
        return redirect(url_for('index'))
        
    logger.debug(f"Sending file: {session['download_path']}")
    return send_file(session['download_path'], 
                    mimetype='text/csv',
                    as_attachment=True, 
                    download_name=session['download_filename'])

# Make the app accessible for test scripts
if __name__ == '__main__':
    print("=" * 80)
    print("Starting QBO Invoice Converter application")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Download folder: {app.config['DOWNLOAD_FOLDER']}")
    print("Access the application at: http://localhost:5000")
    print("=" * 80)
    
    logger.info("Starting QBO Invoice Converter application")
    
    try:
        # Write startup indicator to a file
        with open("app_running.txt", "w") as f:
            f.write(f"App started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("Access at: http://localhost:5000\n")
        
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Error starting app: {str(e)}")
        print(f"Error starting app: {str(e)}")
        # Write error to a file
        with open("app_error.txt", "w") as f:
            f.write(f"Error at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Error: {str(e)}\n")