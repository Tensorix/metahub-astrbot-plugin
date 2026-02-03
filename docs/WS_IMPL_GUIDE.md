# IM 平台接入指南

本文档面向 IM 桥接服务开发者，说明如何通过 WebSocket 接入 Metahub IM Gateway。

## 概述

IM 桥接服务通过 WebSocket 与 Metahub 建立持久双向连接：
- **上行**：将 IM 平台收到的消息转发到 Metahub
- **下行**：接收 Metahub 的发送指令，将消息投递到 IM 平台

```
IM 平台 (QQ/微信/Telegram/...)
       ↕
IM 桥接服务 (你的代码)
       ↕ WebSocket
Metahub Server
```

## 1. 建立连接

### 端点

```
ws://<host>/api/v1/im/gateway?token=<TOKEN>&source=<SOURCE>
```

| 参数 | 必须 | 说明 |
|------|------|------|
| `token` | 是 | JWT access token 或 API Key（`sk-xxx`） |
| `source` | 是 | IM 平台标识，如 `astr_qq`、`astr_wechat`、`astr_telegram` |

### 认证

支持两种认证方式：

**JWT Token**：通过 `/api/v1/auth/login` 获取 access token

```
ws://host/api/v1/im/gateway?token=eyJhbGciOiJIUzI1NiIs...&source=astr_qq
```

**API Key**：通过 API Key 管理接口创建，格式 `sk-xxx`

```
ws://host/api/v1/im/gateway?token=sk-xxxxxxxxxxxx&source=astr_qq
```

> 推荐桥接服务使用 API Key，无需处理 token 过期刷新。

### 连接规则

- 每个 `(user, source)` 只允许一个活跃连接
- 新连接会自动替换旧连接（旧连接收到 close code 4000）
- 认证失败收到 close code 4001

## 2. 消息协议

### 2.1 心跳保活

桥接服务应定期发送 ping，建议间隔 30 秒：

```json
→ {"type": "ping"}
← {"type": "pong"}
```

### 2.2 转发 IM 消息（上行）

当 IM 平台收到新消息时，通过 WebSocket 转发到 Metahub：

```json
→ {
    "type": "message",
    "data": {
        "timestamp": 1706000000,
        "session_id": "group_12345",
        "message_id": "msg_001",
        "session_type": "group",
        "source": "astr_qq",
        "sender": {
            "nickname": "张三",
            "user_id": "10001"
        },
        "self_id": "bot_001",
        "message_str": "明天下午三点开会",
        "message": [
            {"type": "text", "text": "明天下午三点开会"}
        ],
        "group": {
            "group_id": "12345",
            "group_name": "工作群"
        },
        "raw_message": null
    }
}
```

#### data 字段说明

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `timestamp` | int | 是 | 消息时间戳（秒） |
| `session_id` | string | 是 | IM 平台侧的会话 ID |
| `message_id` | string | 是 | IM 平台侧的消息 ID（用于去重） |
| `session_type` | string | 是 | 会话类型：`pm`（私聊）、`group`（群聊）或自定义 |
| `source` | string | 否 | IM 来源，可省略（使用连接时的 source 参数） |
| `sender` | object | 是 | 发送者信息，至少包含 `nickname` |
| `self_id` | string | 是 | 机器人 ID |
| `message_str` | string | 是 | 消息纯文本 |
| `message` | array | 是 | 结构化消息部分（见下方） |
| `group` | object | 否 | 群组信息，群消息时提供 |
| `raw_message` | any | 否 | 原始消息数据 |

#### message 结构化消息

```json
[
    {"type": "text", "text": "你好 "},
    {"type": "at", "name": "李四", "user_id": "10002"},
    {"type": "text", "text": " 明天开会"},
    {"type": "image", "url": "https://example.com/img.png"},
    {"type": "url", "url": "https://example.com/doc"},
    {"type": "json", "data": {"key": "value"}}
]
```

> 这与 webhook 的 `IMMessageWebhookRequest` 格式完全相同，桥接无需维护两套格式。

### 2.3 接收发送指令（下行）

Metahub 需要发送消息到 IM 平台时，桥接会收到：

```json
← {
    "type": "send_message",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_id": "group_12345",
    "message": [
        {"type": "text", "text": "收到，我会准时参加"}
    ],
    "message_str": "收到，我会准时参加"
}
```

| 字段 | 说明 |
|------|------|
| `request_id` | 请求唯一标识，回报结果时必须原样返回 |
| `session_id` | IM 平台侧的会话 ID，桥接据此确定发送目标 |
| `message` | 结构化消息，格式同上行的 message |
| `message_str` | 纯文本回退 |

### 2.4 回报发送结果

桥接完成投递后，**必须**回报结果：

**成功**：
```json
→ {
    "type": "result",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "success": true,
    "data": {
        "message_id": "platform_msg_456"
    }
}
```

**失败**：
```json
→ {
    "type": "result",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "success": false,
    "error": "目标群聊不存在"
}
```

> `request_id` 必须与 `send_message` 中的一致。服务端有 30 秒超时，超时未回报视为失败。

## 3. 参考实现

### Python (websockets)

