# MetaHub WebSocket 实现说明

## 概述

本插件现在支持通过 WebSocket 与 MetaHub 建立持久双向连接，同时保留原有的 Webhook 方式作为 fallback。

## 架构设计

### 文件结构

- `metahub_ws.py`: WebSocket 客户端实现
- `metahub.py`: 原有的 Webhook 客户端（fallback）
- `main.py`: 插件主逻辑，集成 WebSocket 和 Webhook

### 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                        AstrBot 插件                          │
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │  WebSocket   │ 优先    │   Webhook    │ Fallback        │
│  │   客户端     │────────>│   客户端     │                 │
│  └──────────────┘         └──────────────┘                 │
│         ↕                                                    │
│    双向通信                                                  │
└─────────────────────────────────────────────────────────────┘
         ↕
    WebSocket 长连接
         ↕
┌─────────────────────────────────────────────────────────────┐
│                    MetaHub Server                            │
└─────────────────────────────────────────────────────────────┘
```

## 主要特性

### 1. WebSocket 连接管理

- **自动连接**: 收到第一条消息时自动建立连接
- **自动重连**: 连接断开后自动重连（指数退避策略）
- **心跳保活**: 每 30 秒发送 ping 保持连接
- **优雅关闭**: 插件卸载时正确关闭连接

### 2. 双向消息传递

#### 上行（AstrBot → MetaHub）

- 接收 AstrBot 的所有消息事件
- 使用 `unified_msg_origin` 作为 `session_id`
- 优先通过 WebSocket 发送，失败则降级到 Webhook

#### 下行（MetaHub → AstrBot）

- 接收 MetaHub 的 `send_message` 指令
- 解析消息组件（text, image, at 等）
- 通过 `context.send_message()` 发送到对应会话
- 回报发送结果（成功/失败）

### 3. Fallback 机制

当 WebSocket 不可用时，自动降级到 Webhook：

1. WebSocket 未连接
2. WebSocket 发送失败
3. 连接建立过程中

## 配置说明

配置文件：`_conf_schema.json`

```json
{   
    "base_url": {
        "description": "MetaHub Base URL",
        "type": "string",
        "default": "https://app.tensorix.org/api/v1"
    },
    "api_key": {
        "description": "MetaHub API Key",
        "type": "string"
    }
}
```

- `base_url`: MetaHub 服务地址（自动转换为 WebSocket URL）
- `api_key`: API Key（推荐使用 `sk-xxx` 格式）

## 关键实现细节

### 1. session_id 映射

使用 `unified_msg_origin` 作为 `session_id`：

```python
# 上行消息
payload = {
    "session_id": event.unified_msg_origin,  # 使用 unified_msg_origin
    ...
}

# 下行消息
await self.context.send_message(
    session_id,  # 这是 unified_msg_origin
    message_chain
)
```

### 2. source 动态获取

```python
source = f"astr_{event.get_platform_name()}"
```

根据平台名称动态生成，如：
- `astr_qq`
- `astr_wechat`
- `astr_telegram`

### 3. 消息组件转换

#### 上行（AstrBot → MetaHub）

```python
# Plain -> text
{"type": "text", "text": "..."}

# At -> at
{"type": "at", "qq": "...", "name": "..."}

# Image -> image
{"type": "image", "file": "..."}
```

#### 下行（MetaHub → AstrBot）

```python
# text -> MessageChain.message()
message_chain.message(text)

# image -> MessageChain.image()
message_chain.image(url)

# at -> 简化为文本
message_chain.message(f"@{name} ")
```

### 4. 重连策略

- 初始延迟: 5 秒
- 最大延迟: 60 秒
- 策略: 指数退避（每次失败延迟翻倍）
- 成功连接后重置延迟

### 5. 错误处理

- WebSocket 连接错误 → 自动重连
- 消息发送失败 → 降级到 Webhook
- 下行消息处理失败 → 回报错误给 MetaHub
- 所有异常都有详细日志

## 测试

### 单元测试

运行 `test_websocket.py` 进行基本功能测试：

```bash
python test_websocket.py
```

需要先配置：
- `BASE_URL`: MetaHub 服务地址
- `API_KEY`: 有效的 API Key
- `SOURCE`: 测试用的 source 标识

### 集成测试

1. 在 AstrBot 中安装插件
2. 配置 `base_url` 和 `api_key`
3. 发送消息到机器人
4. 检查日志确认 WebSocket 连接状态
5. 从 MetaHub 发送消息测试下行功能

## 日志说明

### 正常运行日志

```
MetaHub 插件初始化完成，等待首条消息以建立 WebSocket 连接
已为 source=astr_qq 启动 WebSocket 连接
正在连接到 MetaHub WebSocket: wss://app.tensorix.org/api/v1/im/gateway
已连接到 MetaHub (source: astr_qq)
发送心跳 ping
收到心跳 pong
通过 WebSocket 发送消息: <unified_msg_origin>
```

### 错误和 Fallback 日志

```
WebSocket 连接断开: ...
将在 5 秒后重连...
WebSocket 发送失败，降级到 Webhook
通过 Webhook 发送消息: <unified_msg_origin>
```

### 下行消息日志

```
收到发送消息指令: request_id=..., session_id=...
已发送消息到 session_id=...
消息发送成功: request_id=...
```

## 与文档的对应关系

实现严格遵循 `docs/WS_IMPL_GUIDE.md` 中的规范：

- ✓ WebSocket 端点和认证
- ✓ 心跳保活（ping/pong）
- ✓ 上行消息格式
- ✓ 下行消息处理
- ✓ 结果回报
- ✓ 重连机制
- ✓ Close Codes 处理
- ✓ 消息去重（通过 message_id）

## 未来改进

1. **多平台支持**: 当前每个 source 一个连接，未来可能需要支持多个平台同时连接
2. **消息队列**: 在 WebSocket 断连期间缓存消息，重连后发送
3. **性能监控**: 添加连接状态、消息延迟等监控指标
4. **更丰富的消息组件**: 支持更多 AstrBot 和 MetaHub 的消息类型
5. **配置优化**: 支持自定义心跳间隔、重连策略等参数

## 故障排查

### WebSocket 无法连接

1. 检查 `base_url` 是否正确
2. 检查 `api_key` 是否有效
3. 检查网络连接和防火墙设置
4. 查看日志中的详细错误信息

### 消息发送失败

1. 检查 WebSocket 连接状态
2. 查看是否降级到 Webhook
3. 检查消息格式是否正确
4. 查看 MetaHub 服务端日志

### 下行消息无法发送

1. 检查 `unified_msg_origin` 是否正确
2. 检查 AstrBot 的 `send_message` API 是否正常
3. 查看消息组件转换是否正确
4. 检查目标会话是否存在

## 贡献

欢迎提交 Issue 和 Pull Request！
