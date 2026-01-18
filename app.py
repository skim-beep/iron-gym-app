import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from streamlit_option_menu import option_menu

# --- 1. НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="IRON GYM OS",
    page_icon="🛡️",
    layout="centered", # Мобильный вид
    initial_sidebar_state="collapsed"
)

# --- 2. ВЫБРАННЫЙ АВАТАР (DESERT OPS) ---
AVATAR_URL = "https://i.pinimg.com/736x/8b/44/49/8b444907994406263702b8d4e92a2334.jpg"

# --- 3. ДИЗАЙН И СТИЛИ (CSS) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

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

    /* Хедер Профиля (ФИНАЛЬНЫЙ ВАРИАНТ - ИДЕАЛЬНЫЙ КРУГ) */
    .profile-header {{
        display: flex;
        align-items: center;
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }}
    
    .avatar-container {{
        width: 80px;
        height: 80px;
        border-radius: 50%; /* Круг */
        overflow: hidden; /* Обрезаем всё лишнее */
        margin-right: 15px;
        border: 2px solid #1A1A1A; /* Тонкая черная рамка */
        flex-shrink: 0;
    }}
    
    .avatar-img {{
        width: 100%;
        height: 100%;
        object-fit: cover; /* Фото заполняет круг ПОЛНОСТЬЮ */
        display: block;
    }}

    .user-info h3 {{
        margin: 0;
        font-size: 22px;
        font-weight: 800;
        color: #1C1C1E;
    }}
    .user-info p {{
        margin: 2px 0 0 0;
        color: #8E8E93;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }}

    /* Метрики */
    div[data-testid="stMetricValue"] {{
        font-size: 32px !important;
        font-weight: 800 !important;
        color: #000000 !important;
    }}
    label[data-testid="stMetricLabel"] {{
        font-size: 13px !important;
        color: #8E8E93 !important;
        font-weight: 600;
    }}

    /* Кнопки */
    div.stButton > button {{
        width: 100%;
        background-color: #000000;
        color: #FFFFFF;
        border-radius: 12px;
        padding: 14px 20px;
        font-weight: 600;
        border: none;
    }}
    div.stButton > button:hover {{
        background-color: #333333;
        color: #FFFFFF;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 4. ПОДКЛЮЧЕНИЕ К БАЗЕ ---
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

# --- 5. ИНТЕРФЕЙС ---

# Хедер (HTML)
st.markdown(f"""
    <div class="profile-header">
        <div class="avatar-container">
            <img src="{AVATAR_URL}" class="avatar-img">
        </div>
        <div class="user-info">
            <h3>SERGEY</h3>
            <p>OPERATOR // IRON GYM OS</p>
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
    if not df.empty and 'weight' in df.columns:
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0)
        df['reps'] = pd.to_numeric(df['reps'], errors='coerce').fillna(0)
        total_vol = (df['weight'] * df['reps']).sum()
        workouts_count = len(df)

    with col1: st.metric("ТОННАЖ", f"{int(total_vol/1000)}k")
    with col2: st.metric("ПОДХОДОВ", f"{workouts_count}")
        
    st.markdown("---")
    st.caption("ДИНАМИКА ОБЪЕМА")
    
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
    st.caption("GEM-BOT TACTICAL ADVISOR")
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if prompt := st.chat_input("Вопрос..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        response = model.generate_content(f"Ты жесткий тактический тренер. Кратко: {prompt}")
        
        with st.chat_message("assistant"): st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
