import abc
import re
from venv import logger
import requests
from datetime import datetime, timedelta

from evaluation.event_flow.services.base_rest_service import BaseRestService

class BaseSMSService(abc.ABC):
    """
    This is an abstract base class for handling OTP operations.
    The methods in this class need to be implemented by any subclass.
    """

    @abc.abstractmethod
    def send_otp(self, phone_number: str, otp_value: str, otp_template_name: str) -> dict:
        """
        Send an OTP to the given phone number.

        Args:
            phone_number (str): The recipient's phone number.
            otp_value (str): The OTP value to be sent.
            otp_template_name (str): The OTP template name.

        Returns:
            dict: The response from the OTP service.
        """
        pass

    @abc.abstractmethod
    def verify_otp(self, phone_number: str, otp_value: str) -> bool:
        """
        Verify if the provided OTP is valid for the given phone number.

        Args:
            phone_number (str): The recipient's phone number.
            otp_value (str): The OTP value to be verified.

        Returns:
            bool: True if the OTP is valid, False otherwise.
        """
        pass


class SMS2FactorService(BaseSMSService,BaseRestService):
    """
    A concrete implementation of the BaseSMSService that interacts with the 2factor.in API
    for sending OTP and uses a local database for verifying OTP.
    """
    
    def __init__(self,api_key):
        self.api_key=api_key
        super().__init__()
    
    def get_base_headers(self):
        return {}
    
    def get_base_url(self) -> str:
        return f"https://2factor.in/API/V1/{self.api_key}/SMS"

    def get_base_url_VOICE(self)->str:
        return f"https://2factor.in/API/V1/{self.api_key}/VOICE"

    def send_otp(self, phone_number: str) -> dict:
        """
        Send an OTP to the given phone number using 2factor.in API.

        Args:
            phone_number (str): The recipient's phone number.
            otp_value (str): The OTP value to be sent.
            otp_template_name (str): The OTP template name.

        Returns:
            bool,str: True/False based on OTP sent status, and a message
        """
        url = f"{self.get_base_url()}/{phone_number}/AUTOGEN/OTP1"
        response = self._get_request(url=url)
        if response.status_code == 200 and response.json()['Status']=='Success':
            return True,"OTP sent successfully"
        else:
            logger.error(f'error sending otp : {response.json()}' )
            return False,"OTP sending failed"
        
    def send_otp_phone(self, phone_number: str) -> dict:
        """
        Send an OTP to the given phone number using 2factor.in API.

        Args:
            phone_number (str): The recipient's phone number.
            otp_value (str): The OTP value to be sent.
            otp_template_name (str): The OTP template name.

        Returns:
            bool,str: True/False based on OTP sent status, and a message
        """
        url = f"{self.get_base_url_VOICE()}/{phone_number}/AUTOGEN"
        response = self._get_request(url=url)
        if response.status_code == 200 and response.json()['Status']=='Success':
            return True,"OTP sent successfully",response.json()['Details']
        else:
            logger.error(f'error sending otp : {response.json()}' )
            return False,"OTP sending failed",None

    def verify_otp(self, phone_number: str, entered_otp_value: str) -> bool:
        """
        Verify if the provided OTP is valid for the given phone number using local database.

        Args:
            phone_number (str): The recipient's phone number.
            entered_otp_value (str): The OTP value entered by the user.

        Returns:
            bool: True if the OTP is valid, False otherwise with message.
        """
        url = f"{self.get_base_url()}/VERIFY3/{phone_number}/{entered_otp_value}"
        response = self._get_request(url=url)
        if response.status_code == 200 and response.json()['Status']=='Success':
            return True,"OTP Verified successfully"
        else:
            logger.error(f'error verifying otp : {response.json()}' )
            return False,"Error in verifying OTP"
        
    def verify_otp_phone(self,code,entered_otp_value):
        import abc
import re
from venv import logger
import requests
from datetime import datetime, timedelta

from evaluation.event_flow.services.base_rest_service import BaseRestService

