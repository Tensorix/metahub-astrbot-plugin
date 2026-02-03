from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult, MessageChain
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from enum import Enum
import json
import asyncio

from .metahub import MetaHub
from .metahub_ws import MetaHubWebSocket


@register("MetaHub", "Tensorix", "MetaHub 集成插件", "0.0.1")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        
        # Webhook 客户端（fallback）
        self.mh_client = MetaHub(
            base_url=config["base_url"], api_key=config["api_key"]
        )
        
        # WebSocket 客户端
        self.mh_ws: MetaHubWebSocket = None
        self.config = config
        
        # 存储 unified_msg_origin 到 source 的映射
        self.session_source_map = {}
    
    async def initialize(self):
        """异步初始化，建立 WebSocket 连接并测试可用性"""
        try:
            # 从配置获取默认 source，或使用 "astr_default"
            default_source = self.config.get("default_source", "astr_default")
            logger.info(f"🔌 正在建立 WebSocket 连接 (source={default_source})...")

            # 创建正式的 WebSocket 连接
            self.mh_ws = MetaHubWebSocket(
                base_url=self.config["base_url"],
                api_key=self.config["api_key"],
                source=default_source,
                on_send_message=self._handle_metahub_send_message
            )

            # 启动连接
            await self.mh_ws.start()

            # 等待连接建立（最多5秒）
            connected = False
            for i in range(50):
                if self.mh_ws.is_connected:
                    connected = True
                    break
                await asyncio.sleep(0.1)

            if connected:
                logger.info("✅ WebSocket 连接成功建立并已测试可用")
                logger.info(f"📡 当前使用 WebSocket 模式 (source={default_source})")
            else:
                logger.warning("❌ WebSocket 连接建立超时（5秒）")
                logger.warning("⚠️  将使用 Webhook 模式作为备选方案")
                # 停止失败的连接
                await self.mh_ws.stop()
                self.mh_ws = None

        except Exception as e:
            logger.error(f"❌ WebSocket 连接失败: {e}", exc_info=True)
            logger.warning("⚠️  将使用 Webhook 模式作为备选方案")
            if self.mh_ws:
                await self.mh_ws.stop()
                self.mh_ws = None
    
    async def _ensure_websocket(self, source: str):
        """确保 WebSocket 连接已建立并匹配当前 source"""
        # 如果 WebSocket 存在且 source 匹配，检查连接状态
        if self.mh_ws and self.mh_ws.source == source:
            if self.mh_ws.is_connected:
                return  # 连接正常，无需处理
            else:
                logger.warning(f"⚠️  WebSocket 连接断开 (source={source})，等待自动重连...")
                # 等待自动重连（最多2秒）
                for i in range(20):
                    if self.mh_ws.is_connected:
                        logger.info(f"✅ WebSocket 已重新连接 (source={source})")
                        return
                    await asyncio.sleep(0.1)

        # 如果 source 不同，需要切换连接
        if self.mh_ws and self.mh_ws.source != source:
            logger.info(f"🔄 检测到 source 变更: {self.mh_ws.source} → {source}，重建连接...")
            await self.mh_ws.stop()
            self.mh_ws = None

        # 创建新的 WebSocket 连接
        if self.mh_ws is None:
            logger.info(f"🔌 为 source={source} 建立新的 WebSocket 连接...")
            self.mh_ws = MetaHubWebSocket(
                base_url=self.config["base_url"],
                api_key=self.config["api_key"],
                source=source,
                on_send_message=self._handle_metahub_send_message
            )
            await self.mh_ws.start()

            # 等待连接建立（最多3秒）
            for i in range(30):
                if self.mh_ws.is_connected:
                    logger.info(f"✅ WebSocket 连接已建立 (source={source})")
                    return
                await asyncio.sleep(0.1)

            logger.warning(f"❌ WebSocket 连接建立超时（3秒），source={source}")
    
    async def _handle_metahub_send_message(self, data: dict) -> dict:
        """
        处理 MetaHub 的发送消息指令（下行）
        
        Args:
            data: {"session_id": str, "message": list, "message_str": str}
            
        Returns:
            {"success": bool, "data": dict, "error": str}
        """
        session_id = data.get("session_id")  # 这是 unified_msg_origin
        message = data.get("message", [])
        message_str = data.get("message_str", "")
        
        try:
            # 构建 MessageChain
            message_chain = MessageChain()
            
            for component in message:
                comp_type = component.get("type")
                
                if comp_type == "text":
                    message_chain.message(component.get("text", ""))
                elif comp_type == "image":
                    # 支持 url 或 file 字段
                    image_url = component.get("url") or component.get("file")
                    if image_url:
                        message_chain.image(image_url)
                elif comp_type == "at":
                    # AstrBot 的 at 功能可能需要特定格式，这里简化处理
                    name = component.get("name", "")
                    message_chain.message(f"@{name} ")
                else:
                    logger.warning(f"不支持的消息组件类型: {comp_type}")
            
            # 如果没有构建任何消息，使用 message_str
            if not message_chain.chain:
                message_chain.message(message_str)
            
            # 发送消息
            await self.context.send_message(session_id, message_chain)

            logger.info(f"📥 [下行消息] 发送成功: session_id={session_id}, message_str='{message_str[:50]}...'")
            return {
                "success": True,
                "data": {}
            }
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

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
            
        if isinstance(c_type, Enum):
            c_type = c_type.value
        elif hasattr(c_type, "value") and not isinstance(c_type, str):
            c_type = c_type.value
        c_type = str(c_type)
        if "." in c_type:
            c_type = c_type.split(".")[-1]
        c_type = c_type.strip()
        c_type_lower = c_type.lower()
        
        if c_type_lower == "plain":
            return {"type": "text", "text": data.get("text", "")}
        elif c_type_lower == "at":
            return {"type": "at", "qq": data.get("qq") or data.get("user_id"), "name": data.get("name")}
        elif c_type_lower == "image":
            return {"type": "image", "file": data.get("file") or data.get("url")}
        
        return None

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        """接收所有消息并转发到 MetaHub"""
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
            
            # 获取 unified_msg_origin 和 source
            unified_msg_origin = event.unified_msg_origin
            source = f"astr_{event.get_platform_name()}"
            
            # 确保 WebSocket 连接已建立
            await self._ensure_websocket(source)
            
            # 存储映射关系
            self.session_source_map[unified_msg_origin] = source
            
            # Construct payload
            payload = {
                "timestamp": get_attr(msg_obj, "timestamp"),
                "session_id": unified_msg_origin,  # 使用 unified_msg_origin
                "message_id": get_attr(msg_obj, "message_id"),
                "session_type": session_type,
                "source": source,
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
                group = get_attr(msg_obj, "group")
                if group:
                    payload["group"] = group if isinstance(group, dict) else vars(group)
            
            # Message Chain
            raw_message = event.get_messages()
            for component in raw_message:
                converted = self._convert_component(component)
                if converted:
                    payload["message"].append(converted)
                else:
                    logger.debug(f"跳过无法转换的消息组件: {component}")
            
            # 优先使用 WebSocket 发送，失败则降级到 Webhook
            success = False
            ws_error_reason = None

            if self.mh_ws and self.mh_ws.is_connected:
                success = await self.mh_ws.send_message(payload)
                if success:
                    logger.info(f"📤 [WebSocket] 发送消息成功: session_id={unified_msg_origin}, msg_id={payload.get('message_id')}")
                else:
                    ws_error_reason = "WebSocket 已连接但发送返回失败"
            elif self.mh_ws:
                ws_error_reason = f"WebSocket 未连接 (is_connected={self.mh_ws.is_connected})"
            else:
                ws_error_reason = "WebSocket 客户端未初始化"

            if not success:
                # Fallback 到 Webhook
                logger.warning(f"⚠️  WebSocket 发送失败，降级到 Webhook。原因: {ws_error_reason}")
                try:
                    self.mh_client.post_message(payload)
                    logger.info(f"📤 [Webhook] 发送消息成功: session_id={unified_msg_origin}, msg_id={payload.get('message_id')}")
                except Exception as e:
                    logger.error(f"❌ Webhook 发送也失败: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"处理或发送消息失败: {e}", exc_info=True)

    async def terminate(self):
        """插件销毁时优雅关闭 WebSocket 连接"""
        if self.mh_ws:
            logger.info("正在关闭 WebSocket 连接...")
            await self.mh_ws.stop()
            logger.info("WebSocket 连接已关闭")
