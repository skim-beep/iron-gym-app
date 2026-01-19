import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.graph_objects as go
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import calendar
from streamlit_option_menu import option_menu
import base64

# --- 1. НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="IRON GYM OS",
    page_icon="🦅",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- 2. НАСТРОЙКИ И ВЕЧНЫЕ ИКОНКИ (BASE64) ---
AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 
ACCENT_COLOR = "#D4AF37" # Золото
ARMY_GREEN = "#6B7A57"   # Хаки для тренировок
MUTED_RED = "#A95C5C"    # Приглушенный красный для пропусков

# Вшитые иконки (никогда не сломаются)
ICON_STAR = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMTAwIDEwMCI+PHBvbHlnb24gcG9pbnRzPSI1MCw1IDYxLDM1IDk1LDM1IDY3LDU1IDc5LDkwIDUwLDcwIDIxLDkwIDMzLDU1IDUsMzUgMzksMzUiIGZpbGw9IiNENEFGMzciIHN0cm9rZT0iIzFDMUMxRSIgc3Ryb2rZS13aWR0aD0iMiIvPjwvc3ZnPg=="
ICON_PV2 = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMTAwIDEwMCI+PHBhdGggZD0iTTUsNDAgTDUwLDE1IEw5NSw0MCBMNTAsNjUgWl0iIGZpbGw9IiNENEFGMzciIHN0cm9rZT0iIzFDMUMxRSIgc3Ryb2rZS13aWR0aD0iMiIvPjwvc3ZnPg=="
ICON_PFC = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMTAwIDEwMCI+PHBhdGggZD0iTTUsMzAgTDUwLDUgTDk1LDMwIEw5NSw1MCBMNTAsNzUgTDUsNTAgWl0iIGZpbGw9IiNENEFGMzciIHN0cm9rZT0iIzFDMUMxRSIgc3Ryb2rZS13aWR0aD0iMiIvPjwvc3ZnPg=="
ICON_SPC = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMTAwIDEwMCI+PHBhdGggZD0iTTUwLDUgTDk1LDMwIEw5NSw3MCBMNTAsOTUgTDUsNzAgTDUsMzAgWl0iIGZpbGw9IiNENEFGMzciIHN0cm9rZT0iIzFDMUMxRSIgc3Ryb2rZS13aWR0aD0iMiIvPjxwYXRoIGQ9Ii01LDQwIEw1MCwxNSBMOTUsNDAgTDUwLDY1IFpNMzAsNDAgTDUwLDMwIEw3MCw0MCBMNTAsNTAgWl0iIGZpbGw9IiNENEFGMzciIHN0cm9rZT0iIzFDMUMxRSIgc3Ryb2rZS13aWR0aD0iMSIvPjwvc3ZnPg=="
ICON_SGT = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMTAwIDEwMCI+PHBhdGggZD0iTTUsMjAgTDUwLDUgTDk1LDIwIEw5NSwzNSBMNTAsMjAgTDUsMzUgWl0gTTUsNDAgTDUwLDI1IEw5NSw0MCBMOTNSw1NSBMNTAsNDAgTDUsNTUgWl0gTTUsNjAgTDUwLDQ1IEw5NSw2MCBMOTUsNzUgTDUwLDYwIEw1LDc1IFpNMjAsNzAgTDUwLDg1IEw4MCw3MCIgZmlsbD0iI0Q0QUYzNyIgc3Ryb2rZT0iIzFDMUMxRSIgc3Ryb2rZS13aWR0aD0iMiIvPjwvc3ZnPg=="
ICON_OFFICER = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMTAwIDEwMCI+PHJlY3QgeD0iMzAiIHk9IjIwIiB3aWR0aD0iNDAiIGhlaWdodD0iNjAiIGZpbGw9IiNENEFGMzciIHN0cm9rZT0iIzFDMUMxRSIgc3Ryb2rZS13aWR0aD0iMiIvPjwvc3ZnPg=="

# --- 3. СИСТЕМА ЗВАНИЙ (РУССКИЙ) ---
RANK_SYSTEM = [
    (0, 9, "РЕКРУТ", "PV1", ICON_STAR),
    (10, 24, "РЯДОВОЙ", "PV2", ICON_PV2),
    (25, 49, "РЯДОВОЙ 1 КЛАССА", "PFC", ICON_PFC),
    (50, 74, "СПЕЦИАЛИСТ", "SPC", ICON_SPC),
    (75, 99, "СЕРЖАНТ", "SGT", ICON_SGT),
    (100, 129, "ШТАБ-СЕРЖАНТ", "SSG", ICON_SGT), # Используем SGT за неимением другого
    (130, 159, "СЕРЖАНТ 1 КЛАССА", "SFC", ICON_SGT),
    (160, 9999, "ОФИЦЕР", "CMD", ICON_OFFICER)
]

