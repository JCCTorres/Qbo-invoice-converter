import os
import requests
import time

def check_app():
    try:
        # Create a status file
        with open("app_status.txt", "w") as f:
            f.write("Checking if app is running...\n")
        
        # Wait for the app to start
        time.sleep(5)
        
        # Try to connect to the app
        try:
            response = requests.get("http://localhost:5000")
            status = f"App is running! Status code: {response.status_code}\nResponse: {response.text[:100]}"
        except Exception as e:
            status = f"Failed to connect to app: {str(e)}"
        
        # Write the status to the file
        with open("app_status.txt", "a") as f:
            f.write(status)
            
        print("Check complete. See app_status.txt for details.")
            
    except Exception as e:
        print(f"Error in check script: {str(e)}")

if __name__ == "__main__":
    check_app() 