import sys
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    logger.debug("Starting test script")
    import app
    logger.debug("Successfully imported app")
    
    logger.debug("Testing app configuration")
    print(f"App secret key: {app.app.secret_key is not None}")
    print(f"Upload folder: {app.app.config['UPLOAD_FOLDER']}")
    print(f"Download folder: {app.app.config['DOWNLOAD_FOLDER']}")
    
    logger.debug("Testing transformer import")
    from transformer import transform_data, save_to_csv, get_unique_customers, validate_file
    logger.debug("Successfully imported transformer functions")
    
    logger.debug("All tests passed")
    
    print("\nStarting app with debug...")
    print("Press Ctrl+C to stop the server")
    
    app.app.run(debug=True, host='0.0.0.0', port=5000)
    
except Exception as e:
    logger.error(f"Error during app startup: {str(e)}")
    traceback.print_exc()
    print(f"Error: {str(e)}")
    sys.exit(1) 