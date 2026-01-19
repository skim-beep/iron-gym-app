import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from streamlit_option_menu import option_menu
import base64

# --- ПОДКЛЮЧЕНИЕ КАЛЕНДАРЯ ---
try:
    from streamlit_calendar import calendar
except ImportError:
    st.error("⚠️ ОШИБКА: Плагин календаря не найден.")
    st.info("Откройте терминал и введите команду: pip install streamlit-calendar")
    st.stop()

# --- 1. НАСТРОЙКИ ---
st.set_page_config(
    page_title="IRON GYM OS",
    page_icon="🦅",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- 2. ТЕМА (DARK CAMO) ---
CAMO_BG = "#0e0e0e"
CAMO_PANEL = "#1c1f1a"
CAMO_GREEN = "#4b5320"
ACCENT_GOLD = "#FFD700"     # Золото (2LT, MAJ)
ACCENT_SILVER = "#E0E0E0"   # Серебро (Остальные офицеры)
TEXT_COLOR = "#B0B0B0"

AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. ГЕНЕРАТОР ЗНАКОВ РАЗЛИЧИЯ (SVG REALISM) ---
def get_rank_svg(rank_type, grade):
    # Логика цветов по уставу
    color = ACCENT_GOLD
    if rank_type == "OFFICER":
        # 0=2LT(Gold), 1=1LT(Silver), 2=CPT(Silver), 3=MAJ(Gold), 4+=Silver
        if grade in [1, 2, 4, 5] or grade >= 6: 
            color = ACCENT_SILVER
    
    # Холст 40x40
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 100 100" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">'
    
    if rank_type == "ENLISTED":
        # Логика полосок и дуг
        chevrons = 0
        rockers = 0
        
        if grade == 1: chevrons = 1 # PV2
        elif grade == 2: chevrons = 1; rockers = 1 # PFC
        elif grade == 3: # SPC (Shield)
             svg += f'<path d="M20,20 L80,20 L80,60 L50,90 L20,60 Z" fill="{CAMO_GREEN}" stroke="{color}" stroke-width="4"/>'
             svg += f'<path d="M50,15 L80,30 L80,50 L50,80 L20,50 L20,30 Z" fill="{color}" stroke="none"/>'
             chevrons = -1 # Skip loops
        elif grade == 4: chevrons = 3 # SGT
        elif grade == 5: chevrons = 3; rockers = 1 # SSG
        elif grade == 6: chevrons = 3; rockers = 2 # SFC
        elif grade >= 7: chevrons = 3; rockers = 3 # MSG/SGM/CSM
        
        if chevrons >= 0:
            for i in range(chevrons):
                y = 35 + (i * 12)
                svg += f'<path d="M15,{y} L50,{y-20} L85,{y}" />'
            for i in range(rockers):
                y = 65 + (i * 10)
                svg += f'<path d="M15,{y-5} Q50,{y+15} 85,{y-5}" />'
            
    elif rank_type == "OFFICER":
        # ПЛАНКИ (BARS)
        if grade == 0 or grade == 1: # 2LT / 1LT
            svg += f'<rect x="40" y="20" width="20" height="60" fill="{color}" stroke="none"/>'
        elif grade == 2: # CPT (2 Bars)
            svg += f'<rect x="25" y="20" width="15" height="60" fill="{color}" stroke="none"/>'
            svg += f'<rect x="60" y="20" width="15" height="60" fill="{color}" stroke="none"/>'
        
        # ДУБОВЫЕ ЛИСТЬЯ (OAK LEAF) - MAJ / LTC
        elif grade == 3 or grade == 4:
            svg += f'<path d="M50,10 Q80,10 80,40 Q80,70 50,90 Q20,70 20,40 Q20,10 50,10 Z" fill="{color}" stroke="none"/>'
            svg += f'<line x1="50" y1="10" x2="50" y2="90" stroke="#111" stroke-width="2"/>'
            
        # ОРЕЛ (EAGLE) - COL
        elif grade == 5:
            svg += f'<path d="M10,30 L40,40 L50,20 L60,40 L90,30 L80,60 L50,80 L20,60 Z" fill="{color}" stroke="none"/>'

        # ЗВЕЗДЫ (STARS) - GENERALS
        elif grade >= 6: 
            stars_count = grade - 5
            # Рисуем 5-конечные звезды
            def draw_star(cx, cy):
                # Координаты звезды
                return f'<polygon points="{cx},{cy-10} {cx+2},{cy-3} {cx+10},{cy-3} {cx+4},{cy+2} {cx+6},{cy+10} {cx},{cy+5} {cx-6},{cy+10} {cx-4},{cy+2} {cx-10},{cy-3} {cx-2},{cy-3}" fill="{color}" stroke="none"/>'

            if stars_count == 5: # GA (Pentagon)
                coords = [(50,20), (20,42), (80,42), (30,75), (70,75)]
                for cx, cy in coords: svg += draw_star(cx, cy)
            else: # Line
                start_x = 50 - ((stars_count-1)*12)
                for i in range(stars_count):
                    svg += draw_star(start_x + (i*25), 50)

    svg += '</svg>'
    b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"

# --- ПОЛНЫЙ СПИСОК ЗВАНИЙ (XP, Title, Abbr, Type, Grade) ---
FULL_RANK_SYSTEM = [
    # Солдатский состав
    (0, 24, "РЕКРУТ", "PV1", "ENLISTED", 0),
    (25, 49, "РЯДОВОЙ", "PV2", "ENLISTED", 1),
    (50, 99, "РЯДОВОЙ 1 КЛ", "PFC", "ENLISTED", 2),
    (100, 149, "СПЕЦИАЛИСТ", "SPC", "ENLISTED", 3),
    (150, 199, "КАПРАЛ", "CPL", "ENLISTED", 3),
    # Сержанты
    (200, 299, "СЕРЖАНТ", "SGT", "ENLISTED", 4),
    (300, 399, "ШТАБ-СЕРЖАНТ", "SSG", "ENLISTED", 5),
    (400, 499, "СЕРЖАНТ 1 КЛ", "SFC", "ENLISTED", 6),
    (500, 649, "МАСТЕР-СЕРЖАНТ", "MSG", "ENLISTED", 7),
    (650, 799, "1-Й СЕРЖАНТ", "1SG", "ENLISTED", 7),
    (800, 999, "СЕРЖАНТ-МАЙОР", "SGM", "ENLISTED", 8),
    # Офицеры
    (1000, 1499, "2-Й ЛЕЙТЕНАНТ", "2LT", "OFFICER", 0),  # GOLD
    (1500, 1999, "1-Й ЛЕЙТЕНАНТ", "1LT", "OFFICER", 1),  # SILVER
    (2000, 2999, "КАПИТАН", "CPT", "OFFICER", 2),        # SILVER
    (3000, 3999, "МАЙОР", "MAJ", "OFFICER", 3),          # GOLD OAK
    (4000, 4999, "ПОДПОЛКОВНИК", "LTC", "OFFICER", 4),   # SILVER OAK
    (5000, 5999, "ПОЛКОВНИК", "COL", "OFFICER", 5),      # EAGLE
    # Генералы
    (6000, 7999, "БРИГАДНЫЙ ГЕНЕРАЛ", "BG", "OFFICER", 6),   # 1 STAR
    (8000, 9999, "ГЕНЕРАЛ-МАЙОР", "MG", "OFFICER", 7),       # 2 STARS
    (10000, 14999, "ГЕНЕРАЛ-ЛЕЙТЕНАНТ", "LTG", "OFFICER", 8), # 3 STARS
    (15000, 24999, "ГЕНЕРАЛ", "GEN", "OFFICER", 9),          # 4 STARS
    (25000, 999999, "ГЕНЕРАЛ АРМИИ", "GA", "OFFICER", 10)    # 5 STARS
]

def get_rank_data(xp):
    for r_min, r_max, title, abbr, r_type, grade in FULL_RANK_SYSTEM:
        if r_min <= xp <= r_max:
            needed = r_max - r_min + 1
            current = xp - r_min
            return {"title": title, "abbr": abbr, "icon": get_rank_svg(r_type, grade), "progress": int((current/needed)*100), "next_xp": needed-current}
    return {"title": "ГЕНЕРАЛ АРМИИ", "abbr": "GA", "icon": get_rank_svg("OFFICER", 10), "progress": 100, "next_xp": 0}

def detect_muscle(ex):
    ex = str(ex).lower()
    if any(x in ex for x in ['жим', 'chest', 'отжимания', 'брусья', 'груд', 'сведения']): return "ГРУДЬ"
    if any(x in ex for x in ['тяга', 'спина', 'back', 'row', 'подтягивания']): return "СПИНА"
    if any(x in ex for x in ['присед', 'ноги', 'legs', 'squat', 'выпады', 'икры']): return "НОГИ"
    if any(x in ex for x in ['бицепс', 'трицепс', 'arms', 'молот']): return "РУКИ"
    if any(x in ex for x in ['плечи', 'махи', 'shouder', 'press', 'армейский']): return "ПЛЕЧИ"
    if any(x in ex for x in ['пресс', 'abs', 'core', 'планка']): return "ПРЕСС"
    return "ОБЩЕЕ"

# --- 4. CSS (TACTICAL FONT & STYLE) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500&display=swap');
    
    .stApp {{ background-color: {CAMO_BG}; color: {TEXT_COLOR}; font-family: 'Roboto Mono', monospace; }}
    #MainMenu, footer, header {{ visibility: hidden; }}

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
    
    /* КАЛЕНДАРЬ СТИЛИ (ПЛАГИН) */
    .fc-theme-standard {{ background-color: {CAMO_PANEL} !important; font-family: 'Oswald' !important; }}
    .fc-col-header-cell {{ background-color: #111 !important; color: #777 !important; border-bottom: 1px solid #333 !important; }}
    .fc-daygrid-day {{ border: 1px solid #2a2a2a !important; }}
    .fc-day-today {{ background-color: rgba(255, 215, 0, 0.05) !important; border: 1px solid {ACCENT_GOLD} !important; }}
    .fc-button-primary {{ background-color: {CAMO_GREEN} !important; border: none !important; color: white !important; font-family: 'Oswald' !important; }}
    .fc-toolbar-title {{ color: {ACCENT_GOLD} !important; font-size: 1.2em !important; }}
    .fc-daygrid-day-number {{ color: {TEXT_COLOR} !important; text-decoration: none !important; }}
    
    input, textarea, select {{ background: #111 !important; color: {ACCENT_GOLD} !important; border: 1px solid #444 !important; font-family: 'Roboto Mono' !important; }}
    .streamlit-expanderHeader {{ background: {CAMO_PANEL} !important; color: {ACCENT_GOLD} !important; font-family: 'Oswald' !important; }}
    div.stButton > button {{ width: 100%; background: #1a1a1a; color: {TEXT_COLOR}; border: 1px solid {CAMO_GREEN}; font-family: 'Oswald'; }}
    </style>
""", unsafe_allow_html=True)

# --- 5. DATA LOADING (SMART & SAFE) ---
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
        
        # УМНЫЙ ПОИСК КОЛОНКИ С ДАТОЙ
        date_col = next((c for c in df.columns if "дат" in c.lower() or "date" in c.lower() or "день" in c.lower()), None)
        
        if date_col:
            df.rename(columns={date_col: 'Date'}, inplace=True)
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
        else:
            st.warning("⚠️ Не найдена колонка с Датой.")
            df['Date'] = pd.to_datetime([])

        # Безопасная обработка чисел
        if 'Вес (кг)' in df.columns: 
            df['Вес (кг)'] = df['Вес (кг)'].astype(str).str.replace(',', '.')
            df['Вес (кг)'] = pd.to_numeric(df['Вес (кг)'], errors='coerce').fillna(0)
        
        if 'Сет' not in df.columns: df['Сет'] = "-"
        if 'Упражнение' not in df.columns: df['Упражнение'] = "Unknown"
        
        df['Muscle'] = df['Упражнение'].apply(detect_muscle)
    else:
        df = pd.DataFrame()
except Exception as e:
    df = pd.DataFrame()

# Статистика
total_xp = len(df)
rank = get_rank_data(total_xp)

# --- 6. ИНТЕРФЕЙС ---
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
    for r_min, r_max, title, abbr, r_type, grade in FULL_RANK_SYSTEM:
        bg = "background:rgba(255,215,0,0.1); border-left:2px solid #FFD700;" if title == rank['title'] else ""
        col = ACCENT_GOLD if title == rank['title'] else "#777"
        st.markdown(f"""<div style="display:flex; align-items:center; padding:8px; border-bottom:1px solid #333; {bg}">
            <img src="{get_rank_svg(r_type, grade)}" style="height:25px; margin-right:10px;">
            <div style="flex-grow:1; color:{col}; font-family:'Oswald';">{title}</div>
            <div style="font-family:'Roboto Mono'; font-size:10px; color:#555;">{r_min}</div>
        </div>""", unsafe_allow_html=True)

selected = option_menu(None, ["ДАШБОРД", "ЖУРНАЛ", "ТРЕНЕР"], icons=["crosshair", "list-task", "robot"], 
    orientation="horizontal", styles={"container": {"padding": "0!important", "background": "transparent"}, "nav-link": {"font-family": "Oswald", "color": "#777"}, "nav-link-selected": {"background": CAMO_GREEN, "color": "white"}})

if selected == "ДАШБОРД":
    # 1. RADAR
    st.markdown('<div class="tac-header">СТАТУС БРОНИ</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    
    # State for calendar click
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

    # 2. CALENDAR (PLUGIN)
    st.markdown('<div class="tac-header">КАЛЕНДАРЬ МИССИЙ</div>', unsafe_allow_html=True)
    events = []
    if not df.empty and 'Date' in df.columns:
        for d in df['Date'].dt.date.unique():
            # Зеленый фон для тренировок
            events.append({
                "title": "✅", 
                "start": str(d), 
                "backgroundColor": CAMO_GREEN, 
                "borderColor": ACCENT_GOLD,
                "display": "background"
            })
    
    cal = calendar(events=events, options={
        "headerToolbar": {"left": "prev,next", "center": "title", "right": "today"},
        "initialView": "dayGridMonth",
        "selectable": True,
        "height": 400
    }, key="main_cal")
    
    if cal.get("callback") == "dateClick":
        clicked = cal["dateClick"]["date"]
        if st.session_state.cal_date != clicked:
            st.session_state.cal_date = clicked
            st.rerun()

    # 3. TABLE
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
