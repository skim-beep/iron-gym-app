import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.graph_objects as go
import plotly.express as px
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

# --- 4. ЛОГИКА ---
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

# --- 5. CSS (ИСПРАВЛЕННЫЙ) ---
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

    /* ПРОФИЛЬ - ИСПРАВЛЕН ГЛЮК */
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
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0)
        df['reps'] = pd.to_numeric(df['reps'], errors='coerce').fillna(0)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
        # Считаем тоннаж для каждого подхода
        df['tonnage'] = df['weight'] * df['reps']
        
except Exception as e:
    df = pd.DataFrame()

user_age = calculate_age(USER_BIRTHDAY)
# Считаем XP как количество уникальных дней тренировок или просто записей? 
# Армейская система: 1 Подход = это мало. 1 Тренировка (день) = 1 XP.
# Но для мотивации давай оставим: 1 Запись (сет) = 1 XP. Так звания идут быстрее.
total_xp = len(df)
rank = get_rank_data(total_xp)

# --- 7. HTML ПРОФИЛЯ (ИСПРАВЛЕННЫЙ) ---
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

if selected == "DASHBOARD":
    # 3 Вкладки: Обзор, История (Как в Excel), Графики
    tab1, tab2, tab3 = st.tabs(["📊 DASHBOARD", "📝 HISTORY", "🏆 RECORDS"])
    
    with tab1:
        col1, col2 = st.columns(2)
        vol = 0
        if not df.empty: vol = df['tonnage'].sum()
        with col1: st.metric("TOTAL LOAD", f"{int(vol/1000)}k")
        with col2: st.metric("MISSIONS COMPLETED", f"{total_xp}")
        
        if not df.empty:
            daily = df.groupby(df['date'].dt.date)['tonnage'].sum().reset_index()
            fig = px.bar(daily, x='date', y='tonnage', color_discrete_sequence=['#007AFF'])
            fig.update_layout(height=250, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
    
    with tab2:
        st.subheader("TACTICAL LOG (HISTORY)")
        if not df.empty:
            # Делаем копию для красивого отображения
            history_df = df.copy()
            # Сортируем: новые сверху
            history_df = history_df.sort_values(by='date', ascending=False)
            # Форматируем дату
            history_df['date'] = history_df['date'].dt.strftime('%d.%m.%Y')
            
            # Выбираем и переименовываем колонки как в твоем Excel
            display_df = history_df[['date', 'exercise', 'weight', 'reps', 'tonnage', 'rpe', 'note']]
            display_df.columns = ['ДАТА', 'УПРАЖНЕНИЕ', 'ВЕС', 'ПОВТ', 'ТОННАЖ', 'RPE', 'ЗАМЕТКА']
            
            # Отображаем таблицу на всю ширину
            st.dataframe(
                display_df, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ВЕС": st.column_config.NumberColumn(format="%.1f kg"),
                    "ТОННАЖ": st.column_config.NumberColumn(format="%d"),
                }
            )
        else:
            st.info("No mission data found.")

    with tab3:
        if not df.empty:
            records = df.groupby('exercise')['weight'].max().reset_index()
            records.columns = ['EXERCISE', 'PR (KG)']
            records = records.sort_values('PR (KG)', ascending=False).head(15)
            st.dataframe(records, use_container_width=True, hide_index=True)

elif selected == "LOGBOOK":
    st.caption("NEW ENTRY")
    with st.form("add"):
        c_date, c_name = st.columns([1, 2])
        with c_date:
            log_date = st.date_input("Date", date.today())
        with c_name:
            # Можно сделать selectbox если наберется база
            ex = st.text_input("Exercise", placeholder="e.g. Bench Press")
        
        c1, c2, c3 = st.columns(3)
        w = c1.number_input("Weight", step=2.5)
        r = c2.number_input("Reps", step=1, value=10)
        rpe = c3.selectbox("RPE", [6,7,8,9,10])
        note = st.text_area("Notes (e.g. 'Локти 45 град')")
        
        if st.form_submit_button("SAVE MISSION"):
            if ex:
                try:
                    date_str = log_date.strftime("%Y-%m-%d")
                    sheet.append_row([date_str, ex, w, r, rpe, "done", note])
                    st.success("Saved!")
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

elif selected == "AI COACH":
    st.caption(f"INSTRUCTOR // {rank['abbr']}")
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    if p := st.chat_input("Ask instructor..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        res = model.generate_content(f"You are a tough army drill sergeant. User rank: {rank['title']}. Question: {p}")
        with st.chat_message("assistant"): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
