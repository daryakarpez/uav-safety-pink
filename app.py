import streamlit as st
import json
import requests
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# 1. КОНФІГУРАЦІЯ СТОРІНКИ ТА СТИЛІЗАЦІЯ

st.set_page_config(page_title="UAV Mission Planner", layout="wide")

# Впровадження кастомного CSS для футуристичного дизайну
st.markdown("""
    <style>
    /* Фон додатка */
    .stApp { 
        background: radial-gradient(circle at center, #001233 0%, #000000 100%); 
        font-family: 'Segoe UI', sans-serif; 
    }
    /* Стиль бічної панелі */
    [data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #000814 0%, #001D3D 100%); 
        border-right: 2px solid #00B4D8; 
    }
    /* Колір заголовків */
    h1, h2, h3, .stMarkdown { color: white !important; }
    
    /* Картка для відображення часового вікна */
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
    /* Індикатори безпеки (світлофор) */
    .indicator { width: 15px; height: 15px; border-radius: 50%; display: inline-block; margin-right: 10px; }
    .bg-green { background-color: #2ECC71; box-shadow: 0 0 10px #2ECC71; }
    .bg-yellow { background-color: #F1C40F; box-shadow: 0 0 10px #F1C40F; }
    .bg-red { background-color: #E74C3C; box-shadow: 0 0 10px #E74C3C; }
    </style>
    """, unsafe_allow_html=True)

# 2. ФУНКЦІЇ ЛОГІКИ ТА ОБРОБКИ ДАНИХ

def get_safety_status(weather_item, params):
    """
    Оцінює безпеку польоту на основі метеоданих та лімітів БПЛА.
    Повертає статус (колір) та числовий коефіцієнт безпеки.
    """
    wind = weather_item['wind']['speed']
    gust = weather_item['wind'].get('gust', wind)  # Пориви вітру якщо доступні
    temp = weather_item['main']['temp']
    hum = weather_item['main']['humidity']
    
    # 1. Перевірка критичних умов 
    if (temp < params['min_temp'] or temp > params['max_temp'] or 
        hum > params['max_humidity'] or wind > params['max_wind'] or 
        gust > params.get('max_gust', params['max_wind'] + 5)):
        return "RED", 0.0
    
    # 2. Розрахунок м'якого коефіцієнта Scoring
    # Пріоритет вітру — 70%, вологості — 30%
    k_wind = max(0, (params['max_wind'] - wind) / params['max_wind'])
    k_hum = max(0, (params['max_humidity'] - hum) / params['max_humidity'])
    score = round((k_wind * 0.7) + (k_hum * 0.3), 2)
    
    if score > 0.7: return "GREEN", score
    if score > 0.4: return "YELLOW", score
    return "RED", score

# 3. ІНІЦІАЛІЗАЦІЯ СТАНУ 

# Створення бази даних БПЛА, якщо вона ще не ініціалізована в сесії
if 'custom_drones' not in st.session_state:
    st.session_state.custom_drones = {
        "Autel EVO II": {"max_wind": 12.0, "max_gust": 17.0, "min_temp": -10.0, "max_temp": 45.0, "max_humidity": 90.0},
        "DJI Mavic 3": {"max_wind": 12.0, "max_gust": 15.0, "min_temp": -10.0, "max_temp": 40.0, "max_humidity": 85.0},
        "FPV Custom 7": {"max_wind": 15.0, "max_gust": 20.0, "min_temp": -15.0, "max_temp": 50.0, "max_humidity": 95.0}
    }

# 4. БІЧНА ПАНЕЛЬ УПРАВЛІННЯ 

st.sidebar.markdown("###  НАЛАШТУВАННЯ МІСІЇ")
city = st.sidebar.text_input("ЛОКАЦІЯ (укр/англ)", "Kyiv")

st.sidebar.markdown("---")
st.sidebar.markdown("###  ПАРАМЕТРИ БПЛА")

