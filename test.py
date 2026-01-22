from metahub import MetaHub

data = {'timestamp': 1767509853, 'group': None, 'self_id': 'webchat', 'sender': {'user_id': 'astrbot', 'nickname': 'astrbot'}, 'type': 'FriendMessage', 'session_id': 'webchat!astrbot!1fe2fa65-66fa-40ca-b017-f28eb0d4fe71', 'message_id': '5f6bb50b-e6c8-44c8-8e01-56576a954fb4', 'message': [{'type': 'Plain', 'text': 'hi', 'convert': True}], 'message_str': 'hi', 'raw_message': ['astrbot', '1fe2fa65-66fa-40ca-b017-f28eb0d4fe71', {'message': [{'type': 'plain', 'text': 'hi'}], 'selected_provider': 'new-api/kimi-k2', 'selected_model': 'kimi-k2', 'enable_streaming': True}]} 

hub = MetaHub(
    base_url="https://app.tensorix.xyz/api/v1",
    token="<PASSWORD>",
)

hub.post_message(data)