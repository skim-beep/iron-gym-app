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

# --- 1. НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="IRON GYM OS",
    page_icon="🦅",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- 2. КОНФИГУРАЦИЯ ---
# ЦВЕТА (CAMO PALETTE)
CAMO_DARK = "#121410"       # Deep Dark Green/Black
CAMO_GREEN = "#4b5320"      # Army Green
CAMO_TEXT = "#8f9779"       # Muted Text
ACCENT_GOLD = "#FFD700"     # Rank Gold
ALERT_RED = "#8B0000"

AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. ГЕНЕРАТОР ШЕВРОНОВ (NANO BANANO SVG) ---
# Уменьшил размер viewbox и логику рисования
def get_rank_svg(rank_type, grade):
    color = ACCENT_GOLD
    # Размер холста уменьшен визуально в CSS, но здесь рисуем в векторе 100х100 для четкости
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 100 100" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round">'
    
    if rank_type == "ENLISTED":
        # Chevrons (^)
        chevrons = min(grade + 1, 3) if grade < 3 else 3
        rockers = 0
        if grade >= 3: rockers = 1 # CPL/SPC/SGT logic simplified for visual
        if grade >= 5: rockers = 2
        if grade >= 7: rockers = 3
        
        # Draw Chevrons
        for i in range(chevrons):
            y = 30 + (i * 15)
            svg += f'<path d="M15,{y} L50,{y-25} L85,{y}" />'
            
        # Draw Rockers (Arc underneath)
        for i in range(rockers):
            y = 65 + (i * 10)
            svg += f'<path d="M15,{y-10} Q50,{y+15} 85,{y-10}" />'
            
    elif rank_type == "OFFICER":
        # Bars and Oak Leaves logic simplified
        if grade == 0: # 2LT (1 Bar)
            svg += f'<rect x="40" y="20" width="20" height="60" fill="{color}" stroke="none"/>'
        elif grade == 1: # 1LT (1 Bar Filled - visual diff)
            svg += f'<rect x="30" y="20" width="40" height="60" fill="{color}" stroke="none"/>'
        elif grade == 2: # CPT (2 Bars)
            svg += f'<rect x="25" y="20" width="15" height="60" fill="{color}" stroke="none"/>'
            svg += f'<rect x="60" y="20" width="15" height="60" fill="{color}" stroke="none"/>'
        elif grade >= 3 and grade <= 5: # MAJ/LTC/COL (Oak Leaf/Eagle rep)
            svg += '<path d="M50,10 L80,40 L65,80 L35,80 L20,40 Z" fill="{color}" stroke="none"/>'.format(color=color)
        elif grade >= 6: # GENERALS (Stars)
            stars = grade - 5
            size = 20
            start_x = 50 - ((stars-1)*15)
            for i in range(stars):
                cx = start_x + (i*30)
                # Simple star shape
                svg += f'<circle cx="{cx}" cy="50" r="8" fill="{color}" stroke="none"/>'

    svg += '</svg>'
    b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"

# --- ПОЛНЫЙ СПИСОК ЗВАНИЙ ---
# Min XP, Max XP, Title, Abbr, Type, Grade (for svg)
FULL_RANK_SYSTEM = [
    # ENLISTED
    (0, 24, "РЕКРУТ", "PV1", "ENLISTED", 0),
    (25, 49, "РЯДОВОЙ", "PV2", "ENLISTED", 1),
    (50, 99, "РЯДОВОЙ 1 КЛ", "PFC", "ENLISTED", 2),
    (100, 149, "СПЕЦИАЛИСТ", "SPC", "ENLISTED", 3),
    (150, 199, "КАПРАЛ", "CPL", "ENLISTED", 3),
    (200, 299, "СЕРЖАНТ", "SGT", "ENLISTED", 4),
    (300, 399, "ШТАБ-СЕРЖАНТ", "SSG", "ENLISTED", 5), # <- Твой текущий уровень (376)
    (400, 499, "СЕРЖАНТ 1 КЛ", "SFC", "ENLISTED", 6),
    (500, 649, "МАСТЕР-СЕРЖАНТ", "MSG", "ENLISTED", 7),
    (650, 799, "ПЕРВЫЙ СЕРЖАНТ", "1SG", "ENLISTED", 7),
    (800, 999, "СЕРЖАНТ-МАЙОР", "SGM", "ENLISTED", 8),
    
    # OFFICERS (Starts at 1000 XP for gameplay balance)
    (1000, 1199, "2-Й ЛЕЙТЕНАНТ", "2LT", "OFFICER", 0),
    (1200, 1499, "1-Й ЛЕЙТЕНАНТ", "1LT", "OFFICER", 1),
    (1500, 1999, "КАПИТАН", "CPT", "OFFICER", 2),
    (2000, 2999, "МАЙОР", "MAJ", "OFFICER", 3),
    (3000, 3999, "ПОДПОЛКОВНИК", "LTC", "OFFICER", 4),
    (4000, 4999, "ПОЛКОВНИК", "COL", "OFFICER", 5),
    (5000, 6999, "БРИГАДНЫЙ ГЕНЕРАЛ", "BG", "OFFICER", 6),
    (7000, 9999, "ГЕНЕРАЛ-МАЙОР", "MG", "OFFICER", 7),
    (10000, 14999, "ГЕНЕРАЛ-ЛЕЙТЕНАНТ", "LTG", "OFFICER", 8),
    (15000, 999999, "ГЕНЕРАЛ", "GEN", "OFFICER", 9)
]

