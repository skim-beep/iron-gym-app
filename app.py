import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.graph_objects as go
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

# --- 2. НАСТРОЙКИ ПРОФИЛЯ ---
# Надежная ссылка на аватар (Tactical Operator)
AVATAR_URL = "https://i.imgur.com/8N3g2QJ.jpeg"
# Иконка звания (US Army Captain - O3)
RANK_ICON = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/US-Army-O3-Collar.svg/800px-US-Army-O3-Collar.svg.png"

USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_TARGET = 90.0 # Цель
USER_WEIGHT_CURRENT = 85.0 # Пока хардкод (можно брать из базы)

# --- 3. ФУНКЦИИ БИОМЕТРИИ ---
def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def calculate_tenure(df):
    if df.empty:
        return "0 ДНЕЙ"
    try:
        # Ищем самую раннюю дату в базе
        first_date = pd.to_datetime(df['date']).min()
        days = (datetime.now() - first_date).days
        if days > 365:
            return f"{days // 365} Г. {days % 365} ДН."
        return f"{days} ДН."
    except:
        return "1 ДЕНЬ"

# --- 4. ДИЗАЙН И СТИЛИ (CSS) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500&display=swap');

    .stApp {{
        background-color: #F2F3F7;
        font-family: 'Inter', sans-serif;
    }}

    #MainMenu, footer, header {{visibility: hidden;}}

    /* Карточки */
    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {{
        background-color: #FFFFFF;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0px 4px 20px rgba(0,0,0,0.05);
    }}

    /* ХЕДЕР ПРОФИЛЯ (СЛОЖНАЯ СТРУКТУРА) */
    .profile-header {{
        display: flex;
        align-items: center;
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 24px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        margin-bottom: 25px;
        border: 1px solid #FFFFFF;
    }}
    
    .avatar-wrapper {{
        position: relative;
        margin-right: 18px;
    }}
    
    .avatar-container {{
        width: 85px;
        height: 85px;
        border-radius: 50%;
        overflow: hidden;
        border: 3px solid #1C1C1E;
    }}
    
    .avatar-img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
    }}
    
    .user-info {{
        flex-grow: 1;
    }}

    .name-rank-row {{
        display: flex;
        align-items: center;
        margin-bottom: 4px;
    }}
    
    .user-name {{
        font-size: 24px;
        font-weight: 900;
        color: #1C1C1E;
        letter-spacing: -0.5px;
        margin-right: 8px;
        line-height: 1;
    }}
    
    .rank-icon {{
        height: 20px;
        width: auto;
    }}

    .rank-title {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: #8E8E93;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
        display: block;
    }}

    /* СТАТИСТИКА (Возраст, Вес, Стаж) */
    .stats-badges {{
        display: flex;
        gap: 8px;
    }}
    
    .stat-badge {{
        background-color: #F2F2F7;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 700;
        color: #3A3A3C;
        display: flex;
        align-items: center;
    }}

    /* Метрики */
    div[data-testid="stMetricValue"] {{
        font-size: 30px !important;
        font-weight: 800 !important;
        color: #000000 !important;
    }}
    label[data-testid="stMetricLabel"] {{
        font-size: 12px !important;
        color: #8E8E93 !important;
        font-weight: 600;
    }}

    /* Кнопки */
    div.stButton > button {{
        width: 100%;
        background-color: #1C1C1E;
        color: #FFFFFF;
        border-radius: 14px;
        padding: 14px;
        font-weight: 600;
        border: none;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 5. ПОДКЛЮЧЕНИЕ К БАЗЕ ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    json_str = st.secrets["service_account_json"]
    creds_dict = json.loads(json_str, strict=False)
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("IRON_GYM_DB").sheet1
    
    data = sheet.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame()

except Exception as e:
    df = pd.DataFrame()

# --- 6. РАСЧЕТ ДАННЫХ ---
user_age = calculate_age(USER_BIRTHDAY)
tenure = calculate_tenure(df)

# --- 7. ИНТЕРФЕЙС ---

# Хедер (HTML)
st.markdown(f"""
    <div class="profile-header">
        <div class="avatar-wrapper">
            <div class="avatar-container">
                <img src="{AVATAR_URL}" class="avatar-img">
            </div>
        </div>
        <div class="user-info">
            <div class="name-rank-row">
                <span class="user-name">SERGEY</span>
                <img src="{RANK_ICON}" class="rank-icon" title="Captain">
            </div>
            <span class="rank-title">CAPTAIN (O-3) // US ARMY</span>
            
            <div class="stats-badges">
                <div class="stat-badge">🎂 {user_age} YEARS</div>
                <div class="stat-badge">⚖️ {USER_WEIGHT_CURRENT} KG</div>
                <div class="stat-badge">⏳ {tenure}</div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Меню
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

# --- ЛОГИКА ВКЛАДОК ---

if selected == "DASHBOARD":
    st.caption("СВОДКА")
    col1, col2 = st.columns(2)
    
    total_vol = 0
    workouts_count = 0
    last_date = "N/A"
    
    if not df.empty and 'weight' in df.columns:
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0)
        df['reps'] = pd.to_numeric(df['reps'], errors='coerce').fillna(0)
        total_vol = (df['weight'] * df['reps']).sum()
        workouts_count = len(df)
        if 'date' in df.columns:
            last_date = df.iloc[-1]['date']

    with col1: st.metric("ТОННАЖ", f"{int(total_vol/1000)}k", "ALL TIME")
    with col2: st.metric("ТРЕНИРОВОК", f"{workouts_count}", f"LAST: {last_date}")
        
    st.markdown("---")
    st.caption("ПРОГРЕСС")
    
    if not df.empty:
        daily_vol = df.groupby('date').apply(lambda x: (x['weight'] * x['reps']).sum()).reset_index(name='vol')
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_vol['date'], y=daily_vol['vol'],
            mode='lines', fill='tozeroy',
            line=dict(color='black', width=3),
            fillcolor='rgba(0, 0, 0, 0.1)'
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=0, b=0), height=200,
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

elif selected == "LOGBOOK":
    st.caption("НОВАЯ ЗАПИСЬ")
    with st.form("entry", clear_on_submit=True):
        ex = st.text_input("Упражнение")
        c1, c2, c3 = st.columns(3)
        w = c1.number_input("Вес", step=2.5)
        r = c2.number_input("Повторы", step=1, value=10)
        rpe = c3.selectbox("RPE", [7,8,9,10])
        note = st.text_area("Заметка")
        
        if st.form_submit_button("ЗАПИСАТЬ"):
            if ex:
                date_now = datetime.now().strftime("%Y-%m-%d")
                try:
                    sheet.append_row([date_now, ex, w, r, rpe, "done", note])
                    st.success("✅ Сохранено!")
                except:
                    st.error("Ошибка записи (проверь столбцы в таблице)")

elif selected == "AI COACH":
    st.caption("TACTICAL ADVISOR")
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if prompt := st.chat_input("Запрос..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        # Контекст для ИИ
        info_context = f"Атлет: Сергей, Возраст: {user_age}, Вес: {USER_WEIGHT_CURRENT}кг."
        
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        response = model.generate_content(f"Ты военный инструктор. Твои данные о бойце: {info_context}. Ответь кратко: {prompt}")
        
        with st.chat_message("assistant"): st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
