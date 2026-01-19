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
CAMO_DARK = "#0e0e0e"       # Глубокий черный фон
CAMO_PANEL = "#1c1f1a"      # Темно-оливковая панель
CAMO_GREEN = "#4b5320"      # Nato Green
CAMO_TEXT = "#B0B0B0"       # Серый текст
ACCENT_GOLD = "#FFD700"     # Gold
ACCENT_SILVER = "#C0C0C0"   # Silver
ALERT_RED = "#8B0000"

AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. ГЕНЕРАТОР ШЕВРОНОВ (УМЕНЬШЕННЫЕ И ТОЧНЫЕ) ---
def get_rank_svg(rank_type, grade):
    color = ACCENT_GOLD # Default
    if rank_type == "OFFICER":
        if grade in [1, 2, 4, 5] or grade >= 6: color = ACCENT_SILVER
    
    # Уменьшил размер SVG до 30x30
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 100 100" fill="none" stroke="{color}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round">'
    
    if rank_type == "ENLISTED":
        chevrons = min(grade + 1, 3) if grade < 3 else 3
        rockers = 0
        if grade >= 3: rockers = 1 
        if grade >= 5: rockers = 2
        if grade >= 7: rockers = 3
        
        for i in range(chevrons):
            y = 35 + (i * 15)
            svg += f'<path d="M15,{y} L50,{y-25} L85,{y}" />'
        for i in range(rockers):
            y = 65 + (i * 12)
            svg += f'<path d="M15,{y-10} Q50,{y+15} 85,{y-10}" />'
            
    elif rank_type == "OFFICER":
        if grade == 0 or grade == 1: # Bars
            svg += f'<rect x="40" y="20" width="20" height="60" fill="{color}" stroke="none"/>'
        elif grade == 2: # 2 Bars
            svg += f'<rect x="25" y="20" width="15" height="60" fill="{color}" stroke="none"/>'
            svg += f'<rect x="60" y="20" width="15" height="60" fill="{color}" stroke="none"/>'
        elif grade == 3 or grade == 4: # Leaves
            svg += f'<path d="M50,15 Q80,15 80,45 Q80,75 50,90 Q20,75 20,45 Q20,15 50,15 Z" fill="{color}" stroke="none"/>'
        elif grade == 5: # Eagle (Simplified)
            svg += f'<path d="M10,40 L50,20 L90,40 L80,70 L50,90 L20,70 Z" fill="{color}" stroke="none"/>'
        elif grade >= 6: # Stars
            stars = grade - 5
            svg += f'<circle cx="50" cy="50" r="12" fill="{color}" stroke="none"/>' # Central star representation

    svg += '</svg>'
    b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"

