import os
import azure.functions as func
import logging
import json
import requests
from requests import Session
from .backup_container import BackupContainer
from azure.storage.blob import ContainerClient
from threading import Thread
from queue import Queue, Empty
import backoff
from typing import List
import time
from applicationinsights import TelemetryClient



# Logz.io configuration
ENV_LOGZIO_URL = os.getenv("LogzioURL")
ENV_LOGZIO_TOKEN = os.getenv("LogzioToken")
AZURE_WEB_JOBS_STORAGE = os.getenv("AzureWebJobsStorage")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
APPINSIGHTS_INSTRUMENTATIONKEY = os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY")
HEADERS = {"Content-Type": "application/json"}
RETRY_WAIT_FIXED = 2  
ENV_MAX_TRIES = int(os.getenv('MAX_TRIES', 3))
ENV_LOG_TYPE = os.getenv('LOG_TYPE', "eventHub")
ENV_FUNCTION_VERSION = os.getenv('FUNCTION_VERSION', '1.0.0')

ENV_THREAD_COUNT = int(os.getenv('THREAD_COUNT', 4))


ENV_BUFFER_SIZE = int(os.getenv('BUFFER_SIZE', 100))  # Batch size
ENV_INTERVAL_TIME = int(os.getenv('INTERVAL_TIME', 10000)) / 1000  # Interval time in seconds

appinsights_key = os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY")
tc = TelemetryClient(appinsights_key) if appinsights_key else None
batch_queue = Queue()
container_client = ContainerClient.from_connection_string(
      conn_str=AZURE_WEB_JOBS_STORAGE,
      container_name=AZURE_STORAGE_CONTAINER_NAME
  )
backup_container = BackupContainer(logging, container_client)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
session = Session()
    
def add_timestamp(log):
    if 'time' in log:
        log['@timestamp'] = log['time']
    return log


def delete_empty_fields_of_log(log):
    if isinstance(log, dict):
        return {k: v for k, v in log.items() if v is not None and v != ""}
    elif isinstance(log, list):
        return [delete_empty_fields_of_log(item) for item in log]
    else:
        return log


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=ENV_MAX_TRIES)
def send_batch(batch_data):
    try:
        batch_str = ''.join(batch_data)
        response = session.post(ENV_LOGZIO_URL, params={"token": ENV_LOGZIO_TOKEN, "type": ENV_LOG_TYPE}, headers=HEADERS, data=batch_str)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send batch: {e}")
        backup_container.write_event_to_blob(batch_data, e)
        if tc:
          tc.track_metric('FailedLogSendCount', len(batch_data))
          tc.flush()
        raise e


def batch_creator(azeventhub):
    local_log_batch = []
    last_batch_time = time.time()
    for event in azeventhub:
        logs = process_eventhub_message(event)
        for log in logs:
            formatted_log = json.dumps(log) + '\n'
            local_log_batch.append(formatted_log)

        # Check the batch size or time interval after processing all logs from the event
        current_time = time.time()
        if len(local_log_batch) >= ENV_BUFFER_SIZE or (current_time - last_batch_time) >= ENV_INTERVAL_TIME:
            logging.info(f"Adding batch of size {len(local_log_batch)} to the sending queue.")
            batch_queue.put(list(local_log_batch))  # Put a copy of the batch
            local_log_batch.clear()  # Clear the local batch
            last_batch_time = current_time

    # Check and send any remaining logs in the batch after processing all events
    if local_log_batch:
        logging.info(f"Adding batch of size {len(local_log_batch)} to the sending queue.")
        batch_queue.put(list(local_log_batch))  # Put a copy of the batch
        local_log_batch.clear()  # Clear the local batch


def batch_sender():
    while True:
        try:
            batch = batch_queue.get(timeout=0.1)
            if batch:
                try:
                    send_batch(batch)
                    logging.info("Batch successfully sent to Logz.io.")
                except Exception as e:
                    logging.warning(f"Batch failed to send: {e}")
                    backup_container.upload_files()  # Upload files after a failed send
                batch_queue.task_done()
        except Empty:
            continue


def start_batch_senders(thread_count=4):
    for _ in range(thread_count):
        Thread(target=batch_sender, daemon=True).start()


def process_eventhub_message(event):
    try:
        message_body = event.get_body().decode('utf-8')
        logs = []
        for line in message_body.splitlines():
            log_entry = json.loads(line)
            
            log_entry['function_version'] = ENV_FUNCTION_VERSION

            log_entry = add_timestamp(log_entry)
            log_entry = delete_empty_fields_of_log(log_entry)

            # Check if this log entry contains nested logs under 'records'
            if 'records' in log_entry and isinstance(log_entry['records'], list):
                for record in log_entry['records']:
                    record['function_version'] = ENV_FUNCTION_VERSION
                    record = add_timestamp(record)
                    record = delete_empty_fields_of_log(record)
                logs.extend(log_entry['records'])  
            else:
                logs.append(log_entry)
        return logs
    except Exception as e:
        logging.error(f"Error processing EventHub message: {e}")
        return []


def main(events: List[func.EventHubEvent]):
    batch_creator_thread = Thread(target=batch_creator, args=(events,), daemon=True)
    batch_creator_thread.start()
    start_batch_senders(thread_count=ENV_THREAD_COUNT)
    batch_creator_thread.join()
    backup_container.upload_files()  # Ensure any remaining files are uploaded
    logging.info('EventHub trigger processing complete.')
