import requests
from datetime import datetime
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ----------------------------
# 1. 获取今天日期
# ----------------------------
date_str = datetime.now().strftime("%Y年%m月%d日 %A")

# ----------------------------
# 2. 获取芝罘区天气（彩云天气API）
# ----------------------------
def get_caiyun_weather():
    """使用彩云天气API获取精准天气"""
    # 从GitHub Actions环境变量获取令牌
    token = os.environ.get("CAIYUN_API_TOKEN")
    if not token:
        logger.error("未找到CAIYUN_API_TOKEN环境变量")
        return None
    
    # 烟台芝罘区经纬度（精确位置）
    longitude = 121.3914
    latitude = 37.5255
    
    # 彩云天气API地址
    url = f"https://api.caiyunapp.com/v2.6/{token}/{longitude},{latitude}/weather.json"
    
    params = {
        "lang": "zh_CN",
        "unit": "metric:v2",
        "alert": "true"
    }
    
    try:
        logger.info("正在请求彩云天气API...")
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") != "ok":
            logger.error(f"彩云API返回错误: {data.get('status')}")
            return None
        
        result = data["result"]
        realtime = result["realtime"]
        daily = result["daily"]
        
        # 天气现象中文映射
        skycon_map = {
            "CLEAR_DAY": "晴", "CLEAR_NIGHT": "晴",
            "PARTLY_CLOUDY_DAY": "多云", "PARTLY_CLOUDY_NIGHT": "多云",
            "CLOUDY": "阴", "LIGHT_RAIN": "小雨",
            "MODERATE_RAIN": "中雨", "HEAVY_RAIN": "大雨",
            "STORM_RAIN": "暴雨", "FOG": "雾",
            "LIGHT_SNOW": "小雪", "MODERATE_SNOW": "中雪",
            "HEAVY_SNOW": "大雪", "WIND": "大风"
        }
        
        # 风向中文映射
        wind_dir_map = {
            "north": "北风", "northeast": "东北风",
            "east": "东风", "southeast": "东南风",
            "south": "南风", "southwest": "西南风",
            "west": "西风", "northwest": "西北风"
        }
        
        # 解析数据
        skycon_en = realtime["skycon"]
        weather_text = skycon_map.get(skycon_en, skycon_en)
        
        temp_now = realtime["temperature"]
        temp_low = daily["temperature"][0]["min"]
        temp_high = daily["temperature"][0]["max"]
        
        wind_speed = realtime["wind"]["speed"]
        wind_dir_en = realtime["wind"]["direction"]
        wind_dir = wind_dir_map.get(wind_dir_en, wind_dir_en)
        
        humidity = realtime["humidity"] * 100
        
        # 获取预警信息
        alerts = result.get("alert", {}).get("content", [])
        alert_text = alerts[0]["title"] if alerts else "无预警"
        
        return {
            "weather": weather_text,
            "temp_now": round(temp_now, 1),
            "temp_low": round(temp_low, 1),
            "temp_high": round(temp_high, 1),
            "wind_dir": f"{wind_dir} {round(wind_speed, 1)}km/h",
            "humidity": round(humidity, 1),
            "alert": alert_text
        }
        
    except Exception as e:
        logger.error(f"获取彩云天气失败: {e}")
        return None

# 获取天气数据
weather_info = get_caiyun_weather()

if weather_info:
    logger.info(f"天气获取成功: {weather_info['weather']}, {weather_info['temp_low']}~{weather_info['temp_high']}℃")
else:
    # 如果失败，使用默认值
    logger.warning("天气API获取失败，使用默认值")
    weather_info = {
        "weather": "未知",
        "temp_now": 0,
        "temp_low": 0,
        "temp_high": 0,
        "wind_dir": "未知",
        "humidity": 0,
        "alert": "无数据"
    }

# ----------------------------
# 3. 构造微信模板消息
# ----------------------------
data = {
    "date": {"value": date_str},
    "region": {"value": "山东省 烟台市 芝罘区"},
    "weather": {"value": weather_info["weather"]},
    "temp": {"value": f"{weather_info['temp_low']}℃ ~ {weather_info['temp_high']}℃"},
    "temp_now": {"value": f"当前 {weather_info['temp_now']}℃"},
    "wind_dir": {"value": weather_info["wind_dir"]},
    "humidity": {"value": f"{weather_info['humidity']}%"},
    "alert": {"value": weather_info["alert"]},
    "today_note": {"value": "数据来自彩云天气，请适时增减衣物"}
}

# ----------------------------
# 4. 推送到微信
# ----------------------------
# 从GitHub Actions环境变量获取微信配置
APPID = os.environ.get("APPID")
APPSECRET = os.environ.get("APPSECRET")
OPENID = os.environ.get("OPENID")
TEMPLATE_ID = os.environ.get("TEMPLATE_ID")

if not all([APPID, APPSECRET, OPENID, TEMPLATE_ID]):
    logger.error("微信配置环境变量不全")
    exit(1)

# 获取 access_token
try:
    token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}"
    token_res = requests.get(token_url, timeout=10)
    token_data = token_res.json()
    access_token = token_data.get("access_token")
    
    if not access_token:
        logger.error(f"获取access_token失败: {token_data}")
        exit(1)
        
    # 发送模板消息
    send_url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    payload = {
        "touser": OPENID,
        "template_id": TEMPLATE_ID,
        "data": data
    }
    
    send_res = requests.post(send_url, json=payload, timeout=10)
    result = send_res.json()
    
    if result.get("errcode") == 0:
        logger.info(f"推送成功！消息ID: {result.get('msgid')}")
    else:
        logger.error(f"推送失败: {result}")
        
except Exception as e:
    logger.error(f"微信推送过程出错: {e}")
