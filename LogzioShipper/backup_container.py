import os
import json
import tempfile
from datetime import datetime
from azure.core.exceptions import ResourceExistsError


class BackupContainer:
    def __init__(self, internal_logger, container_client):
        # Constructor: Initializes the backup container with logging and Azure container client.
        self._context = internal_logger
        self._container_client = container_client
        self.current_folder = None
        self.current_file = None
        self._files_to_upload = []
        self._folder_size = 0
        self._logs_in_bulk = 1
        self._create_new_folder()
        self._create_new_file()

    def _update_folder_size(self):
        # Updates the size of the current folder based on the size of the current file.
        file_path = os.path.join(self.current_folder, self.current_file)
        if os.path.exists(file_path):
            self._folder_size += os.path.getsize(file_path) / 1000  # Size in KB

    @staticmethod
    def _get_date():
        # Static method to get the current date in UTC.
        return datetime.utcnow().strftime("%Y-%m-%d")

    @staticmethod
    def _uniq_string(length=32):
        # Static method to generate a unique string for file naming.
        return os.urandom(length).hex()

    def _create_new_folder(self):
        # Creates a new folder for storing log files. Each folder represents a batch of logs.
        new_folder_name = os.path.join(tempfile.gettempdir(), self._get_date() + "-" + self._uniq_string())
        os.makedirs(new_folder_name, exist_ok=True)
        self._folder_size = 0
        self.current_folder = new_folder_name

    def _create_new_file(self):
        # Creates a new file within the current folder for storing logs.
        unique_suffix = datetime.utcnow().strftime("%Y%m%d%H%M%S%f") + "-" + self._uniq_string()
        self.current_file = f"logs-{unique_suffix}.txt"
        self._logs_in_bulk = 1
        # Include full path for the current file
        self.current_file_full_path = os.path.join(self.current_folder, self.current_file)

    def update_folder_if_max_size_surpassed(self, folder_max_size_in_mb=10000):
        # Checks if the current folder has reached its maximum size. If so, creates a new folder.
        if self._folder_size >= folder_max_size_in_mb:
            self._create_new_folder()

    def update_file_if_bulk_size_surpassed(self, max_shipper_bulk_size=100):
        # Checks if the current file has reached its maximum log count. If so, creates a new file.
        if self._logs_in_bulk >= max_shipper_bulk_size:
            self._update_folder_size()
            self._create_new_file()

    def upload_files(self):
        for file in list(self._files_to_upload):
            if not os.path.exists(file):
                self._context.warning(f"File not found for upload: {file}")
                self._files_to_upload.remove(file)
                continue

            try:
                blob_name = os.path.basename(file)
                blob_client = self._container_client.get_blob_client(blob=blob_name)
                with open(file, 'rb') as data:
                    blob_client.upload_blob(data, overwrite=False)
                self._context.info(f"Uploaded log file to backup container: {blob_name}")
                self._files_to_upload.remove(file)
            except ResourceExistsError as ree:
                self._context.warning(f"A blob with the same name already exists: {ree}")
                new_name = self._rename_file(file)
                self._files_to_upload.append(new_name)
            except Exception as error:
                self._context.error(f"Error during upload of {file}: {error}")

    def _rename_file(self, file):
        new_name = f"{os.path.splitext(file)[0]}-{self._uniq_string()}{os.path.splitext(file)[1]}"
        os.rename(file, new_name)
        return new_name

    def write_event_to_blob(self, event, error):
        event_with_new_line = json.dumps(event) + "\n"
        try:
            with open(self.current_file_full_path, 'a') as file:
                file.write(event_with_new_line)
            self._logs_in_bulk += 1
            if self.current_file_full_path not in self._files_to_upload:
                self._files_to_upload.append(self.current_file_full_path)
        except Exception as error:
            self._context.error(f"Error in appendFile: {error}")

