import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from streamlit_option_menu import option_menu
import base64
import calendar

# --- 1. НАСТРОЙКИ ---
st.set_page_config(
    page_title="IRON GYM OS",
    page_icon="🦅",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- 2. ЦВЕТОВАЯ ПАЛИТРА (HUD STYLE) ---
HUD_BG = "#050505"          # Почти черный
HUD_PANEL = "#121212"       # Темно-серый фон карточек
HUD_BORDER = "#333333"      # Рамки
ACCENT_GREEN = "#00FF41"    # Неоновый тактический зеленый
ACCENT_GOLD = "#FFD700"     # Золото
TEXT_MAIN = "#E0E0E0"

AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. РЕАЛИСТИЧНЫЕ ШЕВРОНЫ (КАК НА САЙТЕ) ---
# Ссылки на официальные PNG изображения (Wikimedia High-Res)
RANK_IMGS = {
    # SOLDIERS & NCOS (Gold Chevrons)
    "PV1": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Army-USA-OR-01.svg/150px-Army-USA-OR-01.svg.png", 
    "PV2": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/Army-USA-OR-02.svg/150px-Army-USA-OR-02.svg.png",
    "PFC": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/ec/Army-USA-OR-03.svg/150px-Army-USA-OR-03.svg.png",
    "SPC": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Army-USA-OR-04b.svg/150px-Army-USA-OR-04b.svg.png",
    "CPL": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Army-USA-OR-04a.svg/150px-Army-USA-OR-04a.svg.png",
    "SGT": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/Army-USA-OR-05.svg/150px-Army-USA-OR-05.svg.png",
    "SSG": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Army-USA-OR-06.svg/150px-Army-USA-OR-06.svg.png",
    "SFC": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Army-USA-OR-07.svg/150px-Army-USA-OR-07.svg.png",
    "MSG": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Army-USA-OR-08b.svg/150px-Army-USA-OR-08b.svg.png",
    "1SG": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Army-USA-OR-08a.svg/150px-Army-USA-OR-08a.svg.png",
    "SGM": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Army-USA-OR-09c.svg/150px-Army-USA-OR-09c.svg.png",
    
    # OFFICERS (Metal Bars/Leaves/Eagles)
    "2LT": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Army-USA-OF-01.svg/100px-Army-USA-OF-01.svg.png", # Gold Bar
    "1LT": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Army-USA-OF-02.svg/100px-Army-USA-OF-02.svg.png", # Silver Bar
    "CPT": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/76/Army-USA-OF-03.svg/100px-Army-USA-OF-03.svg.png", #
    
