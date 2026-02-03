import asyncio
import json
import logging
from typing import Optional, Callable, Awaitable
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


class MetaHubWebSocket:
    """MetaHub WebSocket 客户端，支持双向消息传递和自动重连"""
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        source: str,
        on_send_message: Optional[Callable[[dict], Awaitable[dict]]] = None
    ):
        """
        初始化 WebSocket 客户端
        
        Args:
            base_url: MetaHub 基础URL (如 https://app.tensorix.org/api/v1)
            api_key: API Key (sk-xxx 格式)
            source: IM 平台标识 (如 astr_qq)
            on_send_message: 处理下行消息的回调函数，返回 {"success": bool, "data": dict, "error": str}
        """
        self.base_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        self.api_key = api_key
        self.source = source
        self.on_send_message = on_send_message
        
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._running = False
        self._reconnect_delay = 5  # 初始重连间隔（秒）
        self._max_reconnect_delay = 60  # 最大重连间隔
        self._heartbeat_interval = 30  # 心跳间隔
        
        self._connect_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self.ws is not None

    async def start(self):
        """启动 WebSocket 连接（带自动重连）"""
        if self._running:
            logger.warning("WebSocket 已在运行中")
            return
        
        self._running = True
        self._connect_task = asyncio.create_task(self._connect_loop())
        logger.info("WebSocket 客户端已启动")

    async def stop(self):
        """停止 WebSocket 连接"""
        self._running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._receive_task:
            self._receive_task.cancel()
        if self._connect_task:
            self._connect_task.cancel()
        
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.error(f"关闭 WebSocket 时出错: {e}")
        
        self._connected = False
        self.ws = None
        logger.info("WebSocket 客户端已停止")

    async def _connect_loop(self):
        """连接循环，支持自动重连"""
        while self._running:
            try:
                await self._connect()
            except (ConnectionClosed, ConnectionError, OSError) as e:
                logger.warning(f"WebSocket 连接断开: {e}")
                self._connected = False
                self.ws = None
                
                if self._running:
                    logger.info(f"将在 {self._reconnect_delay} 秒后重连...")
                    await asyncio.sleep(self._reconnect_delay)
                    # 指数退避
                    self._reconnect_delay = min(
                        self._reconnect_delay * 2,
                        self._max_reconnect_delay
                    )
            except Exception as e:
                logger.error(f"WebSocket 连接出现未预期错误: {e}", exc_info=True)
                if self._running:
                    await asyncio.sleep(self._reconnect_delay)

    async def _connect(self):
        """建立 WebSocket 连接"""
        url = f"{self.base_url}/im/gateway?token={self.api_key}&source={self.source}"
        logger.info(f"正在连接到 MetaHub WebSocket: {url.split('?')[0]}")
        
        async with websockets.connect(url) as ws:
            self.ws = ws
            self._connected = True
            self._reconnect_delay = 5  # 重置重连延迟
            logger.info(f"已连接到 MetaHub (source: {self.source})")
            
            # 启动心跳和接收任务
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            # 等待任务完成（通常是连接断开）
            await asyncio.gather(
                self._heartbeat_task,
                self._receive_task,
                return_exceptions=True
            )

    async def _heartbeat_loop(self):
        """心跳保活循环"""
        try:
            while self._connected and self.ws:
                await asyncio.sleep(self._heartbeat_interval)
                if self.ws:
                    await self.ws.send(json.dumps({"type": "ping"}))
                    logger.debug("💓 发送心跳 ping")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"❌ 心跳循环出错: {e}")

    async def _receive_loop(self):
        """接收消息循环"""
        try:
            async for raw_message in self.ws:
                try:
                    data = json.loads(raw_message)
                    msg_type = data.get("type")

                    if msg_type == "pong":
                        logger.debug("💓 收到心跳 pong")
                    elif msg_type == "send_message":
                        logger.info(f"📥 [WebSocket] 收到下行消息: type={msg_type}, request_id={data.get('request_id')}")
                        # 异步处理发送消息指令，不阻塞接收
                        asyncio.create_task(self._handle_send_message(data))
                    else:
                        logger.warning(f"⚠️  收到未知消息类型: {msg_type}, 数据: {data}")

                except json.JSONDecodeError as e:
                    logger.error(f"❌ 解析消息失败: {e}, 原始消息: {raw_message}")
                except Exception as e:
                    logger.error(f"❌ 处理消息时出错: {e}", exc_info=True)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"❌ 接收循环出错: {e}")
            raise

    async def _handle_send_message(self, data: dict):
        """处理 MetaHub 的发送消息指令"""
        request_id = data.get("request_id")
        session_id = data.get("session_id")
        message = data.get("message", [])
        message_str = data.get("message_str", "")

        logger.info(f"📥 [下行消息] 处理中: request_id={request_id}, session_id={session_id}, message_str='{message_str[:50]}...'")

        if not self.on_send_message:
            logger.error("❌ 未设置 on_send_message 回调，无法处理发送消息指令")
            await self._send_result(request_id, False, error="未配置消息发送处理器")
            return

        try:
            # 调用回调函数处理消息发送
            result = await self.on_send_message({
                "session_id": session_id,
                "message": message,
                "message_str": message_str
            })

            success = result.get("success", False)
            if success:
                await self._send_result(
                    request_id,
                    True,
                    data=result.get("data", {})
                )
                logger.info(f"✅ [下行消息] 发送成功: request_id={request_id}, session_id={session_id}")
            else:
                error = result.get("error", "未知错误")
                await self._send_result(request_id, False, error=error)
                logger.error(f"❌ [下行消息] 发送失败: request_id={request_id}, error={error}")

        except Exception as e:
            logger.error(f"❌ 处理发送消息时出错: {e}", exc_info=True)
            await self._send_result(request_id, False, error=str(e))

    async def _send_result(self, request_id: str, success: bool, data: dict = None, error: str = None):
        """回报消息发送结果"""
        if not self.ws:
            logger.error("WebSocket 未连接，无法发送结果")
            return
        
        result = {
            "type": "result",
            "request_id": request_id,
            "success": success
        }
        
        if success and data:
            result["data"] = data
        if not success and error:
            result["error"] = error
        
        try:
            await self.ws.send(json.dumps(result))
        except Exception as e:
            logger.error(f"发送结果失败: {e}")

    async def send_message(self, message_data: dict) -> bool:
        """
        发送消息到 MetaHub（上行）

        Args:
            message_data: 消息数据，格式参考文档中的 message 类型

        Returns:
            是否发送成功
        """
        if not self.is_connected:
            logger.warning(f"⚠️  WebSocket 未连接，无法发送消息 (ws={self.ws is not None}, connected={self._connected})")
            return False

        try:
            payload = {
                "type": "message",
                "data": message_data
            }
            await self.ws.send(json.dumps(payload))
            session_id = message_data.get('session_id')
            msg_id = message_data.get('message_id')
            logger.info(f"📤 [WebSocket] 发送上行消息: session_id={session_id}, message_id={msg_id}")
            return True
        except ConnectionClosed as e:
            logger.error(f"❌ 发送消息失败 - 连接已关闭: code={e.code}, reason={e.reason}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"❌ 发送消息失败 - 异常: {type(e).__name__}: {e}", exc_info=True)
            return False
