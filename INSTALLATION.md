# QBO Invoice Converter - Installation Guide

This guide will help you set up and run the QBO Invoice Converter application on your local computer.

## Prerequisites

- Python 3.8 or higher (Download from [python.org](https://www.python.org/downloads/))
- Basic familiarity with command line operations

## Installation Steps

1. **Extract the application:**
   - If you received a ZIP file, extract it to a location on your computer (e.g., your Desktop or Documents folder)

2. **Install Python:**
   - If you don't already have Python installed, download and install it from [python.org](https://www.python.org/downloads/)
   - During installation, make sure to check the option "Add Python to PATH"

3. **Open a command prompt:**
   - Press `Win + R`, type `cmd` and press Enter
   - Navigate to the application folder:
     ```
     cd C:\path\to\qbo-invoice-converter
     ```
     (Replace `C:\path\to\qbo-invoice-converter` with the actual path where you extracted the files)

4. **Install the required packages:**
   - Run the following command:
     ```
     pip install -r requirements.txt
     ```
   - This will install all the necessary Python libraries

## Running the Application

### Option 1: Using the Batch File (Recommended)

1. Simply double-click the `run_app.bat` file in the application folder
2. A command window will open showing application logs
3. Open your web browser and go to: http://localhost:5000
4. To stop the application, return to the command window and press `Ctrl+C`, then type `Y` to confirm

### Option 2: Using the Command Line

1. Open a command prompt and navigate to the application folder:
   ```
   cd C:\path\to\qbo-invoice-converter
   ```
2. Run the application:
   ```
   python app.py
   ```
3. Open your web browser and go to: http://localhost:5000
4. To stop the application, return to the command window and press `Ctrl+C`

## Troubleshooting

- **Missing packages error:** If you see errors about missing packages, try running the pip install command again:
  ```
  pip install -r requirements.txt
  ```

- **Port already in use:** If port 5000 is already in use, you can modify the `app.py` file and change the port number at the end of the file.

- **File permission errors:** Make sure you have write access to the application folder.

## Using the Application

Once the application is running:

1. Upload your Laundry Service report file
2. Confirm customer names
3. Enter invoice details
4. Review the transformed data
5. Download the CSV file ready for import into QuickBooks Online

## Support

If you encounter any issues, please contact your system administrator or the application developer. 