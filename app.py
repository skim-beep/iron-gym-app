import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import calendar
from streamlit_option_menu import option_menu

# --- 1. НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="IRON GYM OS",
    page_icon="🦅",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- 2. НАСТРОЙКИ ---
AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. СИСТЕМА ЗВАНИЙ ---
RANK_SYSTEM = [
    (0, 9, "PRIVATE RECRUIT", "PV1", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Emblem_of_the_United_States_Department_of_the_Army.svg/100px-Emblem_of_the_United_States_Department_of_the_Army.svg.png"), 
    (10, 24, "PRIVATE (PV2)", "PV2", "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/US_Army_E2.svg/100px-US_Army_E2.svg.png"),
    (25, 49, "PFC", "PFC", "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/US_Army_E3.svg/100px-US_Army_E3.svg.png"),
    (50, 74, "SPECIALIST", "SPC", "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/US_Army_E4_SPC.svg/100px-US_Army_E4_SPC.svg.png"),
    (75, 99, "SERGEANT", "SGT", "https://upload.wikimedia.org/wikipedia/commons/thumb/6/62/US_Army_E5.svg/100px-US_Army_E5.svg.png"),
    (100, 129, "STAFF SERGEANT", "SSG", "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/US_Army_E6.svg/100px-US_Army_E6.svg.png"),
    (130, 159, "SGT 1ST CLASS", "SFC", "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/US_Army_E7.svg/100px-US_Army_E7.svg.png"),
    (160, 189, "MASTER SERGEANT", "MSG", "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/US_Army_E8_MSG.svg/100px-US_Army_E8_MSG.svg.png"),
    (190, 219, "FIRST SERGEANT", "1SG", "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/US_Army_E8_1SG.svg/100px-US_Army_E8_1SG.svg.png"),
    (220, 249, "SGT MAJOR", "SGM", "https://upload.wikimedia.org/wikipedia/commons/thumb/fa/US_Army_E9_SGM.svg/100px-US_Army_E9_SGM.svg.png"),
    (250, 299, "COMMAND SGT MAJOR", "CSM", "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/US_Army_E9_CSM.svg/100px-US_Army_E9_CSM.svg.png"),
    (300, 329, "2ND LIEUTENANT", "2LT", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/US-Army-O1-Shoulder.svg/100px-US-Army-O1-Shoulder.svg.png"),
    (330, 359, "1ST LIEUTENANT", "1LT", "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/US-Army-O2-Shoulder.svg/100px-US-Army-O2-Shoulder.svg.png"),
    (360, 389, "CAPTAIN", "CPT", "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/US-Army-O3-Collar.svg/100px-US-Army-O3-Collar.svg.png"),
    (390, 419, "MAJOR", "MAJ", "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/US-Army-O4-Shoulder.svg/100px-US-Army-O4-Shoulder.svg.png"),
    (420, 449, "LT COLONEL", "LTC", "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/US-Army-O5-Shoulder.svg/100px-US-Army-O5-Shoulder.svg.png"),
    (450, 479, "COLONEL", "COL", "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/US-Army-O6-Shoulder.svg/100px-US-Army-O6-Shoulder.svg.png"),
    (480, 509, "BRIGADIER GENERAL", "BG", "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9c/US-Army-O7-Shoulder.svg/100px-US-Army-O7-Shoulder.svg.png"),
    (510, 539, "MAJOR GENERAL", "MG", "https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/US-Army-O8-Shoulder.svg/100px-US-Army-O8-Shoulder.svg.png"),
    (540, 569, "LT GENERAL", "LTG", "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/US-Army-O9-Shoulder.svg/100px-US-Army-O9-Shoulder.svg.png"),
    (570, 599, "GENERAL", "GEN", "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/US-Army-O10-Shoulder.svg/100px-US-Army-O10-Shoulder.svg.png"),
    (600, 9999, "GENERAL OF ARMY", "GA", "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/US-Army-General_of_the_Army-Shoulder.svg/100px-US-Army-General_of_the_Army-Shoulder.svg.png")
]

# --- 4. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_rank_data(xp):
    for r_min, r_max, title, abbr, icon in RANK_SYSTEM:
        if r_min <= xp <= r_max:
            needed = r_max - r_min + 1
            current = xp - r_min
            percent = int((current / needed) * 100)
            to_go = r_max - xp + 1
            return {"title": title, "abbr": abbr, "icon": icon, "progress": percent, "next_xp": to_go}
    return {"title": "LEGEND", "abbr": "GOD", "icon": RANK_SYSTEM[-1][4], "progress": 100, "next_xp": 0}

def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def detect_muscle_group(exercise_name):
    ex = str(exercise_name).lower()
    if any(x in ex for x in ['жим лежа', 'жим гантелей', 'бабочка', 'chest', 'отжимания', 'брусья', 'груд']): return "ГРУДЬ"
    if any(x in ex for x in ['тяга', 'подтягивания', 'спина', 'back', 'row']): return "СПИНА"
    if any(x in ex for x in ['присед', 'ноги', 'выпады', 'legs', 'squat', 'бег', 'эллипс']): return "НОГИ"
    if any(x in ex for x in ['бицепс', 'трицепс', 'молот', 'arms', 'bicep']): return "РУКИ"
    if any(x in ex for x in ['жим стоя', 'плечи', 'махи', 'shouder', 'press', 'разведение']): return "ПЛЕЧИ"
    if any(x in ex for x in ['пресс', 'планка', 'abs', 'core', 'скручивания']): return "КОР"
    return "ОБЩЕЕ"

# --- 5. CSS СТИЛИ (ИСПРАВЛЕНЫ СКОБКИ) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&display=swap');

    .stApp {{ background-color: #F2F3F7; font-family: 'Inter', sans-serif; }}
    #MainMenu, footer, header {{ visibility: hidden; }}

    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {{
        background-color: #FFFFFF;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0px 4px 20px rgba(0,0,0,0.05);
    }}

    .profile-card {{
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 24px;
        box-shadow: 0 4px 25px rgba(0,0,0,0.05);
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
        border: 2px solid #D4AF37;
        flex-shrink: 0;
        margin-right: 20px;
    }}
    
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    .info-area {{ flex-grow: 1; width: 100%; }}
    
    .user-name {{
        font-size: 26px;
        font-weight: 900;
        color: #1C1C1E;
        line-height: 1;
        margin-bottom: 5px;
    }}
    
    .rank-row {{
        display: flex;
        align-items: center;
        margin-bottom: 10px;
    }}
    
    .rank-title {{
        font-family: 'Black Ops One', cursive;
        font-size: 14px;
        color: #D4AF37;
        text-transform: uppercase;
        margin-right: 10px;
    }}
    
    .rank-icon-img {{ height: 30px; width: auto; }}
    
    .progress-track {{
        width: 100%;
        height: 8px;
        background-color: #E5E5EA;
        border-radius: 4px;
        margin-bottom: 5px;
        overflow: hidden;
    }}
    
    .progress-fill {{
        height: 100%;
        border-radius: 4px;
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%);
        box-shadow: 0 0 10px rgba(0, 198, 255, 0.7);
    }}
    
    .xp-text {{
        font-size: 10px;
        color: #0072FF;
        font-weight: 700;
        text-transform: uppercase;
        float: right;
    }}
    
    .stats-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 15px; }}
    
    .stat-badge {{
        background-color: #F2F2F7;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        color: #3A3A3C;
        display: flex; align-items: center; gap: 5px;
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
    
    /* CALENDAR STYLES - ТЕПЕРЬ С ДВОЙНЫМИ СКОБКАМИ */
    .calendar-table {{ width: 100%; border-collapse: separate; border-spacing: 4px; }}
    .calendar-cell {{ 
        text-align: center; 
        padding: 10px; 
        border-radius: 8px; 
        font-size: 14px; 
        font-weight: 600; 
        color: #1C1C1E;
    }}
    .day-header {{ color: #8E8E93; font-size: 12px; text-transform: uppercase; }}
    .day-trained {{ background-color: #8E8E93; color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }}
    .day-missed {{ background-color: #FFB3B3; color: #8b0000; }}
    .day-today {{ border: 2px solid #D4AF37; color: #D4AF37; font-weight: 900; }}
    .day-empty {{ background-color: transparent; }}
    .day-future {{ color: #D1D1D6; }}
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
        df['Вес (кг)'] = pd.to_numeric(df['Вес (кг)'], errors='coerce').fillna(0)
        df['Повт'] = pd.to_numeric(df['Повт'], errors='coerce').fillna(0)
        df['Тоннаж'] = pd.to_numeric(df['Тоннаж'], errors='coerce').fillna(0)
        df['День/Дата'] = pd.to_datetime(df['День/Дата'], errors='coerce')
        df = df.dropna(subset=['День/Дата'])
        df['Muscle'] = df['Упражнение'].apply(detect_muscle_group)
        
except Exception as e:
    df = pd.DataFrame()

user_age = calculate_age(USER_BIRTHDAY)
trained_dates = set()
if not df.empty:
    trained_dates = set(df['День/Дата'].dt.date)

total_xp = len(df)
rank = get_rank_data(total_xp)

# --- 7. ПРОФИЛЬ ---
profile_html = f"""
<div class="profile-card">
<div class="avatar-area"><img src="{AVATAR_URL}" class="avatar-img"></div>
<div class="info-area">
<div class="user-name">SERGEY</div>
<div class="rank-row">
<span class="rank-title">{rank['title']} // {rank['abbr']}</span>
<img src="{rank['icon']}" class="rank-icon-img">
</div>
<div class="progress-track">
<div class="progress-fill" style="width: {rank['progress']}%;"></div>
</div>
<span class="xp-text">NEXT RANK IN: {rank['next_xp']} MISSIONS</span>
<div class="stats-row">
<div class="stat-badge">🧬 {user_age} YRS</div>
<div class="stat-badge">🛡️ {USER_WEIGHT_CURRENT} KG</div>
</div>
</div>
</div>
"""
st.markdown(profile_html, unsafe_allow_html=True)

# --- 8. МЕНЮ ---
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

# --- 9. DASHBOARD ---
if selected == "DASHBOARD":
    
    # RADAR CHART
    st.subheader("BODY ARMOR STATUS")
    if not df.empty:
        muscle_data = df.groupby('Muscle')['Тоннаж'].sum().reset_index()
        all_muscles = ["ГРУДЬ", "СПИНА", "НОГИ", "РУКИ", "ПЛЕЧИ", "КОР"]
        radar_df = pd.DataFrame({"Muscle": all_muscles})
        radar_df = radar_df.merge(muscle_data, on="Muscle", how="left").fillna(0)
        
        fig = go.Figure(data=go.Scatterpolar(
            r=radar_df['Тоннаж'],
            theta=radar_df['Muscle'],
            fill='toself',
            name='Total Volume',
            line_color='#D4AF37',
            fillcolor='rgba(212, 175, 55, 0.3)'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=False),
                bgcolor='#F2F3F7'
            ),
            showlegend=False,
            height=300,
            margin=dict(l=40, r=40, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
    else:
        st.info("No data for radar.")

    # TACTICAL CALENDAR
    st.subheader("MISSION CALENDAR")
    
    if 'cal_year' not in st.session_state: st.session_state.cal_year = date.today().year
    if 'cal_month' not in st.session_state: st.session_state.cal_month = date.today().month

    def change_month(delta):
        m = st.session_state.cal_month + delta
        y = st.session_state.cal_year
        if m > 12:
            m = 1
            y += 1
        elif m < 1:
            m = 12
            y -= 1
        st.session_state.cal_month = m
        st.session_state.cal_year = y

    col_prev, col_month, col_next = st.columns([1, 2, 1])
    with col_prev: st.button("◀", on_click=change_month, args=(-1,))
    with col_month: 
        month_name = calendar.month_name[st.session_state.cal_month]
        st.markdown(f"<h3 style='text-align: center; margin:0;'>{month_name} {st.session_state.cal_year}</h3>", unsafe_allow_html=True)
    with col_next: st.button("▶", on_click=change_month, args=(1,))

    cal = calendar.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
    today = date.today()
    
    html_cal = '<table class="calendar-table"><thead><tr>'
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for d in days: html_cal += f'<th class="day-header">{d}</th>'
    html_cal += '</tr></thead><tbody>'

    for week in cal:
        html_cal += '<tr>'
        for day in week:
            if day == 0:
                html_cal += '<td class="calendar-cell day-empty"></td>'
            else:
                current_date = date(st.session_state.cal_year, st.session_state.cal_month, day)
                css_class = "calendar-cell"
                
                if current_date == today:
                    css_class += " day-today"
                elif current_date in trained_dates:
                    css_class += " day-trained"
                elif current_date < today and current_date not in trained_dates:
                    css_class += " day-missed"
                elif current_date > today:
                    css_class += " day-future"

                html_cal += f'<td class="{css_class}">{day}</td>'
        html_cal += '</tr>'
    html_cal += '</tbody></table>'
    
    st.markdown(html_cal, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="display:flex; gap:15px; justify-content:center; margin-top:10px; font-size:11px; color:#666;">
        <div style="display:flex; align-items:center;"><div style="width:10px; height:10px; background:#8E8E93; margin-right:5px; border-radius:2px;"></div>COMPLETED</div>
        <div style="display:flex; align-items:center;"><div style="width:10px; height:10px; background:#FFB3B3; margin-right:5px; border-radius:2px;"></div>MISSED</div>
        <div style="display:flex; align-items:center;"><div style="width:10px; height:10px; border:1px solid #D4AF37; margin-right:5px; border-radius:2px;"></div>TODAY</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    tab_hist, tab_rec = st.tabs(["📝 HISTORY", "🏆 RECORDS"])
    
    with tab_hist:
        if not df.empty:
            history_df = df.copy()
            history_df = history_df.sort_values(by='День/Дата', ascending=False)
            history_df['День/Дата'] = history_df['День/Дата'].dt.strftime('%d.%m.%Y')
            cols = ['День/Дата', 'Упражнение', 'Вес (кг)', 'Повт', 'Тоннаж', 'Комментарий / Техника']
            st.dataframe(history_df[cols], use_container_width=True, hide_index=True)
            
    with tab_rec:
        if not df.empty:
            records = df.groupby('Упражнение')['Вес (кг)'].max().reset_index()
            records.columns = ['EXERCISE', 'PR (KG)']
            records = records.sort_values('PR (KG)', ascending=False).head(15)
            st.dataframe(records, use_container_width=True, hide_index=True)

# --- LOGBOOK ---
elif selected == "LOGBOOK":
    st.caption("NEW ENTRY")
    with st.form("add"):
        c_date, c_set, c_ex = st.columns([1.5, 1, 2.5])
        with c_date: log_date = st.date_input("Дата", date.today())
        with c_set: set_group = st.text_input("Сет", placeholder="№1")
        with c_ex: ex = st.text_input("Упражнение", placeholder="Жим...")
        
        c_podhod, c_weight, c_reps = st.columns(3)
        with c_podhod: set_num = st.number_input("Подход", 1, 10, 1)
        with c_weight: w = st.number_input("Вес", step=2.5)
        with c_reps: r = st.number_input("Повт", step=1, value=10)
            
        c_tech, c_my = st.columns(2)
        with c_tech: tech_note = st.text_input("Техника", placeholder="План")
        with c_my: my_note = st.text_input("Мой коммент", placeholder="Факт")
        
        if st.form_submit_button("SAVE MISSION"):
            if ex:
                try:
                    sheet.append_row([log_date.strftime("%Y-%m-%d"), set_group, ex, set_num, w, r, w*r, tech_note, my_note])
                    st.success("Saved!")
                    st.rerun()
                except: st.error("Error")

# --- AI COACH ---
elif selected == "AI COACH":
    st.caption(f"INSTRUCTOR // {rank['abbr']}")
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    if p := st.chat_input("..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        res = model.generate_content(f"Tactical fit coach. User Rank: {rank['title']}. Q: {p}")
        with st.chat_message("assistant"): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
