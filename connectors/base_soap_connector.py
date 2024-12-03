import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseSOAPConnector(ABC):
    """
    Abstract base class for SOAP connectors, providing a base implementation
    for sending SOAP requests.
    """
    def __init__(self, config: dict):
        self._api_url = config.get('api_url')
        self._credentials = config.get('credentials')
        # logger.info("Initialized BaseSOAPConnector with provided configuration.")

    @abstractmethod
    def build_request(self, method: str, body_content: str) -> str:
        """Each subclass should implement its request format."""
        pass

    def _send_soap_request(self, url: str, headers: dict, request_xml: str) -> bytes:
        """
        Sends a SOAP request to the provided URL with headers and request XML.

        :param url: The SOAP endpoint URL.
        :param headers: Headers for the request.
        :param request_xml: The XML body of the request.
        :return: Response content as bytes.
        """
        try:
            response = requests.post(url, headers=headers, data=request_xml)
            response.raise_for_status()
            logger.info(f"SOAP request successful for URL: {url}")
            return response.content
        except Exception as e:
            logger.error(f"SOAP request error for URL {url}: {e}")
            raise Exception(f"SOAP request error: {e}")

    @abstractmethod
    def fetch_raw_data(self) -> List[Dict[str, Any]]:
        """Fetch and parse data from the system. Should be implemented by each connector."""
        pass