# --- СПИСОК ЗВАНИЙ ---
FULL_RANK_SYSTEM = [
    (0, 24, "РЕКРУТ", "PV1", "ENLISTED", 0),
    (25, 49, "РЯДОВОЙ", "PV2", "ENLISTED", 1),
    (50, 99, "РЯДОВОЙ 1 КЛ", "PFC", "ENLISTED", 2),
    (100, 149, "СПЕЦИАЛИСТ", "SPC", "ENLISTED", 3),
    (150, 199, "КАПРАЛ", "CPL", "ENLISTED", 3),
    (200, 299, "СЕРЖАНТ", "SGT", "ENLISTED", 4),
    (300, 399, "ШТАБ-СЕРЖАНТ", "SSG", "ENLISTED", 5),
    (400, 499, "СЕРЖАНТ 1 КЛ", "SFC", "ENLISTED", 6),
    (500, 649, "МАСТЕР-СЕРЖАНТ", "MSG", "ENLISTED", 7),
    (650, 799, "1-Й СЕРЖАНТ", "1SG", "ENLISTED", 7),
    (800, 999, "СЕРЖАНТ-МАЙОР", "SGM", "ENLISTED", 8),
    (1000, 1499, "2-Й ЛЕЙТЕНАНТ", "2LT", "OFFICER", 0),
    (1500, 1999, "1-Й ЛЕЙТЕНАНТ", "1LT", "OFFICER", 1),
    (2000, 2999, "КАПИТАН", "CPT", "OFFICER", 2),
    (3000, 3999, "МАЙОР", "MAJ", "OFFICER", 3),
    (4000, 4999, "ПОДПОЛКОВНИК", "LTC", "OFFICER", 4),
    (5000, 5999, "ПОЛКОВНИК", "COL", "OFFICER", 5),
    (6000, 7999, "БРИГАДНЫЙ ГЕНЕРАЛ", "BG", "OFFICER", 6),   
    (8000, 9999, "ГЕНЕРАЛ-МАЙОР", "MG", "OFFICER", 7),       
    (10000, 14999, "ГЕНЕРАЛ-ЛЕЙТЕНАНТ", "LTG", "OFFICER", 8), 
    (15000, 24999, "ГЕНЕРАЛ", "GEN", "OFFICER", 9),          
    (25000, 999999, "ГЕНЕРАЛ АРМИИ", "GA", "OFFICER", 10)    
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

# --- 5. CSS (STABLE GRID & STYLE) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500&display=swap');

    /* BASE */
    .stApp {{ background-color: {CAMO_DARK}; color: #E0E0E0; font-family: 'Roboto Mono', sans-serif; }}
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* TYPOGRAPHY */
    h1, h2, h3, .tac-font {{ font-family: 'Oswald', sans-serif !important; letter-spacing: 1px; text-transform: uppercase; }}
    
    /* CARDS */
    .camo-card {{
        background-color: {CAMO_PANEL};
        border: 1px solid #333;
        border-left: 4px solid {CAMO_GREEN};
        padding: 15px; margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        border-radius: 4px;
    }}

    /* PROFILE */
    .avatar-area {{
        width: 80px; height: 80px; border: 2px solid {ACCENT_GOLD}; border-radius: 50%;
        overflow: hidden; float: left; margin-right: 15px;
    }}
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    .user-name {{ font-family: 'Oswald', sans-serif; font-size: 28px; color: #FFF; margin: 0; line-height: 1.1; }}
    
    /* PROGRESS */
    .progress-track {{ width: 100%; height: 10px; background: #111; border: 1px solid #444; margin-top: 8px; }}
    .progress-fill {{ height: 100%; background: {CAMO_GREEN}; }}
    
    /* BADGES */
    .stat-badge {{
        background: #111; color: {ACCENT_GOLD}; padding: 3px 8px; 
        border: 1px solid {CAMO_GREEN}; font-size: 12px; margin-right: 5px; font-family: 'Oswald', sans-serif;
    }}

    /* HEADERS */
    .tac-header {{
        font-family: 'Oswald', sans-serif; font-size: 18px; color: {CAMO_TEXT};
        border-bottom: 2px solid {CAMO_GREEN}; padding-bottom: 5px; margin: 20px 0 10px 0;
    }}

    /* CALENDAR GRID (FIXED) */
    /* Убираем отступы у колонок Streamlit, чтобы календарь был плотным */
    div[data-testid="column"] {{ padding: 0px 2px !important; }}
    
    /* CALENDAR BUTTONS */
    div.stButton > button {{
        width: 100%; height: 45px; border: 1px solid #333; 
        background: #1a1a1a; color: #777; border-radius: 4px; font-weight: bold;
        padding: 0px !important;
    }}
    div.stButton > button:hover {{ border-color: {ACCENT_GOLD}; color: {ACCENT_GOLD}; }}
    div.stButton > button:active {{ background: {CAMO_GREEN}; color: #FFF; }}

    /* INPUTS */
    input, textarea, select {{ background: #111 !important; color: {ACCENT_GOLD} !important; border: 1px solid #444 !important; }}
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
        if 'Сет' not in df.columns: df['Сет'] = "-"
        df['Сет'] = df['Сет'].astype(str).replace('', '-')
        df['День/Дата'] = pd.to_datetime(df['День/Дата'], errors='coerce')
        df = df.dropna(subset=['День/Дата'])
        df['Muscle'] = df['Упражнение'].apply(detect_muscle_group)
except:
    df = pd.DataFrame()

total_xp = len(df)
rank = get_rank_data(total_xp)
user_age = calculate_age(USER_BIRTHDAY)
trained_dates = set(df['День/Дата'].dt.date) if not df.empty else set()

# --- 7. UI: ПРОФИЛЬ ---
st.markdown(f"""
<div class="camo-card" style="display:flex; align-items:center;">
    <div class="avatar-area"><img src="{AVATAR_URL}" class="avatar-img"></div>
    <div style="flex-grow:1;">
        <div class="user-name">СЕРГЕЙ</div>
        <div style="margin: 5px 0;">
            <span class="stat-badge">ВОЗРАСТ: {user_age}</span>
            <span class="stat-badge">ВЕС: {USER_WEIGHT_CURRENT}</span>
            <span class="stat-badge">XP: {total_xp}</span>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width: {rank['progress']}%;"></div></div>
        <div style="font-size:10px; color:#666; text-align:right; margin-top:2px; font-family:'Roboto Mono';">
            СЛЕДУЮЩИЙ: {rank['xp_needed']} XP
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# СПИСОК ЗВАНИЙ
with st.expander(f"{rank['title']} // {rank['abbr']} (ОТКРЫТЬ СПИСОК)"):
    for r_min, r_max, title, abbr, r_type, grade in FULL_RANK_SYSTEM:
        is_active = (title == rank['title'])
        bg_style = "background-color:rgba(255,215,0,0.1); border-left:3px solid #FFD700;" if is_active else ""
        text_color = ACCENT_GOLD if is_active else "#777"
        icon_html = get_rank_svg(r_type, grade)
        st.markdown(f"""
        <div style="display:flex; align-items:center; padding:8px; border-bottom:1px solid #333; {bg_style}">
            <img src="{icon_html}" style="height:25px; width:25px; margin-right:15px;">
            <div style="flex-grow:1; color:{text_color}; font-family:'Oswald';">
                {title} <span style="font-size:10px; opacity:0.6;">{abbr}</span>
            </div>
            <div style="font-size:10px; color:#555; font-family:'Roboto Mono';">{r_min} XP</div>
        </div>
        """, unsafe_allow_html=True)

# --- 8. МЕНЮ (COMPACT) ---
# Фиксируем стиль, чтобы не разваливалось
selected = option_menu(
    menu_title=None,
    options=["ДАШБОРД", "ЖУРНАЛ", "ТРЕНЕР"],
    icons=["crosshair", "list-task", "robot"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent", "margin-bottom": "20px"},
        "nav-link": {"font-size": "13px", "color": "#888", "margin": "2px", "font-family": "Oswald", "padding": "10px"},
        "nav-link-selected": {"background-color": CAMO_GREEN, "color": "#FFF", "border": "1px solid #6b7536"},
    }
)

# --- 9. ДАШБОРД ---
if selected == "ДАШБОРД":
    
    # 1. РАДАР (ТЕПЕРЬ ПЕРВЫЙ)
    st.markdown('<div class="tac-header">СТАТУС БРОНИ</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    
    filtered_df = df.copy()
    if 'sel_date' in st.session_state and st.session_state.sel_date:
        filtered_df = df[df['День/Дата'].dt.date == st.session_state.sel_date]
        st.markdown(f"<div style='text-align:center; color:{ACCENT_GOLD}; font-family:Oswald; margin-bottom:10px;'>ДАННЫЕ ЗА: {st.session_state.sel_date.strftime('%d.%m.%Y')}</div>", unsafe_allow_html=True)
        if st.button("СБРОСИТЬ ФИЛЬТР"):
            st.session_state.sel_date = None
            st.rerun()

    if not filtered_df.empty:
        muscle_data = filtered_df.groupby('Muscle')['Сет'].count().reset_index()
        muscle_data.columns = ['Muscle', 'Sets']
        target_muscles = ["ГРУДЬ", "СПИНА", "НОГИ", "РУКИ", "ПЛЕЧИ", "ПРЕСС"]
        radar_df = pd.DataFrame({"Muscle": target_muscles})
        radar_df = radar_df.merge(muscle_data, on="Muscle", how="left").fillna(0)
        
        fig = go.Figure(data=go.Scatterpolar(
            r=radar_df['Sets'], theta=radar_df['Muscle'], fill='toself',
            line=dict(color=ACCENT_GOLD, width=3),
            fillcolor='rgba(255, 215, 0, 0.2)',
            marker=dict(color=ACCENT_GOLD, size=6)
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=False, linecolor='#333'),
                angularaxis=dict(linecolor='#333', tickfont=dict(color=CAMO_TEXT, size=11, family="Oswald")),
                bgcolor='rgba(0,0,0,0)'
            ),
            showlegend=False, height=280, margin=dict(l=40, r=40, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF')
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
    else: st.info("НЕТ ДАННЫХ")
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. КАЛЕНДАРЬ (ТЕПЕРЬ ВТОРОЙ, НАТИВНЫЕ КОЛОНКИ)
    st.markdown('<div class="tac-header">КАЛЕНДАРЬ МИССИЙ</div>', unsafe_allow_html=True)
    st.markdown('<div class="camo-card">', unsafe_allow_html=True)
    
    if 'c_year' not in st.session_state: st.session_state.c_year = date.today().year
    if 'c_month' not in st.session_state: st.session_state.c_month = date.today().month

    def change_m(d):
        m = st.session_state.c_month + d
        y = st.session_state.c_year
        if m>12: m=1; y+=1
        elif m<1: m=12; y-=1
        st.session_state.c_month = m
        st.session_state.c_year = y

    col_l, col_c, col_r = st.columns([1,4,1])
    with col_l: st.button("<", on_click=change_m, args=(-1,), key="p_m")
    with col_c: 
        mn = calendar.month_name[st.session_state.c_month].upper()
        st.markdown(f"<div style='text-align:center; font-family:Oswald; font-size:18px; color:{ACCENT_GOLD}; padding-top:5px;'>{mn} {st.session_state.c_year}</div>", unsafe_allow_html=True)
    with col_r: st.button(">", on_click=change_m, args=(1,), key="n_m")

    cal = calendar.monthcalendar(st.session_state.c_year, st.session_state.c_month)
    today = date.today()
    
    # Заголовки дней
    cols = st.columns(7)
    days = ["ПН","ВТ","СР","ЧТ","ПТ","СБ","ВС"]
    for i, d in enumerate(days):
        cols[i].markdown(f"<div style='text-align:center; font-size:10px; color:#555;'>{d}</div>", unsafe_allow_html=True)

    # Сетка дней (Используем st.columns внутри цикла - это чинит верстку)
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("") # Пустое место
            else:
                curr = date(st.session_state.c_year, st.session_state.c_month, day)
                is_tr = curr in trained_dates
                is_tod = (curr == today)
                
                label = f"{day}"
                # Уникальный ключ для каждой кнопки
                key_id = f"d_{curr}"
                
                if cols[i].button(label, key=key_id):
                    if is_tr: st.session_state.sel_date = curr
                    else: st.session_state.sel_date = None
                    st.rerun()

                # Stylization logic (Inject CSS just for this button)
                bg = "#1a1a1a"; clr = "#555"; brd = "1px solid #333"
                if is_tr: bg = CAMO_GREEN; clr = "#FFF"; brd = f"1px solid {ACCENT_GOLD}"
                elif curr < today: bg = "#251010"; clr = "#855"
                if is_tod: brd = f"2px solid {ACCENT_GOLD}"; clr = ACCENT_GOLD
                
                # JS Hack to apply style to the button generated above
                st.markdown(f"""
                <script>
                    var buttons = window.parent.document.querySelectorAll('div[data-testid="stVerticalBlock"] button');
                    // Find the last added button (simplistic approach, usually works in linear render)
                    // Better approach: use data-testid matching or specific inner text
                    for (var i=0; i<buttons.length; i++) {{
                        if (buttons[i].innerText == "{label}") {{
                            // Apply only if it doesn't have custom style yet (to avoid overwrite loops)
                             buttons[i].style.backgroundColor = "{bg}";
                             buttons[i].style.color = "{clr}";
                             buttons[i].style.border = "{brd}";
                        }}
                    }}
                </script>
                """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 3. ТАБЛИЦА
    st.markdown('<div class="tac-header">ЖУРНАЛ</div>', unsafe_allow_html=True)
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
    if p := st.chat_input("ВОПРОС..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        res = model.generate_content(f"Ты суровый армейский тренер. Звание: {rank['title']}. Отвечай кратко и ясно. Вопрос: {p}")
        with st.chat_message("assistant"): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
    st.markdown('</div>', unsafe_allow_html=True)
