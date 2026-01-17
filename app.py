import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import google.generativeai as genai

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(
    page_title="IRON GYM // AI SYSTEM",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🔐 НАСТРОЙКИ БЕЗОПАСНОСТИ И ИИ
# ==========================================

# --- ВСТАВЬ СВОЙ КЛЮЧ НИЖЕ ВНУТРИ КАВЫЧЕК ---
API_KEY = "AIzaSyBRWFkKEWNvlEP2qb4-geQXOExcCVq7S4c" 

# Настройка Gemini
try:
    genai.configure(api_key=API_KEY)
    # Используем модель, которая точно работала (2.0 или 1.5)
    model = genai.GenerativeModel('models/gemini-flash-latest') 
except Exception as e:
    st.error(f"Ошибка ключа API: {e}")

# ==========================================
# 💾 БАЗА ДАННЫХ
# ==========================================
def init_db():
    conn = sqlite3.connect('gym_data.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            exercise TEXT,
            weight REAL,
            reps INTEGER,
            rpe INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def add_workout(exercise, weight, reps, rpe):
    conn = sqlite3.connect('gym_data.db')
    c = conn.cursor()
    date_now = datetime.now().strftime("%Y-%m-%d")
    c.execute('INSERT INTO workouts (date, exercise, weight, reps, rpe) VALUES (?, ?, ?, ?, ?)',
              (date_now, exercise, weight, reps, rpe))
    conn.commit()
    conn.close()

def get_workouts():
    conn = sqlite3.connect('gym_data.db')
    df = pd.read_sql_query("SELECT * FROM workouts ORDER BY id DESC", conn)
    conn.close()
    return df

init_db()

# ==========================================
# 🎨 ДИЗАЙН (BLACK & GOLD)
# ==========================================
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #000000; border-right: 2px solid #D4AF37; }
    h1, h2, h3 { color: #D4AF37 !important; font-family: 'Arial Black', sans-serif; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Кнопки */
    div.stButton > button { background-color: transparent; color: #D4AF37; border: 2px solid #D4AF37; border-radius: 4px; font-weight: bold; text-transform: uppercase; transition: all 0.3s ease; }
    div.stButton > button:hover { background-color: #D4AF37; color: #000; box-shadow: 0 0 15px #D4AF37; }
    
    /* Метрики и поля */
    div[data-testid="metric-container"] { background-color: #1e1e1e; border: 1px solid #333; border-left: 5px solid #D4AF37; padding: 15px; }
    label[data-testid="stMetricLabel"] { color: #a0a0a0 !important; font-size: 14px; text-transform: uppercase; font-weight: 600; }
    div[data-testid="stMetricValue"] { color: #ffffff !important; font-family: 'Arial', sans-serif; font-weight: bold; }
    input, textarea, select { background-color: #2c2c2c !important; color: white !important; border: 1px solid #555 !important; border-radius: 4px; }
    
    /* Чат с ИИ */
    .stChatMessage { background-color: #1e1e1e; border: 1px solid #333; border-radius: 10px; }
    div[data-testid="stChatMessageAvatar"] { background-color: #D4AF37; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 📊 ГРАФИКИ
# ==========================================
def plot_muscle_radar():
    # Заглушка данных (в будущем можно считать из базы)
    categories = ['ГРУДЬ', 'СПИНА', 'НОГИ', 'БИЦЕПС БЕДРА', 'ПЛЕЧИ', 'РУКИ', 'ПРЕСС']
    values = [75, 60, 85, 70, 55, 80, 65] 
    values_today = [0, 0, 85, 70, 0, 0, 0] 

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill='toself', name='База',
        line_color='#D4AF37', fillcolor='rgba(212, 175, 55, 0.3)', marker=dict(size=8, color='#D4AF37')
    ))
    fig.add_trace(go.Scatterpolar(
        r=values_today, theta=categories, mode='markers', name='Сегодня',
        marker=dict(size=15, color='#ffffff', symbol='cross'), hoverinfo='skip'
    ))
    fig.update_layout(
        polar=dict(bgcolor='#1e1e1e', radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor='#333333'), angularaxis=dict(tickfont=dict(size=12, color='#D4AF37'), gridcolor='#333333')),
        paper_bgcolor='#121212', font=dict(color='#D4AF37'), margin=dict(l=40, r=40, t=40, b=40), showlegend=False, height=350
    )
    return fig

# ==========================================
# 🖥️ ИНТЕРФЕЙС
# ==========================================

# Сайдбар
with st.sidebar:
    st.title("🏆 IRON GYM")
    st.caption("AI POWERED SYSTEM")
    st.markdown("---")
    c1, c2 = st.columns(2)
    c1.metric("АТЛЕТ", "SERGEY")
    c2.metric("СТАТУС", "PRO")
    st.markdown(f"**ДАТА:** {datetime.now().strftime('%d.%m.%Y')}")
    st.markdown("---")
    menu = st.radio("НАВИГАЦИЯ", ["ГЛАВНАЯ", "ДНЕВНИК", "AI ТРЕНЕР"])
    st.markdown("---")
    st.header("🎧 МУЗЫКА")
    music = st.selectbox("ВАЙБ", ["PHONK", "METAL", "RAP"])
    if music == "PHONK":
        st.markdown('<iframe style="border-radius:12px" src="https://open.spotify.com/embed/playlist/37i9dQZF1DX6xZZEgC9Ubl?utm_source=generator" width="100%" height="80" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>', unsafe_allow_html=True)


# Логика меню
df_history = get_workouts()

if menu == "ГЛАВНАЯ":
    st.title("🔥 СВОДКА БОЙЦА")
    
    # Расчет метрик
    total_vol = (df_history['weight'] * df_history['reps']).sum() if not df_history.empty else 0
    last_ex = df_history.iloc[0]['exercise'] if not df_history.empty else "N/A"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ТОННАЖ", f"{int(total_vol):,} КГ".replace(",", " "))
    c2.metric("ПОСЛЕДНЕЕ", last_ex)
    c3.metric("ВЕС ТЕЛА", "85.0", "ЦЕЛЬ 90")
    c4.metric("КАЛОРИИ", "2800", "НОРМА")
    
    st.markdown("---")
    st.subheader("🧬 БИОМЕТРИЯ")
    col_vis, col_inf = st.columns([2,1])
    with col_vis:
        st.plotly_chart(plot_muscle_radar(), use_container_width=True, config={'displayModeBar': False})
    with col_inf:
        st.info("**ФОКУС:** НОГИ")
        st.success("✅ ПРОГРЕСС ЕСТЬ")
        st.warning("⚠️ ПОДТЯНИ ПЛЕЧИ")

elif menu == "ДНЕВНИК":
    st.title("📝 ЖУРНАЛ ПОДХОДОВ")
    with st.container():
        c1, c2 = st.columns([3, 1])
        ex = c1.text_input("Упражнение", placeholder="Жим лежа")
        c1, c2, c3 = st.columns(3)
        w = c1.number_input("Вес (кг)", step=2.5)
        r = c2.number_input("Повторы", step=1)
        rpe = c3.selectbox("RPE", [7,8,9,10])
        
        if st.button("СОХРАНИТЬ В БАЗУ"):
            if ex and w > 0:
                add_workout(ex, w, r, rpe)
                st.success("ЗАПИСАНО!")
                st.rerun()

    st.markdown("### ИСТОРИЯ")
    st.dataframe(df_history[['date', 'exercise', 'weight', 'reps', 'rpe']], use_container_width=True)

elif menu == "AI ТРЕНЕР":
    st.title("🧠 GEMINI: АНАЛИТИЧЕСКИЙ ЦЕНТР")
    
    # Инициализация истории чата
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Отображение старых сообщений
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Поле ввода
    if prompt := st.chat_input("Спроси совет по тренировке..."):
        # 1. Показываем сообщение пользователя
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Формируем контекст для ИИ (отправляем ему историю из базы)
        if not df_history.empty:
            history_str = df_history.head(10).to_string(index=False)
            context_data = f"Ты тренер. Вот мои последние подходы:\n{history_str}\n"
        else:
            context_data = "Ты тренер. У меня пока нет записей о тренировках. "

        # 3. Запрос к Gemini
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            try:
                # Объединяем контекст базы и вопрос пользователя
                chat_prompt = context_data + "Вопрос пользователя: " + prompt
                
                response = model.generate_content(chat_prompt)
                full_response = response.text
                
                message_placeholder.markdown(full_response)
            except Exception as e:
                full_response = f"⚠️ Ошибка связи с ИИ: {e}. Проверь API Key."
                message_placeholder.error(full_response)
        
        # 4. Сохраняем ответ
        st.session_state.messages.append({"role": "assistant", "content": full_response})
