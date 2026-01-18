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

# --- 3. СИСТЕМА ЗВАНИЙ (US ARMY) ---
# (Мин XP, Звание, Аббр, Иконка)
RANK_SYSTEM = [
    # ENLISTED
    # PV1 не имеет шеврона, ставим Логотип Армии
    (0, 9, "PRIVATE RECRUIT", "PV1", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Emblem_of_the_United_States_Department_of_the_Army.svg/150px-Emblem_of_the_United_States_Department_of_the_Army.svg.png"), 
    (10, 24, "PRIVATE (PV2)", "PV2", "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/US_Army_E2.svg/150px-US_Army_E2.svg.png"),
    (25, 49, "PRIVATE 1ST CLASS", "PFC", "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/US_Army_E3.svg/150px-US_Army_E3.svg.png"),
    (50, 74, "SPECIALIST", "SPC", "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/US_Army_E4_SPC.svg/150px-US_Army_E4_SPC.svg.png"),
    (75, 99, "SERGEANT", "SGT", "https://upload.wikimedia.org/wikipedia/commons/thumb/6/62/US_Army_E5.svg/150px-US_Army_E5.svg.png"),
    (100, 129, "STAFF SERGEANT", "SSG", "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/US_Army_E6.svg/150px-US_Army_E6.svg.png"),
    (130, 159, "SGT FIRST CLASS", "SFC", "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/US_Army_E7.svg/150px-US_Army_E7.svg.png"),
    (160, 189, "MASTER SERGEANT", "MSG", "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/US_Army_E8_MSG.svg/150px-US_Army_E8_MSG.svg.png"),
    
    # OFFICERS (примеры)
    (190, 9999, "CAPTAIN", "CPT", "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/US-Army-O3-Collar.svg/150px-US-Army-O3-Collar.svg.png"),
]

# --- 4. ЛОГИКА ---
def get_rank_data(xp):
    for r_min, r_max, title, abbr, icon in RANK_SYSTEM:
        if r_min <= xp <= r_max:
            needed = r_max - r_min + 1
            current = xp - r_min
            percent = int((current / needed) * 100)
            to_go = r_max - xp + 1
            return {
                "title": title, "abbr": abbr, "icon": icon,
                "progress": percent, "next_xp": to_go
            }
    return {"title": "LEGEND", "abbr": "GEN", "icon": RANK_SYSTEM[-1][3], "progress": 100, "next_xp": 0}

def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

# --- 5. CSS (НЕОНОВЫЙ ДИЗАЙН) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&display=swap');

    .stApp {{ background-color: #F2F3F7; font-family: 'Inter', sans-serif; }}
    #MainMenu, footer, header {{ visibility: hidden; }}

    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {{
        background-color: #FFFFFF;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0px 4px 25px rgba(0,0,0,0.05);
    }}

    /* ПРОФИЛЬ */
    .profile-card {{
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 24px;
        /* Легкое свечение всей карточки */
        box-shadow: 0 10px 30px rgba(0,0,0,0.08); 
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
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }}
    
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    
    .info-area {{ flex-grow: 1; width: 100%; }}
    
    .user-name {{
        font-size: 26px;
        font-weight: 900;
        color: #1C1C1E; /* Черное имя для контраста */
        line-height: 1;
        margin-bottom: 4px;
    }}
    
    /* ЗВАНИЕ */
    .rank-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }}
    
    .rank-title {{
        font-family: 'Black Ops One', cursive;
        font-size: 14px;
        color: #8E8E93;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    .rank-icon-img {{
        height: 40px; /* Сделал КРУПНЕЕ */
        width: auto;
        object-fit: contain;
        filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.2));
    }}
    
    /* 🔥🔥 PROGRESS BAR (GLOW EFFECT) 🔥🔥 */
    .progress-track {{
        width: 100%;
        height: 10px; /* Чуть толще */
        background-color: #E0E0E0;
        border-radius: 5px;
        margin-bottom: 8px;
        overflow: hidden;
        border: 1px solid rgba(0,0,0,0.05);
    }}
    
    .progress-fill {{
        height: 100%;
        border-radius: 5px;
        /* Градиент Cyan -> Blue */
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%);
        /* Свечение */
        box-shadow: 0 0 10px #00C6FF, 0 0 20px rgba(0, 114, 255, 0.4);
        /* Анимация движения */
        background-size: 200% 100%;
        animation: gradientMove 3s linear infinite;
        transition: width 0.5s ease-in-out;
    }}

    @keyframes gradientMove {{
        0% {{ background-position: 100% 0; }}
        100% {{ background-position: 0 0; }}
    }}
    
    .xp-text {{
        font-size: 11px;
        color: #0072FF; /* Цвет текста под стать бару */
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        float: right; /* Текст справа */
    }}
    
    .stats-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 20px; }}
    
    .stat-badge {{
        background-color: #F2F2F7;
        padding: 5px 12px;
        border-radius: 8px;
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
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }}
    </style>
""", unsafe_allow_html=True)

# --- 6. ПОДКЛЮЧЕНИЕ ---
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

# --- 7. РАСЧЕТ ---
user_age = calculate_age(USER_BIRTHDAY)
total_xp = len(df) if not df.empty else 0 
rank = get_rank_data(total_xp)

# --- 8. ИНТЕРФЕЙС ---

# HTML
st.markdown(f"""
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
        
        <div style="display: flex; justify-content: space-between; align-items: center;">
             <span style="font-size: 10px; color: #888; font-weight: 600;">LEVEL PROGRESS</span>
             <span class="xp-text">{rank['next_xp']} MISSIONS TO PROMOTION</span>
        </div>

        <div class="stats-row">
            <div class="stat-badge">🎂 {user_age} YRS</div>
            <div class="stat-badge">⚖️ {USER_WEIGHT_CURRENT} KG</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Меню
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
    st.caption("LOG MISSION")
    with st.form("add"):
        ex = st.text_input("Exercise")
        c1, c2, c3 = st.columns(3)
        w = c1.number_input("Weight", step=2.5)
        r = c2.number_input("Reps", step=1, value=10)
        rpe = c3.selectbox("RPE", [7,8,9,10])
        note = st.text_area("Note")
        if st.form_submit_button("COMPLETE MISSION"):
            if ex:
                try:
                    sheet.append_row([datetime.now().strftime("%Y-%m-%d"), ex, w, r, rpe, "done", note])
                    st.success(f"Log Saved! +1 XP")
                    st.rerun() 
                except: st.error("Error")

elif selected == "AI COACH":
    st.caption(f"INSTRUCTOR // {rank['abbr']}")
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if p := st.chat_input("Question..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        res = model.generate_content(f"You are a drill sergeant. User rank: {rank['title']}. Question: {p}")
        with st.chat_message("assistant"): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
