import requests
from datetime import datetime
import os

# ----------------------------
# 1. 获取今天日期
# ----------------------------
date_str = datetime.now().strftime("%Y-%m-%d")

# ----------------------------
# 2. 获取芝罘区天气（wttr.in API）
# ----------------------------
city = "烟台芝罘"
url = f"https://wttr.in/{city}?format=j1"

try:
    res = requests.get(url)
    weather_data = res.json()

    today = weather_data["weather"][0]
    weather_text = today["hourly"][0]["weatherDesc"][0]["value"]
    temp_low = today["mintempC"]
    temp_high = today["maxtempC"]
    wind_dir = today["hourly"][0]["winddir16Point"]
except Exception as e:
    print("天气 API 获取失败:", e)
    weather_text = "未知"
    temp_low = temp_high = "未知"
    wind_dir = "未知"

# ----------------------------
# 3. 构造微信模板消息
# ----------------------------
data = {
    "date": {"value": date_str},
    "region": {"value": "山东省 烟台市 芝罘区"},
    "weather": {"value": weather_text},
    "temp": {"value": f"{temp_low}℃ ~ {temp_high}℃"},
    "wind_dir": {"value": wind_dir},
    "today_note": {"value": "今天注意天气变化，合理安排出行"}
}

# ----------------------------
# 4. 推送到微信
# ----------------------------
APPID = os.environ.get("APPID")
APPSECRET = os.environ.get("APPSECRET")
OPENID = os.environ.get("OPENID")
TEMPLATE_ID = os.environ.get("TEMPLATE_ID")

# 获取 access_token
token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}"
access_token = requests.get(token_url).json().get("access_token")

if access_token:
    send_url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    payload = {
        "touser": OPENID,
        "template_id": TEMPLATE_ID,
        "data": data
    }
    r = requests.post(send_url, json=payload)
    print("推送结果:", r.json())
else:
    print("获取 access_token 失败")