# Перемикач між вибором зі списку та створенням нового
drone_mode = st.sidebar.radio("Дія", ["Обрати зі списку", "Додати новий"], label_visibility="collapsed")

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
    # Тимчасові параметри для аналізу без збереження
    params = {"max_wind": m_wind, "max_gust": m_gust, "min_temp": mi_t, "max_temp": ma_t, "max_humidity": m_hum}
    selected_drone = new_name if new_name else "Нова модель"
else:
    selected_drone = st.sidebar.selectbox("ОБЕРІТЬ БПЛА", list(st.session_state.custom_drones.keys()))
    params = st.session_state.custom_drones[selected_drone]

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 ЧАСОВИЙ ПРОМІЖОК")

start_dt = st.sidebar.datetime_input("ПОЧАТОК", datetime.now())
end_dt = st.sidebar.datetime_input("ЗАВЕРШЕННЯ", datetime.now() + timedelta(hours=24))

analyze_btn = st.sidebar.button("АНАЛІЗУВАТИ БЕЗПЕКУ", use_container_width=True)

# 5. ОСНОВНИЙ БЛОК АНАЛІТИКИ

if analyze_btn:
    # API ключ та запит до OpenWeatherMap 
    api_key = "32b44eeafe4783aa188cc888cc0331c6"
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang=ua"
    
    try:
        response = requests.get(url)
        res = response.json()
        
        if "list" in res:
            st.subheader(f"🛡️ Прогноз безпеки для {selected_drone}")
            st.markdown(f"📍 **Локація:** {res['city']['name']}, {res['city']['country']}")
            st.info("ℹ️ Прогноз базується на 3-годинних інтервалах (обмеження Free API).")
            
            windows = []
            # Фільтрація отриманих даних за часом, обраним користувачем
            for item in res['list']:
                f_dt = datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S')
                s_dt = datetime.combine(start_dt.date(), start_dt.time())
                e_dt = datetime.combine(end_dt.date(), end_dt.time())
                
                if s_dt <= f_dt <= e_dt:
                    status, score = get_safety_status(item, params)
                    windows.append({
                        "time": f_dt, "status": status, "score": score, 
                        "wind": item['wind']['speed'], "gust": item['wind'].get('gust', item['wind']['speed'])
                    })
            
            if windows:
                html_content = ""
                for w in windows:
                    color_class = f"bg-{w['status'].lower()}"
                    # Текстова рекомендація
                    rec = "ОПТИМАЛЬНО" if w['status'] == "GREEN" else "ОБЕРЕЖНО" if w['status'] == "YELLOW" else "ЗАБОРОНЕНО"

                    html_content += f"""
                    <div class="window-card">
                        <div style="display: flex; align-items: center;">
                            <div class="indicator {color_class}"></div>
                            <div>
                                <div style="color: white; font-weight: bold;">{w['time'].strftime('%H:%M')} — {(w['time']+timedelta(hours=3)).strftime('%H:%M')}</div>
                                <div style="color: #00B4D8; font-size: 0.8em;">{w['time'].strftime('%d.%m.%Y')}</div>
                            </div>
                        </div>
                        <div style="color: rgba(255,255,255,0.8); font-size: 0.9em;">{rec}</div>
                        <div style="text-align: right;">
                            <div style="color: white; font-size: 0.8em;">💨 {w['wind']} (п. {w['gust']}) м/с</div>
                            <div style="color: #00B4D8; font-size: 0.8em;">🛡️ {int(w['score']*100)}%</div>
                        </div>
                    </div>
                    """
                components.html(f"<div style='font-family: sans-serif;'>{html_content}</div>", height=500, scrolling=True)
                
                # Фінальний вердикт
                best_times = [w['time'].strftime('%H:%M') for w in windows if w['status'] == "GREEN"]
                if best_times:
                    st.success(f"✅ Рекомендований старт: {', '.join(best_times[:4])}")
                else:
                    st.warning("⚠️ Ідеальних умов не знайдено. Зверніть увагу на 'жовті' проміжки.")
            else:
                st.warning("⚠️ Немає даних для обраного періоду. Оберіть час у межах наступних 5 днів.")
        else:
            st.error("❌ Помилка: Місто не знайдено. Перевірте написання.")
            
    except Exception as e:
        st.error(f"❌ Критична помилка: {e}")
