import datetime

from django.conf import settings

from azure.storage.blob import (
    BlobServiceClient,
    generate_blob_sas,
    BlobSasPermissions,
    ContentSettings,
    BlobClient,
)
from urllib.parse import urlparse, unquote

from storage_service.interface import StorageServiceInterface


class AzureStorageService(StorageServiceInterface):
    """
    AzureStorageService provides an interface to interact with Azure Storage.

    Attributes:
        blob_service_client (BlobServiceClient): The client to interact with the Azure Storage Service.
    """

    def __init__(self):
        self.blob_service_client = BlobServiceClient(
            account_url=f"https://{settings.STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
            credential=settings.STORAGE_ACCOUNT_KEY,
        )

    def get_blob_details(self, container_name, blob_name):
        """
        Get the properties of a blob.

        Parameters:
            container_name (str): The name of the container.
            blob_name (str): The name of the blob.

        Returns:
            BlobProperties: The properties of the blob.
        """
        blob_client = self.blob_service_client.get_blob_client(
            container_name, blob_name
        )
        return blob_client.get_blob_properties()

    def upload_blob(
        self, container_name, blob_name, content, overwrite=True, content_type=None
    ):
        """
        Upload content to a blob.

        Parameters:
            container_name (str): The name of the container.
            blob_name (str): The name of the blob.
            content (bytes): The content to upload.
        """
        blob_client = self.blob_service_client.get_blob_client(
            container_name, blob_name
        )
        blob_client.upload_blob(
            content,
            overwrite=overwrite,
            content_settings=ContentSettings(content_type=content_type),
        )
        return blob_client.url

    def download_blob(self, *, container_name: str, blob_name: str, file_path: str):
        with open(file_path, "wb") as fil:
            fil.write(self.read_blob(container_name, blob_name))

    def _generate_sas_url(
        self,
        container_name,
        blob_name,
        expiry_time,
        allow_read,
        allow_write,
        content_type=None,
    ):
        """
        Generate a SAS URL for a blob.

        Parameters:
            container_name (str): The name of the container.
            blob_name (str): The name of the blob.
            expiry_time (datetime): The expiry time of the SAS URL.
            allow_read (bool): Whether to allow read access.
            allow_write (bool): Whether to allow write access.
            content_type (str, optional): The content type of the blob.

        Returns:
            str: The SAS URL for the blob.
        """
        blob_client = self.blob_service_client.get_blob_client(
            container_name, blob_name
        )

        sas_token = generate_blob_sas(
            account_name=blob_client.account_name,
            container_name=blob_client.container_name,
            blob_name=blob_client.blob_name,
            account_key=settings.STORAGE_ACCOUNT_KEY,
            permission=BlobSasPermissions(read=allow_read, write=allow_write),
            expiry=expiry_time,
        )

        return f"https://{blob_client.account_name}.blob.core.windows.net/{blob_client.container_name}/{blob_name}?{sas_token}"

    def generate_quick_read_url(
        self, *, container_name, blob_name, expiry_in_seconds=300
    ):
        return self.generate_blob_access_url(
            container_name,
            blob_name,
            expiry_time=datetime.datetime.now()
            + datetime.timedelta(minutes=expiry_in_seconds * 60),
            allow_read=True,
            allow_write=False,
        )

    def generate_blob_access_url(
        self,
        container_name,
        blob_name,
        expiry_time,
        allow_read,
        allow_write,
        content_type=None,
    ):
        """
        Generate a access url for a blob.

        Parameters:
            container_name (str): The name of the container.
            blob_name (str): The name of the blob.
            expiry_time (datetime): The expiry time of the SAS URL.
            allow_read (bool): Whether to allow read access.
            allow_write (bool): Whether to allow write access.
            content_type (str, optional): The content type of the blob.

        Returns:
            str: The SAS URL for the blob.
        """
        return self._generate_sas_url(
            container_name,
            blob_name,
            expiry_time,
            allow_read,
            allow_write,
            content_type,
        )

    def create_container(self, container_name):
        """
        Create a new container.

        Parameters:
            container_name (str): The name of the container.
        """
        container_client = self.blob_service_client.get_container_client(container_name)
        container_client.create_container()

    def container_exists(self, container_name):
        """
        Check if a container exists.

        Parameters:
            container_name (str): The name of the container.

        Returns:
            bool: True if the container exists, False otherwise.
        """
        container_client = self.blob_service_client.get_container_client(container_name)
        return container_client.exists()

    def read_blob(self, container_name, blob_name):
        """
        Read the content of a blob.

        Parameters:
            container_name (str): The name of the container.
            blob_name (str): The name of the blob.

        Returns:
            bytes: The content of the blob.
        """
        blob_client = self.blob_service_client.get_blob_client(
            container_name, blob_name
        )
        download_stream = blob_client.download_blob()
        return download_stream.readall()

    def copy_blob(
        self,
        source_container_name,
        source_blob_name,
        destination_container_name,
        destination_blob_name,
    ):
        """
        Copy a blob from a source to destination.

        Parameters:
            source_container_name (str): The name of the source container.
            source_blob_name (str): The name of the source blob.
            destination_container_name (str): The name of the destination container.
            destination_blob_name (str): The name of the destination blob.

        Returns:
            dict: A dictionary containing the status of the copy operation.
        """
        source_blob_client = self.blob_service_client.get_blob_client(
            source_container_name, source_blob_name
        )
        destination_blob_client = self.blob_service_client.get_blob_client(
            destination_container_name, destination_blob_name
        )
        source_blob_url = source_blob_client.url
        copy_operation = destination_blob_client.start_copy_from_url(source_blob_url)
        return copy_operation

    def delete_blob(self, blob_url):
        """
        Delete a blob using authenticated BlobServiceClient.

        Parameters:
            blob_url (str): The full URL of the blob to delete

        Raises:
            ResourceNotFoundError: If the blob does not exist
        """
        try:
            parsed_url = urlparse(blob_url)
            # Extract container name (first segment after domain)
            path_parts = parsed_url.path.lstrip("/").split("/", 1)
            if len(path_parts) != 2:
                raise ValueError("Invalid blob URL format")

            container_name = path_parts[0]
            # Get the rest of the path as blob name, preserving original encoding
            blob_name = unquote(path_parts[1])

            # Create blob client and delete
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )
            blob_client.delete_blob()

        except ValueError as e:
            raise ValueError(f"Failed to parse blob URL: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to delete blob: {str(e)}")
