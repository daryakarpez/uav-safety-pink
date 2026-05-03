import streamlit as st
import json
import requests
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# 1. Налаштування сторінки 
st.set_page_config(page_title="WYVERN TECH | UAV Safety", layout="wide")

st.markdown("""
    <style>
    /* Головний фон - темний градієнт */
    .stApp {
        background: linear-gradient(180deg, #000000 0%, #000033 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Бокова панель - темно-синя */
    [data-testid="stSidebar"] {
        background-color: #000066;
        border-right: 1px solid #ffffff33;
    }
    
    /* Заголовки та текст */
    h1, h2, h3, p, span, label, .stMarkdown {
        color: #FFFFFF !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Кнопка */
    .stButton>button {
        background-color: transparent !important;
        color: #FFFFFF !important;
        border: 2px solid #FFFFFF !important;
        border-radius: 5px;
        font-weight: bold;
        transition: 0.3s;
        text-transform: uppercase;
    }
    .stButton>button:hover {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Поля вводу */
    input, select {
        background-color: rgba(255,255,255,0.1) !important;
        color: white !important;
        border: 1px solid #FFFFFF !important;
    }
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
        return {"DJI Mavic 3": {"max_wind": 12, "min_temp": -10, "max_temp": 40, "max_humidity": 85}}

drones_db = load_drones()

# Заголовок 
st.markdown("<h1 style='text-align: center; font-size: 3em; border: 4px solid white; padding: 10px; display: inline-block;'>WYVERN TECH</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #aaa;'>Next-Generation Drone Safety System</p>", unsafe_allow_html=True)

st.sidebar.header("🕹️ MISSION CONTROL")

if drones_db:
    selected_drone = st.sidebar.selectbox("БПЛА PLATFORM", list(drones_db.keys()))
    city = st.sidebar.text_input("DEPLOYMENT CITY", "Kyiv")
    
    st.sidebar.subheader("⏳ WINDOW OF OPERATION")
    start_dt = st.sidebar.datetime_input("START TIME", datetime.now())
    end_dt = st.sidebar.datetime_input("END TIME", datetime.now() + timedelta(hours=3))
    
    api_key = "32b44eeafe4783aa188cc888cc0331c6" 

    if st.sidebar.button("EXECUTE ANALYSIS"):
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang=ua"
        response = requests.get(url).json()
        
        if "list" in response:
            st.subheader(f"📡 DATA STREAM: {selected_drone} @ {city}")
            
            html_code = """
            <table style="width:100%; border-collapse: collapse; font-family: 'Courier New', Courier, monospace; background-color: transparent; color: white; border: 1px solid white;">
                <tr style="background-color: #000044; border-bottom: 2px solid white;">
                    <th style="padding: 15px; text-align: left; border: 1px solid #444;">TIMESTAMP</th>
                    <th style="padding: 15px; text-align: center; border: 1px solid #444;">SAFETY INDEX</th>
                    <th style="padding: 15px; text-align: center; border: 1px solid #444;">MISSION STATUS</th>
                </tr>
            """
            
            main_score = 0
            count = 0

            for item in response['list'][:15]: 
                f_dt = datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S')
                s_dt = datetime.combine(start_dt.date(), start_dt.time())
                e_dt = datetime.combine(end_dt.date(), end_dt.time())
                
                # Гнучкий фільтр часу 
                is_in_range = (s_dt - timedelta(hours=1, minutes=30)) <= f_dt <= (e_dt + timedelta(hours=1, minutes=30))
                
                score = calculate_safety(item, drones_db[selected_drone])
                
                if is_in_range:
                    bg = "rgba(255, 255, 255, 0.1)"
                    op = "1.0"
                    status = "✅ ACTIVE"
                    main_score += score
                    count += 1
                else:
                    bg = "transparent"
                    op = "0.3"
                    status = "---"

                html_code += f"""
                <tr style="background-color: {bg}; opacity: {op}; border-bottom: 1px solid #444;">
                    <td style="padding: 12px; border: 1px solid #333;">{item['dt_txt']}</td>
                    <td style="padding: 12px; text-align: center; font-weight: bold; border: 1px solid #333;">{score}</td>
                    <td style="padding: 12px; text-align: center; border: 1px solid #333; letter-spacing: 2px;">{status}</td>
                </tr>
                """
            
            html_code += "</table>"
            components.html(html_code, height=500, scrolling=True)

            st.markdown("---")
            if count > 0:
                avg = round(main_score / count, 2)
                if avg > 0.7:
                    st.success(f"✔️ MISSION GUARANTEED. AVG SAFETY: {avg}")
                else:
                    st.error(f"❌ MISSION ABORTED. AVG SAFETY: {avg}")
            else:
                st.warning("⚠️ NO DATA IN SELECTED TIME WINDOW. EXPAND YOUR OPERATIONAL RANGE.")
        else:
            st.error("❌ SIGNAL LOST. CHECK CITY NAME.")
