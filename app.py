import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from streamlit_option_menu import option_menu
import base64
import calendar

# --- 1. НАСТРОЙКИ ---
st.set_page_config(
    page_title="IRON GYM OS",
    page_icon="🦅",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- 2. ЦВЕТОВАЯ ПАЛИТРА (HUD STYLE) ---
# Цвета взяты с твоих картинок
HUD_BG = "#050505"          # Почти черный
HUD_PANEL = "#121212"       # Темно-серый фон карточек
HUD_BORDER = "#333333"      # Рамки
ACCENT_GREEN = "#00FF41"    # Неоновый тактический зеленый
ACCENT_GOLD = "#FFD700"     # Золото для рангов
TEXT_MAIN = "#E0E0E0"
TEXT_DIM = "#777777"

AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. ШЕВРОНЫ (ОФИЦИАЛЬНЫЕ SVG) ---
RANK_IMGS = {
    "PV1": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Army-USA-OR-01.svg/100px-Army-USA-OR-01.svg.png", 
    "PV2": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/Army-USA-OR-02.svg/100px-Army-USA-OR-02.svg.png",
    "PFC": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/ec/Army-USA-OR-03.svg/100px-Army-USA-OR-03.svg.png",
    "SPC": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Army-USA-OR-04b.svg/100px-Army-USA-OR-04b.svg.png",
    "CPL": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Army-USA-OR-04a.svg/100px-Army-USA-OR-04a.svg.png",
    "SGT": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/Army-USA-OR-05.svg/100px-Army-USA-OR-05.svg.png",
    "SSG": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Army-USA-OR-06.svg/100px-Army-USA-OR-06.svg.png",
    "SFC": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Army-USA-OR-07.svg/100px-Army-USA-OR-07.svg.png",
    "MSG": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Army-USA-OR-08b.svg/100px-Army-USA-OR-08b.svg.png",
    "1SG": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Army-USA-OR-08a.svg/100px-Army-USA-OR-08a.svg.png",
    "SGM": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Army-USA-OR-09c.svg/100px-Army-USA-OR-09c.svg.png",
    "2LT": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Army-USA-OF-01.svg/50px-Army-USA-OF-01.svg.png",
    "1LT": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Army-USA-OF-02.svg/50px-Army-USA-OF-02.svg.png",
    "CPT": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/76/Army-USA-OF-03.svg/50px-Army-USA-OF-03.svg.png",
    "MAJ": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Army-USA-OF-04.svg/50px-Army-USA-OF-04.svg.png",
    "LTC": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Army-USA-OF-05.svg/50px-Army-USA-OF-05.svg.png",
    "COL": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Army-USA-OF-06.svg/50px-Army-USA-OF-06.svg.png",
    "BG": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Army-USA-OF-07.svg/100px-Army-USA-OF-07.svg.png",
    "MG": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Army-USA-OF-08.svg/100px-Army-USA-OF-08.svg.png",
    "LTG": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Army-USA-OF-09.svg/100px-Army-USA-OF-09.svg.png",
    "GEN": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Army-USA-OF-10.svg/100px-Army-USA-OF-10.svg.png",
    "GA": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Army-USA-OF-11.svg/100px-Army-USA-OF-11.svg.png"
}

FULL_RANK_SYSTEM = [
    (0, 24, "РЕКРУТ", "PV1"), (25, 49, "РЯДОВОЙ", "PV2"), (50, 99, "РЯДОВОЙ 1 КЛ", "PFC"),
    (100, 149, "СПЕЦИАЛИСТ", "SPC"), (150, 199, "КАПРАЛ", "CPL"), (200, 299, "СЕРЖАНТ", "SGT"),
    (300, 399, "ШТАБ-СЕРЖАНТ", "SSG"), (400, 499, "СЕРЖАНТ 1 КЛ", "SFC"), (500, 649, "МАСТЕР-СЕРЖАНТ", "MSG"),
    (650, 799, "1-Й СЕРЖАНТ", "1SG"), (800, 999, "СЕРЖАНТ-МАЙОР", "SGM"), (1000, 1499, "2-Й ЛЕЙТЕНАНТ", "2LT"),
    (1500, 1999, "1-Й ЛЕЙТЕНАНТ", "1LT"), (2000, 2999, "КАПИТАН", "CPT"), (3000, 3999, "МАЙОР", "MAJ"),
    (4000, 4999, "ПОДПОЛКОВНИК", "LTC"), (5000, 5999, "ПОЛКОВНИК", "COL"), (6000, 7999, "БРИГАДНЫЙ ГЕНЕРАЛ", "BG"),
    (8000, 9999, "ГЕНЕРАЛ-МАЙОР", "MG"), (10000, 14999, "ГЕНЕРАЛ-ЛЕЙТЕНАНТ", "LTG"), (15000, 24999, "ГЕНЕРАЛ", "GEN"),
    (25000, 999999, "ГЕНЕРАЛ АРМИИ", "GA")
]

def get_rank_data(xp):
    for r_min, r_max, title, abbr in FULL_RANK_SYSTEM:
        if r_min <= xp <= r_max:
            needed = r_max - r_min + 1
            current = xp - r_min
            img = RANK_IMGS.get(abbr, RANK_IMGS["PV1"])
            return {"title": title, "abbr": abbr, "icon": img, "progress": int((current/needed)*100), "next_xp": needed-current}
    return {"title": "ГЕНЕРАЛ АРМИИ", "abbr": "GA", "icon": RANK_IMGS["GA"], "progress": 100, "next_xp": 0}

def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def detect_muscle(ex):
    ex = str(ex).lower()
    if any(x in ex for x in ['жим', 'chest', 'отжимания', 'брусья', 'груд']): return "ГРУДЬ"
    if any(x in ex for x in ['тяга', 'спина', 'back', 'row', 'подтягивания']): return "СПИНА"
    if any(x in ex for x in ['присед', 'ноги', 'legs', 'squat', 'выпады']): return "НОГИ"
    if any(x in ex for x in ['бицепс', 'трицепс', 'arms', 'молот']): return "РУКИ"
    if any(x in ex for x in ['плечи', 'махи', 'shouder', 'press', 'армейский']): return "ПЛЕЧИ"
    if any(x in ex for x in ['пресс', 'abs', 'core', 'планка']): return "ПРЕСС"
    return "ОБЩЕЕ"

# --- 4. CSS (HUD DESIGN - TO MATCH IMAGES) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

    /* BASE */
    .stApp {{ background-color: {HUD_BG}; color: {TEXT_MAIN}; font-family: 'Share Tech Mono', monospace; }}
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* FONTS */
    .hud-font {{ font-family: 'Oswald', sans-serif; text-transform: uppercase; letter-spacing: 1px; }}
    
    /* CARDS */
    .hud-card {{
        background-color: {HUD_PANEL};
        border: 1px solid {HUD_BORDER};
        border-top: 2px solid {ACCENT_GREEN}; /* Green Top Border like in image */
        padding: 15px; margin-bottom: 20px;
        position: relative;
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.05); /* Subtle green glow */
    }}
    
    /* DECORATIVE CORNERS (CSS HACK) */
    .hud-card::after {{
        content: ''; position: absolute; bottom: 0; right: 0;
        width: 10px; height: 10px;
        border-bottom: 2px solid {ACCENT_GREEN};
        border-right: 2px solid {ACCENT_GREEN};
    }}

    /* PROFILE */
    .avatar-area {{ 
        width: 80px; height: 80px; 
        border: 2px solid {ACCENT_GOLD}; 
        border-radius: 5px; /* Square with slight radius like HUD */
        overflow: hidden; float: left; margin-right: 15px; 
    }}
    .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
    .user-name {{ font-family: 'Oswald', sans-serif; font-size: 32px; color: #FFF; line-height: 1; }}
    
    /* PROGRESS */
    .progress-track {{ width: 100%; height: 6px; background: #222; margin-top: 8px; border: 1px solid #444; }}
    .progress-fill {{ height: 100%; background: {ACCENT_GREEN}; box-shadow: 0 0 10px {ACCENT_GREEN}; }}
    
    /* BADGES */
    .stat-badge {{ 
        background: rgba(0, 255, 65, 0.1); color: {ACCENT_GREEN}; 
        padding: 2px 8px; border: 1px solid {ACCENT_GREEN}; 
        font-size: 12px; margin-right: 5px; font-family: 'Share Tech Mono'; 
    }}

    /* HEADERS */
    .section-title {{
        font-family: 'Oswald', sans-serif; font-size: 18px; color: {TEXT_MAIN};
        border-left: 4px solid {ACCENT_GREEN}; padding-left: 10px; margin: 25px 0 10px 0;
        text-transform: uppercase; letter-spacing: 2px;
    }}

    /* --- CUSTOM CALENDAR GRID CSS --- */
    /* Force columns to stick together */
    div[data-testid="column"] {{ padding: 0 !important; margin: 0 !important; }}
    div[data-testid="stHorizontalBlock"] {{ gap: 0 !important; }}
    
    /* Calendar Buttons */
    div.stButton > button {{
        width: 100%; aspect-ratio: 1 / 1;
        border: 1px solid #222; 
        background-color: #0A0A0A;
        color: #666;
        border-radius: 0px; 
        font-family: 'Share Tech Mono', monospace; 
        font-size: 14px;
        margin: 0px !important;
        display: flex; align-items: center; justify-content: center;
        transition: all 0.2s;
    }}
    div.stButton > button:hover {{ border: 1px solid {ACCENT_GREEN}; color: {ACCENT_GREEN}; z-index: 5; background-color: #111; }}
    div.stButton > button:active {{ background-color: {ACCENT_GREEN}; color: #000; }}
    
    /* INPUTS */
    input, textarea, select {{ 
        background: #080808 !important; color: {ACCENT_GREEN} !important; 
        border: 1px solid #333 !important; font-family: 'Share Tech Mono' !important; 
    }}
    
    /* EXPANDER */
    .streamlit-expanderHeader {{ background: {HUD_PANEL} !important; color: {ACCENT_GOLD} !important; border: 1px solid #333; }}
    </style>
""", unsafe_allow_html=True)

# --- 5. DATA LOADING ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["service_account_json"], strict=False), scope)
    client = gspread.authorize(creds)
    sheet = client.open("IRON_GYM_DB").sheet1
    raw_data = sheet.get_all_records()
    
    if raw_data:
        df = pd.DataFrame(raw_data)
        df.columns = df.columns.str.strip()
        
        # Smart Date Search
        date_col = next((c for c in df.columns if "дат" in c.lower() or "date" in c.lower() or "день" in c.lower()), None)
        if date_col:
            df.rename(columns={date_col: 'Date'}, inplace=True)
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
        
        # Numeric cleanup
        if 'Вес (кг)' in df.columns: 
            df['Вес (кг)'] = df['Вес (кг)'].astype(str).str.replace(',', '.')
            df['Вес (кг)'] = pd.to_numeric(df['Вес (кг)'], errors='coerce').fillna(0)
        if 'Сет' not in df.columns: df['Сет'] = "-"
        if 'Упражнение' not in df.columns: df['Упражнение'] = "Unknown"
        df['Muscle'] = df['Упражнение'].apply(detect_muscle)
    else: df = pd.DataFrame()
except: df = pd.DataFrame()

total_xp = len(df)
rank = get_rank_data(total_xp)
trained_dates = set(df['Date'].dt.date) if not df.empty else set()

# --- 6. UI: PROFILE ---
st.markdown(f"""
<div class="hud-card" style="display:flex; align-items:center;">
    <div class="avatar-area"><img src="{AVATAR_URL}" class="avatar-img"></div>
    <div style="flex-grow:1;">
        <div class="user-name">SERGEY</div>
        <div style="margin:5px 0;">
            <span class="stat-badge">EXP: {total_xp}</span>
            <span class="stat-badge">{rank['title']}</span>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width: {rank['progress']}%;"></div></div>
        <div style="font-size:10px; color:#777; text-align:right; font-family:'Share Tech Mono';">NEXT RANK IN: {rank['next_xp']}</div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander(f"{rank['title']} // {rank['abbr']} (OPEN LIST)"):
    for r_min, r_max, title, abbr in FULL_RANK_SYSTEM:
        active = "border-left:2px solid #FFD700; background:rgba(255,215,0,0.05);" if title == rank['title'] else ""
        col = ACCENT_GOLD if title == rank['title'] else "#666"
        img = RANK_IMGS.get(abbr, RANK_IMGS["PV1"])
        st.markdown(f"""<div style="display:flex; align-items:center; padding:10px; border-bottom:1px solid #222; {active}">
            <img src="{img}" style="height:30px; margin-right:15px; object-fit:contain;">
            <div style="flex-grow:1; color:{col}; font-family:'Oswald'; letter-spacing:1px;">{title}</div>
            <div style="color:#444; font-size:12px;">{r_min}</div>
        </div>""", unsafe_allow_html=True)

# --- 7. MENU ---
selected = option_menu(None, ["DASHBOARD", "LOGBOOK", "AI COACH"], icons=["crosshair", "list-task", "robot"], 
    orientation="horizontal", styles={
        "container": {"padding": "0!important", "background": "transparent"}, 
        "nav-link": {"font-family": "Oswald", "color": "#666", "text-transform": "uppercase"}, 
        "nav-link-selected": {"background-color": ACCENT_GREEN, "color": "black"}
    })

# --- 8. DASHBOARD ---
if selected == "DASHBOARD":
    
    # 1. RADAR (HUD STYLE)
    st.markdown('<div class="section-title">BODY ARMOR STATUS</div>', unsafe_allow_html=True)
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    
    if 'cal_date' not in st.session_state: st.session_state.cal_date = None
    
    # FILTER LOGIC
    f_df = df.copy()
    status_text = "ALL SYSTEMS NOMINAL (TOTAL)"
    if st.session_state.cal_date:
        f_df = df[df['Date'].dt.date == st.session_state.cal_date]
        status_text = f"DATA FILTER: {st.session_state.cal_date.strftime('%Y-%m-%d')}"
        if st.button("RESET FILTER"):
            st.session_state.cal_date = None
            st.rerun()
            
    st.markdown(f"<div style='text-align:center; color:{ACCENT_GREEN}; font-family:Share Tech Mono; font-size:12px; margin-bottom:10px; border:1px solid #222; padding:5px;'>{status_text}</div>", unsafe_allow_html=True)

    if not f_df.empty:
        muscles = f_df.groupby('Muscle')['Сет'].count().reset_index()
        target = ["ГРУДЬ", "СПИНА", "НОГИ", "РУКИ", "ПЛЕЧИ", "ПРЕСС"]
        radar = pd.DataFrame({"Muscle": target}).merge(muscles, on="Muscle", how="left").fillna(0)
        
        fig = go.Figure(data=go.Scatterpolar(
            r=radar['Сет'], theta=radar['Muscle'], fill='toself',
            line=dict(color=ACCENT_GREEN, width=2),
            fillcolor='rgba(0, 255, 65, 0.1)',
            marker=dict(size=5, color=ACCENT_GREEN)
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=False, linecolor='#333'),
                angularaxis=dict(linecolor='#333', tickfont=dict(color=TEXT_MAIN, family="Oswald")),
                bgcolor='rgba(0,0,0,0)'
            ),
            showlegend=False, height=250, margin=dict(l=30, r=30, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF')
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
    else: st.info("NO DATA FOUND")
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. CALENDAR (CUSTOM HTML GRID - NO PLUGINS NEEDED)
    st.markdown('<div class="section-title">MISSION TIMELINE</div>', unsafe_allow_html=True)
    st.markdown('<div class="hud-card" style="padding:5px;">', unsafe_allow_html=True)
    
    if 'c_year' not in st.session_state: st.session_state.c_year = date.today().year
    if 'c_month' not in st.session_state: st.session_state.c_month = date.today().month

    def change_m(d):
        m = st.session_state.c_month + d
        y = st.session_state.c_year
        if m>12: m=1; y+=1
        elif m<1: m=12; y-=1
        st.session_state.c_month = m
        st.session_state.c_year = y

    c1, c2, c3 = st.columns([1,4,1])
    with c1: st.button(" < ", on_click=change_m, args=(-1,), key="p")
    with c2: 
        mn = calendar.month_name[st.session_state.c_month].upper()
        st.markdown(f"<div style='text-align:center; font-family:Oswald; font-size:18px; color:{ACCENT_GREEN}; padding-top:10px;'>{mn} {st.session_state.c_year}</div>", unsafe_allow_html=True)
    with c3: st.button(" > ", on_click=change_m, args=(1,), key="n")

    cal_obj = calendar.monthcalendar(st.session_state.c_year, st.session_state.c_month)
    today = date.today()
    
    # Headers
    cols = st.columns(7)
    for i, d in enumerate(["MO","TU","WE","TH","FR","SA","SU"]):
        cols[i].markdown(f"<div style='text-align:center; font-size:10px; color:#555;'>{d}</div>", unsafe_allow_html=True)

    # Grid
    for week in cal_obj:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                curr = date(st.session_state.c_year, st.session_state.c_month, day)
                is_tr = curr in trained_dates
                is_tod = (curr == today)
                
                label = f"{day}"
                if cols[i].button(label, key=f"d_{curr}"):
                    if is_tr: st.session_state.cal_date = curr
                    else: st.session_state.cal_date = None
                    st.rerun()

                # HUD Colors
                bg = "#080808"; fg = "#444"; bdr = "1px solid #1a1a1a"
                
                if is_tr: # Trained = Green Filled
                    bg = ACCENT_GREEN; fg = "#000"; bdr = f"1px solid {ACCENT_GREEN}"
                elif curr < today: # Missed = Dark Red/Brown background
                    bg = "#220000"; fg = "#662222"; bdr = "1px solid #330000"
                
                if is_tod: # Today = Gold Border
                    bdr = f"2px solid {ACCENT_GOLD}"; fg = ACCENT_GOLD
                    if not is_tr: bg = "transparent"

                st.markdown(f"""<script>
                    var buttons = window.parent.document.querySelectorAll('div[data-testid="column"] button');
                    for (var i = 0; i < buttons.length; i++) {{
                        if (buttons[i].innerText === "{label}") {{
                            buttons[i].style.backgroundColor = "{bg}";
                            buttons[i].style.color = "{fg}";
                            buttons[i].style.border = "{bdr}";
                        }}
                    }}
                </script>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 3. TABLE
    st.markdown('<div class="section-title">LOG ENTRIES</div>', unsafe_allow_html=True)
    if not f_df.empty:
        show = f_df.sort_values(by=['Date', 'Сет'], ascending=[False, True]).copy()
        show['Date'] = show['Date'].dt.strftime('%d.%m')
        st.dataframe(show[['Date', 'Сет', 'Упражнение', 'Вес (кг)', 'Повт']], use_container_width=True, hide_index=True)

# --- LOGBOOK ---
elif selected == "LOGBOOK":
    st.markdown('<div class="section-title">NEW MISSION ENTRY</div>', unsafe_allow_html=True)
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    with st.form("add"):
        d = st.date_input("DATE")
        c1, c2 = st.columns([1,2])
        with c1: s = st.text_input("SET", "1")
        with c2: e = st.text_input("EXERCISE")
        c3, c4, c5 = st.columns(3)
        with c3: p = st.number_input("REPS", 1)
        with c4: w = st.number_input("WEIGHT", step=2.5)
        with c5: r = st.number_input("RPE", 1) # Using 'r' as extra field if needed
        if st.form_submit_button("COMMIT DATA"):
            try:
                sheet.append_row([str(d), s, e, p, w, r, w*r, "", ""])
                st.success("DATA SECURED")
                st.rerun()
            except Exception as ex: st.error(f"ERR: {ex}")
    st.markdown('</div>', unsafe_allow_html=True)

elif selected == "AI COACH":
    st.markdown('<div class="section-title">TACTICAL AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    if "msg" not in st.session_state: st.session_state.msg = []
    for m in st.session_state.msg: st.chat_message(m["role"]).markdown(m["content"])
    if q := st.chat_input("Command..."):
        st.session_state.msg.append({"role": "user", "content": q})
        st.chat_message("user").markdown(q)
        try:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
            ans = model.generate_content(f"You are an Elite Tactical Fitness Instructor. Rank: {rank['title']}. Answer briefly and sternly. Q: {q}").text
            st.chat_message("assistant").markdown(ans)
            st.session_state.msg.append({"role": "assistant", "content": ans})
        except: st.error("COMMS OFFLINE")
    st.markdown('</div>', unsafe_allow_html=True)
