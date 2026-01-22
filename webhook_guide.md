# 第三方插件 Webhook 集成指南

本文档旨在指导第三方开发者（如 AstrBot 插件开发者）如何将 IM 消息推送到 MetaHub 系统。MetaHub 接收消息后，会利用 AI 智能分析消息内容，自动识别重要事项并创建 Activity。

## 1. 接口概览

- **接口地址**: `POST /api/v1/webhooks/im/message`
- **请求方式**: POST
- **Content-Type**: `application/json`

## 2. 认证方式

接口支持 Bearer Token 认证。请使用 `sk-` 开头的 API Key。

**Header 示例**:
```http
Authorization: Bearer sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> API Key 需要在 MetaHub 系统中生成并分发给插件配置。

## 3. 请求数据结构

请求体必须是一个 JSON 对象，严格遵循以下结构：

| 字段名 | 类型 | 必填 | 描述 | 示例值 |
| :--- | :--- | :--- | :--- | :--- |
| `timestamp` | integer | 是 | 消息时间戳（秒级） | `1705912345` |
| `session_id` | string | 是 | 会话唯一标识（私聊为对方ID，群聊为群ID） | `"123456"` |
| `message_id` | string | 是 | 消息唯一标识 | `"msg_789"` |
| `session_type` | string | 是 | 会话类型 | `"pm"`, `"group"` |
| `source` | string | 是 | 消息来源标识 | `"astr_qq"`, `"astr_wechat"` |
| `self_id` | string | 是 | 机器人自身ID | `"bot_1001"` |
| `sender` | object | 是 | 发送者信息 | `{"user_id": "u1", "nickname": "N"}` |
| `group` | object | 否 | 群组信息（仅群聊时需要） | `{"group_id": "g1", "group_name": "G"}` |
| `message_str` | string | 是 | 消息纯文本内容（用于快速预览） | `"你好"` |
| `message` | array | 是 | 消息链（结构化内容） | `[{"type": "text", "text": "你好"}]` |
| `raw_message` | any | 否 | 原始消息对象（可选，用于调试） | `{...}` |

### 3.1 关键字段详解

#### message (消息链)
数组中的每个元素代表消息的一个片段。支持以下类型：

*   **文本 (text)**
    ```json
    {"type": "text", "text": "明天开会"}
    ```
*   **图片 (image)**
    ```json
    {"type": "image", "file": "https://example.com/img.jpg"}
    ```
*   **提及 (at)**
    ```json
    {"type": "at", "qq": "123456", "name": "张三"}
    ```
    *(注：字段名 `qq` 也可以是 `user_id`)*
*   **链接 (url)**
    ```json
    {"type": "url", "url": "https://google.com"}
    ```
*   **JSON**
    ```json
    {"type": "json", "data": {...}}
    ```

## 4. 完整请求示例

### 示例 1：群聊消息

```json
{
  "timestamp": 1705912345,
  "session_id": "group_888888",
  "message_id": "msg_123456789",
  "session_type": "group",
  "source": "astr_qq",
  "self_id": "bot_1001",
  "sender": {
    "user_id": "user_999",
    "nickname": "Alice"
  },
  "group": {
    "group_id": "group_888888",
    "group_name": "产品研发群"
  },
  "message_str": "@Bob 请整理一下今天的会议记录",
  "message": [
    {
      "type": "at",
      "qq": "user_777",
      "name": "Bob"
    },
    {
      "type": "text",
      "text": " 请整理一下今天的会议记录"
    }
  ],
  "raw_message": {
    "original_field": "debug_info"
  }
}
```

### 示例 2：私聊消息

```json
{
  "timestamp": 1705912400,
  "session_id": "user_999",
  "message_id": "msg_987654321",
  "session_type": "pm",
  "source": "astr_wechat",
  "self_id": "bot_1001",
  "sender": {
    "user_id": "user_999",
    "nickname": "Alice"
  },
  "message_str": "帮我定一个明天早上9点的闹钟",
  "message": [
    {
      "type": "text",
      "text": "帮我定一个明天早上9点的闹钟"
    }
  ]
}
```

## 5. 响应说明

接口为**异步处理**。

- **状态码**: `202 Accepted`
- **响应体**:
  ```json
  {
    "status": "accepted",
    "message": "消息已接收，正在后台处理"
  }
  ```

服务器收到请求后会立即返回 202，并在后台进行 AI 分析。如果分析结果判定为重要消息，系统将自动创建 Activity。
