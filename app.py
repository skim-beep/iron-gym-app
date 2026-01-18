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
    layout="centered", # Важно: режим мобильного приложения (узкий центр)
    initial_sidebar_state="collapsed"
)

# --- 2. ССЫЛКА НА АВАТАР (Военный оператор) ---
# Я поставил качественный референс. Если у тебя есть своя ссылка - замени её здесь.
AVATAR_URL = "https://i.pinimg.com/736x/8b/44/49/8b444907994406263702b8d4e92a2334.jpg" 

# --- 3. CSS СТИЛИ (ДИЗАЙН) ---
st.markdown(f"""
    <style>
    /* Импорт шрифта Inter (как в интерфейсах Apple/Google) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    /* Глобальный фон */
    .stApp {{
        background-color: #F2F3F7; /* Светло-серый "бетон" */
        font-family: 'Inter', sans-serif;
    }}

    /* Скрываем лишнее */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* Карточки (Белые блоки) */
    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {{
        background-color: #FFFFFF;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0px 4px 20px rgba(0,0,0,0.05);
    }}

    /* Заголовки */
    h1, h2, h3 {{
        color: #1C1C1E !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }}

    /* Метрики (Цифры) */
    div[data-testid="stMetricValue"] {{
        font-size: 36px !important;
        font-weight: 800 !important;
        color: #000000 !important;
    }}
    label[data-testid="stMetricLabel"] {{
        font-size: 14px !important;
        color: #8E8E93 !important;
        text-transform: uppercase;
        font-weight: 600;
    }}

    /* Кнопки (Черный стиль Nike/Apple) */
    div.stButton > button {{
        width: 100%;
        background-color: #000000;
        color: #FFFFFF;
        border-radius: 14px;
        padding: 16px 20px;
        font-size: 16px;
        font-weight: 600;
        border: none;
        transition: all 0.2s;
    }}
    div.stButton > button:hover {{
        background-color: #333333;
        color: #FFFFFF;
        transform: scale(1.02);
    }}
    
    /* Поля ввода */
    div[data-baseweb="input"] {{
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        border: 1px solid #E5E5EA !important;
    }}

    /* Хедер Профиля (CSS-магия) */
    .profile-header {{
        display: flex;
        align-items: center;
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }}
    .avatar {{
        width: 70px;
        height: 70px;
        border-radius: 50%;
        margin-right: 15px;
        border: 3px solid #000; /* Черная рамка */
        object-fit: cover;
    }}
    .user-info h3 {{
        margin: 0;
        font-size: 22px;
        color: #000;
    }}
    .user-info p {{
        margin: 0;
        color: #666;
        font-size: 14px;
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
    
    # Загружаем данные
    data = sheet.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame()

except Exception as e:
    st.warning("⚠️ База данных подключается... (Если это первый запуск, обнови страницу)")
    df = pd.DataFrame() # Пустая таблица, чтобы дизайн не ломался

# --- 5. ИНТЕРФЕЙС ---

# Хедер Профиля (HTML)
st.markdown(f"""
    <div class="profile-header">
        <img src="https://img.freepik.com/premium-photo/soldier-tactical-gear-helmet-mask-dark-background_117023-345.jpg" class="avatar">
        <div class="user-info">
            <h3>SERGEY</h3>
            <p>OPERATOR // IRON GYM OS</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# Навигация (Красивые вкладки)
selected = option_menu(
    menu_title=None,
    options=["DASHBOARD", "LOGBOOK", "AI COACH"],
    icons=["bar-chart-fill", "journal-richtext", "cpu-fill"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent"},
        "icon": {"color": "#666", "font-size": "16px"}, 
        "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", "--hover-color": "#eee"},
        "nav-link-selected": {"background-color": "#000", "color": "#fff"}, # Черная активная кнопка
    }
)

# --- ВКЛАДКА 1: ДАШБОРД ---
if selected == "DASHBOARD":
    st.subheader("📊 ТЕКУЩИЙ СТАТУС")
    
    # Сетка 2x2 для метрик
    col1, col2 = st.columns(2)
    
    # Расчет метрик (Заглушки, если база пустая)
    total_vol = 0
    if not df.empty and 'weight' in df.columns:
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0)
        df['reps'] = pd.to_numeric(df['reps'], errors='coerce').fillna(0)
        total_vol = (df['weight'] * df['reps']).sum()

    with col1:
        st.metric("ТОННАЖ", f"{int(total_vol/1000)}k", "ALL TIME")
    with col2:
        st.metric("ТРЕНИРОВОК", f"{len(df)}", "+1 на этой неделе")
        
    st.markdown("---")
    
    # График (Стилизованный под Apple Health)
    st.subheader("📈 ДИНАМИКА")
    if not df.empty:
        # Группируем по датам
        daily_vol = df.groupby('date').apply(lambda x: (x['weight'] * x['reps']).sum()).reset_index(name='vol')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_vol['date'], 
            y=daily_vol['vol'],
            mode='lines',
            fill='tozeroy', # Заливка под графиком
            line=dict(color='black', width=3), # Черная линия
            fillcolor='rgba(0, 0, 0, 0.1)' # Прозрачная черная заливка
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=0, b=0),
            height=250,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#e5e5e5')
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Добавь первую тренировку, чтобы увидеть график.")

# --- ВКЛАДКА 2: ДНЕВНИК ---
elif selected == "LOGBOOK":
    st.subheader("📝 НОВАЯ ЗАПИСЬ")
    
    with st.form("entry_form", clear_on_submit=True):
        st.caption("ПАРАМЕТРЫ ПОДХОДА")
        exercise = st.text_input("Упражнение", placeholder="Например: Жим лежа")
        
        c1, c2, c3 = st.columns(3)
        weight = c1.number_input("Вес (кг)", step=2.5)
        reps = c2.number_input("Повторы", step=1, value=10)
        rpe = c3.selectbox("RPE", [7,8,9,10])
        
        note = st.text_area("Заметка", placeholder="Как ощущения? (Легко/Тяжело/Болит плечо)")
        
        # Большая черная кнопка
        submitted = st.form_submit_button("ЗАПИСАТЬ ПОДХОД")
        
        if submitted and exercise:
            date_now = datetime.now().strftime("%Y-%m-%d")
            # Записываем в Гугл Таблицу (включая заметку)
            try:
                sheet.append_row([date_now, exercise, weight, reps, rpe, "done", note])
                st.success(f"✅ {exercise} добавлен!")
            except:
                st.error("Ошибка записи. Проверь заголовки в таблице (date, exercise, weight, reps, rpe, status, notes)")

# --- ВКЛАДКА 3: AI COACH ---
elif selected == "AI COACH":
    st.subheader("🧠 GEM-BOT TACTICAL")
    
    # Чат интерфейс
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Спроси тренера..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Логика AI (пока базовая)
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        response = model.generate_content(f"Ты элитный тренер. Ответь кратко и по делу: {prompt}")
        
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
