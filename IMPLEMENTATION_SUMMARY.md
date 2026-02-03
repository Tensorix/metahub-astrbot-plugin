# MetaHub WebSocket 实施总结

## 实施完成 ✓

已成功实现 MetaHub 的 WebSocket 接入方式，同时保留原有 Webhook 作为 fallback。

## 新增文件

1. **metahub_ws.py** - WebSocket 客户端核心实现
   - 自动连接和重连（指数退避）
   - 心跳保活（30秒间隔）
   - 双向消息处理
   - 优雅关闭

2. **test_websocket.py** - 独立测试脚本
   - 用于验证 WebSocket 基本功能
   - 模拟消息发送和接收

3. **WEBSOCKET_IMPLEMENTATION.md** - 详细实现文档
   - 架构设计说明
   - 使用指南
   - 故障排查

4. **IMPLEMENTATION_SUMMARY.md** - 本文件

## 修改文件

1. **main.py** - 集成 WebSocket 功能
   - 添加 WebSocket 客户端初始化
   - 实现下行消息处理（MetaHub → AstrBot）
   - 优先使用 WebSocket，失败降级到 Webhook
   - 使用 `unified_msg_origin` 作为 `session_id`
   - 动态获取 `source` 参数
   - 优雅关闭连接

## 核心特性

### 1. 双向通信

- **上行（AstrBot → MetaHub）**
  - 接收所有消息事件
  - 转换消息组件格式
  - 通过 WebSocket 发送到 MetaHub
  - 失败时自动降级到 Webhook

- **下行（MetaHub → AstrBot）**
  - 接收 `send_message` 指令
  - 解析消息组件
  - 通过 `context.send_message()` 发送
  - 回报发送结果

### 2. 连接管理

- 首次收到消息时自动建立连接
- 连接断开后自动重连（5秒起始，最大60秒）
- 每30秒发送心跳保持连接
- 插件卸载时优雅关闭

### 3. Fallback 机制

- WebSocket 未连接 → 使用 Webhook
- WebSocket 发送失败 → 降级到 Webhook
- 确保消息不丢失

## 关键设计决策

### 1. session_id 使用 unified_msg_origin

```python
# 上行
payload["session_id"] = event.unified_msg_origin

# 下行
await self.context.send_message(unified_msg_origin, message_chain)
```

**原因**: `unified_msg_origin` 是 AstrBot 的标准会话标识，能够跨平台唯一标识会话。

### 2. source 动态获取

```python
source = f"astr_{event.get_platform_name()}"
```

**原因**: 支持多平台（QQ、微信、Telegram等），无需硬编码。

### 3. 延迟初始化 WebSocket

在 `initialize()` 中不立即创建连接，而是等待首条消息。

**原因**: 
- 需要从消息事件中获取 `source`
- 避免无消息时的无效连接

### 4. 单一 source 连接

当前每个 source 只维护一个 WebSocket 连接。

**原因**: 
- 符合 MetaHub 的连接规则（每个 user+source 一个连接）
- 简化实现

**未来改进**: 如果需要支持多个平台同时运行，可以维护多个连接。

## 测试建议

### 1. 基本功能测试

```bash
# 修改 test_websocket.py 中的配置
python test_websocket.py
```

### 2. 集成测试

1. 在 AstrBot 中安装插件
2. 配置 `base_url` 和 `api_key`
3. 发送消息到机器人，观察日志
4. 从 MetaHub 发送消息，验证下行功能

### 3. Fallback 测试

1. 断开网络连接
2. 发送消息，应该看到降级到 Webhook
3. 恢复网络，应该自动重连

### 4. 重连测试

1. 启动插件，建立连接
2. 重启 MetaHub 服务
3. 观察插件是否自动重连

## 日志关键字

监控以下日志确认功能正常：

- ✓ `MetaHub 插件初始化完成`
- ✓ `已为 source=xxx 启动 WebSocket 连接`
- ✓ `已连接到 MetaHub`
- ✓ `通过 WebSocket 发送消息`
- ✓ `收到发送消息指令`
- ✓ `已发送消息到 session_id`
- ⚠️ `WebSocket 发送失败，降级到 Webhook`
- ⚠️ `WebSocket 连接断开`
- ⚠️ `将在 X 秒后重连`

## 配置要求

在 AstrBot 插件配置中设置：

```json
{
    "base_url": "https://app.tensorix.org/api/v1",
    "api_key": "sk-your-api-key-here"
}
```

- `base_url` 会自动转换为 WebSocket URL（wss://）
- `api_key` 推荐使用 `sk-xxx` 格式（无需处理过期）

## 依赖项

确保安装了以下 Python 包：

```bash
pip install websockets
```

或使用 uv：

```bash
uv pip install websockets
```

## 与文档的符合性

实现完全符合 `docs/WS_IMPL_GUIDE.md` 规范：

- ✓ WebSocket 端点格式
- ✓ 认证方式（API Key）
- ✓ 心跳协议（ping/pong）
- ✓ 上行消息格式
- ✓ 下行消息处理
- ✓ 结果回报
- ✓ 重连机制
- ✓ Close Codes 处理

## 已知限制

1. **单平台支持**: 当前假设插件只连接一个 IM 平台，如果需要同时支持多个平台，需要维护多个 WebSocket 连接。

2. **消息缓存**: 在 WebSocket 断连期间，消息会立即降级到 Webhook，不会缓存等待重连。

3. **at 组件**: 下行消息中的 at 组件简化为文本，可能需要根据 AstrBot API 进一步优化。

## 下一步

1. **测试**: 在实际环境中测试所有功能
2. **监控**: 观察连接稳定性和消息延迟
3. **优化**: 根据测试结果调整参数（心跳间隔、重连策略等）
4. **扩展**: 根据需求添加更多消息组件支持

## 问题反馈

如有问题，请检查：

1. 日志中的错误信息
2. WebSocket 连接状态
3. MetaHub 服务端状态
4. 网络连接和防火墙设置

详细故障排查请参考 `WEBSOCKET_IMPLEMENTATION.md`。
