# 测试指南

## 测试前准备

### 1. 安装依赖

```bash
pip install websockets
# 或
uv pip install websockets
```

### 2. 准备配置

确保有以下信息：
- MetaHub Base URL (如 `https://app.tensorix.org/api/v1`)
- 有效的 API Key (格式 `sk-xxx`)

## 测试步骤

### 阶段 1: 独立测试（可选）

在集成到 AstrBot 之前，可以先测试 WebSocket 基本功能：

1. 编辑 `test_websocket.py`，填入配置：
   ```python
   BASE_URL = "https://app.tensorix.org/api/v1"
   API_KEY = "your-api-key-here"
   SOURCE = "astr_test"
   ```

2. 运行测试：
   ```bash
   python test_websocket.py
   ```

3. 预期输出：
   ```
   正在测试 WebSocket 连接...
   ✓ WebSocket 连接成功!
   正在发送测试消息...
   ✓ 消息发送成功!
   保持连接 30 秒以测试心跳和接收消息...
   ```

### 阶段 2: AstrBot 集成测试

1. **加载插件**
   - 在 AstrBot 中加载本插件
   - 配置 `base_url` 和 `api_key`

2. **检查初始化**

   查看日志，应该看到：
   ```
   🔌 正在建立 WebSocket 连接 (source=astr_default)...
   正在连接到 MetaHub WebSocket: wss://...
   已连接到 MetaHub (source: astr_default)
   ✅ WebSocket 连接成功建立并已测试可用
   📡 当前使用 WebSocket 模式 (source=astr_default)
   ```

   如果连接失败，会看到：
   ```
   🔌 正在建立 WebSocket 连接 (source=astr_default)...
   ❌ WebSocket 连接建立超时（5秒）
   ⚠️  将使用 Webhook 模式作为备选方案
   ```

3. **测试上行消息**

   a. 向机器人发送一条消息（任意内容）

   b. 查看日志，应该看到：
   ```
   📤 [WebSocket] 发送上行消息: session_id=xxx, message_id=yyy
   📤 [WebSocket] 发送消息成功: session_id=xxx, msg_id=yyy
   ```

   如果 source 发生变化，会看到：
   ```
   🔄 检测到 source 变更: astr_default → astr_qq，重建连接...
   🔌 为 source=astr_qq 建立新的 WebSocket 连接...
   ✅ WebSocket 连接已建立 (source=astr_qq)
   ```

   c. 在 MetaHub 后台确认收到消息

4. **测试心跳**

   保持连接，每 30 秒应该看到（debug 级别）：
   ```
   💓 发送心跳 ping
   💓 收到心跳 pong
   ```

5. **测试下行消息**

   a. 从 MetaHub 发送消息到机器人

   b. 查看日志，应该看到：
   ```
   📥 [WebSocket] 收到下行消息: type=send_message, request_id=xxx
   📥 [下行消息] 处理中: request_id=xxx, session_id=yyy, message_str='Hello...'
   📥 [下行消息] 发送成功: session_id=yyy, message_str='Hello...'
   ✅ [下行消息] 发送成功: request_id=xxx, session_id=yyy
   ```

   c. 在 IM 平台确认收到消息

### 阶段 3: Fallback 测试

1. **测试 WebSocket 失败降级**
   
   a. 断开网络或停止 MetaHub 服务
   
   b. 向机器人发送消息

   c. 查看日志，应该看到：
   ```
   ⚠️  WebSocket 发送失败，降级到 Webhook。原因: WebSocket 未连接
   📤 [Webhook] 发送消息成功: session_id=xxx, msg_id=yyy
   ```

2. **测试自动重连**
   
   a. 恢复网络或启动 MetaHub 服务
   
   b. 查看日志，应该看到：
   ```
   WebSocket 连接断开: ...
   将在 X 秒后重连...
   正在连接到 MetaHub WebSocket: ...
   已连接到 MetaHub (source: ...)
   ```

### 阶段 4: 稳定性测试

1. **长时间运行**
   - 保持插件运行 1-2 小时
   - 定期发送消息
   - 观察是否有异常

2. **高频消息**
   - 快速连续发送多条消息
   - 观察是否都能正常处理

3. **重启测试**
   - 重启 AstrBot
   - 重启 MetaHub 服务
   - 观察重连是否正常

## 检查清单

### ✅ 基本功能

- [ ] WebSocket 连接成功
- [ ] 心跳正常工作
- [ ] 上行消息发送成功
- [ ] 下行消息接收成功
- [ ] 消息内容正确

