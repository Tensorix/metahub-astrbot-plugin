# 快速开始指南

## 安装依赖

```bash
# 使用 pip
pip install websockets

# 或使用 uv
uv pip install websockets
```

## 配置插件

在 AstrBot 插件配置中设置：

```json
{
    "base_url": "https://app.tensorix.org/api/v1",
    "api_key": "sk-your-api-key-here"
}
```

## 启动插件

1. 在 AstrBot 中加载插件
2. 插件会自动初始化
3. 发送第一条消息时会自动建立 WebSocket 连接

## 验证连接

查看日志，应该看到：

```
MetaHub 插件初始化完成，等待首条消息以建立 WebSocket 连接
已为 source=astr_qq 启动 WebSocket 连接
正在连接到 MetaHub WebSocket: wss://...
已连接到 MetaHub (source: astr_qq)
```

## 测试上行消息

1. 向机器人发送消息
2. 查看日志确认消息已发送：
   ```
   通过 WebSocket 发送消息: <session_id>
   ```

## 测试下行消息

1. 从 MetaHub 发送消息到机器人
2. 查看日志确认收到指令：
   ```
   收到发送消息指令: request_id=..., session_id=...
   已发送消息到 session_id=...
   消息发送成功: request_id=...
   ```

## 测试 Fallback

1. 停止 MetaHub 服务或断开网络
2. 发送消息，应该看到：
   ```
   WebSocket 发送失败，降级到 Webhook
   通过 Webhook 发送消息: <session_id>
   ```

## 常见问题

### Q: WebSocket 无法连接？

A: 检查：
- `base_url` 是否正确
- `api_key` 是否有效
- 网络连接是否正常
- 防火墙是否阻止 WebSocket 连接

### Q: 消息发送失败？

A: 查看日志中的详细错误信息，可能原因：
- WebSocket 未连接（会自动降级到 Webhook）
- 消息格式错误
- MetaHub 服务异常

### Q: 下行消息无法接收？

A: 检查：
- WebSocket 连接是否正常
- `unified_msg_origin` 是否正确
- AstrBot 的 `send_message` API 是否正常

## 更多信息

- 详细实现文档: `WEBSOCKET_IMPLEMENTATION.md`
- 实施总结: `IMPLEMENTATION_SUMMARY.md`
- WebSocket 规范: `docs/WS_IMPL_GUIDE.md`
