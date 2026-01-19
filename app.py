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

# --- 1. НАСТРОЙКИ ---
st.set_page_config(
    page_title="IRON GYM OS",
    page_icon="🦅",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- 2. ЦВЕТА (GLOBAL VARIABLES) ---
CAMO_DARK = "#0e0e0e"
CAMO_PANEL = "#1c1f1a"
CAMO_GREEN = "#4b5320"
ACCENT_GOLD = "#FFD700"
ACCENT_SILVER = "#C0C0C0"
TEXT_COLOR = "#B0B0B0"
ALERT_RED = "#8B0000"

AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. ШЕВРОНЫ (SVG) ---
def get_rank_svg(rank_type, grade):
    color = ACCENT_GOLD
    if rank_type == "OFFICER":
        if grade in [1, 2, 4, 5] or grade >= 6: color = ACCENT_SILVER
    
    # SVG 30x30
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

# --- 5. CSS (MONOLITH GRID FIX) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500&display=swap');

    /* GLOBAL */
    .stApp {{ background-color: {CAMO_DARK}; color: {TEXT_COLOR}; font-family: 'Roboto Mono', monospace; }}
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* FONTS */
    h1, h2, h3, .tac-font {{ font-family: 'Oswald', sans-serif !important; text-transform: uppercase; }}
    
    /* CAMO CARD */
    .camo-card {{
        background-color: {CAMO_PANEL}; border: 1px solid #333; border-left: 4px solid {CAMO_GREEN};
        padding: 15px; margin-bottom: 20px; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }}

    /* PROFILE */
    .avatar-area {{ width: 80px; height: 80px; border: 2px solid {ACCENT_GOLD}; border-radius: 50%; overflow: hidden; float: left; margin-right: 15px; }}
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    .user-name {{ font-family: 'Oswald', sans-serif; font-size: 28px; color: #FFF; margin: 0; line-height: 1.1; }}
    .progress-track {{ width: 100%; height: 8px; background: #111; margin-top: 8px; }}
    .progress-fill {{ height: 100%; background: {CAMO_GREEN}; }}
    .stat-badge {{ background: #111; color: {ACCENT_GOLD}; padding: 3px 8px; border: 1px solid {CAMO_GREEN}; font-size: 11px; margin-right: 5px; font-family: 'Oswald'; }}

    /* HEADERS */
    .tac-header {{
        font-family: 'Oswald', sans-serif; font-size: 18px; color: {TEXT_COLOR};
        border-bottom: 2px solid {CAMO_GREEN}; padding-bottom: 5px; margin: 20px 0 10px 0; text-transform: uppercase;
    }}

    /* EXPANDER */
    .streamlit-expanderHeader {{ background-color: {CAMO_PANEL} !important; color: {ACCENT_GOLD} !important; border: 1px solid #333 !important; font-family: 'Oswald' !important; }}
    .rank-row-item {{ display: flex; align-items: center; padding: 8px; border-bottom: 1px solid #333; }}
    
    /* --- CALENDAR GRID FIX --- */
    /* Удаляем отступы колонок, чтобы кнопки слиплись в плитку */
    div[data-testid="column"] {{ padding: 0 !important; gap: 0 !important; }}
    div[data-testid="stHorizontalBlock"] {{ gap: 0 !important; }}
    
    /* Кнопки календаря */
    div.stButton > button {{
        width: 100%; 
        aspect
