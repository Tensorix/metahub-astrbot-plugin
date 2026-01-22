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
            base_url=config["base_url"], token=config["token"]
        )
    
    class _JSONEncoder(json.JSONEncoder):
        """自定义 JSON 编码器，处理 Enum 和对象"""
        def default(self, obj):
            if isinstance(obj, Enum):
                return obj.value
            if hasattr(obj, '__dict__'):
                return vars(obj)
            return str(obj)

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

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        """接收所有消息"""
        try:
            event_dict = json.loads(
                json.dumps(vars(event.message_obj), cls=self._JSONEncoder)
            )
            logger.info(f"发送消息: {event_dict}")
            self.mh_client.post_message(event_dict)
        except Exception as e:
            logger.error(f"序列化或发送消息失败: {e}")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