```python
import asyncio
import json
import websockets


API_URL = "ws://localhost:8000/api/v1/im/gateway"
API_KEY = "sk-your-api-key"
SOURCE = "my_bot"


async def handle_send_message(ws, data: dict):
    """处理服务端的发送消息指令"""
    request_id = data["request_id"]
    session_id = data["session_id"]
    message_str = data["message_str"]

    try:
        # === 在这里调用你的 IM 平台 SDK 发送消息 ===
        # result = await your_im_sdk.send(session_id, message_str)
        print(f"Sending to {session_id}: {message_str}")

        await ws.send(json.dumps({
            "type": "result",
            "request_id": request_id,
            "success": True,
            "data": {"message_id": "sent_001"},
        }))
    except Exception as e:
        await ws.send(json.dumps({
            "type": "result",
            "request_id": request_id,
            "success": False,
            "error": str(e),
        }))


async def forward_im_message(ws, message_data: dict):
    """将 IM 平台收到的消息转发到 Metahub"""
    await ws.send(json.dumps({
        "type": "message",
        "data": message_data,
    }))


async def heartbeat(ws):
    """心跳保活"""
    while True:
        await asyncio.sleep(30)
        await ws.send(json.dumps({"type": "ping"}))


async def main():
    url = f"{API_URL}?token={API_KEY}&source={SOURCE}"

    async with websockets.connect(url) as ws:
        print(f"Connected to Metahub as {SOURCE}")

        # 启动心跳
        asyncio.create_task(heartbeat(ws))

        # 主接收循环
        async for raw in ws:
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "send_message":
                await handle_send_message(ws, data)
            elif msg_type == "pong":
                pass  # 心跳回复
            else:
                print(f"Unknown message: {data}")


if __name__ == "__main__":
    asyncio.run(main())
```

### 带重连的完整示例

```python
import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed


API_URL = "ws://localhost:8000/api/v1/im/gateway"
API_KEY = "sk-your-api-key"
SOURCE = "my_bot"

RECONNECT_DELAY = 5       # 初始重连间隔（秒）
MAX_RECONNECT_DELAY = 60  # 最大重连间隔
HEARTBEAT_INTERVAL = 30


class IMBridge:
    def __init__(self):
        self.ws = None
        self._reconnect_delay = RECONNECT_DELAY

    async def connect(self):
        """带重连的连接管理"""
        while True:
            try:
                url = f"{API_URL}?token={API_KEY}&source={SOURCE}"
                async with websockets.connect(url) as ws:
                    self.ws = ws
                    self._reconnect_delay = RECONNECT_DELAY  # 重置延迟
                    print(f"Connected to Metahub")

                    # 并发运行心跳和消息处理
                    await asyncio.gather(
                        self._heartbeat_loop(),
                        self._receive_loop(),
                    )

            except (ConnectionClosed, ConnectionError, OSError) as e:
                print(f"Connection lost: {e}")
                self.ws = None
                print(f"Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, MAX_RECONNECT_DELAY
                )

    async def _heartbeat_loop(self):
        while self.ws:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await self.ws.send(json.dumps({"type": "ping"}))

    async def _receive_loop(self):
        async for raw in self.ws:
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "send_message":
                # 异步处理，不阻塞接收
                asyncio.create_task(self._handle_send(data))
            elif msg_type == "pong":
                pass

    async def _handle_send(self, data: dict):
        """处理发送指令"""
        request_id = data["request_id"]
        try:
            # === 调用 IM 平台 SDK ===
            # await your_sdk.send(data["session_id"], data["message_str"])

            await self.ws.send(json.dumps({
                "type": "result",
                "request_id": request_id,
                "success": True,
                "data": {},
            }))
        except Exception as e:
            await self.ws.send(json.dumps({
                "type": "result",
                "request_id": request_id,
                "success": False,
                "error": str(e),
            }))

    async def send_to_metahub(self, message_data: dict):
        """供 IM 平台回调使用：转发消息到 Metahub"""
        if self.ws:
            await self.ws.send(json.dumps({
                "type": "message",
                "data": message_data,
            }))


if __name__ == "__main__":
    bridge = IMBridge()
    asyncio.run(bridge.connect())
```

## 4. 注意事项

### 与 Webhook 的关系

WebSocket 和 Webhook 可以并存。对于同一个 IM 平台：
- 如果已建立 WebSocket 连接，**推荐**通过 WebSocket 上行消息（更低延迟）
- 如果 WebSocket 断连，可以回退到 Webhook 继续上行消息
- 发送消息（下行）只能通过 WebSocket

### 消息去重

服务端会根据 `message_id` 做去重。如果同一条消息同时通过 WebSocket 和 Webhook 上行，只会处理一次。

### 超时

发送消息（`send_message`）有 30 秒超时。桥接应在超时内回报 result，否则调用方收到 504 错误。

### 连接唯一性

同一个 `(用户, source)` 只允许一个连接。新连接会替换旧连接，旧连接收到 close code `4000`。桥接应处理此情况并停止旧连接的逻辑。

### Close Codes

| Code | 含义 | 桥接应对 |
|------|------|----------|
| 4000 | 被新连接替换 | 停止当前连接逻辑，可能有另一个实例在运行 |
| 4001 | 认证失败 | 检查 token/API Key 是否有效 |
| 1000 | 正常关闭 | 按需重连 |
| 1006 | 异常断开 | 自动重连 |
