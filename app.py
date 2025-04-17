import os
import json
from datetime import datetime
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import pandas as pd
from werkzeug.utils import secure_filename
from transformer import transform_data, save_to_csv, get_unique_customers, validate_file

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
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload and download directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    # Clear session data when starting fresh
    session.clear()
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
        
        try:
            # Validate the file
            validate_file(file_path)
            logger.debug("File validation passed")
            
            # Extract unique customers
            unique_customers = get_unique_customers(file_path)
            logger.debug(f"Extracted {len(unique_customers)} unique customers")
            
            # Store file path and customers in session
            session['file_path'] = file_path
            session['unique_customers'] = unique_customers
            
            return redirect(url_for('confirm_customers'))
        except Exception as e:
            flash(str(e))
            logger.error(f"Error processing file: {str(e)}")
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
            
        return render_template('invoice_details.html')
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
            
            # Convert DataFrame to JSON for the review page
            transformed_json = transformed_df.to_json(orient='records')
            session['transformed_data'] = transformed_json
            
            return redirect(url_for('review'))
        except Exception as e:
            flash(f'Error processing invoice details: {str(e)}')
            logger.error(f"Error processing invoice details: {str(e)}")
            return redirect(url_for('invoice_details'))

@app.route('/review', methods=['GET', 'POST'])
def review():
    logger.debug("Review endpoint called")
    if request.method == 'GET':
        if 'transformed_data' not in session:
            flash('No transformed data. Please process invoice details first.')
            logger.error("No transformed data in session")
            return redirect(url_for('invoice_details'))
            
        # Convert JSON back to DataFrame
        transformed_df = pd.read_json(session['transformed_data'])
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