# --- 4. ФУНКЦИИ ---
def get_rank_data(xp):
    for r_min, r_max, title, abbr, icon in RANK_SYSTEM:
        if r_min <= xp <= r_max:
            needed = r_max - r_min + 1
            current = xp - r_min
            percent = int((current / needed) * 100)
            to_go = r_max - xp + 1
            return {"title": title, "abbr": abbr, "icon": icon, "progress": percent, "next_xp": to_go}
    return {"title": "ЛЕГЕНДА", "abbr": "GOD", "icon": ICON_OFFICER, "progress": 100, "next_xp": 0}

def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def detect_muscle_group(exercise_name):
    ex = str(exercise_name).lower()
    if any(x in ex for x in ['жим лежа', 'жим гантелей', 'бабочка', 'chest', 'отжимания', 'брусья', 'груд', 'жим в тренажере']): return "ГРУДЬ"
    if any(x in ex for x in ['тяга', 'подтягивания', 'спина', 'back', 'row', 'становая']): return "СПИНА"
    if any(x in ex for x in ['присед', 'ноги', 'выпады', 'legs', 'squat', 'разгибания', 'сгибания']): return "НОГИ"
    if any(x in ex for x in ['бицепс', 'трицепс', 'молот', 'arms', 'bicep', 'концентрированный']): return "РУКИ"
    if any(x in ex for x in ['жим стоя', 'плечи', 'махи', 'shouder', 'press', 'разведение']): return "ПЛЕЧИ"
    if any(x in ex for x in ['пресс', 'планка', 'abs', 'core', 'скручивания']): return "ПРЕСС"
    return "ОБЩЕЕ"

