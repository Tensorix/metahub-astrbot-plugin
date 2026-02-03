# 更新日志

## [未发布] - 2026-01-29

### 新增

- **WebSocket 支持**: 实现了与 MetaHub 的 WebSocket 长连接
  - 自动连接和重连机制（指数退避策略）
  - 心跳保活（30秒间隔）
  - 双向消息传递（上行和下行）
  - 优雅关闭连接

- **新文件**:
  - `metahub_ws.py`: WebSocket 客户端核心实现
  - `test_websocket.py`: 独立测试脚本
  - `WEBSOCKET_IMPLEMENTATION.md`: 详细实现文档
  - `IMPLEMENTATION_SUMMARY.md`: 实施总结
  - `QUICKSTART.md`: 快速开始指南
  - `CHANGELOG.md`: 本文件

### 修改

- **main.py**: 集成 WebSocket 功能
  - 添加 `initialize()` 方法进行异步初始化
  - 添加 `_ensure_websocket()` 方法管理连接
  - 添加 `_handle_metahub_send_message()` 处理下行消息
  - 修改 `on_all_message()` 优先使用 WebSocket
  - 修改 `terminate()` 优雅关闭连接
  - 使用 `unified_msg_origin` 作为 `session_id`
  - 动态获取 `source` 参数

- **README.md**: 更新项目说明
  - 添加特性列表
  - 添加快速开始指南
  - 添加架构图
  - 添加文档链接

### 保留

- **metahub.py**: 保留原有 Webhook 实现作为 fallback
- **配置文件**: 保持向后兼容，无需修改配置

### 技术细节

#### 上行消息（AstrBot → MetaHub）

- 优先通过 WebSocket 发送
- 失败时自动降级到 Webhook
- 使用 `unified_msg_origin` 作为 `session_id`

#### 下行消息（MetaHub → AstrBot）

- 接收 `send_message` 指令
- 解析消息组件（text, image, at）
- 通过 `context.send_message()` 发送
- 回报发送结果

#### 连接管理

- 首次收到消息时自动建立连接
- 连接断开后自动重连（5秒起始，最大60秒）
- 每30秒发送心跳保持连接
- 插件卸载时优雅关闭

#### Fallback 机制

- WebSocket 未连接 → 使用 Webhook
- WebSocket 发送失败 → 降级到 Webhook
- 确保消息不丢失

### 依赖

新增依赖：
- `websockets`: WebSocket 客户端库

### 测试

- 添加独立测试脚本 `test_websocket.py`
- 支持基本功能测试
- 支持集成测试

### 文档

- 完整的实现文档
- 快速开始指南
- 故障排查指南
- 与 MetaHub WebSocket 规范完全符合

### 已知限制

1. 当前假设插件只连接一个 IM 平台
2. WebSocket 断连期间消息立即降级，不缓存
3. at 组件简化为文本处理

### 未来计划

1. 支持多平台同时连接
2. 消息队列和缓存机制
3. 性能监控和指标
4. 更丰富的消息组件支持
5. 可配置的连接参数

---

## [0.0.1] - 之前

### 初始版本

- 基于 Webhook 的 MetaHub 集成
- 支持上行消息（AstrBot → MetaHub）
- 基本的消息组件转换
