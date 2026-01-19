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

# --- 2. ЦВЕТОВАЯ ПАЛИТРА (CAMO) ---
CAMO_DARK = "#1a1c15"       # Основной фон (почти черный)
CAMO_GREEN = "#4b5320"      # Армейский зеленый
CAMO_LIGHT = "#8f9779"      # Светлый хаки (текст)
ACCENT_GOLD = "#FFD700"     # Золото для званий
ALERT_RED = "#8B0000"       # Красный для пропусков
CARD_BG = "#242621"         # Фон карточек

AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. ГЕНЕРАТОР ШЕВРОНОВ (SVG) ---
# Рисуем шевроны кодом, чтобы они никогда не пропадали
def get_rank_svg(rank_code):
    color = ACCENT_GOLD
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60" viewBox="0 0 100 100" fill="none" stroke="{color}" stroke-width="4">'
    
    if rank_code == "PV1": # Звезда (Рекрут)
        svg += '<polygon points="50,10 61,35 90,35 67,55 77,85 50,70 23,85 33,55 10,35 39,35" fill="none"/>'
        
    elif rank_code == "PV2": # 1 Галочка
        svg += '<path d="M10,40 L50,15 L90,40" />'
        
    elif rank_code == "PFC": # 1 Галочка + Дуга
        svg += '<path d="M10,35 L50,10 L90,35" /> <path d="M10,50 Q50,70 90,50" />'
        
    elif rank_code == "SPC": # Щит (Специалист)
        svg += '<path d="M10,20 L90,20 L90,60 L50,90 L10,60 Z" /> <path d="M50,15 L80,30 L80,50 L50,80 L20,50 L20,30 Z" fill="{color}" stroke="none"/>'.format(color=color)
        
    elif rank_code == "SGT": # 3 Галочки
        svg += '<path d="M10,40 L50,15 L90,40" /> <path d="M10,55 L50,30 L90,55" /> <path d="M10,70 L50,45 L90,70" />'
        
    elif rank_code == "SSG": # 3 Галочки + 1 Дуга
        svg += '<path d="M10,35 L50,10 L90,35" /> <path d="M10,50 L50,25 L90,50" /> <path d="M10,65 L50,40 L90,65" /> <path d="M15,80 Q50,95 85,80" />'
        
    elif rank_code == "SFC": # 3 Галочки + 2 Дуги
        svg += '<path d="M10,35 L50,10 L90,35" /> <path d="M10,50 L50,25 L90,50" /> <path d="M10,65 L50,40 L90,65" /> <path d="M15,80 Q50,95 85,80" /> <path d="M15,90 Q50,105 85,90" />'
        
    elif rank_code in ["CMD", "OFFICER"]: # Полоса (Офицер)
        svg += '<rect x="35" y="20" width="30" height="60" rx="2" fill="{color}" stroke="none"/>'.format(color=color)
        
    else: # Дефолт
        svg += '<circle cx="50" cy="50" r="30" />'
        
    svg += '</svg>'
    b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"

RANK_SYSTEM = [
    (0, 9, "РЕКРУТ", "PV1"),
    (10, 24, "РЯДОВОЙ", "PV2"),
    (25, 49, "РЯДОВОЙ 1 КЛ", "PFC"),
    (50, 74, "СПЕЦИАЛИСТ", "SPC"),
    (75, 99, "СЕРЖАНТ", "SGT"),
    (100, 129, "ШТАБ-СЕРЖАНТ", "SSG"),
    (130, 159, "СЕРЖ 1 КЛАССА", "SFC"),
    (160, 9999, "ОФИЦЕР", "CMD")
]

# --- 4. ФУНКЦИИ ---
def get_rank_data(xp):
    for r_min, r_max, title, abbr in RANK_SYSTEM:
        if r_min <= xp <= r_max:
            needed = r_max - r_min + 1
            current = xp - r_min
            percent = int((current / needed) * 100)
            to_go = r_max - xp + 1
            return {"title": title, "abbr": abbr, "icon": get_rank_svg(abbr), "progress": percent, "next_xp": to_go}
    # God mode
    return {"title": "ЛЕГЕНДА", "abbr": "GOD", "icon": get_rank_svg("CMD"), "progress": 100, "next_xp": 0}

