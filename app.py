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

# --- 2. ЦВЕТОВАЯ ПАЛИТРА (TACTICAL HUD) ---
HUD_BG = "#050505"
HUD_PANEL = "#121212"
HUD_BORDER = "#333333"
ACCENT_GREEN = "#00FF41"    # Неоновый зеленый (текст/графики)
ACCENT_GOLD = "#D4AF37"     # Реалистичное золото (текст рангов)
TEXT_MAIN = "#E0E0E0"

AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. РЕАЛИСТИЧНЫЕ ТЕКСТУРЫ (METAL & CLOTH) ---
# Ссылки заменены на "объемные" версии (фото нашивок и значков)
RANK_IMGS = {
    # --- ENLISTED (ЗОЛОТОЕ ШИТЬЕ НА ТЕМНОМ) ---
    "PV1": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/U.S._Army_E-1_insignia.jpg/100px-U.S._Army_E-1_insignia.jpg", # Пустой или патч
    "PV2": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/US_Army_E2_insignia.jpg/100px-US_Army_E2_insignia.jpg",
    "PFC": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/US_Army_E3_insignia.jpg/100px-US_Army_E3_insignia.jpg",
    "SPC": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/US_Army_E4_insignia.jpg/100px-US_Army_E4_insignia.jpg",
    "CPL": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/US_Army_E4_CPL_insignia.jpg/100px-US_Army_E4_CPL_insignia.jpg",
    "SGT": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/US_Army_E5_insignia.jpg/100px-US_Army_E5_insignia.jpg",
    "SSG": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/US_Army_E6_insignia.jpg/100px-US_Army_E6_insignia.jpg",
    "SFC": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/US_Army_E7_insignia.jpg/100px-US_Army_E7_insignia.jpg",
    "MSG": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/US_Army_E8_MSG_insignia.jpg/100px-US_Army_E8_MSG_insignia.jpg",
    "1SG": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/US_Army_E8_1SG_insignia.jpg/100px-US_Army_E8_1SG_insignia.jpg",
    "SGM": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/US_Army_E9_SGM_insignia.jpg/100px-US_Army_E9_SGM_insignia.jpg",
    
    # --- OFFICERS (МЕТАЛЛИЧЕСКИЕ ЗНАЧКИ) ---
    "2LT": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/US-O1_insignia.svg/100px-US-O1_insignia.svg.png", # Gold Bar (Metal look)
    "1LT": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/US-O2_insignia.svg/100px-US-O2_insignia.svg.png", # Silver Bar
    "CPT": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/US-O3_insignia.svg/100px-US-O3_insignia.svg.png", # Silver Bars
    "MAJ": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/US-O4_insignia.svg/100px-US-O4_insignia.svg.png", # Gold Oak
    "LTC": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/US-O5_insignia.svg/100px-US-O5_insignia.svg.png", # Silver Oak
    "COL": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/US-O6_insignia.svg/150px-US-O6_insignia.svg.png", # Silver Eagle
    
    # --- GENERALS (СЕРЕБРЯНЫЕ ЗВЕЗДЫ) ---
    "BG": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Army-USA-OF-07.svg/150px-Army-USA-OF-07.svg.png",
    "MG": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Army-USA-OF-08.svg/150px-Army-USA-OF-08.svg.png",
    "LTG": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Army-USA-OF-09.svg/150px-Army-USA-OF-09.svg.png",
    "GEN": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Army-USA-OF-10.svg/150px-Army-USA-OF-10.svg.png",
    "GA": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Army-USA-OF-11.svg/150px-Army-USA-OF-11.svg.png"
}

