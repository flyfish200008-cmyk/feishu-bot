"""
飞书机器人 - 热点文案生成助手（本地部署版本）
接收飞书消息，调用工作流API生成文案
"""

import os
import json
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = FastAPI()

# 配置
WORKFLOW_API_URL = "https://xqzxthj2vk.coze.site/run"
WORKFLOW_API_TOKEN = os.getenv("WORKFLOW_API_TOKEN")
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")

print("=" * 50)
print("飞书机器人启动中...")
print(f"WORKFLOW_API_URL: {WORKFLOW_API_URL}")
print(f"FEISHU_APP_ID: {FEISHU_APP_ID}")
print("=" * 50)


def get_feishu_access_token():
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }

    response = requests.post(url, json=payload)
    result = response.json()

    if result.get("code") == 0:
        return result.get("app_access_token")
    else:
        raise Exception(f"获取飞书Token失败: {result}")


def send_feishu_message(chat_id, text):
    """发送消息到飞书"""
    access_token = get_feishu_access_token()

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }

    response = requests.post(url, headers=headers, json=payload)
    result = response.json()

    if result.get("code") != 0:
        raise Exception(f"发送消息失败: {result}")

    return result


def call_workflow_api(ip_direction):
    """调用工作流API生成文案"""
    url = WORKFLOW_API_URL
    headers = {
        "Authorization": f"Bearer {WORKFLOW_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "ip_direction": ip_direction
    }

    try:
        print(f"调用工作流API: ip_direction={ip_direction}")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        result = response.json()

        if "error" in result:
            raise Exception(f"工作流API错误: {result}")

        print(f"工作流API响应成功")
        return result

    except requests.exceptions.Timeout:
        raise Exception("工作流API调用超时")
    except Exception as e:
        raise Exception(f"调用工作流失败: {str(e)}")


def extract_ip_direction(text):
    """从消息中提取IP定位方向"""
    text_lower = text.lower()

    if "ai实战" in text_lower or "ai" in text_lower:
        return "AI实战"
    elif "it网络" in text_lower or "it" in text_lower or "网络" in text_lower:
        return "IT网络"
    else:
        # 默认返回AI实战
        return "AI实战"


def format_reply_message(result):
    """格式化回复消息"""
    if "error" in result:
        return f"❌ 生成失败：{result.get('error', '未知错误')}"

    selected_topic = result.get("selected_topic", "未知选题")
    generated_content = result.get("generated_content", "")
    generated_image_url = result.get("generated_image_url", "")

    message = f"📢 热点文案已生成！\n\n"
    message += f"📌 选题：{selected_topic}\n\n"
    message += f"📄 文案：\n{generated_content}\n\n"

    if generated_image_url:
        message += f"🖼️ 配图：{generated_image_url}\n\n"

    message += "💡 再来一个？直接@我即可！"

    return message


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "app_id": FEISHU_APP_ID,
        "workflow_api": WORKFLOW_API_URL
    }


@app.post("/webhook")
async def webhook(request: Request):
    """飞书Webhook接收端点"""
    try:
        # 获取请求体
        data = await request.json()

        print(f"收到飞书事件: {data.get('header', {}).get('event_type', 'unknown')}")
        print(f"完整请求体: {json.dumps(data, ensure_ascii=False)}")
        # 处理飞书URL验证
        if "challenge" in data:
            print(f"处理URL验证: challenge={data['challenge']}")
            return {"challenge": data["challenge"]}

        # 处理消息事件
        header = data.get("header", {})
        event_type = header.get("event_type", "")

        if event_type == "im.message.receive_v1":
            event = data.get("event", {})
            message = event.get("message", {})
            content = json.loads(message.get("content", "{}"))
            chat_id = message.get("chat_id", "")

            # 获取消息文本
            text = content.get("text", "")
            print(f"收到消息: text={text}, chat_id={chat_id}")

            # 检查是否@机器人
            if "@_user_" in text:
                print("检测到@机器人，开始处理...")
                # 提取IP定位方向
                ip_direction = extract_ip_direction(text)
                print(f"提取IP定位方向: {ip_direction}")

                # 调用工作流API
                result = call_workflow_api(ip_direction)

                # 格式化回复
                reply = format_reply_message(result)
                print(f"生成回复: {reply[:100]}...")

                # 发送回复
                send_feishu_message(chat_id, reply)
                print("回复发送成功")

                return {"code": 0, "msg": "success"}

        return {"code": 0, "msg": "ignored"}

    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(status_code=500, content={"code": -1, "msg": str(e)})


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 50)
    print("🚀 启动飞书机器人服务...")
    print("📍 访问地址: http://localhost:8080")
    print("📍 健康检查: http://localhost:8080/health")
    print("📍 Webhook地址: http://localhost:8080/webhook")
    print("=" * 50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8080)
