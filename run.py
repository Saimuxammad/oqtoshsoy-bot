import os
import subprocess
import signal
import sys


def run_ngrok():
    """Run ngrok in a separate process"""
    try:
        ngrok_process = subprocess.Popen(['ngrok', 'http', '8000'],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        print("Started ngrok process")
        return ngrok_process
    except Exception as e:
        print(f"Error starting ngrok: {e}")
        return None


def run_app():
    """Run the FastAPI application"""
    try:
        app_process = subprocess.Popen(['python', 'main.py'],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
        print("Started application process")
        return app_process
    except Exception as e:
        print(f"Error starting application: {e}")
        return None


def main():
    """Main function to run the development environment"""
    print("Starting development environment...")

    # Start ngrok
    ngrok_process = run_ngrok()

    # Start the application
    app_process = run_app()

    # Wait for keyboard interrupt
    try:
        print("Development environment running. Press Ctrl+C to stop.")
        while True:
            pass
    except KeyboardInterrupt:
        print("\nStopping development environment...")

        # Stop processes
        if ngrok_process:
            ngrok_process.terminate()
        if app_process:
            app_process.terminate()

        print("Development environment stopped.")


if __name__ == "__main__":
    main()