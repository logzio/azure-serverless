#!/usr/bin/env python3
# test_logzio_shipper.py - Simple test file for running the Logzio Shipper with custom input

import os
import sys
import json
import time
import logging
import argparse
import datetime
from dotenv import load_dotenv

# Configure logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger()

def setup_environment():
    """Set up necessary environment variables for testing the LogzioShipper"""
    # Load environment variables from .env file if exists
    load_dotenv()
    
    # Required environment variables with default test values
    env_vars = {        
        "AzureWebJobsStorage": os.getenv("AzureWebJobsStorage", "storage"),
        "AZURE_STORAGE_CONTAINER_NAME": os.getenv("AZURE_STORAGE_CONTAINER_NAME", "failedlogbackup"),
        "LogzioURL": os.getenv("LogzioURL", "https://listener.logz.io:8071"),
        "LogzioToken": os.getenv("LogzioToken", "token"),
        "APPINSIGHTS_INSTRUMENTATIONKEY": os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY", "key"),
        "MAX_TRIES": os.getenv("MAX_TRIES", "3"),
        "LOG_TYPE": os.getenv("LOG_TYPE", "eventHub"),
        "FUNCTION_VERSION": os.getenv("FUNCTION_VERSION", "1.0.0"),
        "THREAD_COUNT": os.getenv("THREAD_COUNT", "4"),
        "BUFFER_SIZE": os.getenv("BUFFER_SIZE", "10"),
        "INTERVAL_TIME": os.getenv("INTERVAL_TIME", "5000")  # milliseconds
    }
    
    for key, value in env_vars.items():
      os.environ[key] = value
    
    logger.info("Environment variables set successfully")

setup_environment()

# Now we can import Azure Functions and our module
import azure.functions as func
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from LogzioShipper.__init__ import main, batch_queue


class MockEventHubEvent:
    """Mock class for EventHubEvent to simulate Azure Functions event input"""
    
    def __init__(self, body):
        self.body = body.encode('utf-8') if isinstance(body, str) else body
        
    def get_body(self):
        return self.body


def get_current_time_iso():
    """Get current time in ISO8601 format with timezone for consistency with Azure logs"""
    return datetime.datetime.now().astimezone().isoformat()


def update_log_time(log):
    """Update the time field in a log to current time"""
    if isinstance(log, dict):
        # Update the time field with current time
        if 'time' in log:
            log['time'] = get_current_time_iso()
        
        # Process nested records if they exist
        if 'records' in log and isinstance(log['records'], list):
            for record in log['records']:
                update_log_time(record)
                
        # Process other nested dictionaries
        for key, value in log.items():
            if isinstance(value, (dict, list)):
                update_log_time(value)
    elif isinstance(log, list):
        for item in log:
            update_log_time(item)
    
    return log


def load_sample_logs(file_path=None):
    """
    Load sample logs from a JSON file and update their timestamps to current time
    
    Args:
        file_path: Optional path to a JSON file with sample logs
        
    Returns:
        List of MockEventHubEvent objects
    """
    events = []
    
    # Use provided file path or default to the one in the same directory
    if not file_path:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_logs.json')
    
    if os.path.exists(file_path):
        # Load logs from file
        with open(file_path, 'r') as f:
            try:
                log_data = json.load(f)
                
                # Update timestamps to current time
                log_data = update_log_time(log_data)
                
                if isinstance(log_data, list):
                    # If file contains a list of logs, create one event per item
                    for item in log_data:
                        events.append(MockEventHubEvent(json.dumps(item)))
                else:
                    # If file contains a single log object
                    events.append(MockEventHubEvent(json.dumps(log_data)))
                logger.info(f"Loaded {len(events)} events from {file_path}")
            except json.JSONDecodeError:
                # File might contain one JSON object per line
                f.seek(0)  # Reset file pointer
                log_lines = []
                for line in f:
                    try:
                        log_obj = json.loads(line.strip())
                        # Update timestamp
                        log_obj = update_log_time(log_obj)
                        log_lines.append(json.dumps(log_obj))
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in line: {line}")
                if log_lines:
                    events.append(MockEventHubEvent('\n'.join(log_lines)))
                    logger.info(f"Loaded {len(log_lines)} log lines as a single event")
    else:
        logger.warning(f"Sample logs file {file_path} not found")
        # Generate one sample event if file not found
        sample_log = {
            "time": get_current_time_iso(),
            "resourceId": "/subscriptions/sub123/resourceGroups/test-rg/providers/Microsoft.Test/resource1",
            "category": "TestLogs",
            "operationName": "TestOperation1",
            "level": "Information",
            "properties": {
                "message": "This is a test message",
                "test_id": 1
            },
            "function_version": "test"
        }
        events.append(MockEventHubEvent(json.dumps(sample_log)))
        logger.info("Generated a sample event as fallback")
    
    return events



def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Test the LogzioShipper with sample logs')
    parser.add_argument('--file', type=str, help='Path to a JSON file with sample logs')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    return parser.parse_args()


def main_test():
    """Main test function"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set log level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load sample logs
    events = load_sample_logs(args.file)
    
    if not events:
        logger.error("No events to process. Exiting.")
        sys.exit(1)
    
    try:
        logger.info(f"Processing {len(events)} events...")
        
        func_events = [func.EventHubEvent(body=event.get_body()) for event in events]

        print(os.environ["LogzioToken"])
        
        main(func_events)

        time.sleep(60000)
        
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Error in test execution: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main_test()