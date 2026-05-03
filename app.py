import streamlit as st
import json
import requests
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# 1. Налаштування сторінки
st.set_page_config(page_title="UAV Mission Planner", layout="wide")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at center, #001233 0%, #000000 100%); font-family: 'Segoe UI', sans-serif; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #000814 0%, #001D3D 100%); border-right: 2px solid #00B4D8; }
    h1, h3, .stMarkdown { color: white !important; }
    
    /* Контейнер для вікна з ефектом лінійки */
    .window-card {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 15px 0;
        margin: 0;
        /* Тонка неонова лінія */
        border-bottom: 1px solid rgba(0, 180, 216, 0.2);
        box-shadow: 0px 5px 10px -5px rgba(0, 180, 216, 0.3);
    }

    .indicator { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 12px; }
    .bg-green { background-color: #2ECC71; box-shadow: 0 0 10px #2ECC71; }
    .bg-yellow { background-color: #F1C40F; box-shadow: 0 0 10px #F1C40F; }
    .bg-red { background-color: #E74C3C; box-shadow: 0 0 10px #E74C3C; }
    </style>
    """, unsafe_allow_html=True)

def get_safety_status(weather_item, params):
    wind = weather_item['wind']['speed']
    temp = weather_item['main']['temp']
    hum = weather_item['main']['humidity']
    if temp < params['min_temp'] or temp > params['max_temp'] or hum > params['max_humidity'] or wind > params['max_wind']:
        return "RED", 0.0
    k_wind = max(0, (params['max_wind'] - wind) / params['max_wind'])
    k_hum = max(0, (params['max_humidity'] - hum) / params['max_humidity'])
    score = round((k_wind * 0.7) + (k_hum * 0.3), 2)
    if score > 0.7: return "GREEN", score
    if score > 0.4: return "YELLOW", score
    return "RED", score

def load_drones():
    try:
        with open('drones.json', 'r', encoding='utf-8') as f: return json.load(f)
    except:
        return {"Autel EVO II": {"max_wind": 12, "min_temp": -10, "max_temp": 45, "max_humidity": 90}}

drones_db = load_drones()

# Ліва панель (Без змін дизайну)
st.sidebar.markdown("### ⚙️ НАЛАШТУВАННЯ МІСІЇ")
selected_drone = st.sidebar.selectbox("МОДЕЛЬ БПЛА", list(drones_db.keys()))
city = st.sidebar.text_input("ЛОКАЦІЯ", "Kyiv")
st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 ЧАСОВИЙ ПРОМІЖОК")
start_dt = st.sidebar.datetime_input("ПОЧАТОК", datetime.now())
end_dt = st.sidebar.datetime_input("ЗАВЕРШЕННЯ", datetime.now() + timedelta(hours=24))

if st.sidebar.button("АНАЛІЗУВАТИ БЕЗПЕКУ"):
    api_key = "32b44eeafe4783aa188cc888cc0331c6"
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang=ua"
    res = requests.get(url).json()
    
    if "list" in res:
        html_content = ""
        for item in res['list']:
            f_dt = datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S')
            s_dt = datetime.combine(start_dt.date(), start_dt.time())
            e_dt = datetime.combine(end_dt.date(), end_dt.time())
            
            if s_dt <= f_dt <= e_dt:
                status, score = get_safety_status(item, drones_db[selected_drone])
                color_class = f"bg-{status.lower()}"
                
                # Текст рекомендації
                rec = "Найкращий час для тривалої місії" if status == "GREEN" else \
                      "Можливі пориви вітру, будьте обережні" if status == "YELLOW" else \
                      "Ризик втрати борту! Політ не рекомендується"

                # Верстка рядка з вирівнюванням
                html_content += f"""
                <div class="window-card">
                    <div style="width: 20%; display: flex; align-items: center;">
                        <div class="indicator {color_class}"></div>
                        <div>
                            <div style="color: white; font-weight: bold; font-size: 1.1em; line-height: 1;">{f_dt.strftime('%H:%M')}</div>
                            <div style="color: #00B4D8; font-size: 0.7em; margin-top: 4px;">{f_dt.strftime('%d %b')}</div>
                        </div>
                    </div>
                    <div style="width: 60%; text-align: center;">
                        <span style="color: rgba(255,255,255,0.6); font-size: 0.9em;">{rec}</span>
                    </div>
                    <div style="width: 20%; text-align: right;">
                        <div style="color: white; font-size: 0.8em; opacity: 0.7;">Вітер: {item['wind']['speed']} м/с</div>
                        <div style="color: rgba(0, 180, 216, 0.5); font-size: 0.7em;">Коеф: {score}</div>
                    </div>
                </div>
                """
        
        st.markdown(f"<div style='margin-top: 20px;'>{html_content}</div>", unsafe_allow_html=True)
    else:
        st.error("Помилка отримання даних. Перевірте назву міста.")
