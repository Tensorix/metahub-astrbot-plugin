import requests
import logging

logger = logging.getLogger(__name__)

class MetaHub:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
    
    def post_message(self, data: dict):
        url = f"{self.base_url}/webhooks/im/message"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = self.session.post(url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to post message to MetaHub: {e}")
            if e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise