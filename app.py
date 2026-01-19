import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from streamlit_option_menu import option_menu
import base64

# ПОПЫТКА ИМПОРТА КАЛЕНДАРЯ
try:
    from streamlit_calendar import calendar
except ImportError:
    st.error("⚠️ ПЛАГИН НЕ УСТАНОВЛЕН. Введите в терминал: pip3 install streamlit-calendar")
    st.stop()

# --- 1. НАСТРОЙКИ ---
st.set_page_config(
    page_title="IRON GYM OS",
    page_icon="🦅",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- 2. CAMO THEME ---
CAMO_DARK = "#0e0e0e"
CAMO_PANEL = "#1c1f1a"
CAMO_GREEN = "#4b5320"
ACCENT_GOLD = "#FFD700"
TEXT_COLOR = "#B0B0B0"

AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. НАСТОЯЩИЕ ШЕВРОНЫ (URL) ---
# Мы используем официальные SVG с Wikimedia. Они никогда не пропадут и выглядят идеально.
RANK_IMGS = {
    "PV1": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Army-USA-OR-01.svg/100px-Army-USA-OR-01.svg.png", # Пусто или лого
    "PV2": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/Army-USA-OR-02.svg/100px-Army-USA-OR-02.svg.png",
    "PFC": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/ec/Army-USA-OR-03.svg/100px-Army-USA-OR-03.svg.png",
    "SPC": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Army-USA-OR-04b.svg/100px-Army-USA-OR-04b.svg.png",
    "CPL": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Army-USA-OR-04a.svg/100px-Army-USA-OR-04a.svg.png",
    "SGT": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/Army-USA-OR-05.svg/100px-Army-USA-OR-05.svg.png",
    "SSG": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Army-USA-OR-06.svg/100px-Army-USA-OR-06.svg.png",
    "SFC": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Army-USA-OR-07.svg/100px-Army-USA-OR-07.svg.png",
    "MSG": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Army-USA-OR-08b.svg/100px-Army-USA-OR-08b.svg.png",
    "1SG": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Army-USA-OR-08a.svg/100px-Army-USA-OR-08a.svg.png",
    "SGM": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Army-USA-OR-09c.svg/100px-Army-USA-OR-09c.svg.png",
    
    # OFFICERS (Золото и Серебро соблюдены)
    "2LT": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Army-USA-OF-01.svg/50px-Army-USA-OF-01.svg.png", # Gold Bar
    "1LT": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Army-USA-OF-02.svg/50px-Army-USA-OF-02.svg.png", # Silver Bar
    "CPT": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/76/Army-USA-OF-03.svg/50px-Army-USA-OF-03.svg.png", # 2 Bars
    "MAJ": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Army-USA-OF-04.svg/50px-Army-USA-OF-04.svg.png", # Gold Oak
    "LTC": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Army-USA-OF-05.svg/50px-Army-USA-OF-05.svg.png", # Silver Oak
    "COL": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Army-USA-OF-06.svg/100px-Army-USA-OF-06.svg.png", # Eagle
    
    # GENERALS
    "BG": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Army-USA-OF-07.svg/100px-Army-USA-OF-07.svg.png",
    "MG": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Army-USA-OF-08.svg/100px-Army-USA-OF-08.svg.png",
    "LTG": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Army-USA-OF-09.svg/100px-Army-USA-OF-09.svg.png",
    "GEN": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Army-USA-OF-10.svg/100px-Army-USA-OF-10.svg.png",
    "GA": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Army-USA-OF-11.svg/100px-Army-USA-OF-11.svg.png"
}

FULL_RANK_SYSTEM = [
    (0, 24, "РЕКРУТ", "PV1"), (25, 49, "РЯДОВОЙ", "PV2"),
    (50, 99, "РЯДОВОЙ 1 КЛ", "PFC"), (100, 149, "СПЕЦИАЛИСТ", "SPC"),
    (150, 199, "КАПРАЛ", "CPL"), (200, 299, "СЕРЖАНТ", "SGT"),
    (300, 399, "ШТАБ-СЕРЖАНТ", "SSG"), (400, 499, "СЕРЖАНТ 1 КЛ", "SFC"),
    (500, 649, "МАСТЕР-СЕРЖАНТ", "MSG"), (650, 799, "1-Й СЕРЖАНТ", "1SG"),
    (800, 999, "СЕРЖАНТ-МАЙОР", "SGM"), (1000, 1499, "2-Й ЛЕЙТЕНАНТ", "2LT"),
    (1500, 1999, "1-Й ЛЕЙТЕНАНТ", "1LT"), (2000, 2999, "КАПИТАН", "CPT"),
    (3000, 3999, "МАЙОР", "MAJ"), (4000, 4999, "ПОДПОЛКОВНИК", "LTC"),
    (5000, 5999, "ПОЛКОВНИК", "COL"), (6000, 7999, "БРИГАДНЫЙ ГЕНЕРАЛ", "BG"),
    (8000, 9999, "ГЕНЕРАЛ-МАЙОР", "MG"), (10000, 14999, "ГЕНЕРАЛ-ЛЕЙТЕНАНТ", "LTG"),
    (15000, 24999, "ГЕНЕРАЛ", "GEN"), (25000, 999999, "ГЕНЕРАЛ АРМИИ", "GA")
]

def get_rank_data(xp):
    for r_min, r_max, title, abbr in FULL_RANK_SYSTEM:
        if r_min <= xp <= r_max:
            needed = r_max - r_min + 1
            current = xp - r_min
            # Получаем картинку из словаря, если нет - заглушка
            img = RANK_IMGS.get(abbr, "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Army-USA-OR-01.svg/100px-Army-USA-OR-01.svg.png")
            return {"title": title, "abbr": abbr, "icon": img, "progress": int((current/needed)*100), "next_xp": needed-current}
    return {"title": "ГЕНЕРАЛ АРМИИ", "abbr": "GA", "icon": RANK_IMGS["GA"], "progress": 100, "next_xp": 0}

def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def detect_muscle(ex):
    ex = str(ex).lower()
    if any(x in ex for x in ['жим', 'chest', 'отжимания', 'брусья', 'груд', 'сведения']): return "ГРУДЬ"
    if any(x in ex for x in ['тяга', 'спина', 'back', 'row', 'подтягивания']): return "СПИНА"
    if any(x in ex for x in ['присед', 'ноги', 'legs', 'squat', 'выпады', 'икры']): return "НОГИ"
    if any(x in ex for x in ['бицепс', 'трицепс', 'arms', 'молот']): return "РУКИ"
    if any(x in ex for x in ['плечи', 'махи', 'shouder', 'press', 'армейский']): return "ПЛЕЧИ"
    if any(x in ex for x in ['пресс', 'abs', 'core', 'планка']): return "ПРЕСС"
    return "ОБЩЕЕ"

# --- 4. CSS ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500&display=swap');
    
    .stApp {{ background-color: {CAMO_DARK}; color: {TEXT_COLOR}; font-family: 'Roboto Mono', monospace; }}
    h1, h2, h3, .tac-font {{ font-family: 'Oswald', sans-serif !important; letter-spacing: 1px; text-transform: uppercase; }}
    
    .camo-card {{
        background-color: {CAMO_PANEL}; border: 1px solid #333; border-left: 4px solid {CAMO_GREEN};
        padding: 15px; margin-bottom: 20px; border-radius: 4px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    }}
    .avatar-area {{ width: 80px; height: 80px; border: 2px solid {ACCENT_GOLD}; border-radius: 50%; overflow: hidden; float: left; margin-right: 15px; }}
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    .progress-track {{ width: 100%; height: 8px; background: #111; margin-top: 8px; }}
    .progress-fill {{ height: 100%; background: {CAMO_GREEN}; }}
    .stat-badge {{ background: #111; color: {ACCENT_GOLD}; padding: 3px 8px; border: 1px solid {CAMO_GREEN}; font-size: 11px; margin-right: 5px; font-family: 'Oswald'; }}
    .tac-header {{ font-family: 'Oswald', sans-serif; font-size: 18px; color: {TEXT_COLOR}; border-bottom: 2px solid {CAMO_GREEN}; padding-bottom: 5px; margin: 20px 0 10px 0; }}
    
    /* КАЛЕНДАРЬ СТИЛИ */
    .fc-theme-standard {{ background-color: {CAMO_PANEL} !important; font-family: 'Oswald' !important; }}
    .fc-col-header-cell {{ background-color: #111 !important; color: #777 !important; border-bottom: 1px solid #333 !important; }}
    .fc-daygrid-day {{ border: 1px solid #2a2a2a !important; }}
    .fc-day-today {{ background-color: rgba(255, 215, 0, 0.05) !important; border: 1px solid {ACCENT_GOLD} !important; }}
    .fc-button-primary {{ background-color: {CAMO_GREEN} !important; border: none !important; color: white !important; font-family: 'Oswald' !important; }}
    .fc-toolbar-title {{ color: {ACCENT_GOLD} !important; font-size: 1.2em !important; }}
    
    input, textarea, select {{ background: #111 !important; color: {ACCENT_GOLD} !important; border: 1px solid #444 !important; font-family: 'Roboto Mono' !important; }}
    .streamlit-expanderHeader {{ background: {CAMO_PANEL} !important; color: {ACCENT_GOLD} !important; font-family: 'Oswald' !important; }}
    div.stButton > button {{ width: 100%; background: #1a1a1a; color: {TEXT_COLOR}; border: 1px solid {CAMO_GREEN}; font-family: 'Oswald'; }}
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
        
        # Smart Date Find
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
user_age = (date.today() - USER_BIRTHDAY).days // 365

# --- 6. UI ---
st.markdown(f"""
<div class="camo-card" style="display:flex; align-items:center;">
    <div class="avatar-area"><img src="{AVATAR_URL}" class="avatar-img"></div>
    <div style="flex-grow:1;">
        <div style="font-family:'Oswald'; font-size:28px; color:#FFF; line-height:1;">СЕРГЕЙ</div>
        <div style="margin:5px 0;">
            <span class="stat-badge">LVL: {total_xp}</span>
            <span class="stat-badge">{rank['title']}</span>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width: {rank['progress']}%;"></div></div>
        <div style="font-size:10px; color:#777; text-align:right; font-family:'Roboto Mono';">NEXT: {rank['next_xp']} XP</div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander(f"{rank['title']} // {rank['abbr']} (СПИСОК)"):
    for r_min, r_max, title, abbr in FULL_RANK_SYSTEM:
        bg = "background:rgba(255,215,0,0.1); border-left:2px solid #FFD700;" if title == rank['title'] else ""
        col = ACCENT_GOLD if title == rank['title'] else "#777"
        # Получаем реальную картинку
        img_url = RANK_IMGS.get(abbr, RANK_IMGS["PV1"])
        st.markdown(f"""<div style="display:flex; align-items:center; padding:8px; border-bottom:1px solid #333; {bg}">
            <img src="{img_url}" style="height:35px; width:auto; margin-right:15px; object-fit:contain;">
            <div style="flex-grow:1; color:{col}; font-family:'Oswald';">{title}</div>
            <div style="font-family:'Roboto Mono'; font-size:10px; color:#555;">{r_min}</div>
        </div>""", unsafe_allow_html=True)

selected = option_menu(None, ["ДАШБОРД", "ЖУРНАЛ", "ТРЕНЕР"], icons=["crosshair", "list-task", "robot"], 
    orientation="horizontal", styles={"container": {"padding": "0!important", "background": "transparent"}, "nav-link": {"font-family": "Oswald", "color": "#777"}, "nav-link-selected": {"background": CAMO_GREEN, "color": "white"}})

if selected == "ДАШБОРД":
    st.markdown('<div class="tac-header">СТАТУС БРОНИ</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    if 'cal_date' not in st.session_state: st.session_state.cal_date = None
    
    f_df = df.copy()
    if st.session_state.cal_date:
        sel_dt = pd.to_datetime(st.session_state.cal_date).date()
        f_df = df[df['Date'].dt.date == sel_dt]
        st.markdown(f"<div style='text-align:center; color:{ACCENT_GOLD}; font-family:Oswald; margin-bottom:5px;'>ОТЧЕТ: {sel_dt.strftime('%d.%m.%Y')}</div>", unsafe_allow_html=True)
        if st.button("❌ СБРОСИТЬ ФИЛЬТР"):
            st.session_state.cal_date = None
            st.rerun()

    if not f_df.empty:
        muscles = f_df.groupby('Muscle')['Сет'].count().reset_index()
        target = ["ГРУДЬ", "СПИНА", "НОГИ", "РУКИ", "ПЛЕЧИ", "ПРЕСС"]
        radar = pd.DataFrame({"Muscle": target}).merge(muscles, on="Muscle", how="left").fillna(0)
        fig = go.Figure(data=go.Scatterpolar(r=radar['Сет'], theta=radar['Muscle'], fill='toself', line=dict(color=ACCENT_GOLD), fillcolor='rgba(255, 215, 0, 0.2)', marker=dict(size=6, color=ACCENT_GOLD)))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, linecolor='#333'), angularaxis=dict(linecolor='#333', tickfont=dict(color=TEXT_COLOR, family="Oswald"))), showlegend=False, height=250, margin=dict(l=35, r=35, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF'))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
    else: st.info("Нет данных")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="tac-header">КАЛЕНДАРЬ МИССИЙ</div>', unsafe_allow_html=True)
    events = []
    if not df.empty:
        for d in df['Date'].dt.date.unique():
            events.append({"title": "✅", "start": str(d), "backgroundColor": CAMO_GREEN, "borderColor": ACCENT_GOLD, "display": "background"})
    
    cal = calendar(events=events, options={"headerToolbar": {"left": "prev,next", "center": "title", "right": "today"}, "initialView": "dayGridMonth", "selectable": True, "height": 400}, key="main_cal")
    
    if cal.get("callback") == "dateClick":
        clicked = cal["dateClick"]["date"]
        if st.session_state.cal_date != clicked:
            st.session_state.cal_date = clicked
            st.rerun()

    st.markdown('<div class="tac-header">ЖУРНАЛ</div>', unsafe_allow_html=True)
    if not f_df.empty:
        show = f_df.sort_values(by=['Date', 'Сет'], ascending=[False, True]).copy()
        show['Date'] = show['Date'].dt.strftime('%d.%m')
        st.dataframe(show[['Date', 'Сет', 'Упражнение', 'Вес (кг)', 'Повт']], use_container_width=True, hide_index=True)

elif selected == "ЖУРНАЛ":
    st.markdown('<div class="tac-header">НОВАЯ ЗАПИСЬ</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    with st.form("add"):
        d = st.date_input("ДАТА")
        c1, c2 = st.columns([1,2])
        with c1: s = st.text_input("СЕТ", "№1")
        with c2: e = st.text_input("УПРАЖНЕНИЕ")
        c3, c4, c5 = st.columns(3)
        with c3: p = st.number_input("ПОДХОД", 1)
        with c4: w = st.number_input("ВЕС", step=2.5)
        with c5: r = st.number_input("ПОВТ", 1)
        if st.form_submit_button("СОХРАНИТЬ"):
            try:
                sheet.append_row([str(d), s, e, p, w, r, w*r, "", ""])
                st.success("OK")
                st.rerun()
            except Exception as ex: st.error(f"Error: {ex}")
    st.markdown('</div>', unsafe_allow_html=True)

elif selected == "ТРЕНЕР":
    st.markdown('<div class="tac-header">ИНСТРУКТОР</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    if "msg" not in st.session_state: st.session_state.msg = []
    for m in st.session_state.msg: st.chat_message(m["role"]).markdown(m["content"])
    if q := st.chat_input("..."):
        st.session_state.msg.append({"role": "user", "content": q})
        st.chat_message("user").markdown(q)
        try:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
            ans = model.generate_content(f"Role: Army Drill Sergeant. User Rank: {rank['title']}. Q: {q}").text
            st.chat_message("assistant").markdown(ans)
            st.session_state.msg.append({"role": "assistant", "content": ans})
        except: st.error("Connection lost.")
    st.markdown('</div>', unsafe_allow_html=True)
