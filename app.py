import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(
    page_title="IRON GYM // CLOUD",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🔐 ПОДКЛЮЧЕНИЕ КЛЮЧЕЙ ---
try:
    # 1. Ключ Gemini
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

    # 2. Ключи Google Sheets (читаем JSON как текст из секретов)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # Превращаем текст из секретов обратно в словарь
    json_str = st.secrets["service_account_json"]
    creds_dict = json.loads(json_str, strict=False)
    
    # Страховка от сбоев переноса строк в приватном ключе
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    # Открываем таблицу по имени
    sheet = client.open("IRON_GYM_DB").sheet1

except Exception as e:
    st.error(f"🔴 Ошибка подключения: {e}")
    st.info("Чек-лист: 1) Таблица называется IRON_GYM_DB? 2) Бот (email из JSON) добавлен в таблицу как Редактор? 3) JSON скопирован в Secrets корректно?")
    st.stop()


# --- ФУНКЦИИ ---
def add_workout(exercise, weight, reps, rpe):
    date_now = datetime.now().strftime("%Y-%m-%d")
    try:
        sheet.append_row([date_now, exercise, weight, reps, rpe])
        return True
    except Exception as e:
        st.error(f"Ошибка записи: {e}")
        return False

def get_workouts():
    try:
        data = sheet.get_all_records()
        if data:
            return pd.DataFrame(data)
        else:
            return pd.DataFrame(columns=["date", "exercise", "weight", "reps", "rpe"])
    except:
        return pd.DataFrame(columns=["date", "exercise", "weight", "reps", "rpe"])

# --- ДИЗАЙН ---
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #000000; border-right: 2px solid #D4AF37; }
    h1, h2, h3 { color: #D4AF37 !important; font-family: 'Arial Black', sans-serif; text-transform: uppercase; letter-spacing: 1px; }
    div.stButton > button { background-color: transparent; color: #D4AF37; border: 2px solid #D4AF37; border-radius: 4px; font-weight: bold; text-transform: uppercase; transition: all 0.3s ease; }
    div.stButton > button:hover { background-color: #D4AF37; color: #000; box-shadow: 0 0 15px #D4AF37; }
    div[data-testid="metric-container"] { background-color: #1e1e1e; border: 1px solid #333; border-left: 5px solid #D4AF37; padding: 15px; }
    label[data-testid="stMetricLabel"] { color: #a0a0a0 !important; font-size: 14px; text-transform: uppercase; font-weight: 600; }
    div[data-testid="stMetricValue"] { color: #ffffff !important; font-family: 'Arial', sans-serif; font-weight: bold; }
    input, textarea, select { background-color: #2c2c2c !important; color: white !important; border: 1px solid #555 !important; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- ГРАФИК ---
def plot_muscle_radar():
    categories = ['ГРУДЬ', 'СПИНА', 'НОГИ', 'БИЦЕПС БЕДРА', 'ПЛЕЧИ', 'РУКИ', 'ПРЕСС']
    values = [75, 60, 85, 70, 55, 80, 65] 
    values_today = [0, 0, 85, 70, 0, 0, 0] 
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', name='База', line_color='#D4AF37', fillcolor='rgba(212, 175, 55, 0.3)'))
    fig.add_trace(go.Scatterpolar(r=values_today, theta=categories, mode='markers', name='Сегодня', marker=dict(size=15, color='#ffffff', symbol='cross'), hoverinfo='skip'))
    fig.update_layout(polar=dict(bgcolor='#1e1e1e', radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor='#333333'), angularaxis=dict(tickfont=dict(size=12, color='#D4AF37'), gridcolor='#333333')), paper_bgcolor='#121212', font=dict(color='#D4AF37'), margin=dict(l=40, r=40, t=40, b=40), showlegend=False, height=350)
    return fig

# --- ИНТЕРФЕЙС ---
with st.sidebar:
    st.title("💎 IRON CLOUD")
    st.caption("SYNC: GOOGLE SHEETS ✅")
    st.markdown("---")
    st.metric("АТЛЕТ", "SERGEY")
    menu = st.radio("МЕНЮ", ["ГЛАВНАЯ", "ДНЕВНИК", "AI ТРЕНЕР"])

df_history = get_workouts()

if menu == "ГЛАВНАЯ":
    st.title("🔥 СВОДКА")
    if not df_history.empty and 'weight' in df_history.columns:
        df_history['weight'] = pd.to_numeric(df_history['weight'], errors='coerce').fillna(0)
        df_history['reps'] = pd.to_numeric(df_history['reps'], errors='coerce').fillna(0)
        total_vol = (df_history['weight'] * df_history['reps']).sum()
        last_date = df_history.iloc[-1]['date'] if 'date' in df_history.columns else "Нет данных"
    else:
        total_vol = 0
        last_date = "Нет данных"
    
    c1, c2 = st.columns(2)
    c1.metric("ТОННАЖ (ALL TIME)", f"{int(total_vol):,} KG")
    c2.metric("ПОСЛЕДНЯЯ ТРЕНЯ", last_date)
    st.markdown("---")
    c1, c2 = st.columns([2,1])
    with c1: st.plotly_chart(plot_muscle_radar(), use_container_width=True, config={'displayModeBar': False})
    with c2: st.info("Данные надежно хранятся в Google Таблице.")

elif menu == "ДНЕВНИК":
    st.title("📝 ЖУРНАЛ")
    with st.container():
        c1, c2 = st.columns([3, 1])
        ex = c1.text_input("Упражнение")
        c1, c2, c3 = st.columns(3)
        w = c1.number_input("Вес", step=2.5)
        r = c2.number_input("Повторы", step=1)
        rpe = c3.selectbox("RPE", [7,8,9,10])
        
        if st.button("СОХРАНИТЬ В ОБЛАКО"):
            if ex:
                if add_workout(ex, w, r, rpe):
                    st.success("✅ Записано в таблицу!")
                    st.rerun()

    if not df_history.empty:
        st.dataframe(df_history, use_container_width=True)

elif menu == "AI ТРЕНЕР":
    st.title("🧠 GEMINI CLOUD")
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if prompt := st.chat_input("Вопрос..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        if not df_history.empty:
            history_str = df_history.tail(10).to_string(index=False)
            context = f"Вот последние тренировки атлета из базы данных:\n{history_str}\n"
        else:
            context = "В базе данных пока нет записей о тренировках."
            
        with st.chat_message("assistant"):
            try:
                response = model.generate_content(context + "Вопрос пользователя: " + prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Ошибка AI: {e}")
