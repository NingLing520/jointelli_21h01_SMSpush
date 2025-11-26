import requests
import hashlib
import random
import string
import time
import hmac
import base64
import json

# -----------------------------
# ======== 配置区域 ============
# -----------------------------

CPE_BASE = "http://192.168.0.1" # CPE设备地址
USERNAME = "USERNAME" # 用户名
PASSWORD = "PASSWORD" # 密码

# 钉钉机器人配置 - 只需要token部分，不要完整URL
DING_ACCESS_TOKEN = "TOKEN"  # 钉钉access_token

# 加签secret
DING_SECRET = "SECRET" # 钉钉加签secret

CHECK_INTERVAL = 5  # 轮询短信间隔（秒）


# -----------------------------
# ====== 生成钉钉加签 ==========
# -----------------------------

def ding_signed_url():
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{DING_SECRET}"
    hmac_code = hmac.new(DING_SECRET.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode("utf-8")
    return f"https://oapi.dingtalk.com/robot/send?access_token={DING_ACCESS_TOKEN}&timestamp={timestamp}&sign={sign}"


# -----------------------------
# ====== 发送钉钉消息 ==========
# -----------------------------

def ding_send(text):
    webhook = ding_signed_url()
    data = {
        "msgtype": "text",
        "text": {"content": text}
    }
    try:
        r = requests.post(webhook, json=data, timeout=10)
        result = r.json()
        print("[钉钉返回]:", result)
        
        # 检查是否发送成功
        if result.get("errcode") == 0:
            print("✓ 钉钉消息发送成功")
            return True
        else:
            print(f"✗ 钉钉消息发送失败: {result.get('errmsg')}")
            return False
            
    except Exception as e:
        print("[钉钉错误]:", e)
        return False


# -----------------------------
# ====== CPE 登录逻辑 =========
# -----------------------------

def random_salt(length=64):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


def cpe_login(session):
    # 清除可能存在的重复 cookie
    session.cookies.clear()
    session.get(CPE_BASE)  # 获取初始 cookie

    salt = random_salt()
    enc_pwd = sha256(f"{salt}:{PASSWORD}")

    t = int(time.time() * 1000)
    url = f"{CPE_BASE}/cgi-bin/luci/login/action_login?flag=action_login&t={t}"

    payload = {
        "username": USERNAME,
        "password": enc_pwd,
        "salt": salt
    }

    r = session.post(url, json=payload)
    print("登录响应:", r.text)

    try:
        data = r.json()
        if data.get("sessionid"):
            token = data["sessionid"]
            # 只设置一个 sysauth cookie
            session.cookies.set("sysauth", token, domain='192.168.0.1', path='/')
            print("登录成功，Token =", token)
            return True
    except:
        pass

    print("登录失败")
    return False


# -----------------------------
# ====== 获取短信列表 =========
# -----------------------------

def fetch_sms(session):
    """获取短信列表 - 使用正确的批量JSON-RPC格式"""
    t = int(time.time() * 1000)
    url = f"{CPE_BASE}/ubus/?flag=all_sms&t={t}"
    
    # 使用正确的批量JSON-RPC格式
    payload = [
        {
            "jsonrpc": "2.0",
            "method": "call", 
            "id": "1",
            "params": [
                session.cookies.get("sysauth"),
                "sms_app",
                "all_sms", 
                {}
            ]
        },
        {
            "jsonrpc": "2.0",
            "method": "call",
            "id": "2", 
            "params": [
                session.cookies.get("sysauth"),
                "phone_book",
                "read_book",
                {"device": "1", "type": "ALL"}
            ]
        },
        {
            "jsonrpc": "2.0", 
            "method": "call",
            "id": "3",
            "params": [
                session.cookies.get("sysauth"), 
                "sms_app",
                "get_addr",
                {}
            ]
        }
    ]
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        r = session.post(url, json=payload, headers=headers)
        print("短信接口原始响应:", r.text)
        
        data = r.json()
        return data
        
    except Exception as e:
        print("短信请求失败:", e)
        return None


# -----------------------------
# ====== 解析短信数据 =========
# -----------------------------

def parse_sms_data(sms_data):
    """解析短信数据，提取所有短信"""
    messages = []
    
    if not sms_data or not isinstance(sms_data, list) or len(sms_data) == 0:
        return messages
    
    # 第一个元素包含短信数据
    first_call = sms_data[0]
    
    if "result" in first_call:
        result_data = first_call["result"]
        
        # result_data 格式: [0, {实际数据}]
        if isinstance(result_data, list) and len(result_data) > 1:
            actual_data = result_data[1]
            
            # 短信数据在 data 字段中
            if "data" in actual_data and isinstance(actual_data["data"], dict):
                data_dict = actual_data["data"]
                
                # 提取所有 data1, data2, data3... 格式的短信
                for key in data_dict:
                    if key.startswith("data"):
                        msg = data_dict[key]
                        messages.append(msg)
    
    return messages


# -----------------------------
# ===== 时间戳转换函数 ========
# -----------------------------

def format_timestamp(timestamp_str):
    """将Unix时间戳转换为可读格式"""
    try:
        timestamp = int(timestamp_str)
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
    except:
        return timestamp_str


# -----------------------------
# ===== 主循环：监控短信 ========
# -----------------------------

def main():
    session = requests.Session()

    print("正在登录 CPE…")
    if not cpe_login(session):
        return

    seen = set()  # 防止重复发送
    print("🚀 短信监控系统已启动，开始监控新短信...")

    while True:
        sms_data = fetch_sms(session)

        if not sms_data:
            print("读取短信失败，尝试重新登录…")
            cpe_login(session)
            time.sleep(2)
            continue

        # 解析短信数据
        messages = parse_sms_data(sms_data)

        if not messages:
            print("未找到短信数据")
            time.sleep(CHECK_INTERVAL)
            continue

        # 处理每条短信
        new_message_found = False
        for msg in messages:
            msg_id = msg.get("index")
            content = msg.get("content", "")
            phone = msg.get("addr", "未知号码")
            time_str = msg.get("time", "")
            
            # 格式化时间
            formatted_time = format_timestamp(time_str)

            if msg_id and msg_id not in seen:
                seen.add(msg_id)
                new_message_found = True

                text = f"📩【新短信】\n来自：{phone}\n时间：{formatted_time}\n内容：{content}"
                print(f"发现新短信: ID={msg_id}, 来自={phone}")
                
                # 发送到钉钉
                ding_send(text)

        if not new_message_found:
            print(f"⏳ 未发现新短信，{CHECK_INTERVAL}秒后继续检查...")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()