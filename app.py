import streamlit as st
import json
import requests
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# 1. Налаштування сторінки
st.set_page_config(page_title="Планувальник місій БПЛА", layout="wide")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at center, #001233 0%, #000000 100%); font-family: 'Segoe UI', sans-serif; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #000814 0%, #001D3D 100%); border-right: 2px solid #00B4D8; }
    h1, h3, .stMarkdown { color: white !important; }
    
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
    gust = weather_item['wind'].get('gust', wind) # Отримуємо пориви, якщо є
    temp = weather_item['main']['temp']
    hum = weather_item['main']['humidity']
    
    # Критичні умови
    if (temp < params['min_temp'] or temp > params['max_temp'] or 
        hum > params['max_humidity'] or wind > params['max_wind'] or 
        gust > params.get('max_gust', params['max_wind'] + 5)):
        return "RED", 0.0
    
    # Розрахунок коефіцієнта
    k_wind = max(0, (params['max_wind'] - wind) / params['max_wind'])
    k_hum = max(0, (params['max_humidity'] - hum) / params['max_humidity'])
    score = round((k_wind * 0.7) + (k_hum * 0.3), 2)
    
    if score > 0.7: return "GREEN", score
    if score > 0.4: return "YELLOW", score
    return "RED", score

# 2. Управління даними БПЛА
if 'custom_drones' not in st.session_state:
    st.session_state.custom_drones = {"Autel EVO II": {"max_wind": 12.0, "max_gust": 17.0, "min_temp": -10.0, "max_temp": 45.0, "max_humidity": 90.0}}

# Ліва панель
st.sidebar.markdown("### ⚙️ НАЛАШТУВАННЯ МІСІЇ")
city = st.sidebar.text_input("ЛОКАЦІЯ (назва міста укр/англ)", "Kyiv")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛸 ПАРАМЕТРИ БПЛА")

# Вибір або додавання нового
drone_mode = st.sidebar.radio("Вибір БПЛА", ["Обрати зі списку", "Додати новий"], label_visibility="collapsed")

if drone_mode == "Додати новий":
    new_name = st.sidebar.text_input("Назва моделі")
    c1, c2 = st.sidebar.columns(2)
    m_wind = c1.number_input("Макс. вітер (м/с)", 0.0, 30.0, 10.0)
    m_gust = c2.number_input("Макс. пориви (м/с)", 0.0, 40.0, 15.0)
    mi_t = c1.number_input("Мін. темп. (°C)", -50.0, 20.0, -10.0)
    ma_t = c2.number_input("Макс. темп. (°C)", 10.0, 60.0, 40.0)
    m_hum = st.sidebar.slider("Макс. вологість (%)", 0, 100, 85)
    
    if st.sidebar.button("ЗБЕРЕГТИ МОДЕЛЬ"):
        st.session_state.custom_drones[new_name] = {
            "max_wind": m_wind, "max_gust": m_gust, 
            "min_temp": mi_t, "max_temp": ma_t, "max_humidity": m_hum
        }
        st.sidebar.success(f"Модель {new_name} додана!")
        st.rerun()

selected_drone = st.sidebar.selectbox("ОБРАНА МОДЕЛЬ", list(st.session_state.custom_drones.keys()))
params = st.session_state.custom_drones[selected_drone]

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 ЧАСОВИЙ ПРОМІЖОК")
start_dt = st.sidebar.datetime_input("ПОЧАТОК", datetime.now())
end_dt = st.sidebar.datetime_input("ЗАВЕРШЕННЯ", datetime.now() + timedelta(hours=24))

# Основна логіка
if st.sidebar.button("АНАЛІЗУВАТИ БЕЗПЕКУ"):
    api_key = "32b44eeafe4783aa188cc888cc0331c6"
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang=ua"
    
    try:
        res = requests.get(url).json()
        
        if "list" in res:
            st.subheader(f"🛡️ Рекомендовані вікна для {selected_drone} у м. {res['city']['name']}")
            st.info("Примітка: Прогноз базується на 3-годинних інтервалах (обмеження безкоштовного API).")
            
            windows = []
            for item in res['list']:
                f_dt = datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S')
                s_dt = datetime.combine(start_dt.date(), start_dt.time())
                e_dt = datetime.combine(end_dt.date(), end_dt.time())
                
                if s_dt <= f_dt <= e_dt:
                    status, score = get_safety_status(item, params)
                    windows.append({
                        "time": f_dt, 
                        "status": status, 
                        "score": score, 
                        "wind": item['wind']['speed'],
                        "gust": item['wind'].get('gust', item['wind']['speed'])
                    })
            
            if windows:
                html_content = ""
                for w in windows:
                    color_class = f"bg-{w['status'].lower()}"
                    
                    if w['status'] == "GREEN":
                        rec = "Оптимальні умови для польоту"
                    elif w['status'] == "YELLOW":
                        rec = "Обмежена безпека (будьте уважні)"
                    else:
                        rec = "НЕБЕЗПЕЧНО! Перевищення лімітів БПЛА"

                    html_content += f"""
                    <div class="window-card">
                        <div style="display: flex; align-items: center;">
                            <div class="indicator {color_class}"></div>
                            <div>
                                <div style="color: white; font-weight: bold; font-size: 1.1em;">
                                    {w['time'].strftime('%H:%M')} — {(w['time'] + timedelta(hours=3)).strftime('%H:%M')}
                                </div>
                                <div style="color: #00B4D8; font-size: 0.85em;">{w['time'].strftime('%d.%m.%Y')}</div>
                            </div>
                        </div>
                        <div style="text-align: center; flex-grow: 1; padding: 0 20px;">
                            <span style="color: rgba(255,255,255,0.7); font-size: 0.9em;">{rec}</span>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: white; font-size: 0.8em; opacity: 0.6;">Вітер: {w['wind']} (пориви {w['gust']}) м/с</div>
                            <div style="color: white; font-size: 0.8em; opacity: 0.6;">Безпека: {int(w['score']*100)}%</div>
                        </div>
                    </div>
                    """
                components.html(f"<div style='font-family: sans-serif;'>{html_content}</div>", height=500, scrolling=True)
                
                # Підсумок
                best = [w['time'].strftime('%H:%M') for w in windows if w['status'] == "GREEN"]
                if best:
                    st.success(f"✅ Оптимальні вікна (старт): {', '.join(best)}")
                else:
                    st.warning("⚠️ Не знайдено ідеальних умов. Перевірте вікна з жовтим статусом.")
            else:
                st.info("ℹ️ Немає даних для аналізу в обраний період.")
        else:
            st.error("❌ Місто не знайдено. Спробуйте ввести назву англійською або уточніть назву.")
    except Exception as e:
        st.error(f"❌ Помилка з'єднання: {e}")
