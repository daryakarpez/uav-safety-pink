import streamlit as st
import json
import requests
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import plotly.graph_objects as go  # Додано для графіків

# ==========================================
# 1. КОНФІГУРАЦІЯ СТОРІНКИ ТА СТИЛІЗАЦІЯ
# ==========================================
st.set_page_config(page_title="UAV Mission Planner", layout="wide")

st.markdown("""
    <style>
    .stApp { 
        background: radial-gradient(circle at center, #001233 0%, #000000 100%); 
        font-family: 'Segoe UI', sans-serif; 
    }
    [data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #000814 0%, #001D3D 100%); 
        border-right: 2px solid #00B4D8; 
    }
    h1, h2, h3, .stMarkdown { color: white !important; }
    
    .window-card {
        background: rgba(0, 180, 216, 0.03);
        border-bottom: 1px solid rgba(0, 180, 216, 0.15);
        padding: 12px 15px;
        transition: background 0.3s;
    }
    .window-card:hover {
        background: rgba(0, 180, 216, 0.08);
    }
    .indicator { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 12px; }
    .bg-green { background-color: #2ECC71; box-shadow: 0 0 8px #2ECC71; }
    .bg-yellow { background-color: #F1C40F; box-shadow: 0 0 8px #F1C40F; }
    .bg-red { background-color: #E74C3C; box-shadow: 0 0 8px #E74C3C; }
    
    /* Стиль для попередження про часові проміжки */
    .time-info {
        background: rgba(0, 180, 216, 0.1);
        border-left: 4px solid #00B4D8;
        padding: 15px;
        margin-bottom: 20px;
        border-radius: 4px;
        font-size: 0.9em;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. ФУНКЦІЇ ЛОГІКИ
# ==========================================
def get_safety_status(weather_item, params):
    wind = weather_item['wind']['speed']
    gust = weather_item['wind'].get('gust', wind)
    temp = weather_item['main']['temp']
    hum = weather_item['main']['humidity']
    
    if (temp < params['min_temp'] or temp > params['max_temp'] or 
        hum > params['max_humidity'] or wind > params['max_wind'] or 
        gust > params.get('max_gust', params['max_wind'] + 5)):
        return "RED", 0.0
    
    k_wind = max(0, (params['max_wind'] - wind) / params['max_wind'])
    k_hum = max(0, (params['max_humidity'] - hum) / params['max_humidity'])
    score = round((k_wind * 0.7) + (k_hum * 0.3), 2)
    
    if score > 0.7: return "GREEN", score
    if score > 0.4: return "YELLOW", score
    return "RED", score

# ==========================================
# 3. ІНІЦІАЛІЗАЦІЯ БАЗИ ДАНИХ
# ==========================================
if 'custom_drones' not in st.session_state:
    st.session_state.custom_drones = {
        "Autel EVO II": {"max_wind": 12.0, "max_gust": 17.0, "min_temp": -10.0, "max_temp": 45.0, "max_humidity": 90.0},
        "DJI Mavic 3": {"max_wind": 12.0, "max_gust": 15.0, "min_temp": -10.0, "max_temp": 40.0, "max_humidity": 85.0},
        "FPV Custom 7": {"max_wind": 15.0, "max_gust": 20.0, "min_temp": -15.0, "max_temp": 50.0, "max_humidity": 95.0}
    }

# ==========================================
# 4. БІЧНА ПАНЕЛЬ (SIDEBAR)
# ==========================================
st.sidebar.markdown("### ⚙️ НАЛАШТУВАННЯ МІСІЇ")
city = st.sidebar.text_input("ЛОКАЦІЯ", "Kyiv")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛸 ПАРАМЕТРИ БПЛА")
drone_mode = st.sidebar.radio("Режим", ["Обрати зі списку", "Додати новий"], label_visibility="collapsed")

if drone_mode == "Додати новий":
    new_name = st.sidebar.text_input("Назва моделі")
    c1, c2 = st.sidebar.columns(2)
    m_wind = c1.number_input("Макс. вітер (м/с)", 0.0, 30.0, 10.0)
    m_gust = c2.number_input("Макс. пориви (м/с)", 0.0, 40.0, 15.0)
    mi_t = c1.number_input("Мін. темп. (°C)", -50.0, 20.0, -10.0)
    ma_t = c2.number_input("Макс. темп. (°C)", 10.0, 60.0, 40.0)
    m_hum = st.sidebar.slider("Макс. вологість (%)", 0, 100, 85)
    
    if st.sidebar.button("ЗБЕРЕГТИ МОДЕЛЬ"):
        if new_name:
            st.session_state.custom_drones[new_name] = {
                "max_wind": m_wind, "max_gust": m_gust, 
                "min_temp": mi_t, "max_temp": ma_t, "max_humidity": m_hum
            }
            st.rerun()
    params = {"max_wind": m_wind, "max_gust": m_gust, "min_temp": mi_t, "max_temp": ma_t, "max_humidity": m_hum}
    selected_drone = new_name if new_name else "Нова модель"
else:
    selected_drone = st.sidebar.selectbox("ОБРАНА МОДЕЛЬ", list(st.session_state.custom_drones.keys()))
    params = st.session_state.custom_drones[selected_drone]

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 ЧАСОВИЙ ПРОМІЖОК")
start_dt = st.sidebar.datetime_input("ПОЧАТОК", datetime.now())
end_dt = st.sidebar.datetime_input("ЗАВЕРШЕННЯ", datetime.now() + timedelta(hours=24))

analyze_btn = st.sidebar.button("АНАЛІЗУВАТИ БЕЗПЕКУ", use_container_width=True)

# ==========================================
# 5. ОСНОВНИЙ ЕКРАН
# ==========================================
if analyze_btn:
    api_key = "32b44eeafe4783aa188cc888cc0331c6"
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang=ua"
    
    try:
        res = requests.get(url).json()
        if "list" in res:
            # ПОЛЕ З ПОПЕРЕДЖЕННЯМ ПРО ЧАСОВИЙ ПРОМІЖОК
            st.markdown("""
                <div class="time-info">
                    <strong>ℹ️ Чому крок прогнозу становить 3 години?</strong><br>
                    Система використовує дані глобальних метеорологічних моделей (GFS/ECMWF) через API OpenWeather. 
                    Безкоштовні та стандартні наукові профілі надають дані з дискретністю 3 години. 
                    Це оптимальний баланс між точністю прогнозування фронтальних змін та обчислювальною потужністю серверів.
                </div>
                """, unsafe_allow_html=True)

            st.subheader(f"🛡️ Прогноз безпеки для {selected_drone}")
            
            windows = []
            for item in res['list']:
                f_dt = datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S')
                s_dt = datetime.combine(start_dt.date(), start_dt.time())
                e_dt = datetime.combine(end_dt.date(), end_dt.time())
                
                if s_dt <= f_dt <= e_dt:
                    status, score = get_safety_status(item, params)
                    windows.append({
                        "time": f_dt, "status": status, "score": score, 
                        "wind": item['wind']['speed'], "gust": item['wind'].get('gust', item['wind']['speed']),
                        "temp": item['main']['temp'], "hum": item['main']['humidity']
                    })
            
            if windows:
                # Заголовок таблиці
                header_html = """
                <div style="display: grid; grid-template-columns: 1.5fr 1fr 2fr 1.2fr; gap: 10px; padding: 10px 15px; color: #00B4D8; font-weight: bold; font-size: 0.75em; text-transform: uppercase; letter-spacing: 1.5px; border-bottom: 1px solid rgba(0, 180, 216, 0.3); margin-bottom: 5px;">
                    <div>Час місії</div>
                    <div>Рівень безпеки (%)</div>
                    <div>Погодні умови</div>
                    <div style="text-align: right;">Пориви вітру</div>
                </div>
                """
                
                rows_html = ""
                for w in windows:
                    color_class = f"bg-{w['status'].lower()}"
                    
                    reasons = []
                    if w['wind'] > params['max_wind']: reasons.append("Високий вітер")
                    if w['gust'] > params.get('max_gust', params['max_wind']+5): reasons.append("Сильні пориви")
                    if w['hum'] > params['max_humidity']: reasons.append("Висока вологість")
                    elif w['hum'] > 75: reasons.append("Підвищена вологість")
                    if w['temp'] < params['min_temp']: reasons.append("Низька темп.")
                    elif w['temp'] > params['max_temp']: reasons.append("Висока темп.")
                    
                    reason_text = ", ".join(reasons) if reasons else "У межах норми"

                    rows_html += f"""
                    <div class="window-card" style="display: grid; grid-template-columns: 1.5fr 1fr 2fr 1.2fr; gap: 10px; align-items: center;">
                        <div style="display: flex; align-items: center;">
                            <div class="indicator {color_class}"></div>
                            <div>
                                <div style="color: white; font-weight: bold; font-size: 0.95em;">{w['time'].strftime('%H:%M')} — {(w['time']+timedelta(hours=3)).strftime('%H:%M')}</div>
                                <div style="color: rgba(255,255,255,0.4); font-size: 0.75em;">{w['time'].strftime('%d.%m.%Y')}</div>
                            </div>
                        </div>
                        <div style="color: #00B4D8; font-weight: bold; font-size: 1.2em;">{int(w['score']*100)}%</div>
                        <div style="color: rgba(255,255,255,0.8); font-size: 0.85em;">{reason_text}</div>
                        <div style="text-align: right; color: white; font-weight: 500;">
                            {w['gust']} <span style="font-size: 0.8em; opacity: 0.5;">м/с</span>
                        </div>
                    </div>
                    """
                
                components.html(f'<div style="font-family: sans-serif;">{header_html}{rows_html}</div>', height=400, scrolling=True)
                
                # ГРАФІК «ЯПОНСЬКІ СВІЧКИ» (ВІТЕР ТА ПОРИВИ)
                st.markdown("### 📊 Динаміка вітрового навантаження")
                
                fig = go.Figure(data=[go.Candlestick(
                    x=[w['time'] for w in windows],
                    open=[w['wind'] for w in windows],
                    high=[w['gust'] for w in windows],
                    low=[w['wind'] * 0.8 for w in windows], # Умовний мінімум для візуалізації
                    close=[w['gust'] for w in windows],
                    increasing_line_color='#00B4D8', decreasing_line_color='#E74C3C'
                )])

                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color="white",
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=400,
                    xaxis_rangeslider_visible=False,
                    yaxis_title="м/с",
                    xaxis_title="Час"
                )
                fig.update_xaxes(gridcolor='rgba(255,255,255,0.1)')
                fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
                
                st.plotly_chart(fig, use_container_width=True)

                # Короткий підсумок
                best = [w['time'].strftime('%H:%M') for w in windows if w['status'] == "GREEN"]
                if best:
                    st.success(f"✅ Оптимальні вікна для старту: {', '.join(best[:5])}")
                else:
                    st.warning("⚠️ Немає ідеальних умов. Зверніть увагу на проміжки з помірним ризиком.")
            else:
                st.info("ℹ️ Дані для обраного періоду відсутні (максимум 5 днів вперед).")
        else:
            st.error("❌ Місто не знайдено.")
    except Exception as e:
        st.error(f"❌ Помилка: {e}")
