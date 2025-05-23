import os
import sys
import json
import time
import uuid
import datetime
import logging
import pytest
import requests
import azure.functions as func

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from LogzioShipper.__init__ import main

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def get_current_time_iso():
    return datetime.datetime.now().astimezone().isoformat()


def update_log_time(log):
    if isinstance(log, dict):
        if 'time' in log:
            log['time'] = get_current_time_iso()
        for v in log.values():
            if isinstance(v, (dict, list)):
                update_log_time(v)
    elif isinstance(log, list):
        for item in log:
            update_log_time(item)
    return log


def inject_test_run_id(log, run_id):
    if isinstance(log, dict):
        log['test_run_id'] = run_id
        for v in log.values():
            if isinstance(v, (dict, list)):
                inject_test_run_id(v, run_id)
    elif isinstance(log, list):
        for item in log:
            inject_test_run_id(item, run_id)
    return log


class MockEventHubEvent:
    def __init__(self, body):
        self.body = body.encode('utf-8') if isinstance(body, str) else body

    def get_body(self):
        return self.body


def load_sample_logs(run_id, file_path=None):
    events = []
    if not file_path:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_logs.json')

    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                log_data = json.load(f)
            except json.JSONDecodeError:
                f.seek(0)
                lines = [json.loads(line) for line in f if line.strip()]
                log_data = lines

        log_data = update_log_time(log_data)
        log_data = inject_test_run_id(log_data, run_id)

        if isinstance(log_data, list):
            for item in log_data:
                events.append(MockEventHubEvent(json.dumps(item)))
        else:
            events.append(MockEventHubEvent(json.dumps(log_data)))

        logger.info(f"Loaded {len(events)} events from {file_path}")
    else:
        logger.warning(f"{file_path} not found; generating fallback event")
        sample = {
            "time": get_current_time_iso(),
            "resourceId": "/subscriptions/.../resource1",
            "category": "TestLogs",
            "operationName": "TestOp",
            "level": "Info",
            "properties": {"message": "fallback", "test_id": 1},
        }
        sample = inject_test_run_id(sample, run_id)
        events.append(MockEventHubEvent(json.dumps(sample)))

    return events


def fetch_and_assert(run_id, api_key, timeout=120, interval=5):
    url = "https://api.logz.io/v1/search"
    payload = {
        "query": {"query_string": {"query": f"test_run_id:{run_id}"}},
        "from": 0, "size": 1,
        "sort": [{ "@timestamp": {"order": "desc"} }]
    }
    headers = {"Content-Type": "application/json", "X-API-TOKEN": api_key}

    end_time = time.time() + timeout
    while time.time() < end_time:
        r = requests.post(url, json=payload, headers=headers)
        r.raise_for_status()
        hits = r.json().get("hits", {}).get("total", 0)
        if isinstance(hits, dict):
            hits = hits.get("value", 0)
        if hits > 0:
            logger.info(f"✅ Found {hits} log(s) for run_id={run_id}")
            return
        time.sleep(interval)

    pytest.fail(f"No logs found for test_run_id={run_id} after {timeout}s")


def env_setup():
    """
    Automatically set environment variables for all tests.
    """
    env_vars = {
        "AzureWebJobsStorage": os.getenv("AzureWebJobsStorage", "storage"),
        "AZURE_STORAGE_CONTAINER_NAME": os.getenv("AZURE_STORAGE_CONTAINER_NAME", "failedlogbackup"),
        "LogzioURL": os.getenv("LogzioURL", "https://listener.logz.io:8071"),
        "LogzioToken": os.getenv("LogzioToken", "token"),
        "LogzioApiToken": os.getenv("LogzioApiToken", "token"),
        "APPINSIGHTS_INSTRUMENTATIONKEY": os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY", "key"),
        "MAX_TRIES": os.getenv("MAX_TRIES", "3"),
        "LOG_TYPE": os.getenv("LOG_TYPE", "eventHub"),
        "FUNCTION_VERSION": os.getenv("FUNCTION_VERSION", "1.0.0"),
        "THREAD_COUNT": os.getenv("THREAD_COUNT", "4"),
        "BUFFER_SIZE": os.getenv("BUFFER_SIZE", "10"),
        "INTERVAL_TIME": os.getenv("INTERVAL_TIME", "5000"),
    }
    for key, value in env_vars.items():
        os.environ[key] = value

@pytest.fixture
def run_id():
    """
    Generate a unique test run ID.
    """
    return uuid.uuid4().hex

@pytest.fixture
def func_events(run_id):
    """
    Prepare a list of Azure Function EventHubEvent objects with sample logs.
    """
    events = load_sample_logs(run_id)
    assert events, "No events loaded"
    return [func.EventHubEvent(body=e.get_body()) for e in events]

# --- Test Cases ---

def test_logzio_shipper_end_to_end(run_id, func_events):
    """
    End-to-end test: send sample events to the Azure Function and verify logs in Logz.io.
    """
    env_setup()

    main(func_events)

    fetch_and_assert(run_id, os.environ["LogzioApiToken"], timeout=120, interval=5)