# --- 4. ФУНКЦИИ ---
def get_rank_data(xp):
    for r_min, r_max, title, abbr, r_type, grade in FULL_RANK_SYSTEM:
        if r_min <= xp <= r_max:
            needed = r_max - r_min + 1
            current = xp - r_min
            percent = int((current / needed) * 100)
            to_go = r_max - xp + 1
            return {
                "title": title, "abbr": abbr, 
                "icon": get_rank_svg(r_type, grade), 
                "progress": percent, "next_xp": to_go,
                "current_min": r_min, "current_max": r_max
            }
    return {"title": "GOD", "abbr": "GOD", "icon": get_rank_svg("OFFICER", 9), "progress": 100, "next_xp": 0}

def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def detect_muscle_group(exercise_name):
    ex = str(exercise_name).lower()
    if any(x in ex for x in ['жим лежа', 'жим гантелей', 'бабочка', 'chest', 'отжимания', 'брусья', 'груд', 'жим в тренажере']): return "ГРУДЬ"
    if any(x in ex for x in ['тяга', 'подтягивания', 'спина', 'back', 'row', 'становая']): return "СПИНА"
    if any(x in ex for x in ['присед', 'ноги', 'выпады', 'legs', 'squat', 'разгибания', 'сгибания']): return "НОГИ"
    if any(x in ex for x in ['бицепс', 'трицепс', 'молот', 'arms', 'bicep', 'концентрированный']): return "РУКИ"
    if any(x in ex for x in ['жим стоя', 'плечи', 'махи', 'shouder', 'press', 'разведение']): return "ПЛЕЧИ"
    if any(x in ex for x in ['пресс', 'планка', 'abs', 'core', 'скручивания']): return "ПРЕСС"
    return "ОБЩЕЕ"