class BaseSMSService(abc.ABC):
    """
    This is an abstract base class for handling OTP operations.
    The methods in this class need to be implemented by any subclass.
    """

    @abc.abstractmethod
    def send_otp(self, phone_number: str, otp_value: str, otp_template_name: str) -> dict:
        """
        Send an OTP to the given phone number.

        Args:
            phone_number (str): The recipient's phone number.
            otp_value (str): The OTP value to be sent.
            otp_template_name (str): The OTP template name.

        Returns:
            dict: The response from the OTP service.
        """
        pass

    @abc.abstractmethod
    def verify_otp(self, phone_number: str, otp_value: str) -> bool:
        """
        Verify if the provided OTP is valid for the given phone number.

        Args:
            phone_number (str): The recipient's phone number.
            otp_value (str): The OTP value to be verified.

        Returns:
            bool: True if the OTP is valid, False otherwise.
        """
        pass


class SMS2FactorService(BaseSMSService,BaseRestService):
    """
    A concrete implementation of the BaseSMSService that interacts with the 2factor.in API
    for sending OTP and uses a local database for verifying OTP.
    """
    
    def __init__(self,api_key):
        self.api_key=api_key
        super().__init__()
    
    def get_base_headers(self):
        return {}
    
    def get_base_url(self) -> str:
        return f"https://2factor.in/API/V1/{self.api_key}/SMS"

    def get_base_url_VOICE(self)->str:
        return f"https://2factor.in/API/V1/{self.api_key}/VOICE"

    def send_otp(self, phone_number: str) -> dict:
        """
        Send an OTP to the given phone number using 2factor.in API.

        Args:
            phone_number (str): The recipient's phone number.
            otp_value (str): The OTP value to be sent.
            otp_template_name (str): The OTP template name.

        Returns:
            bool,str: True/False based on OTP sent status, and a message
        """
        url = f"{self.get_base_url()}/{phone_number}/AUTOGEN/OTP1"
        response = self._get_request(url=url)
        if response.status_code == 200 and response.json()['Status']=='Success':
            return True,"OTP sent successfully"
        else:
            logger.error(f'error sending otp : {response.json()}' )
            return False,"OTP sending failed"
        
    def send_otp_phone(self, phone_number: str) -> dict:
        """
        Send an OTP to the given phone number using 2factor.in API.

        Args:
            phone_number (str): The recipient's phone number.
            otp_value (str): The OTP value to be sent.
            otp_template_name (str): The OTP template name.

        Returns:
            bool,str: True/False based on OTP sent status, and a message
        """
        url = f"{self.get_base_url_VOICE()}/{phone_number}/AUTOGEN"
        response = self._get_request(url=url)
        if response.status_code == 200 and response.json()['Status']=='Success':
            return True,"OTP sent successfully",response.json()['Details']
        else:
            logger.error(f'error sending otp : {response.json()}' )
            return False,"OTP sending failed",None

    def verify_otp(self, phone_number: str, entered_otp_value: str) -> bool:
        """
        Verify if the provided OTP is valid for the given phone number using local database.

        Args:
            phone_number (str): The recipient's phone number.
            entered_otp_value (str): The OTP value entered by the user.

        Returns:
            bool: True if the OTP is valid, False otherwise with message.
        """
        url = f"{self.get_base_url()}/VERIFY3/{phone_number}/{entered_otp_value}"
        response = self._get_request(url=url)
        if response.status_code == 200 and response.json()['Status']=='Success':
            return True,"OTP Verified successfully"
        else:
            logger.error(f'error verifying otp : {response.json()}' )
            return False,"Error in verifying OTP"
        
    def verify_otp_phone(self,code,entered_otp_value):
        url = f"{self.get_base_url_VOICE()}/VERIFY/{code}/{entered_otp_value}"
        response = self._get_request(url=url)
        if response.status_code == 200 and response.json()['Status']=='Success':
            return True,"OTP Verified successfully"
        else:
            logger.error(f'error sending otp : {response.json()}' )
            return False,"OTP Verification Failed"
