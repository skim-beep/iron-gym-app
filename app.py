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

# --- 1. НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="IRON GYM OS",
    page_icon="🦅",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- 2. НАСТРОЙКИ ---
AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 
ACCENT_COLOR = "#D4AF37" # Classic Gold

# --- 3. ЗВАНИЯ ---
RANK_SYSTEM = [
    (0, 9, "PRIVATE RECRUIT", "PV1", "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/United_States_Army_Star_Logo.svg/200px-United_States_Army_Star_Logo.svg.png"), 
    (10, 24, "PRIVATE (PV2)", "PV2", "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/US_Army_E2.svg/100px-US_Army_E2.svg.png"),
    (25, 49, "PFC", "PFC", "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/US_Army_E3.svg/100px-US_Army_E3.svg.png"),
    (50, 74, "SPECIALIST", "SPC", "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/US_Army_E4_SPC.svg/100px-US_Army_E4_SPC.svg.png"),
    (75, 99, "SERGEANT", "SGT", "https://upload.wikimedia.org/wikipedia/commons/thumb/6/62/US_Army_E5.svg/100px-US_Army_E5.svg.png"),
    (100, 129, "STAFF SERGEANT", "SSG", "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/US_Army_E6.svg/100px-US_Army_E6.svg.png"),
    (130, 159, "SGT 1ST CLASS", "SFC", "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/US_Army_E7.svg/100px-US_Army_E7.svg.png"),
    (160, 189, "MASTER SERGEANT", "MSG", "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/US_Army_E8_MSG.svg/100px-US_Army_E8_MSG.svg.png"),
    (190, 219, "FIRST SERGEANT", "1SG", "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/US_Army_E8_1SG.svg/100px-US_Army_E8_1SG.svg.png"),
    (220, 249, "SGT MAJOR", "SGM", "https://upload.wikimedia.org/wikipedia/commons/thumb/fa/US_Army_E9_SGM.svg/100px-US_Army_E9_SGM.svg.png"),
    (250, 299, "COMMAND SGT MAJOR", "CSM", "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/US_Army_E9_CSM.svg/100px-US_Army_E9_CSM.svg.png"),
    (300, 9999, "OFFICER", "CMD", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/US-Army-O1-Shoulder.svg/100px-US-Army-O1-Shoulder.svg.png")
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
    return {"title": "LEGEND", "abbr": "GOD", "icon": RANK_SYSTEM[-1][4], "progress": 100, "next_xp": 0}

def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def detect_muscle_group(exercise_name):
    ex = str(exercise_name).lower()
    if any(x in ex for x in ['жим лежа', 'жим гантелей', 'бабочка', 'chest', 'отжимания', 'брусья', 'груд', 'жим в тренажере']): return "ГРУДЬ"
    if any(x in ex for x in ['тяга', 'подтягивания', 'спина', 'back', 'row']): return "СПИНА"
    if any(x in ex for x in ['присед', 'ноги', 'выпады', 'legs', 'squat', 'бег', 'эллипс', 'разминка']): return "НОГИ/КАРДИО"
    if any(x in ex for x in ['бицепс', 'трицепс', 'молот', 'arms', 'bicep', 'концентрированный']): return "РУКИ"
    if any(x in ex for x in ['жим стоя', 'плечи', 'махи', 'shouder', 'press', 'разведение']): return "ПЛЕЧИ"
    if any(x in ex for x in ['пресс', 'планка', 'abs', 'core', 'скручивания']): return "КОР"
    return "ОБЩЕЕ"

# --- 5. CLEAN LIGHT CSS ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&display=swap');

    .stApp {{ background-color: #F2F3F7; font-family: 'Inter', sans-serif; color: #1C1C1E; }}
    #MainMenu, footer, header {{ visibility: hidden; }}

    .clean-card {{
        background-color: #FFFFFF; border-radius: 20px; padding: 20px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #FFFFFF;
    }}

    .profile-card {{ display: flex; align-items: center; }}
    .avatar-area {{
        width: 80px; height: 80px; border-radius: 50%; border: 2px solid {ACCENT_COLOR}; 
        overflow: hidden; margin-right: 20px; flex-shrink: 0;
    }}
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    .info-area {{ flex-grow: 1; }}
    .user-name {{
        font-family: 'Black Ops One', cursive; font-size: 26px; color: {ACCENT_COLOR}; 
        letter-spacing: 1px; margin: 0; text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .rank-row {{ display: flex; align-items: center; margin-bottom: 8px; }}
    .rank-title {{ color: #8E8E93; font-weight: 700; margin-right: 10px; font-size: 13px; }}
    .rank-icon-img {{ height: 28px; width: auto; object-fit: contain; }}
    
    .progress-track {{
        width: 100%; height: 8px; background: #E5E5EA; border-radius: 4px; overflow: hidden; margin-top: 5px;
    }}
    .progress-fill {{ height: 100%; background-color: {ACCENT_COLOR}; }}
    .xp-text {{ font-size: 10px; color: #8E8E93; float: right; margin-top: 2px; font-weight: 600; }}

    .stat-badge {{
        background: #F2F2F7; padding: 4px 10px; border-radius: 8px; font-size: 11px; 
        font-weight: 600; color: #3A3A3C; margin-right: 5px; display: inline-flex; align-items: center;
    }}

    .section-title {{
        font-size: 14px; font-weight: 800; color: #8E8E93; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px;
    }}

    div.stButton > button {{
        width: 100%; background: #1C1C1E; color: #FFF; border: none; border-radius: 12px; padding: 14px; font-weight: 700;
    }}
    
    .calendar-table {{ width: 100%; border-collapse: separate; border-spacing: 4px; }}
    .calendar-cell {{ 
        text-align: center; padding: 10px 5px; border-radius: 8px; font-size: 13px; 
        font-weight: 700; background: #F2F2F7; color: #3A3A3C; 
    }}
    .day-trained {{ background: {ACCENT_COLOR}; color: #FFF; }}
    .day-missed {{ background: #FFB3B3; color: #FFF; }}
    .day-today {{ border: 2px solid {ACCENT_COLOR}; background: transparent; }}
    .day-header {{ color: #8E8E93; font-size: 11px; text-transform: uppercase; padding-bottom: 5px; }}
    
    div[data-baseweb="input"] {{ background-color: #F2F2F7 !important; border-radius: 8px !important; }}
    </style>
""", unsafe_allow_html=True)

# --- 6. ЗАГРУЗКА ДАННЫХ (SMART REPAIR) ---
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
        # 1. Чистим названия колонок от пробелов (на всякий случай)
        df.columns = df.columns.str.strip()
        
        # 2. Меняем запятые на точки в числах
        for col in ['Вес (кг)', 'Тоннаж']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.')
        
        # 3. Приводим типы
        df['Вес (кг)'] = pd.to_numeric(df['Вес (кг)'], errors='coerce').fillna(0)
        df['Повт'] = pd.to_numeric(df['Повт'], errors='coerce').fillna(0)
        df['Тоннаж'] = pd.to_numeric(df['Тоннаж'], errors='coerce').fillna(0)
        
        # 4. Обрабатываем колонку "Сет" (если ее нет или она пустая)
        if 'Сет' not in df.columns:
            df['Сет'] = "-"
        df['Сет'] = df['Сет'].astype(str).replace('', '-')
        
        # 5. Дата
        df['День/Дата'] = pd.to_datetime(df['День/Дата'], errors='coerce')
        df = df.dropna(subset=['День/Дата'])
        
        # 6. Мышцы
        df['Muscle'] = df['Упражнение'].apply(detect_muscle_group)
        
except Exception as e:
    df = pd.DataFrame()

# Stats
total_xp = len(df)
rank = get_rank_data(total_xp)
user_age = calculate_age(USER_BIRTHDAY)
trained_dates = set(df['День/Дата'].dt.date) if not df.empty else set()

# --- 7. HEADER & SYNC ---
col_logo, col_sync = st.columns([3, 1])
with col_logo:
    st.markdown(f"<div style='font-family:\"Black Ops One\"; font-size:20px; color:#1C1C1E;'>IRON GYM OS</div>", unsafe_allow_html=True)
with col_sync:
    if st.button("🔄 SYNC"):
        st.rerun()

# ПРОФИЛЬ
st.markdown(f"""
<div class="clean-card profile-card">
    <div class="avatar-area"><img src="{AVATAR_URL}" class="avatar-img"></div>
    <div class="info-area">
        <div class="user-name">SERGEY</div>
        <div class="rank-row">
            <span class="rank-title">{rank['title']}</span>
            <img src="{rank['icon']}" class="rank-icon-img" referrerPolicy="no-referrer">
        </div>
        <div class="progress-track"><div class="progress-fill" style="width: {rank['progress']}%;"></div></div>
        <div style="margin-top:4px;">
            <span class="stat-badge">XP: {total_xp}</span>
            <span class="xp-text">NEXT: {rank['next_xp']}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 8. MENU ---
selected = option_menu(
    menu_title=None,
    options=["DASHBOARD", "LOGBOOK", "AI COACH"],
    icons=["bar-chart-fill", "journal-richtext", "cpu-fill"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent"},
        "nav-link": {"font-size": "12px", "color": "#1C1C1E", "margin": "0px"},
        "nav-link-selected": {"background-color": "#1C1C1E", "color": "#FFF"},
    }
)

# --- 9. DASHBOARD ---
if selected == "DASHBOARD":
    
    st.markdown('<div class="section-title">BODY ARMOR STATUS</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="clean-card">', unsafe_allow_html=True)
    if not df.empty:
        muscle_data = df.groupby('Muscle')['Тоннаж'].sum().reset_index()
        all_muscles = ["ГРУДЬ", "СПИНА", "НОГИ/КАРДИО", "РУКИ", "ПЛЕЧИ", "КОР"]
        radar_df = pd.DataFrame({"Muscle": all_muscles})
        radar_df = radar_df.merge(muscle_data, on="Muscle", how="left").fillna(0)
        
        fig = go.Figure(data=go.Scatterpolar(
            r=radar_df['Тоннаж'], theta=radar_df['Muscle'], fill='toself',
            line=dict(color=ACCENT_COLOR, width=2),
            fillcolor='rgba(212, 175, 55, 0.2)'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=False, linecolor='#E5E5EA'),
                angularaxis=dict(linecolor='#E5E5EA', tickfont=dict(color='#8E8E93', size=10)),
                bgcolor='rgba(0,0,0,0)'
            ),
            showlegend=False, height=280, margin=dict(l=30, r=30, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#1C1C1E')
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
    else: st.info("No data yet.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">MISSION CALENDAR</div>', unsafe_allow_html=True)
    st.markdown('<div class="clean-card">', unsafe_allow_html=True)
    
    if 'c_year' not in st.session_state: st.session_state.c_year = date.today().year
    if 'c_month' not in st.session_state: st.session_state.c_month = date.today().month

    def change_m(d):
        m = st.session_state.c_month + d
        y = st.session_state.c_year
        if m>12: m=1; y+=1
        elif m<1: m=12; y-=1
        st.session_state.c_month = m
        st.session_state.c_year = y

    c1, c2, c3 = st.columns([1,3,1])
    with c1: st.button("◀", on_click=change_m, args=(-1,))
    with c2: 
        m_name = calendar.month_name[st.session_state.c_month].upper()
        st.markdown(f"<div style='text-align:center; font-weight:800; color:#1C1C1E; padding-top:10px;'>{m_name} {st.session_state.c_year}</div>", unsafe_allow_html=True)
    with c3: st.button("▶", on_click=change_m, args=(1,))

    cal = calendar.monthcalendar(st.session_state.c_year, st.session_state.c_month)
    today = date.today()
    
    h = '<table class="calendar-table"><thead><tr>'
    for d in ["M","T","W","T","F","S","S"]: h += f'<th class="day-header">{d}</th>'
    h += '</tr></thead><tbody>'
    for week in cal:
        h += '<tr>'
        for day in week:
            if day==0: h += '<td class="calendar-cell day-empty"></td>'
            else:
                curr = date(st.session_state.c_year, st.session_state.c_month, day)
                cls = "calendar-cell"
                if curr == today: cls += " day-today"
                elif curr in trained_dates: cls += " day-trained"
                elif curr < today: cls += " day-missed"
                else: cls += " day-future"
                h += f'<td class="{cls}">{day}</td>'
        h += '</tr>'
    h += '</tbody></table>'
    st.markdown(h, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # TABLE WITH SET COLUMN
    st.markdown('<div class="section-title">COMBAT LOG</div>', unsafe_allow_html=True)
    if not df.empty:
        hdf = df.copy().sort_values(by='День/Дата', ascending=False)
        hdf['День/Дата'] = hdf['День/Дата'].dt.strftime('%d.%m')
        # ПОКАЗЫВАЕМ КОЛОНКУ СЕТ
        st.dataframe(hdf[['День/Дата', 'Сет', 'Упражнение', 'Вес (кг)', 'Повт']], use_container_width=True, hide_index=True)

# --- LOGBOOK ---
elif selected == "LOGBOOK":
    st.markdown('<div class="section-title">NEW MISSION</div>', unsafe_allow_html=True)
    st.markdown('<div class="clean-card">', unsafe_allow_html=True)
    with st.form("entry_form"):
        d = st.date_input("Дата")
        c1, c2 = st.columns([1,2])
        with c1: s_grp = st.text_input("Сет", placeholder="№1")
        with c2: ex_name = st.text_input("Упражнение")
        
        c3, c4, c5 = st.columns(3)
        with c3: s_num = st.number_input("Подход", 1, 10, 1)
        with c4: w_val = st.number_input("Вес", step=2.5)
        with c5: r_val = st.number_input("Повт", 1, 100, 10)
        
        c6, c7 = st.columns(2)
        with c6: tech = st.text_input("Техника")
        with c7: comm = st.text_input("Мой коммент")
        
        if st.form_submit_button("SAVE"):
            try:
                sheet.append_row([d.strftime("%Y-%m-%d"), s_grp, ex_name, s_num, w_val, r_val, w_val*r_val, tech, comm])
                st.success("SAVED")
                st.rerun()
            except: st.error("ERROR")
    st.markdown('</div>', unsafe_allow_html=True)

# --- COACH ---
elif selected == "AI COACH":
    st.markdown(f'<div class="section-title">INSTRUCTOR // {rank["abbr"]}</div>', unsafe_allow_html=True)
    st.markdown('<div class="clean-card">', unsafe_allow_html=True)
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    if p := st.chat_input("..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        res = model.generate_content(f"Tactical fit coach. User Rank: {rank['title']}. Q: {p}")
        with st.chat_message("assistant"): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
    st.markdown('</div>', unsafe_allow_html=True)