# --- 5. TACTICAL CAMO CSS (BLACK OPS FONT EVERYWHERE) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&display=swap');

    /* ГЛОБАЛЬНЫЙ ШРИФТ */
    html, body, [class*="css"], font, span, div, button, input, select, textarea, h1, h2, h3, h4, h5, h6 {{
        font-family: 'Black Ops One', cursive !important;
    }}

    .stApp {{
        background-color: {CAMO_DARK};
        color: #E0E0E0;
    }}
    
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* КАРТОЧКА КАМУФЛЯЖ */
    .camo-card {{
        background-color: #242621;
        border: 1px solid #333;
        border-left: 5px solid {CAMO_GREEN};
        padding: 15px;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    }}

    /* ПРОФИЛЬ */
    .avatar-area {{
        width: 80px; height: 80px; 
        border: 2px solid {ACCENT_GOLD}; border-radius: 10px;
        overflow: hidden; float: left; margin-right: 15px;
    }}
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    
    .user-name {{ font-size: 28px; color: #FFF; margin: 0; line-height: 1; }}
    
    /* ЗВАНИЕ И ПРОГРЕСС */
    .rank-display {{ font-size: 16px; color: {ACCENT_GOLD}; margin-top: 5px; cursor: pointer; }}
    .rank-icon-img {{ height: 25px; width: auto; vertical-align: middle; margin-left: 10px; }}
    
    .progress-track {{
        width: 100%; height: 12px; background: #111; border: 1px solid #444; margin-top: 8px;
    }}
    .progress-fill {{ 
        height: 100%; 
        background: repeating-linear-gradient(45deg, {CAMO_GREEN}, {CAMO_GREEN} 10px, #3a4019 10px, #3a4019 20px); 
    }}
    
    .stat-badge {{
        background: #111; color: {CAMO_TEXT}; padding: 2px 8px; 
        border: 1px solid {CAMO_GREEN}; font-size: 12px; margin-right: 5px;
    }}

    /* EXPANDER STYLE (СПИСОК ЗВАНИЙ) */
    .streamlit-expanderHeader {{
        background-color: #242621 !important;
        color: {CAMO_TEXT} !important;
        border: 1px solid #333 !important;
        font-size: 14px !important;
    }}
    .rank-row-item {{
        display: flex; align-items: center; padding: 8px; 
        border-bottom: 1px solid #333;
    }}
    .rank-row-active {{
        background-color: rgba(255, 215, 0, 0.1);
        border-left: 3px solid {ACCENT_GOLD};
    }}

    /* МЕНЮ */
    div[data-testid="stHorizontalBlock"] button {{
        border-radius: 0px !important;
    }}

    /* ЗАГОЛОВКИ */
    .tac-header {{
        font-size: 20px; color: {CAMO_TEXT};
        border-bottom: 2px solid {CAMO_GREEN}; padding-bottom: 5px; margin: 25px 0 10px 0;
    }}

    /* КНОПКИ КАЛЕНДАРЯ */
    .cal-btn {{
        width: 100%; height: 45px; border: 1px solid #333; 
        background: #1a1a1a; color: #555; font-size: 14px;
        cursor: pointer; display: flex; align-items: center; justify-content: center;
    }}
    .cal-btn:hover {{ border-color: {ACCENT_GOLD}; color: {ACCENT_GOLD}; }}
    .cal-btn.trained {{ background: {CAMO_GREEN}; color: #FFF; }}
    .cal-btn.missed {{ background: {ALERT_RED}; color: #FFF; opacity: 0.5; }}
    .cal-btn.today {{ border: 2px solid {ACCENT_GOLD}; color: {ACCENT_GOLD}; }}
    
    /* INPUTS */
    input, textarea, select {{ 
        background: #111 !important; color: {ACCENT_GOLD} !important; 
        border: 1px solid #444 !important; font-family: 'Black Ops One', cursive !important;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 6. ЗАГРУЗКА ДАННЫХ ---
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
        df.columns = df.columns.str.strip()
        for col in ['Вес (кг)', 'Тоннаж']:
            if col in df.columns: df[col] = df[col].astype(str).str.replace(',', '.')
        df['Вес (кг)'] = pd.to_numeric(df['Вес (кг)'], errors='coerce').fillna(0)
        df['Повт'] = pd.to_numeric(df['Повт'], errors='coerce').fillna(0)
        df['Тоннаж'] = pd.to_numeric(df['Тоннаж'], errors='coerce').fillna(0)
        if 'Сет' not in df.columns: df['Сет'] = "-"
        df['Сет'] = df['Сет'].astype(str).replace('', '-')
        df['День/Дата'] = pd.to_datetime(df['День/Дата'], errors='coerce')
        df = df.dropna(subset=['День/Дата'])
        df['Muscle'] = df['Упражнение'].apply(detect_muscle_group)
except Exception as e:
    df = pd.DataFrame()

total_xp = len(df)
rank = get_rank_data(total_xp)
user_age = calculate_age(USER_BIRTHDAY)
trained_dates = set(df['День/Дата'].dt.date) if not df.empty else set()

# --- 7. UI ПРОФИЛЯ ---
st.markdown(f"""
<div class="camo-card" style="display:flex; align-items:center;">
    <div class="avatar-area"><img src="{AVATAR_URL}" class="avatar-img"></div>
    <div style="flex-grow:1;">
        <div class="user-name">СЕРГЕЙ</div>
        <div style="margin-top:5px; margin-bottom:5px;">
            <span class="stat-badge">ВОЗРАСТ: {user_age}</span>
            <span class="stat-badge">ВЕС: {USER_WEIGHT_CURRENT}</span>
            <span class="stat-badge" style="border-color:{ACCENT_GOLD}; color:{ACCENT_GOLD}">XP: {total_xp}</span>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width: {rank['progress']}%;"></div></div>
        <div style="font-size:10px; color:#555; text-align:right;">СЛЕД. РАНГ: {rank['next_xp']} XP</div>
    </div>
</div>
""", unsafe_allow_html=True)

# РАСКРЫВАЮЩИЙСЯ СПИСОК ЗВАНИЙ
with st.expander(f"{rank['title']} // {rank['abbr']} (НАЖМИ)"):
    for r_min, r_max, title, abbr, r_type, grade in FULL_RANK_SYSTEM:
        is_active = (title == rank['title'])
        active_class = "rank-row-active" if is_active else ""
        text_color = ACCENT_GOLD if is_active else "#777"
        icon_html = get_rank_svg(r_type, grade)
        
        st.markdown(f"""
        <div class="rank-row-item {active_class}">
            <img src="{icon_html}" style="height:30px; width:30px; margin-right:15px;">
            <div style="flex-grow:1; color:{text_color};">
                <div style="font-size:14px;">{title}</div>
                <div style="font-size:10px; opacity:0.7;">XP: {r_min} - {r_max}</div>
            </div>
            {'<div style="color:'+ACCENT_GOLD+';">◀ ТЫ ТУТ</div>' if is_active else ''}
        </div>
        """, unsafe_allow_html=True)

# --- 8. МЕНЮ ---
selected = option_menu(
    menu_title=None,
    options=["ДАШБОРД", "ЖУРНАЛ", "ТРЕНЕР"],
    icons=["crosshair", "list-task", "robot"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent"},
        "nav-link": {"font-size": "14px", "color": "#777", "margin": "2px"},
        "nav-link-selected": {"background-color": CAMO_GREEN, "color": "#FFF", "border": "1px solid #6b7536"},
    }
)

# --- 9. ДАШБОРД ---
if selected == "ДАШБОРД":
    
    # Инициализация календаря
    if 'c_year' not in st.session_state: st.session_state.c_year = date.today().year
    if 'c_month' not in st.session_state: st.session_state.c_month = date.today().month
    if 'sel_date' not in st.session_state: st.session_state.sel_date = None

    # КАЛЕНДАРЬ
    st.markdown('<div class="tac-header">КАЛЕНДАРЬ МИССИЙ</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    
    def change_m(d):
        m = st.session_state.c_month + d
        y = st.session_state.c_year
        if m>12: m=1; y+=1
        elif m<1: m=12; y-=1
        st.session_state.c_month = m
        st.session_state.c_year = y

    # Встроенная навигация
    c_l, c_c, c_r = st.columns([1,4,1])
    with c_l: st.button("<", on_click=change_m, args=(-1,), key="prev")
    with c_c: 
        mn = calendar.month_name[st.session_state.c_month].upper()
        st.markdown(f"<div style='text-align:center; font-size:20px; color:{ACCENT_GOLD}; padding-top:5px;'>{mn} {st.session_state.c_year}</div>", unsafe_allow_html=True)
    with c_r: st.button(">", on_click=change_m, args=(1,), key="next")

    cal = calendar.monthcalendar(st.session_state.c_year, st.session_state.c_month)
    today = date.today()
    
    # Дни недели
    cols = st.columns(7)
    for i, d in enumerate(["ПН","ВТ","СР","ЧТ","ПТ","СБ","ВС"]):
        cols[i].markdown(f"<div style='text-align:center; font-size:12px; color:#555;'>{d}</div>", unsafe_allow_html=True)

    # Дни
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                curr = date(st.session_state.c_year, st.session_state.c_month, day)
                is_tr = curr in trained_dates
                is_tod = (curr == today)
                
                label = f"{day}"
                if cols[i].button(label, key=f"d_{curr}"):
                    if is_tr: st.session_state.sel_date = curr
                    else: st.session_state.sel_date = None

                # CSS Hack for colors
                bg = "#1a1a1a"
                clr = "#555"
                brd = "1px solid #333"
                if is_tr: 
                    bg = CAMO_GREEN; clr = "#FFF"; brd = f"1px solid {ACCENT_GOLD}"
                elif curr < today: 
                    bg = "#2a1515"; clr = "#a55" # Dark Red bg
                if is_tod: 
                    brd = f"2px solid {ACCENT_GOLD}"; clr = ACCENT_GOLD
                
                st.markdown(f"""<script>
                    var btns = window.parent.document.querySelectorAll('button');
                    for (var i=0; i<btns.length; i++) {{
                        if (btns[i].innerText == "{label}" && !btns[i].disabled) {{
                            btns[i].style.backgroundColor = "{bg}";
                            btns[i].style.color = "{clr}";
                            btns[i].style.border = "{brd}";
                        }}
                    }}
                </script>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ФИЛЬТР И РАДАР
    filtered_df = df.copy()
    filter_msg = "ОБЩАЯ СТАТИСТИКА"
    
    if st.session_state.sel_date:
        filtered_df = df[df['День/Дата'].dt.date == st.session_state.sel_date]
        filter_msg = f"ОТЧЕТ ЗА {st.session_state.sel_date.strftime('%d.%m.%Y')}"
        if st.button("СБРОСИТЬ ФИЛЬТР"):
            st.session_state.sel_date = None
            st.rerun()
            
    st.markdown(f"<div style='text-align:center; color:{ACCENT_GOLD}; margin-bottom:10px;'>{filter_msg}</div>", unsafe_allow_html=True)

    st.markdown('<div class="tac-header">СТАТУС БРОНИ</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    if not filtered_df.empty:
        muscle_data = filtered_df.groupby('Muscle')['Сет'].count().reset_index()
        muscle_data.columns = ['Muscle', 'Sets']
        target_muscles = ["ГРУДЬ", "СПИНА", "НОГИ", "РУКИ", "ПЛЕЧИ", "ПРЕСС"]
        radar_df = pd.DataFrame({"Muscle": target_muscles})
        radar_df = radar_df.merge(muscle_data, on="Muscle", how="left").fillna(0)
        
        # Исправленный цвет (RGBA)
        fig = go.Figure(data=go.Scatterpolar(
            r=radar_df['Sets'], theta=radar_df['Muscle'], fill='toself',
            line=dict(color=ACCENT_GOLD, width=3),
            fillcolor='rgba(255, 215, 0, 0.2)',
            marker=dict(color=ACCENT_GOLD, size=8)
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=False, linecolor='#333'),
                angularaxis=dict(linecolor='#333', tickfont=dict(color=CAMO_TEXT, size=12, family="Black Ops One")),
                bgcolor='rgba(0,0,0,0)'
            ),
            showlegend=False, height=280, margin=dict(l=40, r=40, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF')
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
    else: st.info("НЕТ ДАННЫХ")
    st.markdown('</div>', unsafe_allow_html=True)

    # ТАБЛИЦА
    st.markdown('<div class="tac-header">ЖУРНАЛ ЗАПИСЕЙ</div>', unsafe_allow_html=True)
    if not filtered_df.empty:
        hdf = filtered_df.copy().sort_values(by=['День/Дата', 'Сет'], ascending=[False, True])
        hdf['День/Дата'] = hdf['День/Дата'].dt.strftime('%d.%m')
        st.dataframe(hdf[['День/Дата', 'Сет', 'Упражнение', 'Вес (кг)', 'Повт']], use_container_width=True, hide_index=True)

# --- ЖУРНАЛ ---
elif selected == "ЖУРНАЛ":
    st.markdown('<div class="tac-header">НОВАЯ ЗАПИСЬ</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    with st.form("entry_form"):
        d = st.date_input("ДАТА")
        c1, c2 = st.columns([1,2])
        with c1: s_grp = st.text_input("СЕТ", "№1")
        with c2: ex_name = st.text_input("УПРАЖНЕНИЕ")
        c3, c4, c5 = st.columns(3)
        with c3: s_num = st.number_input("ПОДХОД", 1, 10, 1)
        with c4: w_val = st.number_input("ВЕС", step=2.5)
        with c5: r_val = st.number_input("ПОВТ", 1, 100, 10)
        c6, c7 = st.columns(2)
        with c6: tech = st.text_input("ТЕХНИКА")
        with c7: comm = st.text_input("КОММЕНТ")
        
        if st.form_submit_button("СОХРАНИТЬ"):
            try:
                sheet.append_row([d.strftime("%Y-%m-%d"), s_grp, ex_name, s_num, w_val, r_val, w_val*r_val, tech, comm])
                st.success("УСПЕШНО")
                st.rerun()
            except: st.error("ОШИБКА")
    st.markdown('</div>', unsafe_allow_html=True)

# --- ТРЕНЕР ---
elif selected == "ТРЕНЕР":
    st.markdown(f'<div class="tac-header">ИНСТРУКТОР // {rank["abbr"]}</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    if p := st.chat_input("ЗАДАТЬ ВОПРОС..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        res = model.generate_content(f"Ты суровый армейский тренер. Звание: {rank['title']}. Отвечай коротко и ясно. Вопрос: {p}")
        with st.chat_message("assistant"): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
    st.markdown('</div>', unsafe_allow_html=True)
