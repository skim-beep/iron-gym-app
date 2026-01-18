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

# --- 2. НАСТРОЙКИ ПРОФИЛЯ ---

# ТВОЙ АВАТАР (Прямая ссылка)
AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"

# Иконка звания (Капитан)
RANK_ICON = "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Captain_icon.svg/1024px-Captain_icon.svg.png"

USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. ФУНКЦИИ ---
def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def calculate_tenure(df):
    if df.empty: return "0 ДНЕЙ"
    try:
        first = pd.to_datetime(df['date']).min()
        days = (datetime.now() - first).days
        return f"{days} ДН."
    except: return "1 ДЕНЬ"

# --- 4. CSS СТИЛИ ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500&display=swap');

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
        /* ИЗМЕНЕНИЕ: Тонкий золотой контур в 1px */
        border: 1px solid #D4AF37; 
        flex-shrink: 0;
        margin-right: 20px;
    }}
    
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    
    .info-area {{ flex-grow: 1; }}
    
    .name-row {{
        display: flex;
        align-items: center;
        margin-bottom: 5px;
    }}
    
    /* ЗОЛОТОЕ ИМЯ + СВЕЧЕНИЕ */
    .user-name {{
        font-size: 24px;
        font-weight: 900;
        color: #D4AF37;
        margin-right: 10px;
        line-height: 1;
        text-shadow: 0 0 10px #FFD700, 0 0 20px #D4AF37, 0 0 30px rgba(212, 175, 55, 0.4);
    }}
    
    .rank-img {{ width: 22px; height: auto; }}
    
    .rank-text {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: #8E8E93;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        display: block;
        margin-bottom: 10px;
    }}
    
    .stats-row {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    
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

# --- 5. ПОДКЛЮЧЕНИЕ ---
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

user_age = calculate_age(USER_BIRTHDAY)
tenure = calculate_tenure(df)

# --- 6. ИНТЕРФЕЙС ---

# HTML
st.markdown(f"""
<div class="profile-card">
    <div class="avatar-area">
        <img src="{AVATAR_URL}" class="avatar-img">
    </div>
    <div class="info-area">
        <div class="name-row">
            <span class="user-name">SERGEY</span>
            <img src="{RANK_ICON}" class="rank-img">
        </div>
        <span class="rank-text">CAPTAIN (O-3) // US ARMY</span>
        <div class="stats-row">
            <div class="stat-badge">🎂 {user_age} YRS</div>
            <div class="stat-badge">⚖️ {USER_WEIGHT_CURRENT} KG</div>
            <div class="stat-badge">⏳ {tenure}</div>
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
    st.caption("СВОДКА")
    col1, col2 = st.columns(2)
    vol = 0
    cnt = 0
    if not df.empty and 'weight' in df.columns:
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0)
        df['reps'] = pd.to_numeric(df['reps'], errors='coerce').fillna(0)
        vol = (df['weight'] * df['reps']).sum()
        cnt = len(df)
        
    with col1: st.metric("ТОННАЖ", f"{int(vol/1000)}k")
    with col2: st.metric("ТРЕНИРОВОК", f"{cnt}")
    
    if not df.empty:
        st.markdown("---")
        daily = df.groupby('date').apply(lambda x: (x['weight']*x['reps']).sum()).reset_index(name='v')
        fig = go.Figure(go.Scatter(x=daily['date'], y=daily['v'], fill='tozeroy', line=dict(color='black')))
        fig.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})

elif selected == "LOGBOOK":
    st.caption("НОВАЯ ЗАПИСЬ")
    with st.form("add"):
        ex = st.text_input("Упражнение")
        c1, c2, c3 = st.columns(3)
        w = c1.number_input("Вес", step=2.5)
        r = c2.number_input("Повторы", step=1, value=10)
        rpe = c3.selectbox("RPE", [7,8,9,10])
        note = st.text_area("Заметка")
        if st.form_submit_button("СОХРАНИТЬ"):
            if ex:
                try:
                    sheet.append_row([datetime.now().strftime("%Y-%m-%d"), ex, w, r, rpe, "done", note])
                    st.success("Записано!")
                except: st.error("Ошибка базы")

elif selected == "AI COACH":
    st.caption("GEM-BOT TACTICAL")
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if p := st.chat_input("Вопрос..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        res = model.generate_content(f"Ты военный тренер. Атлет: Сергей, {user_age} лет. Кратко: {p}")
        with st.chat_message("assistant"): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
