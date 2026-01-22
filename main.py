from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from enum import Enum
import json

from .metahub import MetaHub


@register("helloworld", "YourName", "一个简单的 Hello World 插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.mh_client = MetaHub(
            base_url=config["base_url"], api_key=config["api_key"]
        )
    
    # async def initialize(self):
    #     """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 hello world 指令"""  # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str  # 用户发的纯文本消息字符串
        message_chain = (
            event.get_messages()
        )  # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(
            f"Hello, {user_name}, 你发了 {message_str}!"
        )  # 发送一条纯文本消息

    def _convert_component(self, component):
        """Convert AstrBot message component to MetaHub format"""
        if isinstance(component, dict):
            c_type = component.get("type")
            data = component
        else:
            c_type = getattr(component, "type", None)
            data = vars(component) if hasattr(component, "__dict__") else {}
        
        if not c_type:
            return None
            
        c_type = str(c_type)
        
        if c_type == "Plain":
            return {"type": "text", "text": data.get("text", "")}
        elif c_type == "At":
            return {"type": "at", "qq": data.get("qq") or data.get("user_id"), "name": data.get("name")}
        elif c_type == "Image":
            return {"type": "image", "file": data.get("file") or data.get("url")}
        
        return None

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        """接收所有消息"""
        try:
            msg_obj = event.message_obj
            
            # Safe attribute access helper
            def get_attr(obj, name, default=None):
                if isinstance(obj, dict):
                    return obj.get(name, default)
                return getattr(obj, name, default)

            # Determine session type
            raw_type = str(get_attr(msg_obj, "type"))
            session_type = "group" if "Group" in raw_type else "pm"
            
            # Construct payload
            payload = {
                "timestamp": get_attr(msg_obj, "timestamp"),
                "session_id": event.get_session_id(),
                "message_id": get_attr(msg_obj, "message_id"),
                "session_type": session_type,
                "source": f"astr_{event.get_platform_name()}",
                "self_id": event.get_self_id(),
                "message_str": event.message_str,
                "message": []
            }

            # Sender
            payload["sender"] = {
                "user_id": event.get_sender_id(),
                "nickname": event.get_sender_name()
            }

            # Group
            if session_type == "group":
                # Fallback to msg_obj for group details as event.get_group() return type is uncertain
                group = get_attr(msg_obj, "group")
                if group:
                    payload["group"] = group if isinstance(group, dict) else vars(group)
            
            # Message Chain
            raw_message = event.get_messages()
            for component in raw_message:
                converted = self._convert_component(component)
                if converted:
                    payload["message"].append(converted)
            
            # Add raw_message for debugging if needed
            # payload["raw_message"] = json.loads(json.dumps(vars(msg_obj), default=str))

            logger.info(f"发送消息到 MetaHub: {payload}")
            self.mh_client.post_message(payload)
            
        except Exception as e:
            logger.error(f"处理或发送消息失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
