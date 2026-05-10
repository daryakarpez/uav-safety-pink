if windows:
                # 1. Створюємо заголовок таблиці
                header_html = """
                <div style="display: grid; grid-template-columns: 1.5fr 1fr 2fr 1.2fr; gap: 10px; padding: 10px 15px; color: #00B4D8; font-weight: bold; font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid rgba(0, 180, 216, 0.3); margin-bottom: 10px;">
                    <div>Час місії</div>
                    <div>Рівень безпеки (%)</div>
                    <div>Погодні умови</div>
                    <div style="text-align: right;">Пориви вітру</div>
                </div>
                """
                
                html_content = header_html
                
                for w in windows:
                    color_class = f"bg-{w['status'].lower()}"
                    
                    # Логіка причин обмеження та уточнення вологості
                    reasons = []
                    if w['wind'] > params['max_wind']: 
                        reasons.append("Високий вітер")
                    if w['gust'] > params.get('max_gust', params['max_wind']+5): 
                        reasons.append("Сильні пориви")
                    if w['temp'] < params['min_temp']: 
                        reasons.append("Низька темп.")
                    elif w['temp'] > params['max_temp']: 
                        reasons.append("Висока темп.")
                    
                    # Уточнення вологості (якщо вона є причиною або близька до критичної)
                    if w['hum'] > params['max_humidity']:
                        reasons.append("Висока вологість")
                    elif w['hum'] > 70: # Наприклад, просто інформативно, якщо вологість висока
                        if not reasons: reasons.append("Підвищена вологість")

                    reason_text = ", ".join(reasons) if reasons else "У межах норми"
                    
                    # Генеруємо рядок таблиці
                    html_content += f"""
                    <div class="window-card" style="display: grid; grid-template-columns: 1.5fr 1fr 2fr 1.2fr; gap: 10px; align-items: center; border-radius: 0; border: none; border-bottom: 1px solid rgba(255,255,255,0.05); margin-bottom: 0;">
                        <div style="display: flex; align-items: center;">
                            <div class="indicator {color_class}"></div>
                            <div>
                                <div style="color: white; font-weight: bold; font-size: 0.95em;">
                                    {w['time'].strftime('%H:%M')} — {(w['time']+timedelta(hours=3)).strftime('%H:%M')}
                                </div>
                                <div style="color: rgba(255,255,255,0.4); font-size: 0.75em;">{w['time'].strftime('%d.%m.%Y')}</div>
                            </div>
                        </div>

                        <div>
                            <div style="color: #00B4D8; font-weight: bold; font-size: 1.2em;">{int(w['score']*100)}%</div>
                        </div>

                        <div style="color: rgba(255,255,255,0.8); font-size: 0.85em;">
                            {reason_text}
                        </div>

                        <div style="text-align: right;">
                            <div style="color: white; font-size: 1.1em; font-weight: 500;">{w['gust']} <span style="font-size: 0.7em; opacity: 0.6;">м/с</span></div>
                        </div>
                    </div>
                    """
                
                # Вивід фінального HTML
                components.html(f'<div style="font-family: sans-serif; background: transparent;">{html_content}</div>', height=550, scrolling=True)