FULL_RANK_SYSTEM = [
    (0, 24, "РЕКРУТ", "PV1"), (25, 49, "РЯДОВОЙ", "PV2"), (50, 99, "РЯДОВОЙ 1 КЛ", "PFC"),
    (100, 149, "СПЕЦИАЛИСТ", "SPC"), (150, 199, "КАПРАЛ", "CPL"), (200, 299, "СЕРЖАНТ", "SGT"),
    (300, 399, "ШТАБ-СЕРЖАНТ", "SSG"), (400, 499, "СЕРЖАНТ 1 КЛ", "SFC"), (500, 649, "МАСТЕР-СЕРЖАНТ", "MSG"),
    (650, 799, "1-Й СЕРЖАНТ", "1SG"), (800, 999, "СЕРЖАНТ-МАЙОР", "SGM"), (1000, 1499, "2-Й ЛЕЙТЕНАНТ", "2LT"),
    (1500, 1999, "1-Й ЛЕЙТЕНАНТ", "1LT"), (2000, 2999, "КАПИТАН", "CPT"), (3000, 3999, "МАЙОР", "MAJ"),
    (4000, 4999, "ПОДПОЛКОВНИК", "LTC"), (5000, 5999, "ПОЛКОВНИК", "COL"), (6000, 7999, "БРИГАДНЫЙ ГЕНЕРАЛ", "BG"),
    (8000, 9999, "ГЕНЕРАЛ-МАЙОР", "MG"), (10000, 14999, "ГЕНЕРАЛ-ЛЕЙТЕНАНТ", "LTG"), (15000, 24999, "ГЕНЕРАЛ", "GEN"),
    (25000, 999999, "ГЕНЕРАЛ АРМИИ", "GA")
]

def get_rank_data(xp):
    for r_min, r_max, title, abbr in FULL_RANK_SYSTEM:
        if r_min <= xp <= r_max:
            needed = r_max - r_min + 1
            current = xp - r_min
            # Если конкретной картинки нет, берем PV2 как заглушку
            img = RANK_IMGS.get(abbr, RANK_IMGS["PV2"])
            return {"title": title, "abbr": abbr, "icon": img, "progress": int((current/needed)*100), "next_xp": needed-current}
    return {"title": "ГЕНЕРАЛ АРМИИ", "abbr": "GA", "icon": RANK_IMGS["GA"], "progress": 100, "next_xp": 0}

def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def detect_muscle(ex):
    ex = str(ex).lower()
    if any(x in ex for x in ['жим', 'chest', 'отжимания', 'брусья', 'груд']): return "ГРУДЬ"
    if any(x in ex for x in ['тяга', 'спина', 'back', 'row', 'подтягивания']): return "СПИНА"
    if any(x in ex for x in ['присед', 'ноги', 'legs', 'squat', 'выпады']): return "НОГИ"
    if any(x in ex for x in ['бицепс', 'трицепс', 'arms', 'молот']): return "РУКИ"
    if any(x in ex for x in ['плечи', 'махи', 'shouder', 'press', 'армейский']): return "ПЛЕЧИ"
    if any(x in ex for x in ['пресс', 'abs', 'core', 'планка']): return "ПРЕСС"
    return "ОБЩЕЕ"

