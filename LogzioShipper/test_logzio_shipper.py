#!/usr/bin/env python3
# test_logzio_shipper.py - Simple test file for running the Logzio Shipper with custom input

import os
import sys
import json
import time
import logging
import azure.functions as func
from dotenv import load_dotenv

# Direct import from local __init__.py file rather than as a module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from LogzioShipper.__init__ import main, batch_queue, get_message, process_error_messages

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger()

# Load environment variables from .env file if exists
load_dotenv()


class MockEventHubEvent:
    """Mock class for EventHubEvent to simulate Azure Functions event input"""
    
    def __init__(self, body):
        self.body = body.encode('utf-8') if isinstance(body, str) else body
        
    def get_body(self):
        return self.body


def setup_environment():
    """Set up necessary environment variables if not already set"""
    
    # Required environment variables with default test values
    env_vars = {
        "AzureWebJobsStorage": os.getenv("AzureWebJobsStorage", "DefaultEndpointsProtocol=https;AccountName=teststorage;AccountKey=dummykey==;EndpointSuffix=core.windows.net"),
        "AZURE_STORAGE_CONTAINER_NAME": os.getenv("AZURE_STORAGE_CONTAINER_NAME", "logs-backup"),
        "LogzioURL": os.getenv("LogzioURL", "https://listener.logz.io:8071"),
        "LogzioToken": os.getenv("LogzioToken", "your-token-goes-here"),
        "APPINSIGHTS_INSTRUMENTATIONKEY": os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY", "dummy-key"),
        "MAX_TRIES": os.getenv("MAX_TRIES", "3"),
        "LOG_TYPE": os.getenv("LOG_TYPE", "eventHub"),
        "FUNCTION_VERSION": os.getenv("FUNCTION_VERSION", "1.0.0"),
        "THREAD_COUNT": os.getenv("THREAD_COUNT", "4"),
        "BUFFER_SIZE": os.getenv("BUFFER_SIZE", "10"),
        "INTERVAL_TIME": os.getenv("INTERVAL_TIME", "5000")  # milliseconds
    }
    
    # Set environment variables if not already set
    for key, value in env_vars.items():
        os.environ[key] = value
    
    logger.info("Environment variables set successfully")


def load_sample_logs():
    """
    Load sample logs from the static sample_logs.json file
    
    Returns:
        List of MockEventHubEvent objects
    """
    events = []
    # Use static file path
    sample_logs_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_logs.json')
    
    if os.path.exists(sample_logs_file):
        # Load logs from file
        with open(sample_logs_file, 'r') as f:
            try:
                log_data = json.load(f)
                if isinstance(log_data, list):
                    # If file contains a list of logs, create one event per item
                    for item in log_data:
                        events.append(MockEventHubEvent(json.dumps(item)))
                else:
                    # If file contains a single log object
                    events.append(MockEventHubEvent(json.dumps(log_data)))
                logger.info(f"Loaded {len(events)} events from {sample_logs_file}")
            except json.JSONDecodeError:
                # File might contain one JSON object per line
                f.seek(0)  # Reset file pointer
                log_lines = []
                for line in f:
                    try:
                        log_lines.append(line.strip())
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in line: {line}")
                if log_lines:
                    events.append(MockEventHubEvent('\n'.join(log_lines)))
                    logger.info(f"Loaded {len(log_lines)} log lines as a single event")
    else:
        logger.warning(f"Sample logs file {sample_logs_file} not found")
        # Generate one sample event if file not found
        sample_log = {
            "time": "2025-05-08T10:00:00.000Z",
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


def wait_for_processing(timeout=10):
    """Wait for the batch queue to be empty or until timeout"""
    start_time = time.time()
    while not batch_queue.empty():
        if time.time() - start_time > timeout:
            logger.warning(f"Timeout after {timeout} seconds, queue still contains items")
            break
        logger.info(f"Waiting for queue to be processed. Current size: {batch_queue.qsize()}")
        time.sleep(1)


if __name__ == "__main__":
    # Set up environment
    setup_environment()
    
    # Load sample logs from static file
    events = load_sample_logs()
    
    if not events:
        logger.error("No events to process. Exiting.")
        sys.exit(1)
    
    try:
        logger.info(f"Processing {len(events)} events...")
        
        # Create a list of proper EventHubEvent objects
        func_events = [func.EventHubEvent(body=event.get_body()) for event in events]
        
        # Run the main function with our test events
        main(func_events)
        
        # Wait for processing to complete
        wait_for_processing(10)
        
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Error in test execution: {e}", exc_info=True)
        sys.exit(1)