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
    
    /* Стиль для блоків часових вікон */
    .window-card {
        background: rgba(0, 180, 216, 0.05);
        border: 1px solid rgba(0, 180, 216, 0.3);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .indicator { width: 15px; height: 15px; border-radius: 50%; display: inline-block; margin-right: 10px; }
    .bg-green { background-color: #2ECC71; box-shadow: 0 0 10px #2ECC71; }
    .bg-yellow { background-color: #F1C40F; box-shadow: 0 0 10px #F1C40F; }
    .bg-red { background-color: #E74C3C; box-shadow: 0 0 10px #E74C3C; }
    </style>
    """, unsafe_allow_html=True)

def get_safety_status(weather_item, params):
    wind = weather_item['wind']['speed']
    temp = weather_item['main']['temp']
    hum = weather_item['main']['humidity']
    
    # Критичні умови
    if temp < params['min_temp'] or temp > params['max_temp'] or hum > params['max_humidity'] or wind > params['max_wind']:
        return "RED", 0.0
    
    # Розрахунок коефіцієнта
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

st.write("<h1 style='text-align:center;'>ПРОГНОЗ ВІКОН ДЛЯ ПОЛЬОТІВ</h1>", unsafe_allow_html=True)

# Ліва панель (БЕЗ ЗМІН ДИЗАЙНУ)
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
        st.subheader(f"🛡️ Рекомендовані вікна для {selected_drone}")
        
        # Аналізуємо точки прогнозу та групуємо їх у "вікна"
        windows = []
        for item in res['list']:
            f_dt = datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S')
            s_dt = datetime.combine(start_dt.date(), start_dt.time())
            e_dt = datetime.combine(end_dt.date(), end_dt.time())
            
            if s_dt <= f_dt <= e_dt:
                status, score = get_safety_status(item, drones_db[selected_drone])
                windows.append({"time": f_dt, "status": status, "score": score, "wind": item['wind']['speed']})
        
        if windows:
            html_content = ""
            for i in range(len(windows)):
                w = windows[i]
                color_class = f"bg-{w['status'].lower()}"
                
                # Текст рекомендації залежно від статусу
                if w['status'] == "GREEN":
                    rec = "Найкращий час для тривалої місії"
                elif w['status'] == "YELLOW":
                    rec = "Можливі пориви вітру, будьте обережні"
                else:
                    rec = "Ризик втрати борту! Політ не рекомендується"

                html_content += f"""
                <div class="window-card">
                    <div style="display: flex; align-items: center;">
                        <div class="indicator {color_class}"></div>
                        <div>
                            <div style="color: white; font-weight: bold; font-size: 1.1em;">
                                {w['time'].strftime('%H:%M')} — { (w['time'] + timedelta(hours=3)).strftime('%H:%M') }
                            </div>
                            <div style="color: #00B4D8; font-size: 0.85em;">{w['time'].strftime('%d %b')}</div>
                        </div>
                    </div>
                    <div style="text-align: center; flex-grow: 1; padding: 0 20px;">
                        <span style="color: rgba(255,255,255,0.7); font-size: 0.9em;">{rec}</span>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: white; font-size: 0.8em; opacity: 0.6;">Вітер: {w['wind']} м/с</div>
                        <div style="color: white; font-size: 0.8em; opacity: 0.6;">Коеф: {w['score']}</div>
                    </div>
                </div>
                """
            components.html(f"<div style='font-family: sans-serif;'>{html_content}</div>", height=600, scrolling=True)
            
            # Підсумок під таблицею
            best_windows = [w['time'].strftime('%H:%M') for w in windows if w['status'] == "GREEN"]
            if best_windows:
                st.success(f"✅ Знайдено оптимальні вікна: {', '.join(best_windows[:3])}...")
            else:
                st.warning("⚠️ Оптимальних вікон (зелених) не знайдено. Розгляньте варіанти з жовтим статусом.")
        else:
            st.info("ℹ️ Немає даних для аналізу в обраний період.")
    else:
        st.error("❌ Помилка отримання даних. Перевірте назву міста.")
