# QuickBooks Online Invoice Converter

A web application for converting Laundry Service reports to a format compatible with QuickBooks Online's bulk invoice import.

## Features

- Upload Excel files from your laundry service system
- Verify and edit customer names to match your QuickBooks Online customers
- Generate sequential invoice numbers
- Set invoice dates and automatically calculate due dates
- Review and edit data before generating the final CSV file
- Download a CSV file ready for import into QuickBooks Online

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Local Setup

1. Clone the repository:
   ```
   git clone https://github.com/JCCTorres/Qbo-invoice-converter.git
   cd Qbo-invoice-converter
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows:
     ```
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```
     source venv/bin/activate
     ```

4. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Run the application:
   ```
   python app.py
   ```

6. Open your browser and go to `http://127.0.0.1:5000/`

## Usage

1. **Upload File**: Export your report from your laundry service system as an Excel file (.xlsx) and upload it.

2. **Confirm Customers**: Review the customer names extracted from the file and make any necessary edits to match your QuickBooks Online customers.

3. **Enter Invoice Details**: Provide the starting invoice number (next available number in your QuickBooks Online account) and the invoice date.

4. **Review & Edit**: Review the transformed data and make any necessary edits.

5. **Download CSV**: Generate and download the CSV file ready for import into QuickBooks Online.

## Importing to QuickBooks Online

1. Log in to your QuickBooks Online account.
2. Go to Sales > Invoices.
3. Click on the dropdown next to "New invoice" and select "Import".
4. Follow the QBO instructions to import your CSV file.

## Server Deployment

### Using Gunicorn and Nginx

1. Install Gunicorn:
   ```
   pip install gunicorn
   ```

2. Create a systemd service file (on Linux):
   ```
   sudo nano /etc/systemd/system/qbo-converter.service
   ```

3. Add the following content:
   ```
   [Unit]
   Description=QBO Invoice Converter
   After=network.target

   [Service]
   User=<your-username>
   WorkingDirectory=/path/to/qbo-invoice-converter
   ExecStart=/path/to/qbo-invoice-converter/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

4. Start and enable the service:
   ```
   sudo systemctl start qbo-converter
   sudo systemctl enable qbo-converter
   ```

5. Install and configure Nginx:
   ```
   sudo apt install nginx
   sudo nano /etc/nginx/sites-available/qbo-converter
   ```

6. Add the following Nginx configuration:
   ```
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

7. Enable the site and restart Nginx:
   ```
   sudo ln -s /etc/nginx/sites-available/qbo-converter /etc/nginx/sites-enabled
   sudo systemctl restart nginx
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Flask
- Pandas
- Tabulator.js
- Bootstrap

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.