import abc
import dataclasses
import typing
from django.conf import settings
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

import logging

logger = logging.getLogger(__name__)


class TimeoutHTTPAdapter(HTTPAdapter):
    DEFAULT_TIMEOUT = 5

    def __init__(self, *args, **kwargs):
        self.timeout = self.DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


# class SpeechToTextResponseDTO(dataclasses.dataclass):
#     success: bool
#     output_upload_response: str
#     transcript_upload_response: str

class BaseRestService(abc.ABC):

    @abc.abstractmethod
    def get_base_url(self) -> str:
        pass

    @abc.abstractmethod
    def get_base_headers(self) -> {}:
        pass

    def __init__(self, TIMEOUT=30, CONNECTION_TIMEOUT=30, MAX_RETRIES=1, **kwargs):
        self.base_url = self.get_base_url()
        self._timeout = kwargs.get('timeout', TIMEOUT)
        self._connection_timeout = kwargs.get('connection_timeout', CONNECTION_TIMEOUT)
        self.retries = Retry(total=kwargs.get('max_retries', MAX_RETRIES))

    def __get_session(self, use_retry=False):
        s = requests.Session()
        if use_retry:
            adapter = TimeoutHTTPAdapter(max_retries=self.retries, timeout=(self._connection_timeout, self._timeout,))
        else:
            adapter = TimeoutHTTPAdapter(timeout=(self._connection_timeout, self._timeout,))
        s.mount('http://', adapter)
        s.mount('https://', adapter)
        return s

    def _get_request(self, *, url, params=None, use_retry=True, custom_headers=None):
        custom_headers = {} if custom_headers is None else custom_headers
        headers = {'accept': 'application/json', **self.get_base_headers()}
        headers = {**headers, **custom_headers}
        return self.__get_session(use_retry=use_retry).get(url, params=params, headers=headers)

    def _post_request(self, *, url, data: typing.Dict, use_retry=True, custom_headers=None):
        custom_headers = {} if custom_headers is None else custom_headers
        headers = {'content-type': 'application/json', **self.get_base_headers()}
        headers = {**headers, **custom_headers}
        return self.__get_session(use_retry=use_retry).post(url, json=data, headers=headers)
    
    def _patch_request(self, *, url, data: typing.Dict, use_retry=True, custom_headers=None):
        custom_headers = {} if custom_headers is None else custom_headers
        headers = {'content-type': 'application/json', **self.get_base_headers()}
        headers = {**headers, **custom_headers}
        return self.__get_session(use_retry=use_retry).patch(url, json=data, headers=headers)