# --- 5. CSS СТИЛЬ "СВЕТЛОЕ СТЕКЛО" ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&display=swap');

    .stApp {{
        background-color: #EEF2F7; /* Очень светлый серо-голубой фон */
        font-family: 'Inter', sans-serif;
        color: #1C1C1E;
    }}
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* СТЕКЛЯННАЯ ПЛИТКА */
    .glass-tile {{
        background: rgba(255, 255, 255, 0.7); /* Полупрозрачный белый */
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.8);
        padding: 20px;
        margin-bottom: 20px;
    }}

    /* ПРОФИЛЬ */
    .profile-card {{ display: flex; align-items: center; }}
    .avatar-area {{
        width: 80px; height: 80px; border-radius: 50%; border: 2px solid {ACCENT_COLOR}; 
        overflow: hidden; margin-right: 20px; flex-shrink: 0; box-shadow: 0 4px 10px rgba(212, 175, 55, 0.2);
    }}
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    .info-area {{ flex-grow: 1; }}
    .user-name {{
        font-family: 'Black Ops One', cursive; font-size: 26px; color: {ACCENT_COLOR}; 
        letter-spacing: 1px; margin: 0; text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }}
    .rank-row {{ display: flex; align-items: center; margin-bottom: 8px; }}
    .rank-title {{ color: #555; font-weight: 700; margin-right: 10px; font-size: 14px; }}
    .rank-icon-img {{ height: 30px; width: auto; object-fit: contain; }}
    
    .progress-track {{
        width: 100%; height: 8px; background: rgba(0,0,0,0.05); border-radius: 4px; overflow: hidden; margin-top: 5px;
    }}
    .progress-fill {{ height: 100%; background: linear-gradient(90deg, {ACCENT_COLOR}, #F0E68C); }}
    .xp-text {{ font-size: 10px; color: #777; float: right; margin-top: 2px; font-weight: 600; }}

    .stat-badge {{
        background: rgba(255,255,255,0.5); padding: 4px 10px; border-radius: 8px; font-size: 11px; 
        font-weight: 600; color: #333; margin-right: 5px; display: inline-flex; align-items: center; border: 1px solid rgba(0,0,0,0.05);
    }}

    /* ЗАГОЛОВКИ */
    .section-title {{
        font-family: 'Black Ops One', cursive;
        font-size: 16px; color: #333; text-transform: uppercase; letter-spacing: 1px; margin: 25px 0 10px 0;
        padding-left: 10px; border-left: 3px solid {ACCENT_COLOR};
    }}

    /* КНОПКИ */
    div.stButton > button {{
        width: 100%; background: rgba(255,255,255,0.8); color: {ACCENT_COLOR}; border: 1px solid {ACCENT_COLOR};
        border-radius: 12px; padding: 12px; font-weight: 700; transition: 0.2s;
    }}
    div.stButton > button:hover {{ background: {ACCENT_COLOR}; color: white; }}
    div.stButton > button:active {{ transform: scale(0.98); }}

    /* КАЛЕНДАРЬ - КНОПКИ ДНЕЙ */
    .cal-btn {{
        width: 100%; height: 45px; border-radius: 10px; border: none; font-weight: 700; font-size: 14px;
        color: #333; background: rgba(255,255,255,0.5); box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        cursor: pointer; transition: 0.2s;
    }}
    .cal-btn:hover {{ background: rgba(255,255,255,0.8); }}
    .cal-btn.trained {{ background: {ARMY_GREEN}; color: white; }}
    .cal-btn.missed {{ background: {MUTED_RED}; color: white; }}
    .cal-btn.today {{ border: 2px solid {ACCENT_COLOR}; color: {ACCENT_COLOR}; background: rgba(212, 175, 55, 0.1); }}
    .cal-btn.empty {{ background: transparent; box-shadow: none; cursor: default; }}
    
    /* ПОЛЯ ВВОДА В СТЕКЛЕ */
    div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {{
        background-color: rgba(255,255,255,0.5) !important; 
        border: 1px solid rgba(0,0,0,0.1) !important;
        backdrop-filter: blur(5px);
    }}
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
        df['Тоннаж'] = pd.to_numeric(df['Тоннаж'], errors='coerce').fillna(0)
        if 'Сет' not in df.columns: df['Сет'] = "-"
        df['Сет'] = df['Сет'].astype(str).replace('', '-')
        df['День/Дата'] = pd.to_datetime(df['День/Дата'], errors='coerce')
        df = df.dropna(subset=['День/Дата'])
        df['Muscle'] = df['Упражнение'].apply(detect_muscle_group)
except Exception as e:
    df = pd.DataFrame()

# Статистика
total_xp = len(df)
rank = get_rank_data(total_xp)
user_age = calculate_age(USER_BIRTHDAY)
trained_dates = set(df['День/Дата'].dt.date) if not df.empty else set()

# --- 7. ПРОФИЛЬ И СПИСОК ЗВАНИЙ ---
st.markdown(f"""
<div class="glass-tile profile-card">
    <div class="avatar-area"><img src="{AVATAR_URL}" class="avatar-img"></div>
    <div class="info-area">
        <div class="user-name">СЕРГЕЙ</div>
        <div class="rank-row">
            <span class="rank-title">{rank['title']}</span>
            <img src="{rank['icon']}" class="rank-icon-img">
        </div>
        <div class="progress-track"><div class="progress-fill" style="width: {rank['progress']}%;"></div></div>
        <div style="margin-top:4px;">
            <span class="stat-badge">ОПЫТ: {total_xp}</span>
            <span class="xp-text">СЛЕД. ЗВАНИЕ ЧЕРЕЗ: {rank['next_xp']}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander("📜 ПОСМОТРЕТЬ ВСЕ ЗВАНИЯ И ШЕВРОНЫ"):
    for r_min, r_max, title, abbr, icon in RANK_SYSTEM:
        st.markdown(f"""
        <div style="display:flex; align-items:center; margin-bottom:10px; padding: 5px; border-bottom: 1px solid rgba(0,0,0,0.05);">
            <img src="{icon}" style="height:40px; width:auto; margin-right:15px;">
            <div>
                <div style="font-weight:bold; color:#333;">{title} ({abbr})</div>
                <div style="font-size:12px; color:#777;">Миссий: {r_min} - {r_max}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- 8. МЕНЮ (РУССКОЕ, КОРОТКОЕ) ---
selected = option_menu(
    menu_title=None,
    options=["ДАШБОРД", "ЖУРНАЛ", "ТРЕНЕР"],
    icons=["bar-chart-fill", "journal-richtext", "cpu-fill"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent", "margin-bottom": "20px"},
        "nav-link": {"font-size": "12px", "color": "#333", "margin": "2px", "--hover-color": "rgba(212, 175, 55, 0.2)"},
        "nav-link-selected": {"background-color": ACCENT_COLOR, "color": "#FFF"},
    }
)

# --- 9. ДАШБОРД (ИНТЕРАКТИВНЫЙ) ---
if selected == "ДАШБОРД":
    
    # Инициализация состояний календаря
    if 'c_year' not in st.session_state: st.session_state.c_year = date.today().year
    if 'c_month' not in st.session_state: st.session_state.c_month = date.today().month
    if 'selected_date' not in st.session_state: st.session_state.selected_date = None

    # --- КАЛЕНДАРЬ (ИНТЕРАКТИВНЫЙ БЛОК) ---
    st.markdown('<div class="section-title">ТАКТИЧЕСКИЙ КАЛЕНДАРЬ</div>', unsafe_allow_html=True)
    calendar_container = st.container()
    with calendar_container:
        st.markdown('<div class="glass-tile">', unsafe_allow_html=True)
        
        # Навигация месяца
        c1, c2, c3 = st.columns([1, 4, 1])
        def change_m(d):
            m = st.session_state.c_month + d
            y = st.session_state.c_year
            if m > 12: m = 1; y += 1
            elif m < 1: m = 12; y -= 1
            st.session_state.c_month = m
            st.session_state.c_year = y
            # Не сбрасываем выбранную дату при переключении месяца, чтобы можно было смотреть историю
        
        with c1: st.button("◀", on_click=change_m, args=(-1,), key="prev_m")
        with c2:
            m_name = calendar.month_name[st.session_state.c_month].upper()
            st.markdown(f"<div style='text-align:center; font-family:\"Black Ops One\"; font-size:18px; color:#333; padding-top:10px;'>{m_name} {st.session_state.c_year}</div>", unsafe_allow_html=True)
        with c3: st.button("▶", on_click=change_m, args=(1,), key="next_m")

        # Сетка календаря на кнопках
        cal = calendar.monthcalendar(st.session_state.c_year, st.session_state.c_month)
        today = date.today()
        
        # Заголовки дней недели
        cols = st.columns(7)
        days_header = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
        for i, col in enumerate(cols):
            col.markdown(f"<div style='text-align:center; font-size:11px; color:#777; margin-bottom:5px;'>{days_header[i]}</div>", unsafe_allow_html=True)

        # Генерация кнопок дней
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0:
                    cols[i].markdown('<div class="cal-btn empty"></div>', unsafe_allow_html=True)
                else:
                    curr_date = date(st.session_state.c_year, st.session_state.c_month, day)
                    btn_class = "cal-btn"
                    is_trained = curr_date in trained_dates
                    
                    if curr_date == today: btn_class += " today"
                    elif is_trained: btn_class += " trained"
                    elif curr_date < today: btn_class += " missed"
                    
                    # Кнопка дня
                    if cols[i].button(f"{day}", key=f"day_{curr_date}", help=f"Нажмите, чтобы увидеть данные за {curr_date.strftime('%d.%m.%Y')}"):
                        if is_trained:
                            st.session_state.selected_date = curr_date
                        else:
                            st.session_state.selected_date = None # Сброс если нажали на пустой день
                            st.toast("В этот день тренировок не было.", icon="ℹ️")

                    # Применение CSS стилей к кнопке через JS хак (Streamlit не дает стилизовать кнопки напрямую)
                    st.markdown(f"""
                        <script>
                        var elements = window.parent.document.querySelectorAll('button[kind="secondary"]');
                        for (var i = 0; i < elements.length; i++) {{
                            if (elements[i].innerText == "{day}" && elements[i].parentElement.parentElement.parentElement.innerHTML.includes("day_{curr_date}")) {{
                                elements[i].className = '{btn_class}';
                            }}
                        }}
                        </script>
                        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ФИЛЬТРАЦИЯ ДАННЫХ ---
    filtered_df = df.copy()
    filter_status_text = "ОБЗОР ЗА ВСЁ ВРЕМЯ"
    
    if st.session_state.selected_date:
        filtered_df = df[df['День/Дата'].dt.date == st.session_state.selected_date]
        filter_status_text = f"✅ ФИЛЬТР: {st.session_state.selected_date.strftime('%d.%m.%Y')}"
        if st.button("❌ СБРОСИТЬ ФИЛЬТР (ПОКАЗАТЬ ВСЁ)"):
            st.session_state.selected_date = None
            st.rerun()
            
    st.markdown(f"<div style='text-align:center; font-weight:bold; color:{ACCENT_COLOR}; margin-bottom:10px;'>{filter_status_text}</div>", unsafe_allow_html=True)

    # --- РАДАР ---
    st.markdown('<div class="section-title">СТАТУС БРОНИ (ПОДХОДЫ)</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-tile">', unsafe_allow_html=True)
    if not filtered_df.empty:
        muscle_data = filtered_df.groupby('Muscle')['Сет'].count().reset_index()
        muscle_data.columns = ['Muscle', 'Sets']
        target_muscles = ["ГРУДЬ", "СПИНА", "НОГИ", "РУКИ", "ПЛЕЧИ", "ПРЕСС"]
        radar_df = pd.DataFrame({"Muscle": target_muscles})
        radar_df = radar_df.merge(muscle_data, on="Muscle", how="left").fillna(0)
        
        fig = go.Figure(data=go.Scatterpolar(
            r=radar_df['Sets'], theta=radar_df['Muscle'], fill='toself',
            line=dict(color=ACCENT_COLOR, width=2),
            fillcolor='rgba(212, 175, 55, 0.3)'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=False, linecolor='rgba(0,0,0,0.1)'),
                angularaxis=dict(linecolor='rgba(0,0,0,0.1)', tickfont=dict(color='#555', size=11, weight="bold")),
                bgcolor='rgba(0,0,0,0)'
            ),
            showlegend=False, height=280, margin=dict(l=30, r=30, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#1C1C1E')
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
    else: st.info("Нет данных за выбранный период.")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- ТАБЛИЦА ---
    st.markdown('<div class="section-title">ЖУРНАЛ БОЕВЫХ ДЕЙСТВИЙ</div>', unsafe_allow_html=True)
    if not filtered_df.empty:
        hdf = filtered_df.copy().sort_values(by=['День/Дата', 'Сет'], ascending=[False, True])
        hdf['День/Дата'] = hdf['День/Дата'].dt.strftime('%d.%m')
        st.dataframe(hdf[['День/Дата', 'Сет', 'Упражнение', 'Вес (кг)', 'Повт']], use_container_width=True, hide_index=True)
    else: st.info("Нет записей.")

# --- ЖУРНАЛ ---
elif selected == "ЖУРНАЛ":
    st.markdown('<div class="section-title">НОВАЯ МИССИЯ</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-tile">', unsafe_allow_html=True)
    with st.form("entry_form"):
        d = st.date_input("Дата")
        c1, c2 = st.columns([1,2])
        with c1: s_grp = st.text_input("Сет (Группа)", placeholder="№1")
        with c2: ex_name = st.text_input("Упражнение")
        c3, c4, c5 = st.columns(3)
        with c3: s_num = st.number_input("Подход №", 1, 10, 1)
        with c4: w_val = st.number_input("Вес (кг)", step=2.5)
        with c5: r_val = st.number_input("Повт", 1, 100, 10)
        c6, c7 = st.columns(2)
        with c6: tech = st.text_input("План/Техника")
        with c7: comm = st.text_input("Мой коммент")
        
        if st.form_submit_button("ЗАПИСАТЬ ДАННЫЕ"):
            if ex_name:
                try:
                    sheet.append_row([d.strftime("%Y-%m-%d"), s_grp, ex_name, s_num, w_val, r_val, w_val*r_val, tech, comm])
                    st.success("ДАННЫЕ ВНЕСЕНЫ УСПЕШНО")
                    st.rerun()
                except: st.error("ОШИБКА ЗАПИСИ")
            else: st.warning("Введите название упражнения")
    st.markdown('</div>', unsafe_allow_html=True)

# --- ТРЕНЕР ---
elif selected == "ТРЕНЕР":
    st.markdown(f'<div class="section-title">ИНСТРУКТОР // {rank["abbr"]}</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-tile" style="min-height:400px;">', unsafe_allow_html=True)
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    if p := st.chat_input("Запросить инструктаж..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        # Промпт на русском для тренера
        res = model.generate_content(f"Ты суровый армейский инструктор по физподготовке. Звание пользователя: {rank['title']}. Отвечай коротко, четко, по-военному, на русском языке. Вопрос: {p}")
        with st.chat_message("assistant"): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
    st.markdown('</div>', unsafe_allow_html=True)
