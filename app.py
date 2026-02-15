"""
飞书机器人 - 热点文案生成助手
接收飞书消息，调用工作流API生成文案
"""

import os
import json
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import hashlib
import hmac

app = FastAPI()

# 配置
WORKFLOW_API_URL = "https://xqzxthj2vk.coze.site/run"
WORKFLOW_API_TOKEN = os.getenv("WORKFLOW_API_TOKEN", "Y77BCTP7KJ7RN32AMFCQQYEPPM3JNYRA")
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")


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
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        result = response.json()

        if "error" in result:
            raise Exception(f"工作流API错误: {result}")

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
    print("=" * 50)
    print("🔄 开始格式化回复消息")
    print(f"📊 输入数据: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print("=" * 50)

    # 🔧 强制调试模式：直接返回工作流API的原始数据
    # 返回完整的原始数据，用于调试
    message = "🔍 【调试模式】工作流API返回的原始数据：\n\n"
    message += "```json\n"
    message += json.dumps(result, ensure_ascii=False, indent=2)
    message += "\n```"
    print(f"💬 调试模式返回: {message[:500]}...")
    return message


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    """飞书Webhook接收端点"""
    try:
        # 获取请求体
        data = await request.json()
        print("=" * 50)
        print("📨 收到飞书Webhook请求")
        print(f"完整请求体: {json.dumps(data, ensure_ascii=False, indent=2)}")
        print("=" * 50)

        # 处理飞书URL验证
        if "challenge" in data:
            print("✅ 飞书URL验证请求")
            return {"challenge": data["challenge"]}

        # 处理消息事件
        header = data.get("header", {})
        event_type = header.get("event_type", "")
        print(f"📌
