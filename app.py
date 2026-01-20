import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from streamlit_option_menu import option_menu
import calendar

# --- 1. НАСТРОЙКИ ---
st.set_page_config(
    page_title="IRON GYM OS",
    page_icon="🦅",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- 2. COLORS (NEON CYBER) ---
COLOR_BG = "#09090b"           # Deep Black/Zinc
COLOR_CARD = "rgba(24, 24, 27, 0.6)" # Translucent Dark
COLOR_ACCENT = "#22c55e"       # Modern Neon Green
COLOR_TEXT_MAIN = "#fafafa"
COLOR_TEXT_DIM = "#a1a1aa"
COLOR_BORDER = "rgba(255, 255, 255, 0.1)"

AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. ICONS (REALISTIC) ---
RANK_IMGS = {
    "PV1": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/U.S._Army_E-1_insignia.jpg/100px-U.S._Army_E-1_insignia.jpg",
    "PV2": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/US_Army_E2_insignia.jpg/100px-US_Army_E2_insignia.jpg",
    "PFC": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/US_Army_E3_insignia.jpg/100px-US_Army_E3_insignia.jpg",
    "SPC": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/US_Army_E4_insignia.jpg/100px-US_Army_E4_insignia.jpg",
    "SGT": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/US_Army_E5_insignia.jpg/100px-US_Army_E5_insignia.jpg",
    "SSG": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/US_Army_E6_insignia.jpg/100px-US_Army_E6_insignia.jpg",
    "SFC": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/US_Army_E7_insignia.jpg/100px-US_Army_E7_insignia.jpg",
    "MSG": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/US_Army_E8_MSG_insignia.jpg/100px-US_Army_E8_MSG_insignia.jpg",
    "1SG": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/US_Army_E8_1SG_insignia.jpg/100px-US_Army_E8_1SG_insignia.jpg",
    "SGM": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/US_Army_E9_SGM_insignia.jpg/100px-US_Army_E9_SGM_insignia.jpg",
    "2LT": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/US-O1_insignia.svg/50px-US-O1_insignia.svg.png",
    "1LT": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/US-O2_insignia.svg/50px-US-O2_insignia.svg.png",
    "CPT": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/US-O3_insignia.svg/50px-US-O3_insignia.svg.png",
    "MAJ": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/US-O4_insignia.svg/50px-US-O4_insignia.svg.png",
    "LTC": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/US-O5_insignia.svg/50px-US-O5_insignia.svg.png",
    "COL": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/US-O6_insignia.svg/100px-US-O6_insignia.svg.png",
    "BG": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Army-USA-OF-07.svg/100px-Army-USA-OF-07.svg.png",
    "MG": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Army-USA-OF-08.svg/100px-Army-USA-OF-08.svg.png",
    "LTG": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Army-USA-OF-09.svg/100px-Army-USA-OF-09.svg.png",
    "GEN": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Army-USA-OF-10.svg/100px-Army-USA-OF-10.svg.png",
    "GA": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Army-USA-OF-11.svg/100px-Army-USA-OF-11.svg.png"
}

FULL_RANK_SYSTEM = [
    (0, 24, "RECRUIT", "PV1"), (25, 49, "PRIVATE", "PV2"), (50, 99, "PFC", "PFC"),
    (100, 149, "SPECIALIST", "SPC"), (150, 199, "SERGEANT", "SGT"), (200, 299, "STAFF SGT", "SSG"),
    (300, 399, "SGT 1ST CLASS", "SFC"), (400, 499, "MASTER SGT", "MSG"), (500, 649, "1ST SGT", "1SG"),
    (650, 799, "SGT MAJOR", "SGM"), (800, 999, "2ND LIEUTENANT", "2LT"), (1000, 1499, "1ST LIEUTENANT", "1LT"),
    (1500, 1999, "CAPTAIN", "CPT"), (2000, 2999, "MAJOR", "MAJ"), (3000, 3999, "LT COLONEL", "LTC"),
    (4000, 4999, "COLONEL", "COL"), (5000, 5999, "BRIG GENERAL", "BG"), (6000, 7999, "MAJOR GEN", "MG"),
    (8000, 9999, "LT GENERAL", "LTG"), (10000, 24999, "GENERAL", "GEN"), (25000, 999999, "GEN OF ARMY", "GA")
]

def get_rank_data(xp):
    for r_min, r_max, title, abbr in FULL_RANK_SYSTEM:
        if r_min <= xp <= r_max:
            needed = r_max - r_min + 1
            current = xp - r_min
            img = RANK_IMGS.get(abbr, RANK_IMGS["PV1"])
            return {"title": title, "abbr": abbr, "icon": img, "progress": int((current/needed)*100), "next_xp": needed-current}
    return {"title": "GEN OF ARMY", "abbr": "GA", "icon": RANK_IMGS["GA"], "progress": 100, "next_xp": 0}

def detect_muscle(ex):
    ex = str(ex).lower()
    if any(x in ex for x in ['жим', 'chest', 'отжимания']): return "ГРУДЬ"
    if any(x in ex for x in ['тяга', 'спина', 'back', 'row']): return "СПИНА"
    if any(x in ex for x in ['присед', 'ноги', 'legs']): return "НОГИ"
    if any(x in ex for x in ['бицепс', 'трицепс', 'arms']): return "РУКИ"
    if any(x in ex for x in ['плечи', 'махи', 'shouder']): return "ПЛЕЧИ"
    if any(x in ex for x in ['пресс', 'abs', 'core']): return "ПРЕСС"
    return "ОБЩЕЕ"

# --- 4. MODERN CSS (GLASSMORPHISM) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

    /* BASE RESET */
    .stApp {{
        background: radial-gradient(circle at top, #18181b, #000000);
        color: {COLOR_TEXT_MAIN};
        font-family: 'Inter', sans-serif;
    }}
    
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* MODERN GLASS CARD */
    .glass-card {{
        background: {COLOR_CARD};
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid {COLOR_BORDER};
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 24px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }}
    
    /* TYPOGRAPHY */
    h1, h2, h3, .section-title {{
        font-family: 'Rajdhani', sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 700;
        color: {COLOR_TEXT_MAIN};
    }}
    
    .section-title {{
        font-size: 14px;
        color: {COLOR_ACCENT};
        margin-bottom: 12px;
        opacity: 0.9;
    }}

    /* PROFILE */
    .profile-container {{ display: flex; align-items: center; gap: 20px; }}
    .avatar-frame {{
        width: 80px; height: 80px;
        border-radius: 20px;
        background: url('{AVATAR_URL}') no-repeat center/cover;
        border: 2px solid {COLOR_ACCENT};
        box-shadow: 0 0 20px rgba(34, 197, 94, 0.2);
    }}
    .rank-info {{ flex-grow: 1; }}
    .user-name {{ font-family: 'Rajdhani', sans-serif; font-size: 28px; line-height: 1; margin-bottom: 5px; }}
    
    /* PROGRESS BAR */
    .xp-bar-bg {{ width: 100%; height: 6px; background: rgba(255,255,255,0.1); border-radius: 10px; overflow: hidden; margin-top: 10px; }}
    .xp-bar-fill {{ height: 100%; background: {COLOR_ACCENT}; border-radius: 10px; }}
    
    /* BADGES */
    .badge {{
        background: rgba(34, 197, 94, 0.1);
        color: {COLOR_ACCENT};
        border: 1px solid rgba(34, 197, 94, 0.2);
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 600;
        display: inline-block;
        margin-right: 5px;
    }}

    /* CUSTOM CALENDAR BUTTONS */
    div.stButton > button {{
        width: 100%; aspect-ratio: 1 / 1;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.05);
        color: {COLOR_TEXT_DIM};
        border-radius: 12px; /* Smooth corners */
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    div.stButton > button:hover {{
        background: rgba(34, 197, 94, 0.1);
        border-color: {COLOR_ACCENT};
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(34, 197, 94, 0.15);
    }}
    
    /* INPUTS STYLING */
    div[data-baseweb="input"] {{
        background-color: rgba(255,255,255,0.03) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }}
    input {{ color: white !important; }}
    
    /* EXPANDER */
    .streamlit-expanderHeader {{
        background: transparent !important;
        color: {COLOR_TEXT_DIM} !important;
        font-family: 'Rajdhani', sans-serif !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px;
    }}
    
    /* REMOVE PADDING FROM COLUMNS FOR GRID */
    div[data-testid="column"] {{ padding: 2px !important; }}
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
        date_col = next((c for c in df.columns if "дат" in c.lower() or "date" in c.lower() or "день" in c.lower()), None)
        if date_col:
            df.rename(columns={date_col: 'Date'}, inplace=True)
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
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

# --- 6. UI: MODERN PROFILE ---
st.markdown(f"""
<div class="glass-card">
    <div class="profile-container">
        <div class="avatar-frame"></div>
        <div class="rank-info">
            <div class="user-name">SERGEY</div>
            <div style="display:flex; align-items:center;">
                <span class="badge">XP: {total_xp}</span>
                <span class="badge">{rank['title']}</span>
            </div>
            <div class="xp-bar-bg"><div class="xp-bar-fill" style="width: {rank['progress']}%;"></div></div>
            <div style="font-size:10px; color:#666; margin-top:5px; text-align:right;">NEXT RANK IN: {rank['next_xp']} XP</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander(f"{rank['title']} // {rank['abbr']} (VIEW RANKS)"):
    for r_min, r_max, title, abbr in FULL_RANK_SYSTEM:
        active = f"background:rgba(34,197,94,0.1); border:1px solid {COLOR_ACCENT}; border-radius:10px;" if title == rank['title'] else ""
        color = "white" if title == rank['title'] else "#666"
        img = RANK_IMGS.get(abbr, RANK_IMGS["PV1"])
        st.markdown(f"""<div style="display:flex; align-items:center; padding:10px; margin-bottom:5px; {active}">
            <img src="{img}" style="height:35px; width:auto; margin-right:15px; object-fit:contain;">
            <div style="flex-grow:1; color:{color}; font-family:'Rajdhani'; font-weight:700; font-size:16px;">{title}</div>
            <div style="color:#444; font-size:12px; font-family:'Inter';">{r_min}</div>
        </div>""", unsafe_allow_html=True)

selected = option_menu(None, ["DASHBOARD", "LOGBOOK", "AI COACH"], icons=["grid", "plus-square", "cpu"], 
    orientation="horizontal", styles={
        "container": {"padding": "0!important", "background": "transparent", "margin-bottom":"20px"}, 
        "nav-link": {"font-family": "Rajdhani", "font-weight":"bold", "color": "#777", "font-size":"14px"}, 
        "nav-link-selected": {"background-color": COLOR_ACCENT, "color": "black", "border-radius":"10px"}
    })

if selected == "DASHBOARD":
    
    # 1. RADAR
    st.markdown('<div class="section-title">PERFORMANCE METRICS</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    if 'cal_date' not in st.session_state: st.session_state.cal_date = None
    
    f_df = df.copy()
    info_txt = "TOTAL HISTORY"
    if st.session_state.cal_date:
        f_df = df[df['Date'].dt.date == st.session_state.cal_date]
        info_txt = f"DATE: {st.session_state.cal_date.strftime('%d.%m.%Y')}"
        if st.button("CLEAR FILTER", use_container_width=True):
            st.session_state.cal_date = None
            st.rerun()
            
    st.markdown(f"<div style='text-align:center; color:{COLOR_ACCENT}; font-size:12px; font-weight:bold; margin-bottom:10px; letter-spacing:1px;'>{info_txt}</div>", unsafe_allow_html=True)

    if not f_df.empty:
        muscles = f_df.groupby('Muscle')['Сет'].count().reset_index()
        target = ["ГРУДЬ", "СПИНА", "НОГИ", "РУКИ", "ПЛЕЧИ", "ПРЕСС"]
        radar = pd.DataFrame({"Muscle": target}).merge(muscles, on="Muscle", how="left").fillna(0)
        
        fig = go.Figure(data=go.Scatterpolar(
            r=radar['Сет'], theta=radar['Muscle'], fill='toself',
            line=dict(color=COLOR_ACCENT, width=3), fillcolor='rgba(34, 197, 94, 0.1)', marker=dict(size=6, color="white")
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=False, linecolor='rgba(255,255,255,0.1)'),
                angularaxis=dict(linecolor='rgba(255,255,255,0.1)', tickfont=dict(color=COLOR_TEXT_DIM, family="Inter", size=10)),
                bgcolor='rgba(0,0,0,0)'
            ),
            showlegend=False, height=260, margin=dict(l=30, r=30, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white')
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
    else: st.info("No data available.")
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. CALENDAR (MODERN GRID)
    st.markdown('<div class="section-title">ACTIVITY LOG</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card" style="padding:10px;">', unsafe_allow_html=True)
    
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
    with c1: st.button("‹", on_click=change_m, args=(-1,), key="p")
    with c2: 
        mn = calendar.month_name[st.session_state.c_month].upper()
        st.markdown(f"<div style='text-align:center; font-family:Rajdhani; font-weight:700; font-size:18px; color:white; padding-top:10px;'>{mn} {st.session_state.c_year}</div>", unsafe_allow_html=True)
    with c3: st.button("›", on_click=change_m, args=(1,), key="n")

    cal_obj = calendar.monthcalendar(st.session_state.c_year, st.session_state.c_month)
    today = date.today()
    
    cols = st.columns(7)
    for i, d in enumerate(["M","T","W","T","F","S","S"]):
        cols[i].markdown(f"<div style='text-align:center; font-size:10px; color:#555; margin-bottom:5px;'>{d}</div>", unsafe_allow_html=True)

    for week in cal_obj:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0: cols[i].write("")
            else:
                curr = date(st.session_state.c_year, st.session_state.c_month, day)
                is_tr = curr in trained_dates
                is_tod = (curr == today)
                label = f"{day}"
                if cols[i].button(label, key=f"d_{curr}"):
                    if is_tr: st.session_state.cal_date = curr
                    else: st.session_state.cal_date = None
                    st.rerun()

                # Modern Styles
                bg = "rgba(255,255,255,0.02)"; fg = "#555"; bdr = "1px solid rgba(255,255,255,0.05)"
                
                if is_tr: # Trained = Green Glow
                    bg = "rgba(34, 197, 94, 0.2)"; fg = "white"; bdr = f"1px solid {COLOR_ACCENT}"
                elif curr < today: # Missed = Red tint
                    bg = "rgba(239, 68, 68, 0.1)"; fg = "#7f1d1d"; bdr = "1px solid rgba(239, 68, 68, 0.2)"
                
                if is_tod: # Today = White Border
                    bdr = "1px solid white"; fg = "white"; 
                    if not is_tr: bg = "transparent"

                st.markdown(f"""<script>
                    var buttons = window.parent.document.querySelectorAll('div[data-testid="column"] button');
                    for (var i = 0; i < buttons.length; i++) {{
                        if (buttons[i].innerText === "{label}") {{
                            buttons[i].style.background = "{bg}";
                            buttons[i].style.color = "{fg}";
                            buttons[i].style.border = "{bdr}";
                            if ("{is_tr}" == "True") {{ buttons[i].style.boxShadow = "0 0 10px rgba(34, 197, 94, 0.2)"; }}
                        }}
                    }}
                </script>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">RECENT LOGS</div>', unsafe_allow_html=True)
    if not f_df.empty:
        show = f_df.sort_values(by=['Date', 'Сет'], ascending=[False, True]).copy()
        show['Date'] = show['Date'].dt.strftime('%d.%m')
        st.dataframe(show[['Date', 'Сет', 'Упражнение', 'Вес (кг)', 'Повт']], use_container_width=True, hide_index=True)

elif selected == "LOGBOOK":
    st.markdown('<div class="section-title">NEW ENTRY</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    with st.form("add"):
        d = st.date_input("DATE")
        c1, c2 = st.columns([1,2])
        with c1: s = st.text_input("SET", "1")
        with c2: e = st.text_input("EXERCISE")
        c3, c4, c5 = st.columns(3)
        with c3: p = st.number_input("REPS", 1)
        with c4: w = st.number_input("WEIGHT", step=2.5)
        with c5: r = st.number_input("RPE", 1)
        if st.form_submit_button("SAVE DATA", use_container_width=True):
            try:
                sheet.append_row([str(d), s, e, p, w, r, w*r, "", ""])
                st.success("SAVED")
                st.rerun()
            except Exception as ex: st.error(f"ERR: {ex}")
    st.markdown('</div>', unsafe_allow_html=True)

elif selected == "AI COACH":
    st.markdown('<div class="section-title">NEURAL LINK</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    if "msg" not in st.session_state: st.session_state.msg = []
    for m in st.session_state.msg: st.chat_message(m["role"]).markdown(m["content"])
    if q := st.chat_input("Ask Coach..."):
        st.session_state.msg.append({"role": "user", "content": q})
        st.chat_message("user").markdown(q)
        try:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
            ans = model.generate_content(f"Tactical Coach. Rank: {rank['title']}. Brief & Strict. Q: {q}").text
            st.chat_message("assistant").markdown(ans)
            st.session_state.msg.append({"role": "assistant", "content": ans})
        except: st.error("OFFLINE")
    st.markdown('</div>', unsafe_allow_html=True)