### ✅ 消息组件

- [ ] 纯文本消息
- [ ] 图片消息
- [ ] At 消息
- [ ] 混合消息

### ✅ 高级功能

- [ ] 自动重连
- [ ] Fallback 到 Webhook
- [ ] 优雅关闭
- [ ] 多平台支持（如果有）

### ✅ 边界情况

- [ ] 网络断开恢复
- [ ] 服务重启
- [ ] 无效配置
- [ ] 异常消息格式

## 常见问题

### Q: 连接失败，显示 4001 错误

A: API Key 无效或过期，请检查配置。

### Q: 连接成功但无法发送消息

A: 检查消息格式是否正确，查看详细错误日志。

### Q: 下行消息无法接收

A: 
1. 确认 WebSocket 连接正常
2. 检查 `unified_msg_origin` 是否正确
3. 查看 MetaHub 后台是否有错误

### Q: 频繁重连

A: 
1. 检查网络稳定性
2. 检查 MetaHub 服务状态
3. 查看详细错误日志

### Q: Fallback 不工作

A: 
1. 确认 Webhook 配置正确
2. 检查 `metahub.py` 是否正常
3. 查看错误日志

## 日志分析

### 正常日志示例

```
[INFO] 🔌 正在建立 WebSocket 连接 (source=astr_default)...
[INFO] 正在连接到 MetaHub WebSocket: wss://app.tensorix.org/api/v1/im/gateway
[INFO] 已连接到 MetaHub (source: astr_default)
[INFO] ✅ WebSocket 连接成功建立并已测试可用
[INFO] 📡 当前使用 WebSocket 模式 (source=astr_default)
[DEBUG] 💓 发送心跳 ping
[DEBUG] 💓 收到心跳 pong
[INFO] 📤 [WebSocket] 发送上行消息: session_id=platform_qq_group_12345, message_id=msg_123
[INFO] 📤 [WebSocket] 发送消息成功: session_id=platform_qq_group_12345, msg_id=msg_123
[INFO] 📥 [WebSocket] 收到下行消息: type=send_message, request_id=550e8400-...
[INFO] 📥 [下行消息] 处理中: request_id=550e8400-..., session_id=platform_qq_group_12345, message_str='Hello...'
[INFO] 📥 [下行消息] 发送成功: session_id=platform_qq_group_12345, message_str='Hello...'
[INFO] ✅ [下行消息] 发送成功: request_id=550e8400-..., session_id=platform_qq_group_12345
```

### 异常日志示例

```
[WARNING] WebSocket 连接断开: Connection closed
[INFO] 将在 5 秒后重连...
[WARNING] ⚠️  WebSocket 发送失败，降级到 Webhook。原因: WebSocket 未连接
[INFO] 📤 [Webhook] 发送消息成功: session_id=platform_qq_group_12345, msg_id=msg_123
[ERROR] ❌ Webhook 发送也失败: [详细错误信息]
```

## 性能指标

记录以下指标以评估性能：

- **连接建立时间**: 从启动到连接成功的时间
- **消息延迟**: 从发送到接收的时间
- **重连时间**: 断开后重新连接的时间
- **内存使用**: 长时间运行的内存占用
- **CPU 使用**: 正常运行时的 CPU 占用

## 测试报告模板

```markdown
# MetaHub WebSocket 测试报告

## 测试环境
- AstrBot 版本: 
- Python 版本: 
- 操作系统: 
- MetaHub URL: 
- IM 平台: 

## 测试结果

### 基本功能
- WebSocket 连接: ✅/❌
- 心跳保活: ✅/❌
- 上行消息: ✅/❌
- 下行消息: ✅/❌

### 高级功能
- 自动重连: ✅/❌
- Fallback: ✅/❌
- 多平台: ✅/❌

### 性能指标
- 连接建立时间: X 秒
- 平均消息延迟: X 毫秒
- 重连时间: X 秒
- 内存使用: X MB
- CPU 使用: X%

## 问题和建议

[记录发现的问题和改进建议]

## 总结

[总体评价]
```

## 下一步

测试完成后：

1. 填写测试报告
2. 记录发现的问题
3. 提出改进建议
4. 更新文档（如需要）

如有问题，请参考：
- `WEBSOCKET_IMPLEMENTATION.md` - 详细实现文档
- `IMPLEMENTATION_SUMMARY.md` - 实施总结
- `docs/WS_IMPL_GUIDE.md` - WebSocket 规范
