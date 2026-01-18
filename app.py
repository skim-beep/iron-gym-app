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

# ТВОЙ АВАТАР
AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"

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

# --- 4. CSS СТИЛИ (РИСУЕМ ЗВАНИЕ КОДОМ) ---
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
        border: 1px solid #D4AF37;
        flex-shrink: 0;
        margin-right: 20px;
    }}
    
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    
    .info-area {{ flex-grow: 1; }}
    
    .name-row {{
        display: flex;
        align-items: center;
        margin-bottom: 4px;
    }}
    
    .user-name {{
        font-size: 26px;
        font-weight: 900;
        color: #D4AF37;
        line-height: 1;
        text-shadow: 0 0 15px rgba(212, 175, 55, 0.5);
    }}
    
    /* СТРОКА ЗВАНИЯ */
    .rank-row {{
        display: flex;
        align-items: center; 
        margin-bottom: 12px;
    }}
    
    .rank-text {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: #8E8E93;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin: 0;
    }}

    /* 🔥 РИСУЕМ ЗНАК КАПИТАНА (ДВЕ ПОЛОСКИ) CSS-ОМ */
    .captain-badge {{
        display: flex;
        gap: 4px; /* Расстояние между шпалами */
        margin-left: 10px;
        padding: 2px;
    }}
    
    .silver-bar {{
        width: 8px;
        height: 24px;
        /* Градиент под серебро/металл */
        background: linear-gradient(135deg, #E0E0E0 0%, #A0A0A0 50%, #606060 100%);
        border: 1px solid #000000;
        border-radius: 2px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.3);
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
        </div>
        <div class="rank-row">
            <span class="rank-text">CAPTAIN (O-3) // US ARMY</span>
            <div class="captain-badge">
                <div class="silver-bar"></div>
                <div class="silver-bar"></div>
            </div>
        </div>
