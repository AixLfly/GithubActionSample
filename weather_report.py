#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions安全版 - 天气推送脚本
所有敏感信息从环境变量读取
"""

import requests
import os
import sys
import json
from datetime import datetime

# ================================
# 日志输出函数
# ================================
def log_info(msg):
    print(f"[INFO] {msg}")

def log_error(msg):
    print(f"[ERROR] {msg}")

def log_success(msg):
    print(f"[SUCCESS] {msg}")

# ================================
# 配置验证
# ================================
def validate_config():
    """验证环境变量是否设置"""
    required_vars = [
        "APPID",           # 微信APPID
        "APPSECRET",       # 微信APPSECRET
        "OPENID",          # 用户OPENID
        "TEMPLATE_ID",     # 模板ID
        "CAIYUN_API_TOKEN" # 彩云天气令牌
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        log_error(f"缺少环境变量: {', '.join(missing_vars)}")
        log_error("请在GitHub仓库的 Settings > Secrets and variables > Actions 中设置")
        return False
    
    # 显示配置摘要（隐藏敏感信息）
    log_info("环境变量检查通过:")
    for var in required_vars:
        value = os.environ.get(var)
        if len(value) > 8:
            display = f"{value[:4]}...{value[-4:]}"
        else:
            display = value
        log_info(f"  {var}: {display}")
    
    return True

# ================================
# 天气获取函数
# ================================
def get_caiyun_weather():
    """获取彩云天气数据"""
    token = os.environ.get("CAIYUN_API_TOKEN")
    longitude = 121.3914  # 烟台芝罘区
    latitude = 37.5255
    
    url = f"https://api.caiyunapp.com/v2.6/{token}/{longitude},{latitude}/weather.json"
    params = {"lang": "zh_CN", "unit": "metric:v2"}
    
    try:
        log_info("正在获取彩云天气数据...")
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") != "ok":
            log_error(f"彩云API错误: {data.get('status')}")
            return None
        
        result = data["result"]
        realtime = result["realtime"]
        daily = result["daily"]
        
        # 天气现象映射
        skycon_map = {
            "CLEAR_DAY": "晴", "CLEAR_NIGHT": "晴",
            "PARTLY_CLOUDY_DAY": "多云", "PARTLY_CLOUDY_NIGHT": "多云",
            "CLOUDY": "阴", "LIGHT_RAIN": "小雨",
            "MODERATE_RAIN": "中雨", "HEAVY_RAIN": "大雨",
            "LIGHT_SNOW": "小雪", "MODERATE_SNOW": "中雪",
            "HEAVY_SNOW": "大雪", "WIND": "大风",
            "FOG": "雾", "HAZE": "雾霾"
        }
        
        # 风向映射
        wind_dir_map = {
            "north": "北风", "northeast": "东北风",
            "east": "东风", "southeast": "东南风",
            "south": "南风", "southwest": "西南风",
            "west": "西风", "northwest": "西北风"
        }
        
        # 解析数据
        weather_en = realtime["skycon"]
        weather_zh = skycon_map.get(weather_en, weather_en)
        
        temp_now = round(realtime["temperature"], 1)
        temp_min = round(daily["temperature"][0]["min"], 1)
        temp_max = round(daily["temperature"][0]["max"], 1)
        
        wind_speed = round(realtime["wind"]["speed"], 1)
        wind_dir_en = realtime["wind"]["direction"]
        wind_dir_zh = wind_dir_map.get(wind_dir_en, wind_dir_en)
        
        humidity = round(realtime["humidity"] * 100, 1)
        
        # 获取预警信息
        alert_content = result.get("alert", {}).get("content", [])
        alert_text = alert_content[0]["title"] if alert_content else "暂无预警"
        
        log_success(f"天气获取成功: {weather_zh} {temp_min}℃~{temp_max}℃")
        
        return {
            "weather": weather_zh,
            "weather_en": weather_en,
            "temp_now": temp_now,
            "temp_low": temp_min,
            "temp_high": temp_max,
            "wind_speed": wind_speed,
            "wind_dir": wind_dir_zh,
            "humidity": humidity,
            "wind_full": f"{wind_dir_zh} {wind_speed}km/h",
            "alert": alert_text
        }
        
    except requests.exceptions.RequestException as e:
        log_error(f"网络请求失败: {e}")
    except KeyError as e:
        log_error(f"数据解析失败: {e}")
    except Exception as e:
        log_error(f"获取天气异常: {e}")
    
    return None

# ================================
# 微信推送函数
# ================================
def send_wechat_message(weather_data):
    """发送微信模板消息"""
    # 获取access_token
    token_url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": os.environ.get("APPID"),
        "secret": os.environ.get("APPSECRET")
    }
    
    try:
        log_info("正在获取微信access_token...")
        token_res = requests.get(token_url, params=params, timeout=10)
        token_data = token_res.json()
        
        access_token = token_data.get("access_token")
        if not access_token:
            log_error(f"获取token失败: {token_data}")
            return False
        
        log_success(f"token获取成功")
        
        # 准备模板数据
        date_str = datetime.now().strftime("%Y年%m月%d日 %A")
        
        # 根据温度生成建议
        temp = weather_data["temp_now"]
        if temp < 0:
            advice = "❄️ 气温极低，注意防寒保暖"
        elif temp < 10:
            advice = "🧥 天气寒冷，建议穿厚外套"
        elif temp < 20:
            advice = "🍃 天气凉爽，适宜外出"
        else:
            advice = "😊 天气舒适，注意适时增减衣物"
        
        template_data = {
            "date": {"value": date_str, "color": "#173177"},
            "region": {"value": "山东省 烟台市 芝罘区", "color": "#173177"},
            "weather": {"value": weather_data["weather"], "color": "#FF4500"},
            "temp": {"value": f"{weather_data['temp_low']}℃ ~ {weather_data['temp_high']}℃", "color": "#FF4500"},
            "temp_now": {"value": f"当前 {weather_data['temp_now']}℃", "color": "#FF0000"},
            "wind_dir": {"value": weather_data["wind_full"], "color": "#1E90FF"},
            "humidity": {"value": f"{weather_data['humidity']}%", "color": "#4169E1"},
            "alert": {"value": weather_data["alert"], "color": "#FF6347"},
            "today_note": {"value": f"{advice} | 数据来自彩云天气", "color": "#32CD32"}
        }
        
        # 发送消息
        send_url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
        payload = {
            "touser": os.environ.get("OPENID"),
            "template_id": os.environ.get("TEMPLATE_ID"),
            "data": template_data
        }
        
        log_info("正在发送微信消息...")
        send_res = requests.post(send_url, json=payload, timeout=10)
        result = send_res.json()
        
        if result.get("errcode") == 0:
            log_success(f"推送成功！消息ID: {result.get('msgid')}")
            return True
        else:
            log_error(f"推送失败: {result}")
            return False
            
    except requests.exceptions.RequestException as e:
        log_error(f"网络请求失败: {e}")
    except Exception as e:
        log_error(f"推送过程异常: {e}")
    
    return False

# ================================
# 主程序
# ================================
def main():
    print("=" * 50)
    print("🌤️ 烟台芝罘区天气推送 (GitHub Actions安全版)")
    print("=" * 50)
    
    # 1. 验证配置
    log_info("验证环境变量...")
    if not validate_config():
        sys.exit(1)
    
    # 2. 获取天气
    weather = get_caiyun_weather()
    if not weather:
        log_error("天气获取失败，程序退出")
        sys.exit(1)
    
    # 显示天气详情
    print("\n📊 天气详情:")
    print(f"  天气状况: {weather['weather']}")
    print(f"  当前温度: {weather['temp_now']}℃")
    print(f"  今日范围: {weather['temp_low']}℃ ~ {weather['temp_high']}℃")
    print(f"  风力风向: {weather['wind_full']}")
    print(f"  空气湿度: {weather['humidity']}%")
    print(f"  预警信息: {weather['alert']}")
    
    # 3. 推送微信
    print("\n" + "=" * 50)
    success = send_wechat_message(weather)
    
    print("\n" + "=" * 50)
    if success:
        log_success("任务完成！请检查微信是否收到消息")
    else:
        log_error("任务失败")

if __name__ == "__main__":
    main()
