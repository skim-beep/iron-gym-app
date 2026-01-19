import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from streamlit_option_menu import option_menu
import base64
from streamlit_calendar import calendar  # БИБЛИОТЕКА КАЛЕНДАРЯ

# --- 1. НАСТРОЙКИ ---
st.set_page_config(
    page_title="IRON GYM OS",
    page_icon="🦅",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- 2. КОНФИГУРАЦИЯ (CAMO THEME) ---
CAMO_DARK = "#121212"
CAMO_PANEL = "#1E1E1E"
CAMO_GREEN = "#4b5320"
ACCENT_GOLD = "#FFD700"
ACCENT_SILVER = "#C0C0C0"
TEXT_COLOR = "#E0E0E0"
ALERT_RED = "#500000" # Темно-красный для пропусков

AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. ШЕВРОНЫ (SVG) ---
def get_rank_svg(rank_type, grade):
    color = ACCENT_GOLD
    if rank_type == "OFFICER":
        if grade in [1, 2, 4, 5] or grade >= 6: color = ACCENT_SILVER
    
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 100 100" fill="none" stroke="{color}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round">'
    
    if rank_type == "ENLISTED":
        chevrons = min(grade + 1, 3) if grade < 3 else 3
        rockers = 0
        if grade >= 3: rockers = 1 
        if grade >= 5: rockers = 2
        if grade >= 7: rockers = 3
        for i in range(chevrons): svg += f'<path d="M15,{35 + (i * 15)} L50,{10 + (i * 15)} L85,{35 + (i * 15)}" />'
        for i in range(rockers): svg += f'<path d="M15,{55 + (i * 12)} Q50,{80 + (i * 12)} 85,{55 + (i * 12)}" />'
            
    elif rank_type == "OFFICER":
        if grade <= 1: svg += f'<rect x="40" y="20" width="20" height="60" fill="{color}" stroke="none"/>'
        elif grade == 2: svg += f'<rect x="25" y="20" width="15" height="60" fill="{color}" stroke="none"/> <rect x="60" y="20" width="15" height="60" fill="{color}" stroke="none"/>'
        elif grade <= 4: svg += f'<path d="M50,15 Q80,15 80,45 Q80,75 50,90 Q20,75 20,45 Q20,15 50,15 Z" fill="{color}" stroke="none"/>'
        elif grade == 5: svg += f'<path d="M10,40 L50,20 L90,40 L80,70 L50,90 L20,70 Z" fill="{color}" stroke="none"/>'
        elif grade >= 6: svg += f'<circle cx="50" cy="50" r="15" fill="{color}" stroke="none"/>'

    svg += '</svg>'
    b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"

FULL_RANK_SYSTEM = [
    (0, 24, "РЕКРУТ", "PV1", "ENLISTED", 0), (25, 49, "РЯДОВОЙ", "PV2", "ENLISTED", 1),
    (50, 99, "РЯДОВОЙ 1 КЛ", "PFC", "ENLISTED", 2), (100, 149, "СПЕЦИАЛИСТ", "SPC", "ENLISTED", 3),
    (150, 199, "КАПРАЛ", "CPL", "ENLISTED", 3), (200, 299, "СЕРЖАНТ", "SGT", "ENLISTED", 4),
    (300, 399, "ШТАБ-СЕРЖАНТ", "SSG", "ENLISTED", 5), (400, 499, "СЕРЖАНТ 1 КЛ", "SFC", "ENLISTED", 6),
    (500, 649, "МАСТЕР-СЕРЖАНТ", "MSG", "ENLISTED", 7), (650, 799, "1-Й СЕРЖАНТ", "1SG", "ENLISTED", 7),
    (800, 999, "СЕРЖАНТ-МАЙОР", "SGM", "ENLISTED", 8), (1000, 1499, "2-Й ЛЕЙТЕНАНТ", "2LT", "OFFICER", 0),
    (1500, 1999, "1-Й ЛЕЙТЕНАНТ", "1LT", "OFFICER", 1), (2000, 2999, "КАПИТАН", "CPT", "OFFICER", 2),
    (3000, 3999, "МАЙОР", "MAJ", "OFFICER", 3), (4000, 4999, "ПОДПОЛКОВНИК", "LTC", "OFFICER", 4),
    (5000, 5999, "ПОЛКОВНИК", "COL", "OFFICER", 5), (6000, 7999, "БРИГАДНЫЙ ГЕНЕРАЛ", "BG", "OFFICER", 6),
    (8000, 9999, "ГЕНЕРАЛ-МАЙОР", "MG", "OFFICER", 7), (10000, 14999, "ГЕНЕРАЛ-ЛЕЙТЕНАНТ", "LTG", "OFFICER", 8),
    (15000, 24999, "ГЕНЕРАЛ", "GEN", "OFFICER", 9), (25000, 999999, "ГЕНЕРАЛ АРМИИ", "GA", "OFFICER", 10)
]

# --- 4. ФУНКЦИИ ---
def get_rank_data(xp):
    for r_min, r_max, title, abbr, r_type, grade in FULL_RANK_SYSTEM:
        if r_min <= xp <= r_max:
            needed = r_max - r_min + 1
            current = xp - r_min
            percent = int((current / needed) * 100)
            return {"title": title, "abbr": abbr, "icon": get_rank_svg(r_type, grade), "progress": percent, "next_xp_total": r_max + 1, "xp_needed": needed - current}
    return {"title": "ГЕНЕРАЛ АРМИИ", "abbr": "GA", "icon": get_rank_svg("OFFICER", 10), "progress": 100, "next_xp_total": xp, "xp_needed": 0}

def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def detect_muscle_group(exercise_name):
    ex = str(exercise_name).lower()
    if any(x in ex for x in ['жим лежа', 'жим гантелей', 'бабочка', 'chest', 'отжимания', 'брусья', 'груд']): return "ГРУДЬ"
    if any(x in ex for x in ['тяга', 'подтягивания', 'спина', 'back', 'row', 'становая']): return "СПИНА"
    if any(x in ex for x in ['присед', 'ноги', 'выпады', 'legs', 'squat', 'разгибания']): return "НОГИ"
    if any(x in ex for x in ['бицепс', 'трицепс', 'молот', 'arms', 'bicep', 'концентрированный']): return "РУКИ"
    if any(x in ex for x in ['жим стоя', 'плечи', 'махи', 'shouder', 'press', 'разведение']): return "ПЛЕЧИ"
    if any(x in ex for x in ['пресс', 'планка', 'abs', 'core', 'скручивания']): return "ПРЕСС"
    return "ОБЩЕЕ"

# --- 5. CSS ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500&display=swap');

    .stApp {{ background-color: {CAMO_DARK}; color: {TEXT_COLOR}; font-family: 'Roboto Mono', monospace; }}
    #MainMenu, footer, header {{ visibility: hidden; }}

    h1, h2, h3, .tac-font {{ font-family: 'Oswald', sans-serif !important; letter-spacing: 1px; text-transform: uppercase; }}
    
    .camo-card {{
        background-color: {CAMO_PANEL}; border: 1px solid #333; border-left: 4px solid {CAMO_GREEN};
        padding: 15px; margin-bottom: 20px; border-radius: 4px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    }}

    .avatar-area {{ width: 80px; height: 80px; border: 2px solid {ACCENT_GOLD}; border-radius: 50%; overflow: hidden; float: left; margin-right: 15px; }}
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    .user-name {{ font-family: 'Oswald', sans-serif; font-size: 28px; color: #FFF; margin: 0; line-height: 1.1; }}
    .progress-track {{ width: 100%; height: 8px; background: #111; margin-top: 8px; }}
    .progress-fill {{ height: 100%; background: {CAMO_GREEN}; }}
    .stat-badge {{ background: #111; color: {ACCENT_GOLD}; padding: 3px 8px; border: 1px solid {CAMO_GREEN}; font-size: 11px; margin-right: 5px; font-family: 'Oswald'; }}

    .tac-header {{
        font-family: 'Oswald', sans-serif; font-size: 18px; color: {TEXT_COLOR};
        border-bottom: 2px solid {CAMO_GREEN}; padding-bottom: 5px; margin: 20px 0 10px 0; text-transform: uppercase;
    }}

    .streamlit-expanderHeader {{ background-color: {CAMO_PANEL} !important; color: {ACCENT_GOLD} !important; border: 1px solid #333 !important; font-family: 'Oswald' !important; }}
    
    input, textarea, select {{ background: #111 !important; color: {ACCENT_GOLD} !important; border: 1px solid #444 !important; font-family: 'Roboto Mono' !important; }}
    
    /* Кнопки */
    div.stButton > button {{ border: 1px solid {CAMO_GREEN}; background: #1a1a1a; color: {TEXT_COLOR}; font-family: 'Oswald'; }}
    </style>
""", unsafe_allow_html=True)

# --- 6. ЗАГРУЗКА ДАННЫХ ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["service_account_json"], strict=False), scope)
    client = gspread.authorize(creds)
    sheet = client.open("IRON_GYM_DB").sheet1
    raw_data = sheet.get_all_records()
    df = pd.DataFrame(raw_data) if raw_data else pd.DataFrame()
    
    if not df.empty:
        df.columns = df.columns.str.strip()
        for col in ['Вес (кг)', 'Тоннаж']:
            if col in df.columns: df[col] = df[col].astype(str).str.replace(',', '.')
        df['Вес (кг)'] = pd.to_numeric(df['Вес (кг)'], errors='coerce').fillna(0)
        df['Повт'] = pd.to_numeric(df['Повт'], errors='coerce').fillna(0)
        if 'Сет' not in df.columns: df['Сет'] = "-"
        df['Сет'] = df['Сет'].astype(str).replace('', '-')
        df['День/Дата'] = pd.to_datetime(df['День/Дата'], errors='coerce')
        df = df.dropna(subset=['День/Дата'])
        df['Muscle'] = df['Упражнение'].apply(detect_muscle_group)
except: df = pd.DataFrame()

total_xp = len(df)
rank = get_rank_data(total_xp)
user_age = calculate_age(USER_BIRTHDAY)
# Список уникальных дат тренировок (строки YYYY-MM-DD)
trained_dates_set = set(df['День/Дата'].dt.strftime('%Y-%m-%d')) if not df.empty else set()

# --- 7. ПРОФИЛЬ ---
st.markdown(f"""
<div class="camo-card" style="display:flex; align-items:center;">
    <div class="avatar-area"><img src="{AVATAR_URL}" class="avatar-img"></div>
    <div style="flex-grow:1;">
        <div class="user-name">СЕРГЕЙ</div>
        <div style="margin: 5px 0;">
            <span class="stat-badge">LVL: {total_xp}</span>
            <span class="stat-badge">{rank['title']}</span>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width: {rank['progress']}%;"></div></div>
        <div style="font-size:10px; color:#666; text-align:right; font-family:'Roboto Mono';">NEXT: {rank['xp_needed']} XP</div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander(f"{rank['title']} // {rank['abbr']} (СПИСОК)"):
    for r_min, r_max, title, abbr, r_type, grade in FULL_RANK_SYSTEM:
        bg = "background-color:rgba(255,215,0,0.1); border-left:2px solid #FFD700;" if title == rank['title'] else ""
        col = ACCENT_GOLD if title == rank['title'] else "#777"
        st.markdown(f"""<div style="display:flex; align-items:center; padding:8px; border-bottom:1px solid #333; {bg}">
            <img src="{get_rank_svg(r_type, grade)}" style="height:25px; margin-right:10px;">
            <div style="flex-grow:1; color:{col}; font-family:'Oswald';">{title}</div>
            <div style="font-family:'Roboto Mono'; font-size:10px; color:#555;">{r_min}</div>
        </div>""", unsafe_allow_html=True)

# --- 8. МЕНЮ ---
selected = option_menu(
    menu_title=None,
    options=["ДАШБОРД", "ЖУРНАЛ", "ТРЕНЕР"],
    icons=["crosshair", "list-task", "robot"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent", "margin-bottom": "20px"},
        "nav-link": {"font-size": "13px", "color": "#777", "margin": "0px", "font-family": "Oswald"},
        "nav-link-selected": {"background-color": CAMO_GREEN, "color": "#FFF"},
    }
)

# --- 9. ДАШБОРД ---
if selected == "ДАШБОРД":
    
    # 1. РАДАР
    st.markdown('<div class="tac-header">СТАТУС БРОНИ</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    
    # Инициализация даты фильтра
    if 'cal_sel_date' not in st.session_state:
        st.session_state.cal_sel_date = None

    filtered_df = df.copy()
    filter_msg = "ОБЩАЯ СТАТИСТИКА"
    
    if st.session_state.cal_sel_date:
        sel_d = st.session_state.cal_sel_date
        # Фильтруем данные (переводим строку YYYY-MM-DD в дату)
        filtered_df = df[df['День/Дата'].dt.strftime('%Y-%m-%d') == sel_d]
        filter_msg = f"ОТЧЕТ ЗА: {sel_d}"
        if st.button("❌ СБРОСИТЬ ФИЛЬТР"):
            st.session_state.cal_sel_date = None
            st.rerun()

    st.markdown(f"<div style='text-align:center; color:{ACCENT_GOLD}; font-family:Oswald; margin-bottom:5px;'>{filter_msg}</div>", unsafe_allow_html=True)

    if not filtered_df.empty:
        muscle_data = filtered_df.groupby('Muscle')['Сет'].count().reset_index()
        muscle_data.columns = ['Muscle', 'Sets']
        target_muscles = ["ГРУДЬ", "СПИНА", "НОГИ", "РУКИ", "ПЛЕЧИ", "ПРЕСС"]
        radar_df = pd.DataFrame({"Muscle": target_muscles})
        radar_df = radar_df.merge(muscle_data, on="Muscle", how="left").fillna(0)
        
        fig = go.Figure(data=go.Scatterpolar(
            r=radar_df['Sets'], theta=radar_df['Muscle'], fill='toself',
            line=dict(color=ACCENT_GOLD, width=2),
            fillcolor='rgba(255, 215, 0, 0.2)',
            marker=dict(color=ACCENT_GOLD, size=6)
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=False, linecolor='#333'),
                angularaxis=dict(linecolor='#333', tickfont=dict(color=TEXT_COLOR, size=11, family="Oswald")),
                bgcolor='rgba(0,0,0,0)'
            ),
            showlegend=False, height=250, margin=dict(l=35, r=35, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF')
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
    else: st.info("Нет данных")
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. ПРОФЕССИОНАЛЬНЫЙ КАЛЕНДАРЬ
    st.markdown('<div class="tac-header">КАЛЕНДАРЬ МИССИЙ</div>', unsafe_allow_html=True)
    
    # Генерация событий для календаря
    calendar_events = []
    
    # Чтобы найти пропущенные дни, возьмем диапазон от первой тренировки до сегодня
    if not df.empty:
        min_date = df['День/Дата'].min().date()
        today = date.today()
        # Генерируем все дни от начала до сегодня
        all_days = [min_date + timedelta(days=x) for x in range((today - min_date).days + 1)]
        
        for d in all_days:
            d_str = d.strftime("%Y-%m-%d")
            if d_str in trained_dates_set:
                # ТРЕНИРОВКА (ЗЕЛЕНЫЙ)
                calendar_events.append({
                    "title": "✅",
                    "start": d_str,
                    "backgroundColor": CAMO_GREEN,
                    "borderColor": ACCENT_GOLD,
                    "display": "background"
                })
            else:
                # ПРОПУСК (КРАСНЫЙ) - только если это день в прошлом
                calendar_events.append({
                    "title": "❌",
                    "start": d_str,
                    "backgroundColor": ALERT_RED,
                    "borderColor": "#330000",
                    "display": "background"
                })

    # Опции календаря
    cal_options = {
        "headerToolbar": {
            "left": "prev,next",
            "center": "title",
            "right": "today"
        },
        "initialView": "dayGridMonth",
        "selectable": True, # Разрешаем клик
    }
    
    # Стилизация календаря через CSS инъекцию внутрь компонента
    custom_css = f"""
        .fc {{ background-color: {CAMO_PANEL}; font-family: 'Oswald', sans-serif; }}
        .fc-theme-standard td, .fc-theme-standard th {{ border-color: #333; }}
        .fc-col-header-cell {{ background-color: #111; color: {ACCENT_GOLD}; }}
        .fc-daygrid-day-number {{ color: {TEXT_COLOR}; text-decoration: none; }}
        .fc-day-today {{ background-color: rgba(255, 215, 0, 0.1) !important; border: 2px solid {ACCENT_GOLD} !important; }}
        .fc-button-primary {{ background-color: #111; border-color: {CAMO_GREEN}; color: {ACCENT_GOLD}; text-transform: uppercase; }}
        .fc-button-primary:hover {{ background-color: {CAMO_GREEN}; color: white; }}
        .fc-button-active {{ background-color: {CAMO_GREEN} !important; color: white !important; }}
    """

    cal = calendar(events=calendar_events, options=cal_options, custom_css=custom_css, key="tactical_cal")
    
    # Обработка клика
    if cal.get("callback") == "dateClick":
        clicked_date = cal["dateClick"]["date"]
        # Обновляем состояние только если дата изменилась
        if st.session_state.cal_sel_date != clicked_date:
            st.session_state.cal_sel_date = clicked_date
            st.rerun()

    # 3. ТАБЛИЦА
    st.markdown('<div class="tac-header">ЖУРНАЛ</div>', unsafe_allow_html=True)
    if not filtered_df.empty:
        hdf = filtered_df.copy().sort_values(by=['День/Дата', 'Сет'], ascending=[False, True])
        hdf['День/Дата'] = hdf['День/Дата'].dt.strftime('%d.%m')
        st.dataframe(hdf[['День/Дата', 'Сет', 'Упражнение', 'Вес (кг)', 'Повт']], use_container_width=True, hide_index=True)

# --- ЖУРНАЛ ---
elif selected == "ЖУРНАЛ":
    st.markdown('<div class="tac-header">НОВАЯ ЗАПИСЬ</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    with st.form("entry"):
        d = st.date_input("ДАТА")
        c1, c2 = st.columns([1,2])
        with c1: s_grp = st.text_input("СЕТ", "№1")
        with c2: ex_name = st.text_input("УПРАЖНЕНИЕ")
        c3, c4, c5 = st.columns(3)
        with c3: s_num = st.number_input("ПОДХОД", 1)
        with c4: w_val = st.number_input("ВЕС", step=2.5)
        with c5: r_val = st.number_input("ПОВТ", 1)
        c6, c7 = st.columns(2)
        with c6: tech = st.text_input("ТЕХНИКА")
        with c7: comm = st.text_input("КОММЕНТ")
        if st.form_submit_button("СОХРАНИТЬ"):
            try:
                sheet.append_row([d.strftime("%Y-%m-%d"), s_grp, ex_name, s_num, w_val, r_val, w_val*r_val, tech, comm])
                st.success("OK")
                st.rerun()
            except: st.error("ERR")
    st.markdown('</div>', unsafe_allow_html=True)

elif selected == "ТРЕНЕР":
    st.markdown(f'<div class="tac-header">ИНСТРУКТОР // {rank["abbr"]}</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    if p := st.chat_input("..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        res = model.generate_content(f"Армейский тренер. Звание: {rank['title']}. Вопрос: {p}")
        with st.chat_message("assistant"): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
    st.markdown('</div>', unsafe_allow_html=True)
