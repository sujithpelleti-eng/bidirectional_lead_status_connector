from abc import ABC, abstractmethod

import requests


class BaseRESTConnector(ABC):
    def __init__(self, config: dict):
        self.api_url = config.get("api_url")
        self.credentials = config.get("credentials")

    @abstractmethod
    def build_request_url(self, method: str) -> str:
        """Subclasses should define how to build the API endpoint URL."""
        pass

    def send_rest_request(self, method: str):
        try:
            request_url = self.build_request_url(method)
            headers = {
                "Authorization": f"Bearer {self.credentials['api_token']}",
                "Content-Type": "application/json",
            }
            response = requests.get(request_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"REST request error: {e}")
