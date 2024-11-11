from abc import ABC, abstractmethod

class StorageServiceInterface(ABC):
    
    blob_service_client = None
    
    @abstractmethod
    def get_blob_details(self, container_name, blob_name):
        pass

    @abstractmethod
    def upload_blob(self, container_name, blob_name, content):
        pass

    @abstractmethod
    def download_blob(self, *, container_name:str, blob_name:str, file_path:str):
        pass

    @abstractmethod
    def generate_blob_access_url(self, container_name, blob_name, expiry_time, allow_read, allow_write):
        pass

    @abstractmethod
    def create_container(self, container_name):
        pass
    
    @abstractmethod
    def container_exists(self, container_name):
        pass

    @abstractmethod
    def read_blob(self, container_name, blob_name):
        pass
