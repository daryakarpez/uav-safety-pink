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
    
    /* Стиль "Лінійка": лише нижня напівпрозора лінія зі світінням */
    .window-card {
        background: transparent;
        border: none;
        /* Тонка напівпрозора лінія */
        border-bottom: 1px solid rgba(0, 180, 216, 0.2); 
        padding: 15px 0px; 
        margin-bottom: 0px; 
        display: flex;
        justify-content: space-between;
        /* Вирівнювання по нижньому краю, щоб текст лежав на лінії */
        align-items: flex-end; 
        box-shadow: 0px 4px 10px -6px rgba(0, 180, 216, 0.3);
    }

    /* Колонки для чіткого вирівнювання тексту */
    .col-time { width: 20%; text-align: left; }
    .col-rec { width: 60%; text-align: center; padding-bottom: 2px; }
    .col-data { width: 20%; text-align: right; }

    /* Приховуємо зайві відступи Streamlit */
    .block-container { padding-top: 2rem; }
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
                
                # Колір тексту залежно від статусу (без точок)
                status_color = "#2ECC71" if w['status'] == "GREEN" else "#F1C40F" if w['status'] == "YELLOW" else "#E74C3C"
                
                if w['status'] == "GREEN":
                    rec = "Найкращий час для тривалої місії"
                elif w['status'] == "YELLOW":
                    rec = "Можливі пориви вітру, будьте обережні"
                else:
                    rec = "Ризик втрати борту! Не рекомендується"

                # Формуємо рядок з напівпрозорою лінією
                html_content += f"""
                <div class="window-card">
                    <div class="col-time">
                        <div style="color: white; font-weight: bold; font-size: 1.1em; line-height: 1;">
                            {w['time'].strftime('%H:%M')}
                        </div>
                        <div style="color: #00B4D8; font-size: 0.7em; margin-top: 3px; opacity: 0.6;">
                            {w['time'].strftime('%d %b')}
                        </div>
                    </div>
                    
                    <div class="col-rec" style="color: {status_color};">
                        {rec}
                    </div>
                    
                    <div class="col-data">
                        <div style="color: white; font-size: 0.8em; opacity: 0.6;">Вітер: {w['wind']} м/с</div>
                        <div style="color: rgba(0, 180, 216, 0.4); font-size: 0.7em;">Коеф: {w['score']}</div>
                    </div>
                </div>
                """
            
            # Вивід через markdown для кращої інтеграції стилів сторінки
            st.markdown(f"<div style='font-family: sans-serif;'>{html_content}</div>", unsafe_allow_html=True)
            
            best_windows = [w['time'].strftime('%H:%M') for w in windows if w['status'] == "GREEN"]
            if best_windows:
                st.success(f"✅ Знайдено оптимальні вікна: {', '.join(best_windows[:3])}...")
            else:
                st.warning("⚠️ Оптимальних вікон (зелених) не знайдено.")
        else:
            st.info("ℹ️ Немає даних для аналізу в обраний період.")
    else:
        st.error("❌ Помилка отримання даних. Перевірте назву міста.")
