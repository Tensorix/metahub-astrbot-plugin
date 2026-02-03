# MetaHub AstrBot 插件

MetaHub 集成插件，支持通过 WebSocket 和 Webhook 与 MetaHub 服务进行双向通信。

## 特性

- ✅ **WebSocket 长连接**: 与 MetaHub 保持持久双向连接
- ✅ **自动重连**: 连接断开后自动重连（指数退避策略）
- ✅ **心跳保活**: 每 30 秒自动发送心跳
- ✅ **双向消息**: 支持上行（AstrBot → MetaHub）和下行（MetaHub → AstrBot）
- ✅ **Fallback 机制**: WebSocket 失败时自动降级到 Webhook
- ✅ **多平台支持**: 自动识别 IM 平台（QQ、微信、Telegram 等）

## 快速开始

### 1. 安装依赖

```bash
pip install websockets
```

### 2. 配置插件

在 AstrBot 插件配置中设置：

```json
{
    "base_url": "https://app.tensorix.org/api/v1",
    "api_key": "sk-your-api-key-here"
}
```

### 3. 启动使用

加载插件后，发送第一条消息即可自动建立 WebSocket 连接。

详细使用说明请参考 [快速开始指南](QUICKSTART.md)。

## 文档

- [快速开始](QUICKSTART.md) - 安装和配置指南
- [实施总结](IMPLEMENTATION_SUMMARY.md) - 实现概述和关键设计
- [详细文档](WEBSOCKET_IMPLEMENTATION.md) - 完整的实现文档
- [WebSocket 规范](docs/WS_IMPL_GUIDE.md) - MetaHub WebSocket 接入规范

## 架构

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

## 支持

- [AstrBot 帮助文档](https://astrbot.app)
- [MetaHub 文档](https://tensorix.org)