def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def detect_muscle_group(exercise_name):
    ex = str(exercise_name).lower()
    if any(x in ex for x in ['жим лежа', 'жим гантелей', 'бабочка', 'chest', 'отжимания', 'брусья', 'груд', 'жим в тренажере']): return "ГРУДЬ"
    if any(x in ex for x in ['тяга', 'подтягивания', 'спина', 'back', 'row', 'становая']): return "СПИНА"
    if any(x in ex for x in ['присед', 'ноги', 'выпады', 'legs', 'squat', 'разгибания', 'сгибания']): return "НОГИ"
    if any(x in ex for x in ['бицепс', 'трицепс', 'молот', 'arms', 'bicep', 'концентрированный', 'французский']): return "РУКИ"
    if any(x in ex for x in ['жим стоя', 'плечи', 'махи', 'shouder', 'press', 'разведение']): return "ПЛЕЧИ"
    if any(x in ex for x in ['пресс', 'планка', 'abs', 'core', 'скручивания']): return "ПРЕСС"
    return "ОБЩЕЕ"

# --- 5. TACTICAL CAMO CSS (STYLES) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&display=swap');

    /* BASE BACKGROUND */
    .stApp {{
        background-color: {CAMO_DARK};
        font-family: 'Roboto Mono', monospace;
        color: #E0E0E0;
    }}
    
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* CAMO CARD CONTAINER */
    .camo-card {{
        background-color: {CARD_BG};
        border-left: 4px solid {CAMO_GREEN};
        border-top: 1px solid #333;
        border-right: 1px solid #333;
        border-bottom: 1px solid #333;
        padding: 15px;
        margin-bottom: 15px;
        border-radius: 4px; /* Угловатые края */
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        position: relative;
    }}
    
    /* ДЕКОРАТИВНЫЕ БОЛТЫ */
    .camo-card::after {{
        content: '+';
        position: absolute;
        top: 5px; right: 5px;
        color: {CAMO_GREEN};
        font-weight: bold;
    }}

    /* PROFILE */
    .avatar-area {{
        width: 80px; height: 80px; 
        border: 2px solid {ACCENT_GOLD}; 
        border-radius: 10px; /* Квадрат с легким скруглением */
        overflow: hidden; float: left; margin-right: 15px;
    }}
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    
    .user-name {{
        font-family: 'Black Ops One', cursive; 
        font-size: 28px; 
        color: #FFF; 
        margin: 0; line-height: 1;
        letter-spacing: 2px;
    }}
    
    /* CUSTOM EXPANDER FOR RANKS */
    .streamlit-expanderHeader {{
        font-family: 'Black Ops One', cursive;
        color: {ACCENT_GOLD} !important;
        background-color: rgba(255, 215, 0, 0.05) !important;
        border: 1px solid {ACCENT_GOLD} !important;
        border-radius: 4px !important;
    }}
    
    .rank-icon-img {{ height: 35px; width: auto; vertical-align: middle; }}
    
    /* PROGRESS BAR */
    .progress-track {{
        width: 100%; height: 10px; background: #111; border: 1px solid #444; margin-top: 8px;
    }}
    .progress-fill {{ height: 100%; background: repeating-linear-gradient(45deg, {CAMO_GREEN}, {CAMO_GREEN} 10px, #3a4019 10px, #3a4019 20px); }}
    
    /* BADGES */
    .stat-badge {{
        background: #111; color: {CAMO_LIGHT}; padding: 4px 8px; 
        border: 1px solid {CAMO_GREEN}; font-size: 11px; margin-right: 5px;
    }}

    /* BUTTONS */
    div.stButton > button {{
        background: {CAMO_GREEN}; color: #FFF; 
        border: 1px solid #6b7536; border-radius: 0px; 
        font-family: 'Black Ops One', cursive;
        letter-spacing: 1px;
    }}
    div.stButton > button:hover {{ border-color: {ACCENT_GOLD}; color: {ACCENT_GOLD}; }}
    
    /* CALENDAR BUTTONS */
    .cal-btn {{
        width: 100%; height: 40px; border: 1px solid #333; 
        background: #1a1a1a; color: #777; font-weight: bold; cursor: pointer;
    }}
    .cal-btn.trained {{ background: {CAMO_GREEN}; color: #FFF; border: 1px solid {ACCENT_GOLD}; }}
    .cal-btn.missed {{ background: {ALERT_RED}; color: #FFF; opacity: 0.6; }}
    .cal-btn.today {{ border: 2px solid {ACCENT_GOLD}; color: {ACCENT_GOLD}; }}
    
    /* HEADERS */
    .tac-header {{
        font-family: 'Black Ops One', cursive; font-size: 18px; color: {CAMO_LIGHT};
        border-bottom: 2px solid {CAMO_GREEN}; padding-bottom: 5px; margin: 20px 0 10px 0;
    }}
    
    /* INPUTS */
    input, textarea, select {{ background: #111 !important; color: white !important; border: 1px solid #444 !important; }}
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

# --- 7. ПРОФИЛЬ (CAMO STYLE) ---
# Верхняя часть с аватаром
st.markdown(f"""
<div class="camo-card" style="display:flex; align-items:center;">
    <div class="avatar-area"><img src="{AVATAR_URL}" class="avatar-img"></div>
    <div style="flex-grow:1;">
        <div class="user-name">SERGEY</div>
        <div style="margin-bottom:5px;">
            <span class="stat-badge">AGE: {user_age}</span>
            <span class="stat-badge">WGHT: {USER_WEIGHT_CURRENT}KG</span>
            <span class="stat-badge" style="border-color:{ACCENT_GOLD}; color:{ACCENT_GOLD}">XP: {total_xp}</span>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width: {rank['progress']}%;"></div></div>
    </div>
</div>
""", unsafe_allow_html=True)

# РАСКРЫВАЮЩИЙСЯ СПИСОК ЗВАНИЙ (ВМЕСТО КНОПКИ)
with st.expander(f"{rank['title']} // {rank['abbr']} (НАЖМИ ДЛЯ СПИСКА)"):
    st.markdown(f"<div style='text-align:center; margin-bottom:10px;'><img src='{rank['icon']}' width='80'></div>", unsafe_allow_html=True)
    st.markdown("---")
    for r_min, r_max, title, abbr in RANK_SYSTEM:
        # Рисуем мини-шеврон для каждого
        icon_html = get_rank_svg(abbr).replace('width="60"', 'width="30"').replace('height="60"', 'height="30"')
        active_style = f"color:{ACCENT_GOLD}; font-weight:bold;" if title == rank['title'] else "color:#777;"
        st.markdown(f"""
        <div style="display:flex; align-items:center; margin-bottom:5px;">
            <img src="{icon_html}" style="margin-right:10px;">
            <div style="{active_style} font-family:'Roboto Mono'; font-size:12px;">{abbr} - {title} <span style="font-size:10px; opacity:0.5">({r_min}-{r_max})</span></div>
        </div>
        """, unsafe_allow_html=True)

# --- 8. МЕНЮ ---
# Настраиваем цвета option_menu под камуфляж
selected = option_menu(
    menu_title=None,
    options=["ДАШБОРД", "ЖУРНАЛ", "ТРЕНЕР"],
    icons=["crosshair", "clipboard-data", "robot"], # Иконки поменял на более тактические
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent"},
        "nav-link": {"font-size": "12px", "color": "#AAA", "margin": "2px", "font-family": "Black Ops One"},
        "nav-link-selected": {"background-color": CAMO_GREEN, "color": "#FFF", "border": "1px solid #6b7536"},
    }
)

# --- 9. ДАШБОРД ---
if selected == "ДАШБОРД":
    
    # КАЛЕНДАРЬ
    st.markdown('<div class="tac-header">ТАКТИЧЕСКИЙ КАЛЕНДАРЬ</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    
    if 'c_year' not in st.session_state: st.session_state.c_year = date.today().year
    if 'c_month' not in st.session_state: st.session_state.c_month = date.today().month
    if 'sel_date' not in st.session_state: st.session_state.sel_date = None

    def change_m(d):
        m = st.session_state.c_month + d
        y = st.session_state.c_year
        if m>12: m=1; y+=1
        elif m<1: m=12; y-=1
        st.session_state.c_month = m
        st.session_state.c_year = y

    # Навигация календаря встроена
    col_l, col_c, col_r = st.columns([1,4,1])
    with col_l: st.button("<", on_click=change_m, args=(-1,), key="p_m")
    with col_c: 
        m_name = calendar.month_name[st.session_state.c_month].upper()
        st.markdown(f"<div style='text-align:center; font-family:\"Black Ops One\"; font-size:20px; color:{ACCENT_GOLD}; padding-top:5px;'>{m_name} {st.session_state.c_year}</div>", unsafe_allow_html=True)
    with col_r: st.button(">", on_click=change_m, args=(1,), key="n_m")

    # Сетка
    cal = calendar.monthcalendar(st.session_state.c_year, st.session_state.c_month)
    today = date.today()
    
    # Дни недели
    cols = st.columns(7)
    for i, d in enumerate(["ПН","ВТ","СР","ЧТ","ПТ","СБ","ВС"]):
        cols[i].markdown(f"<div style='text-align:center; font-size:10px; color:#555;'>{d}</div>", unsafe_allow_html=True)

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                curr = date(st.session_state.c_year, st.session_state.c_month, day)
                # Определяем стиль кнопки через KEY
                is_trained = curr in trained_dates
                is_today = (curr == today)
                
                # Emoji для статуса (так как стилизовать кнопку сложно, используем эмодзи в тексте кнопки)
                label = f"{day}"
                
                # Кнопка
                if cols[i].button(label, key=f"d_{curr}"):
                    if is_trained:
                        st.session_state.sel_date = curr
                    else:
                        st.session_state.sel_date = None

                # CSS Hack для раскраски кнопок
                btn_color = "#222" # Default
                txt_color = "#777"
                border = "1px solid #333"
                
                if is_trained: 
                    btn_color = CAMO_GREEN
                    txt_color = "#FFF"
                    border = f"1px solid {ACCENT_GOLD}"
                elif curr < today:
                    btn_color = "#3a1a1a" # Dark Red bg
                    txt_color = "#a55"
                
                if is_today:
                    border = f"2px solid {ACCENT_GOLD}"
                    txt_color = ACCENT_GOLD
                
                # Применяем стиль к конкретной кнопке через JS (самый надежный способ в Streamlit для сетки)
                st.markdown(f"""
                <script>
                    var btns = window.parent.document.querySelectorAll('button');
                    for (var i=0; i<btns.length; i++) {{
                        if (btns[i].innerText == "{label}" && !btns[i].disabled) {{
                            btns[i].style.backgroundColor = "{btn_color}";
                            btns[i].style.color = "{txt_color}";
                            btns[i].style.border = "{border}";
                            btns[i].style.borderRadius = "4px";
                        }}
                    }}
                </script>
                """, unsafe_allow_html=True)
                
    st.markdown('</div>', unsafe_allow_html=True)

    # ФИЛЬТР
    filtered_df = df.copy()
    if st.session_state.sel_date:
        filtered_df = df[df['День/Дата'].dt.date == st.session_state.sel_date]
        st.markdown(f"<div style='text-align:center; color:{ACCENT_GOLD}; border:1px solid {ACCENT_GOLD}; padding:5px; margin-bottom:10px;'>ОТЧЕТ ЗА: {st.session_state.sel_date.strftime('%d.%m.%Y')}</div>", unsafe_allow_html=True)
        if st.button("СБРОСИТЬ ФИЛЬТР"):
            st.session_state.sel_date = None
            st.rerun()

    # РАДАР
    st.markdown('<div class="tac-header">СТАТУС БРОНИ (SETS)</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    if not filtered_df.empty:
        muscle_data = filtered_df.groupby('Muscle')['Сет'].count().reset_index()
        muscle_data.columns = ['Muscle', 'Sets']
        target_muscles = ["ГРУДЬ", "СПИНА", "НОГИ", "РУКИ", "ПЛЕЧИ", "ПРЕСС"]
        radar_df = pd.DataFrame({"Muscle": target_muscles})
        radar_df = radar_df.merge(muscle_data, on="Muscle", how="left").fillna(0)
        
        fig = go.Figure(data=go.Scatterpolar(
            r=radar_df['Sets'], theta=radar_df['Muscle'], fill='toself',
            line=dict(color=ACCENT_GOLD, width=2),
            fillcolor='rgba(255, 215, 0, 0.2)',
            marker=dict(color=ACCENT_GOLD, size=6)
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=False, linecolor='#333'),
                angularaxis=dict(linecolor='#333', tickfont=dict(color=CAMO_LIGHT, size=10, family="Roboto Mono")),
                bgcolor='rgba(0,0,0,0)'
            ),
            showlegend=False, height=280, margin=dict(l=30, r=30, t=10, b=10),
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
    st.markdown('<div class="tac-header">НОВАЯ МИССИЯ</div>', unsafe_allow_html=True)
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
        
        if st.form_submit_button("ЗАПИСАТЬ"):
            try:
                sheet.append_row([d.strftime("%Y-%m-%d"), s_grp, ex_name, s_num, w_val, r_val, w_val*r_val, tech, comm])
                st.success("ЗАПИСАНО")
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
    if p := st.chat_input("ВОПРОС..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        res = model.generate_content(f"Ты армейский инструктор. Отвечай кратко, сурово, на русском. Вопрос: {p}")
        with st.chat_message("assistant"): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
    st.markdown('</div>', unsafe_allow_html=True)
