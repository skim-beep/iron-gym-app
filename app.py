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

# --- 5. CSS ---
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
        transition: width 0.5s ease-in-out;
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
    
    # Приводим данные к нужному типу для графиков
    if not df.empty:
        # Пытаемся преобразовать вес и повторы в числа (если там есть текст, ставим 0)
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0)
        df['reps'] = pd.to_numeric(df['reps'], errors='coerce').fillna(0)
        # Приводим дату к формату даты
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        # Убираем пустые даты
        df = df.dropna(subset=['date'])
        
except Exception as e:
    df = pd.DataFrame()
    st.error(f"Data Link Error: {e}")

user_age = calculate_age(USER_BIRTHDAY)
total_xp = len(df)
rank = get_rank_data(total_xp)

# --- 7. ПРОФИЛЬ ---
st.markdown(f"""
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
""", unsafe_allow_html=True)

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

# --- 9. РАЗДЕЛЫ ---

if selected == "DASHBOARD":
    
    # Создаем вкладки для аналитики
    tab1, tab2, tab3 = st.tabs(["📊 OVERVIEW", "📈 PROGRESS", "🏆 RECORDS"])
    
    with tab1:
        col1, col2 = st.columns(2)
        vol = 0
        if not df.empty:
            vol = (df['weight'] * df['reps']).sum()
        with col1: st.metric("TOTAL LOAD", f"{int(vol/1000)}k", help="Общий поднятый вес в кг")
        with col2: st.metric("MISSIONS", f"{total_xp}", help="Количество записей в базе")
        
        if not df.empty:
            st.markdown("##### VOLUME HISTORY")
            # Группируем по дням
            daily = df.groupby(df['date'].dt.date).apply(lambda x: (x['weight']*x['reps']).sum()).reset_index(name='v')
            fig = px.area(daily, x='date', y='v', color_discrete_sequence=['#007AFF'])
            fig.update_layout(height=250, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
        else:
            st.info("No data available yet. Start training!")

    with tab2:
        if not df.empty:
            st.caption("EXERCISE ANALYSIS")
            # Список уникальных упражнений
            all_exercises = df['exercise'].unique().tolist()
            if all_exercises:
                selected_ex = st.selectbox("Select Target", all_exercises)
                
                # Фильтруем данные
                ex_data = df[df['exercise'] == selected_ex].sort_values('date')
                
                if not ex_data.empty:
                    # График рабочего веса
                    fig2 = px.line(ex_data, x='date', y='weight', markers=True, title=f"{selected_ex} (Weight)", color_discrete_sequence=['#FF3B30'])
                    fig2.update_layout(height=300, margin=dict(l=0,r=0,t=30,b=0), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig2, use_container_width=True)
            else:
                st.warning("Exercise list is empty.")
        else:
            st.info("Log your first mission to see analytics.")

    with tab3:
        if not df.empty:
            st.caption("PERSONAL RECORDS (PR)")
            # Находим максимальный вес для каждого упражнения
            # Группируем по упражнению -> берем макс вес -> сортируем
            records = df.groupby('exercise')['weight'].max().reset_index()
            records.columns = ['EXERCISE', 'MAX WEIGHT (KG)']
            records = records.sort_values('MAX WEIGHT (KG)', ascending=False).head(10) # Топ 10
            
            # Красивая таблица
            st.dataframe(
                records, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "MAX WEIGHT (KG)": st.column_config.NumberColumn(format="%.1f kg")
                }
            )
        else:
            st.info("No records yet.")

elif selected == "LOGBOOK":
    st.caption("MISSION LOG")
    with st.form("add"):
        # Предустановленные упражнения + возможность ввода своего
        common_exercises = ["Squat", "Bench Press", "Deadlift", "Overhead Press", "Pull Up", "Dumbbell Row"]
        # Используем text_input с автодополнением (в новых версиях Streamlit нет чистого autocomplete, используем selectbox with custom option logic или просто text)
        # Для простоты пока оставим text_input, но можно сделать selectbox с возможностью писать
        ex = st.text_input("Exercise Name (e.g. Bench Press)")
        
        c1, c2, c3 = st.columns(3)
        w = c1.number_input("Weight (kg)", step=2.5, min_value=0.0)
        r = c2.number_input("Reps", step=1, value=10, min_value=0)
        rpe = c3.selectbox("RPE (Intensity)", [6,7,8,9,10])
        note = st.text_area("Debrief Note")
        
        if st.form_submit_button("COMPLETE MISSION"):
            if ex:
                try:
                    # Дата как строка для Google Sheets
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    sheet.append_row([date_str, ex, w, r, rpe, "done", note])
                    st.success("Log Saved! +1 XP")
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
            else:
                st.error("Enter exercise name!")

elif selected == "AI COACH":
    st.caption(f"INSTRUCTOR // {rank['abbr']}")
    
    # Инициализация чата
    if "messages" not in st.session_state: st.session_state.messages = []
    
    # Вывод истории
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    # Ввод вопроса
    if p := st.chat_input("Request Intel..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        # Контекст для ИИ
        context = f"You are a strict tactical fitness instructor. User rank: {rank['title']}. Age: {user_age}. Current Weight: {USER_WEIGHT_CURRENT}kg."
        if not df.empty:
            # Даем ИИ немного статистики, чтобы он был умнее
            last_workouts = df.tail(3).to_string()
            context += f" Last 3 missions: {last_workouts}"
            
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        res = model.generate_content(f"{context} User asks: {p}")
        
        with st.chat_message("assistant"): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
