import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.graph_objects as go
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from streamlit_option_menu import option_menu

# --- 1. НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="IRON GYM OS",
    page_icon="🦅",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- 2. НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ ---
AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. ПОЛНАЯ ТАБЛИЦА ЗВАНИЙ (US ARMY) ---
# Структура: (Мин. XP, Звание, Аббревиатура, Ссылка на иконку)
RANK_SYSTEM = [
    # --- ENLISTED (РЯДОВЫЕ И СЕРЖАНТЫ) ---
    (0, 9, "PRIVATE RECRUIT", "PV1", "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/US_Army_E2.svg/160px-US_Army_E2.svg.png"),
    (10, 24, "PRIVATE FIRST CLASS", "PFC", "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/US_Army_E3.svg/160px-US_Army_E3.svg.png"),
    (25, 49, "SPECIALIST", "SPC", "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/US_Army_E4_SPC.svg/160px-US_Army_E4_SPC.svg.png"),
    (50, 74, "SERGEANT", "SGT", "https://upload.wikimedia.org/wikipedia/commons/thumb/6/62/US_Army_E5.svg/160px-US_Army_E5.svg.png"),
    (75, 99, "STAFF SERGEANT", "SSG", "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/US_Army_E6.svg/160px-US_Army_E6.svg.png"),
    (100, 129, "SGT FIRST CLASS", "SFC", "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/US_Army_E7.svg/160px-US_Army_E7.svg.png"),
    (130, 159, "MASTER SERGEANT", "MSG", "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/US_Army_E8_MSG.svg/160px-US_Army_E8_MSG.svg.png"),
    (160, 189, "SERGEANT MAJOR", "SGM", "https://upload.wikimedia.org/wikipedia/commons/thumb/fa/US_Army_E9_SGM.svg/160px-US_Army_E9_SGM.svg.png"),
    (190, 219, "COMMAND SGT MAJOR", "CSM", "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/US_Army_E9_CSM.svg/160px-US_Army_E9_CSM.svg.png"),
    (220, 249, "SGT MAJOR OF ARMY", "SMA", "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/US_Army_E9_SMA.svg/160px-US_Army_E9_SMA.svg.png"),

    # --- WARRANT OFFICERS (УОРЕНТ-ОФИЦЕРЫ) ---
    (250, 274, "WARRANT OFFICER 1", "WO1", "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/US_Army_WO1.svg/60px-US_Army_WO1.svg.png"),
    (275, 299, "CHIEF WARRANT 2", "CW2", "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/US_Army_CW2.svg/60px-US_Army_CW2.svg.png"),
    (300, 319, "CHIEF WARRANT 5", "CW5", "https://upload.wikimedia.org/wikipedia/commons/thumb/6/63/US_Army_CW5.svg/60px-US_Army_CW5.svg.png"),

    # --- OFFICERS (ОФИЦЕРЫ) ---
    (320, 339, "2ND LIEUTENANT", "2LT", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/US-Army-O1-Shoulder.svg/120px-US-Army-O1-Shoulder.svg.png"),
    (340, 359, "1ST LIEUTENANT", "1LT", "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/US-Army-O2-Shoulder.svg/120px-US-Army-O2-Shoulder.svg.png"),
    (360, 389, "CAPTAIN", "CPT", "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/US-Army-O3-Collar.svg/160px-US-Army-O3-Collar.svg.png"),
    (390, 419, "MAJOR", "MAJ", "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/US-Army-O4-Shoulder.svg/160px-US-Army-O4-Shoulder.svg.png"),
    (420, 449, "LT COLONEL", "LTC", "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/US-Army-O5-Shoulder.svg/160px-US-Army-O5-Shoulder.svg.png"),
    (450, 479, "COLONEL", "COL", "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/US-Army-O6-Shoulder.svg/160px-US-Army-O6-Shoulder.svg.png"),
    
    # --- GENERALS (ГЕНЕРАЛЫ) ---
    (480, 499, "BRIGADIER GENERAL", "BG", "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9c/US-Army-O7-Shoulder.svg/160px-US-Army-O7-Shoulder.svg.png"),
    (500, 524, "MAJOR GENERAL", "MG", "https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/US-Army-O8-Shoulder.svg/160px-US-Army-O8-Shoulder.svg.png"),
    (525, 9999, "GENERAL OF THE ARMY", "GA", "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/US-Army-General_of_the_Army-Shoulder.svg/160px-US-Army-General_of_the_Army-Shoulder.svg.png")
]

# --- 4. ЛОГИКА РАСЧЕТА РАНГА ---
def get_rank_data(xp):
    for r_min, r_max, title, abbr, icon in RANK_SYSTEM:
        if r_min <= xp <= r_max:
            needed = r_max - r_min + 1
            current = xp - r_min
            percent = int((current / needed) * 100)
            to_go = r_max - xp + 1
            return {
                "title": title, "abbr": abbr, "icon": icon,
                "progress": percent, "next_xp": to_go, "color": "#D4AF37"
            }
    # Если выше максимума
    return {"title": "LEGEND", "abbr": "GOD", "icon": RANK_SYSTEM[-1][4], "progress": 100, "next_xp": 0, "color": "#FF3B30"}

def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

# --- 5. CSS СТИЛИ ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&display=swap');

    .stApp {{ background-color: #F2F3F7; font-family: 'Inter', sans-serif; }}
    #MainMenu, footer, header {{ visibility: hidden; }}

    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {{
        background-color: #FFFFFF;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0px 4px 20px rgba(0,0,0,0.05);
    }}

    /* ПРОФИЛЬ */
    .profile-card {{
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        margin-bottom: 25px;
        display: flex;
        flex-direction: row;
        align-items: center;
        border: 1px solid #FFFFFF;
    }}
    
    .avatar-area {{
        width: 85px;
        height: 85px;
        border-radius: 50%;
        overflow: hidden;
        border: 2px solid #D4AF37;
        flex-shrink: 0;
        margin-right: 20px;
        background: #000;
    }}
    
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    
    .info-area {{ flex-grow: 1; width: 100%; }}
    
    .user-name {{
        font-size: 26px;
        font-weight: 900;
        color: #D4AF37;
        line-height: 1;
        margin-bottom: 2px;
        text-shadow: 0 0 15px rgba(212, 175, 55, 0.4);
    }}
    
    .rank-row {{
        display: flex;
        align-items: center;
        margin-bottom: 8px;
    }}
    
    .rank-title {{
        font-family: 'Black Ops One', cursive;
        font-size: 14px;
        color: #1C1C1E;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-right: 10px;
    }}
    
    .rank-icon-img {{
        height: 28px;
        width: auto;
        filter: drop-shadow(0px 2px 2px rgba(0,0,0,0.2));
    }}
    
    /* PROGRESS BAR */
    .progress-track {{
        width: 100%;
        height: 6px;
        background-color: #E5E5EA;
        border-radius: 3px;
        margin-bottom: 6px;
        overflow: hidden;
    }}
    
    .progress-fill {{
        height: 100%;
        background-color: #34C759;
        border-radius: 3px;
        transition: width 0.5s ease-in-out;
    }}
    
    .xp-text {{
        font-size: 10px;
        color: #8E8E93;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    .stats-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }}
    
    .stat-badge {{
        background-color: #F2F2F7;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        color: #3A3A3C;
    }}

    div.stButton > button {{
        width: 100%;
        background-color: #1C1C1E;
        color: #FFFFFF;
        border-radius: 12px;
        padding: 14px;
        font-weight: 600;
        border: none;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 6. ПОДКЛЮЧЕНИЕ К БАЗЕ ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["service_account_json"], strict=False), scope
    )
    client = gspread.authorize(creds)
    sheet = client.open("IRON_GYM_DB").sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame()
except:
    df = pd.DataFrame()

# --- 7. РАСЧЕТ ДАННЫХ ---
user_age = calculate_age(USER_BIRTHDAY)
total_xp = len(df) if not df.empty else 0 
rank = get_rank_data(total_xp)

# --- 8. ИНТЕРФЕЙС (HTML БЕЗ ОТСТУПОВ!) ---

profile_html = f"""
<div class="profile-card">
<div class="avatar-area">
<img src="{AVATAR_URL}" class="avatar-img">
</div>
<div class="info-area">
<div class="user-name">SERGEY</div>
<div class="rank-row">
<span class="rank-title">{rank['title']} // {rank['abbr']}</span>
<img src="{rank['icon']}" class="rank-icon-img">
</div>
<div class="progress-track">
<div class="progress-fill" style="width: {rank['progress']}%;"></div>
</div>
<span class="xp-text">PROMOTION IN: {rank['next_xp']} MISSIONS (TOTAL: {total_xp})</span>
<div class="stats-row">
<div class="stat-badge">🎂 {user_age} YRS</div>
<div class="stat-badge">⚖️ {USER_WEIGHT_CURRENT} KG</div>
</div>
</div>
</div>
"""
st.markdown(profile_html, unsafe_allow_html=True)

# МЕНЮ
selected = option_menu(
    menu_title=None,
    options=["DASHBOARD", "LOGBOOK", "AI COACH"],
    icons=["bar-chart-fill", "journal-richtext", "cpu-fill"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent"},
        "nav-link-selected": {"background-color": "#000", "color": "#fff"},
    }
)

if selected == "DASHBOARD":
    st.caption("TACTICAL OVERVIEW")
    col1, col2 = st.columns(2)
    vol = 0
    if not df.empty and 'weight' in df.columns:
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0)
        df['reps'] = pd.to_numeric(df['reps'], errors='coerce').fillna(0)
        vol = (df['weight'] * df['reps']).sum()
        
    with col1: st.metric("TOTAL LOAD", f"{int(vol/1000)}k")
    with col2: st.metric("MISSIONS", f"{total_xp}")
    
    if not df.empty:
        st.markdown("---")
        daily = df.groupby('date').apply(lambda x: (x['weight']*x['reps']).sum()).reset_index(name='v')
        fig = go.Figure(go.Scatter(x=daily['date'], y=daily['v'], fill='tozeroy', line=dict(color='black')))
        fig.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})

elif selected == "LOGBOOK":
    st.caption("MISSION LOG (EARN XP)")
    with st.form("add"):
        ex = st.text_input("Exercise")
        c1, c2, c3 = st.columns(3)
        w = c1.number_input("Weight", step=2.5)
        r = c2.number_input("Reps", step=1, value=10)
        rpe = c3.selectbox("RPE", [7,8,9,10])
        note = st.text_area("Debrief Note")
        if st.form_submit_button("COMPLETE MISSION"):
            if ex:
                try:
                    sheet.append_row([datetime.now().strftime("%Y-%m-%d"), ex, w, r, rpe, "done", note])
                    st.success(f"Mission Logged! Rank Progress Updated.")
                    st.rerun() 
                except: st.error("Database Connection Failed")

elif selected == "AI COACH":
    st.caption(f"INSTRUCTOR // {rank['abbr']} LEVEL")
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if p := st.chat_input("Request Intel..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        res = model.generate_content(f"Ты военный инструктор. Мое звание: {rank['title']}. Отвечай коротко и по-военному. Вопрос: {p}")
        with st.chat_message("assistant"): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
