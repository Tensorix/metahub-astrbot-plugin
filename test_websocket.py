"""
简单的 WebSocket 测试脚本
用于验证 MetaHub WebSocket 连接功能
"""
import asyncio
import json
from metahub_ws import MetaHubWebSocket


async def mock_send_message_handler(data: dict) -> dict:
    """模拟处理发送消息指令"""
    print(f"[模拟] 收到发送消息指令:")
    print(f"  session_id: {data.get('session_id')}")
    print(f"  message_str: {data.get('message_str')}")
    print(f"  message: {data.get('message')}")
    
    # 模拟成功发送
    return {
        "success": True,
        "data": {"message_id": "test_msg_001"}
    }


async def test_websocket():
    """测试 WebSocket 连接"""
    # 配置（请替换为实际的配置）
    BASE_URL = "https://app.tensorix.org/api/v1"
    API_KEY = "your-api-key-here"  # 替换为实际的 API Key
    SOURCE = "astr_test"
    
    print(f"正在测试 WebSocket 连接...")
    print(f"BASE_URL: {BASE_URL}")
    print(f"SOURCE: {SOURCE}")
    print()
    
    # 创建 WebSocket 客户端
    ws_client = MetaHubWebSocket(
        base_url=BASE_URL,
        api_key=API_KEY,
        source=SOURCE,
        on_send_message=mock_send_message_handler
    )
    
    # 启动连接
    await ws_client.start()
    
    # 等待连接建立
    await asyncio.sleep(2)
    
    if ws_client.is_connected:
        print("✓ WebSocket 连接成功!")
        print()
        
        # 测试发送消息
        test_message = {
            "timestamp": 1706000000,
            "session_id": "test_session_001",
            "message_id": "test_msg_001",
            "session_type": "pm",
            "source": SOURCE,
            "sender": {
                "nickname": "测试用户",
                "user_id": "test_user_001"
            },
            "self_id": "bot_001",
            "message_str": "这是一条测试消息",
            "message": [
                {"type": "text", "text": "这是一条测试消息"}
            ]
        }
        
        print("正在发送测试消息...")
        success = await ws_client.send_message(test_message)
        if success:
            print("✓ 消息发送成功!")
        else:
            print("✗ 消息发送失败")
        
        print()
        print("保持连接 30 秒以测试心跳和接收消息...")
        print("(如果 MetaHub 发送消息指令，将会触发 mock_send_message_handler)")
        await asyncio.sleep(30)
    else:
        print("✗ WebSocket 连接失败")
    
    # 停止连接
    print()
    print("正在关闭连接...")
    await ws_client.stop()
    print("✓ 连接已关闭")


if __name__ == "__main__":
    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
