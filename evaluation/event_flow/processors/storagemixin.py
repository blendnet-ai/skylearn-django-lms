import requests


class ProcessorStorageMixin:

    def download_file_get_content(self,*, url:str):
        response = requests.get(url, allow_redirects=True)
        if response.status_code != 200:
            raise Exception(
                f"Error in reading transcript. Response code = {response.status_code}. Response - {response.content}")
        return response