import requests

class MetaHub:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
    
    def post_message(self, data:dict):
        url = f"{self.base_url}/api/v1/webhooks/im/message"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = self.session.post(url, json=data, headers=headers)
        return response.json()