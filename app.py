import streamlit as st
import json
import requests
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# 1. Налаштування сторінки
st.set_page_config(page_title="UAV Safety Pink System", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFF0F5; }
    [data-testid="stSidebar"] { background-color: #FFC0CB; }
    h1, h2, h3, p, span, label, .stMarkdown {
        color: #FFFFFF !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
    }
    .stButton>button {
        background-color: #C71585 !important;
        color: #FFFFFF !important;
        border-radius: 15px;
        border: 2px solid #FFFFFF !important;
        font-weight: bold;
        height: 3em;
        width: 100%;
    }
    input, select, [data-testid="stHeader"] { background: transparent; }
    </style>
    """, unsafe_allow_html=True)

def calculate_safety(weather_item, params):
    wind = weather_item['wind']['speed']
    temp = weather_item['main']['temp']
    hum = weather_item['main']['humidity']
    k_wind = max(0, (params['max_wind'] - wind) / params['max_wind'])
    k_hum = max(0, (params['max_humidity'] - hum) / params['max_humidity'])
    if temp < params['min_temp'] or temp > params['max_temp'] or hum > params['max_humidity']:
        return 0.0
    return round((k_wind * 0.7) + (k_hum * 0.3), 2)

def load_drones():
    try:
        with open('drones.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

drones_db = load_drones()

st.title("🌸 UAV SAFETY DECISION SUPPORT")

# 4. Бокова панель
st.sidebar.header("⚙️ ПАРАМЕТРИ МІСІЇ")

if drones_db:
    selected_drone = st.sidebar.selectbox("Модель БПЛА", list(drones_db.keys()))
    city = st.sidebar.text_input("Місто", "Kyiv")
    
    st.sidebar.subheader("⏳ Час місії")
    # Робимо проміжок за замовчуванням (сьогодні - завтра)
    start_dt = st.sidebar.datetime_input("Початок", datetime.now())
    end_dt = st.sidebar.datetime_input("Кінець", datetime.now() + timedelta(hours=24))
    
    api_key = "32b44eeafe4783aa188cc888cc0331c6" 

    if st.sidebar.button("РОЗРАХУВАТИ БЕЗПЕКУ"):
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang=ua"
        response = requests.get(url).json()
        
        if "list" in response:
            st.subheader(f"📊 Аналіз для {selected_drone} у місті {city}")
            
            # Формуємо HTML-строку без зайвих переносів
            html_code = """
            <table style="width:100%; border-collapse: collapse; font-family: sans-serif; background-color: white; color: #C71585; border-radius: 10px; overflow: hidden;">
                <tr style="background-color: #C71585; color: white;">
                    <th style="padding: 15px; text-align: left;">📅 Час</th>
                    <th style="padding: 15px; text-align: center;">🛡️ Індекс</th>
                    <th style="padding: 15px; text-align: center;">📝 Статус</th>
                </tr>
            """
            
            main_score = 0
            count = 0

            for item in response['list'][:15]: 
                f_dt = datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S')
                # Перетворюємо start_dt/end_dt у формат datetime для порівняння
                s_dt = datetime.combine(start_dt.date(), start_dt.time()) if isinstance(start_dt, datetime) else start_dt
                e_dt = datetime.combine(end_dt.date(), end_dt.time()) if isinstance(end_dt, datetime) else end_dt
                
                score = calculate_safety(item, drones_db[selected_drone])
                is_in_range = s_dt <= f_dt <= e_dt
                
                bg = "#FFF0F5" if (is_in_range and score > 0.5) else ("#FFB6C1" if is_in_range else "#FFFFFF")
                op = "1.0" if is_in_range else "0.4"
                status = "🎯 В межах місії" if is_in_range else "---"
                
                if is_in_range:
                    main_score += score
                    count += 1

                html_code += f"""
                <tr style="background-color: {bg}; opacity: {op}; border-bottom: 1px solid #FFC0CB;">
                    <td style="padding: 12px;">{item['dt_txt']}</td>
                    <td style="padding: 12px; text-align: center; font-weight: bold;">{score}</td>
                    <td style="padding: 12px; text-align: center;">{status}</td>
                </tr>
                """
            
            html_code += "</table>"
            
            # ВИКОРИСТОВУЄМО КОМПОНЕНТ ДЛЯ 100% ВІДОБРАЖЕННЯ HTML
            components.html(html_code, height=500, scrolling=True)

            st.write("---")
            if count > 0:
                avg = round(main_score / count, 2)
                if avg > 0.7:
                    st.success(f"💖 Політ дозволено! Середній індекс: {avg}")
                else:
                    st.error(f"💔 Небезпечно! Середній індекс: {avg}")
            else:
                st.warning("⚠️ Оберіть інший час у меню зліва.")
        else:
            st.error("❌ Помилка API. Перевірте місто.")