# --- 4. CSS (HUD DESIGN) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

    .stApp {{ background-color: {HUD_BG}; color: {TEXT_MAIN}; font-family: 'Share Tech Mono', monospace; }}
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* КАРТОЧКА */
    .hud-card {{
        background-color: {HUD_PANEL};
        border: 1px solid {HUD_BORDER};
        border-top: 2px solid {ACCENT_GREEN};
        padding: 15px; margin-bottom: 20px;
        position: relative;
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.05);
    }}
    /* Декоративный уголок */
    .hud-card::after {{
        content: ''; position: absolute; bottom: 0; right: 0;
        width: 10px; height: 10px;
        border-bottom: 2px solid {ACCENT_GREEN};
        border-right: 2px solid {ACCENT_GREEN};
    }}

    /* АВАТАР И РАНГ */
    .avatar-area {{ 
        width: 80px; height: 80px; 
        border: 2px solid {ACCENT_GOLD}; 
        border-radius: 5px; 
        overflow: hidden; float: left; margin-right: 15px; 
    }}
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    .user-name {{ font-family: 'Oswald', sans-serif; font-size: 32px; color: #FFF; line-height: 1; }}
    
    .progress-track {{ width: 100%; height: 6px; background: #222; margin-top: 8px; border: 1px solid #444; }}
    .progress-fill {{ height: 100%; background: {ACCENT_GREEN}; box-shadow: 0 0 10px {ACCENT_GREEN}; }}
    
    .stat-badge {{ 
        background: rgba(0, 255, 65, 0.1); color: {ACCENT_GREEN}; 
        padding: 2px 8px; border: 1px solid {ACCENT_GREEN}; 
        font-size: 12px; margin-right: 5px; font-family: 'Share Tech Mono'; 
    }}

    /* ЗАГОЛОВКИ */
    .section-title {{
        font-family: 'Oswald', sans-serif; font-size: 18px; color: {TEXT_MAIN};
        border-left: 4px solid {ACCENT_GREEN}; padding-left: 10px; margin: 25px 0 10px 0;
        text-transform: uppercase; letter-spacing: 2px;
    }}

    /* --- КАЛЕНДАРЬ (БЕЗ ПЛАГИНА) --- */
    div[data-testid="column"] {{ padding: 0 !important; margin: 0 !important; }}
    div[data-testid="stHorizontalBlock"] {{ gap: 0 !important; }}
    
    div.stButton > button {{
        width: 100%; aspect-ratio: 1 / 1;
        border: 1px solid #222; background-color: #0A0A0A; color: #666;
        border-radius: 0px; font-family: 'Share Tech Mono', monospace; font-size: 14px;
        margin: 0px !important; display: flex; align-items: center; justify-content: center;
        transition: all 0.2s;
    }}
    div.stButton > button:hover {{ border: 1px solid {ACCENT_GREEN}; color: {ACCENT_GREEN}; z-index: 5; background-color: #111; }}
    
    /* INPUTS */
    input, textarea, select {{ 
        background: #080808 !important; color: {ACCENT_GREEN} !important; 
        border: 1px solid #333 !important; font-family: 'Share Tech Mono' !important; 
    }}
    
    .streamlit-expanderHeader {{ background: {HUD_PANEL} !important; color: {ACCENT_GOLD} !important; border: 1px solid #333; }}
    </style>
""", unsafe_allow_html=True)

# --- 5. DATA LOADING ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["service_account_json"], strict=False), scope)
    client = gspread.authorize(creds)
    sheet = client.open("IRON_GYM_DB").sheet1
    raw_data = sheet.get_all_records()
    
    if raw_data:
        df = pd.DataFrame(raw_data)
        df.columns = df.columns.str.strip()
        date_col = next((c for c in df.columns if "дат" in c.lower() or "date" in c.lower() or "день" in c.lower()), None)
        if date_col:
            df.rename(columns={date_col: 'Date'}, inplace=True)
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
        
        if 'Вес (кг)' in df.columns: 
            df['Вес (кг)'] = df['Вес (кг)'].astype(str).str.replace(',', '.')
            df['Вес (кг)'] = pd.to_numeric(df['Вес (кг)'], errors='coerce').fillna(0)
        if 'Сет' not in df.columns: df['Сет'] = "-"
        if 'Упражнение' not in df.columns: df['Упражнение'] = "Unknown"
        df['Muscle'] = df['Упражнение'].apply(detect_muscle)
    else: df = pd.DataFrame()
except: df = pd.DataFrame()

total_xp = len(df)
rank = get_rank_data(total_xp)
trained_dates = set(df['Date'].dt.date) if not df.empty else set()

# --- 6. UI: PROFILE ---
st.markdown(f"""
<div class="hud-card" style="display:flex; align-items:center;">
    <div class="avatar-area"><img src="{AVATAR_URL}" class="avatar-img"></div>
    <div style="flex-grow:1;">
        <div class="user-name">SERGEY</div>
        <div style="margin:5px 0;">
            <span class="stat-badge">EXP: {total_xp}</span>
            <span class="stat-badge">{rank['title']}</span>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width: {rank['progress']}%;"></div></div>
        <div style="font-size:10px; color:#777; text-align:right; font-family:'Share Tech Mono';">NEXT RANK IN: {rank['next_xp']}</div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander(f"{rank['title']} // {rank['abbr']} (OPEN LIST)"):
    for r_min, r_max, title, abbr in FULL_RANK_SYSTEM:
        active = "border-left:2px solid #D4AF37; background:rgba(212,175,55,0.1);" if title == rank['title'] else ""
        col = ACCENT_GOLD if title == rank['title'] else "#666"
        img = RANK_IMGS.get(abbr, RANK_IMGS["PV1"])
        st.markdown(f"""<div style="display:flex; align-items:center; padding:10px; border-bottom:1px solid #222; {active}">
            <img src="{img}" style="height:40px; margin-right:15px; object-fit:contain;">
            <div style="flex-grow:1; color:{col}; font-family:'Oswald'; letter-spacing:1px;">{title}</div>
            <div style="color:#444; font-size:12px;">{r_min}</div>
        </div>""", unsafe_allow_html=True)

selected = option_menu(None, ["DASHBOARD", "LOGBOOK", "AI COACH"], icons=["crosshair", "list-task", "robot"], 
    orientation="horizontal", styles={
        "container": {"padding": "0!important", "background": "transparent"}, 
        "nav-link": {"font-family": "Oswald", "color": "#666", "text-transform": "uppercase"}, 
        "nav-link-selected": {"background-color": ACCENT_GREEN, "color": "black"}
    })

if selected == "DASHBOARD":
    
    # 1. RADAR
    st.markdown('<div class="section-title">BODY ARMOR STATUS</div>', unsafe_allow_html=True)
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    
    if 'cal_date' not in st.session_state: st.session_state.cal_date = None
    
    f_df = df.copy()
    status_text = "ALL SYSTEMS NOMINAL"
    if st.session_state.cal_date:
        f_df = df[df['Date'].dt.date == st.session_state.cal_date]
        status_text = f"FILTER: {st.session_state.cal_date.strftime('%Y-%m-%d')}"
        if st.button("RESET FILTER"):
            st.session_state.cal_date = None
            st.rerun()
            
    st.markdown(f"<div style='text-align:center; color:{ACCENT_GREEN}; font-family:Share Tech Mono; font-size:12px; margin-bottom:10px; border:1px solid #222; padding:5px;'>{status_text}</div>", unsafe_allow_html=True)

    if not f_df.empty:
        muscles = f_df.groupby('Muscle')['Сет'].count().reset_index()
        target = ["ГРУДЬ", "СПИНА", "НОГИ", "РУКИ", "ПЛЕЧИ", "ПРЕСС"]
        radar = pd.DataFrame({"Muscle": target}).merge(muscles, on="Muscle", how="left").fillna(0)
        
        fig = go.Figure(data=go.Scatterpolar(
            r=radar['Сет'], theta=radar['Muscle'], fill='toself',
            line=dict(color=ACCENT_GREEN, width=2), fillcolor='rgba(0, 255, 65, 0.1)', marker=dict(size=5, color=ACCENT_GREEN)
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, showticklabels=False, linecolor='#333'), angularaxis=dict(linecolor='#333', tickfont=dict(color=TEXT_MAIN, family="Oswald"))),
            showlegend=False, height=250, margin=dict(l=30, r=30, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF')
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
    else: st.info("NO DATA")
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. CALENDAR (NO PLUGIN)
    st.markdown('<div class="section-title">MISSION TIMELINE</div>', unsafe_allow_html=True)
    st.markdown('<div class="hud-card" style="padding:5px;">', unsafe_allow_html=True)
    
    if 'c_year' not in st.session_state: st.session_state.c_year = date.today().year
    if 'c_month' not in st.session_state: st.session_state.c_month = date.today().month

    def change_m(d):
        m = st.session_state.c_month + d
        y = st.session_state.c_year
        if m>12: m=1; y+=1
        elif m<1: m=12; y-=1
        st.session_state.c_month = m
        st.session_state.c_year = y

    c1, c2, c3 = st.columns([1,4,1])
    with c1: st.button(" < ", on_click=change_m, args=(-1,), key="p")
    with c2: 
        mn = calendar.month_name[st.session_state.c_month].upper()
        st.markdown(f"<div style='text-align:center; font-family:Oswald; font-size:18px; color:{ACCENT_GREEN}; padding-top:10px;'>{mn} {st.session_state.c_year}</div>", unsafe_allow_html=True)
    with c3: st.button(" > ", on_click=change_m, args=(1,), key="n")

    cal_obj = calendar.monthcalendar(st.session_state.c_year, st.session_state.c_month)
    today = date.today()
    
    cols = st.columns(7)
    for i, d in enumerate(["MO","TU","WE","TH","FR","SA","SU"]):
        cols[i].markdown(f"<div style='text-align:center; font-size:10px; color:#555;'>{d}</div>", unsafe_allow_html=True)

    for week in cal_obj:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0: cols[i].write("")
            else:
                curr = date(st.session_state.c_year, st.session_state.c_month, day)
                is_tr = curr in trained_dates
                is_tod = (curr == today)
                label = f"{day}"
                if cols[i].button(label, key=f"d_{curr}"):
                    if is_tr: st.session_state.cal_date = curr
                    else: st.session_state.cal_date = None
                    st.rerun()

                bg = "#080808"; fg = "#444"; bdr = "1px solid #1a1a1a"
                if is_tr: bg = ACCENT_GREEN; fg = "#000"; bdr = f"1px solid {ACCENT_GREEN}"
                elif curr < today: bg = "#220000"; fg = "#662222"; bdr = "1px solid #330000"
                if is_tod: bdr = f"2px solid {ACCENT_GOLD}"; fg = ACCENT_GOLD; bg = "transparent" if not is_tr else bg

                st.markdown(f"""<script>
                    var buttons = window.parent.document.querySelectorAll('div[data-testid="column"] button');
                    for (var i = 0; i < buttons.length; i++) {{
                        if (buttons[i].innerText === "{label}") {{
                            buttons[i].style.backgroundColor = "{bg}";
                            buttons[i].style.color = "{fg}";
                            buttons[i].style.border = "{bdr}";
                        }}
                    }}
                </script>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 3. TABLE
    st.markdown('<div class="section-title">LOG ENTRIES</div>', unsafe_allow_html=True)
    if not f_df.empty:
        show = f_df.sort_values(by=['Date', 'Сет'], ascending=[False, True]).copy()
        show['Date'] = show['Date'].dt.strftime('%d.%m')
        st.dataframe(show[['Date', 'Сет', 'Упражнение', 'Вес (кг)', 'Повт']], use_container_width=True, hide_index=True)

elif selected == "LOGBOOK":
    st.markdown('<div class="section-title">NEW MISSION ENTRY</div>', unsafe_allow_html=True)
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    with st.form("add"):
        d = st.date_input("DATE")
        c1, c2 = st.columns([1,2])
        with c1: s = st.text_input("SET", "1")
        with c2: e = st.text_input("EXERCISE")
        c3, c4, c5 = st.columns(3)
        with c3: p = st.number_input("REPS", 1)
        with c4: w = st.number_input("WEIGHT", step=2.5)
        with c5: r = st.number_input("RPE", 1)
        if st.form_submit_button("COMMIT DATA"):
            try:
                sheet.append_row([str(d), s,
                
