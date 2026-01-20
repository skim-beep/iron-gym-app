import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from streamlit_option_menu import option_menu
import calendar

# --- 1. SETTINGS ---
st.set_page_config(
    page_title="IronGym",
    page_icon="",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. APPLE COLORS ---
IOS_BG = "#000000"
IOS_CARD = "#1C1C1E"         # Secondary System Fill
IOS_BTN_BG = "#2C2C2E"       # Tertiary System Fill
IOS_BLUE = "#0A84FF"
IOS_TEXT = "#FFFFFF"
IOS_SUBTEXT = "#8E8E93"

AVATAR_URL = "https://i.ibb.co.com/TDhQXVTR/unnamed-3.jpg"
USER_BIRTHDAY = date(1985, 2, 20)
USER_WEIGHT_CURRENT = 85.0 

# --- 3. ASSETS ---
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
    (0, 24, "Recruit", "PV1"), (25, 49, "Private", "PV2"), (50, 99, "PFC", "PFC"),
    (100, 149, "Specialist", "SPC"), (150, 199, "Sergeant", "SGT"), (200, 299, "Staff Sgt", "SSG"),
    (300, 399, "SFC", "SFC"), (400, 499, "Master Sgt", "MSG"), (500, 649, "1st Sgt", "1SG"),
    (650, 799, "Sgt Major", "SGM"), (800, 999, "2nd Lt", "2LT"), (1000, 1499, "1st Lt", "1LT"),
    (1500, 1999, "Captain", "CPT"), (2000, 2999, "Major", "MAJ"), (3000, 3999, "Lt Col", "LTC"),
    (4000, 4999, "Colonel", "COL"), (5000, 5999, "Brig Gen", "BG"), (6000, 7999, "Maj Gen", "MG"),
    (8000, 9999, "Lt Gen", "LTG"), (10000, 24999, "General", "GEN"), (25000, 999999, "Gen of Army", "GA")
]

def get_rank_data(xp):
    for r_min, r_max, title, abbr in FULL_RANK_SYSTEM:
        if r_min <= xp <= r_max:
            needed = r_max - r_min + 1
            current = xp - r_min
            img = RANK_IMGS.get(abbr, RANK_IMGS["PV1"])
            return {"title": title, "abbr": abbr, "icon": img, "progress": int((current/needed)*100), "next_xp": needed-current}
    return {"title": "Gen of Army", "abbr": "GA", "icon": RANK_IMGS["GA"], "progress": 100, "next_xp": 0}

def detect_muscle(ex):
    ex = str(ex).lower()
    if any(x in ex for x in ['жим', 'chest', 'отжимания']): return "ГРУДЬ"
    if any(x in ex for x in ['тяга', 'спина', 'back', 'row']): return "СПИНА"
    if any(x in ex for x in ['присед', 'ноги', 'legs']): return "НОГИ"
    if any(x in ex for x in ['бицепс', 'трицепс', 'arms']): return "РУКИ"
    if any(x in ex for x in ['плечи', 'махи', 'shouder']): return "ПЛЕЧИ"
    if any(x in ex for x in ['пресс', 'abs', 'core']): return "ПРЕСС"
    return "ОБЩЕЕ"

# --- 4. CSS (iOS WIDGET STYLE) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: -apple-system, BlinkMacSystemFont, "Inter", sans-serif;
    }}

    .stApp {{
        background-color: {IOS_BG};
        color: {IOS_TEXT};
    }}
    
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* IOS CARD CONTAINER */
    .ios-card {{
        background-color: {IOS_CARD};
        border-radius: 22px;
        padding: 20px;
        margin-bottom: 24px;
        border: 1px solid #2C2C2E;
    }}

    /* PROFILE */
    .profile-header {{ display: flex; align-items: center; gap: 16px; }}
    .avatar-img {{
        width: 60px; height: 60px; border-radius: 50%; object-fit: cover;
    }}
    .user-info h2 {{ margin: 0; font-size: 20px; font-weight: 700; color: white; }}
    .user-info p {{ margin: 0; font-size: 14px; color: {IOS_SUBTEXT}; }}
    
    .progress-track {{
        width: 100%; height: 6px; background: #3a3a3c; border-radius: 10px; margin-top: 16px;
    }}
    .progress-fill {{
        height: 100%; background: {IOS_BLUE}; border-radius: 10px;
    }}

    /* SECTION TITLES */
    .section-header {{
        font-size: 22px; font-weight: 700; color: white; margin: 30px 0 16px 0;
    }}

    /* CALENDAR WIDGET GRID (FIX) */
    /* This creates the dark card effect for calendar */
    div[data-testid="stHorizontalBlock"] {{
        background-color: {IOS_CARD};
        border-radius: 16px;
        padding: 4px;
    }}
    
    div[data-testid="column"] {{ padding: 2px !important; }}
    
    /* Calendar Buttons */
    div.stButton > button {{
        width: 100%; aspect-ratio: 1/1;
        background-color: transparent; /* Transparent to blend with card */
        border: none;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        font-size: 16px;
    }}
    div.stButton > button:hover {{ background-color: #3A3A3C; }}
    
    /* INPUTS */
    div[data-baseweb="input"] {{
        background-color: {IOS_BTN_BG} !important;
        border-radius: 10px !important;
        border: none !important;
    }}
    input {{ color: white !important; font-size: 16px; }}
    
    /* SEGMENTED CONTROL FIX */
    .nav-link-selected {{
        background-color: #636366 !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    }}
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
        date_col = next((c for c in df.columns if "дат" in c.lower() or "date" in c.lower()), None)
        if date_col:
            df.rename(columns={date_col: 'Date'}, inplace=True)
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
        if 'Вес (кг)' in df.columns: 
            df['Вес (кг)'] = pd.to_numeric(df['Вес (кг)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
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
<div class="ios-card">
    <div class="profile-header">
        <img src="{AVATAR_URL}" class="avatar-img">
        <div class="user-info">
            <h2>Sergey</h2>
            <p>{rank['title']} • {total_xp} XP</p>
        </div>
        <div style="flex-grow:1;"></div>
        <img src="{rank['icon']}" style="height:45px; object-fit:contain;">
    </div>
    <div class="progress-track">
        <div class="progress-fill" style="width: {rank['progress']}%;"></div>
    </div>
    <div style="margin-top:8px; display:flex; justify-content:space-between; font-size:13px; color:#8E8E93;">
        <span>Current Rank</span>
        <span>{rank['next_xp']} XP to next</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 7. NAVIGATION (SEGMENTED CONTROL) ---
selected = option_menu(None, ["Summary", "Logbook", "Coach"], 
    icons=["grid.fill", "list.bullet", "waveform"], 
    default_index=0, orientation="horizontal",
    styles={
        "container": {"padding": "4px", "background-color": "#1C1C1E", "border-radius": "12px", "margin-bottom": "25px"},
        "icon": {"color": "#8E8E93", "font-size": "14px"}, 
        "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", "color": "#8E8E93", "font-weight": "600"},
        "nav-link-selected": {"background-color": "#636366", "color": "#FFF", "border-radius": "10px"},
    }
)

if selected == "Summary":
    
    # --- CALENDAR WIDGET ---
    st.markdown('<div class="section-header">Calendar</div>', unsafe_allow_html=True)
    
    # State
    if 'c_year' not in st.session_state: st.session_state.c_year = date.today().year
    if 'c_month' not in st.session_state: st.session_state.c_month = date.today().month
    if 'cal_date' not in st.session_state: st.session_state.cal_date = None

    def change_m(d):
        m = st.session_state.c_month + d
        y = st.session_state.c_year
        if m>12: m=1; y+=1
        elif m<1: m=12; y-=1
        st.session_state.c_month = m
        st.session_state.c_year = y

    # CONTAINER CARD START
    with st.container():
        # Header (Month)
        c1, c2, c3 = st.columns([1,4,1])
        with c1: st.button("‹", on_click=change_m, args=(-1,), key="p")
        with c2: 
            mn = calendar.month_name[st.session_state.c_month]
            st.markdown(f"<div style='text-align:center; font-weight:700; font-size:18px; color:white; padding-top:8px;'>{mn} {st.session_state.c_year}</div>", unsafe_allow_html=True)
        with c3: st.button("›", on_click=change_m, args=(1,), key="n")

        # Days of Week
        cols = st.columns(7)
        for i, d in enumerate(["M","T","W","T","F","S","S"]):
            cols[i].markdown(f"<div style='text-align:center; font-size:13px; color:#8E8E93; font-weight:600; margin-bottom:10px;'>{d}</div>", unsafe_allow_html=True)

        # Calendar Grid
        cal_obj = calendar.monthcalendar(st.session_state.c_year, st.session_state.c_month)
        today = date.today()

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

                    # Styling Logic
                    bg = "transparent"
                    fg = "white"
                    border = "none"
                    
                    if is_tr: # Trained -> Green Circle
                        bg = "#30D158" 
                        fg = "black"
                    elif is_tod: # Today -> Blue Text
                        fg = "#0A84FF"
                        bg = "#2C2C2E"

                    st.markdown(f"""<script>
                        var buttons = window.parent.document.querySelectorAll('div[data-testid="column"] button');
                        for (var i = 0; i < buttons.length; i++) {{
                            if (buttons[i].innerText === "{label}") {{
                                buttons[i].style.backgroundColor = "{bg}";
                                buttons[i].style.color = "{fg}";
                                buttons[i].style.borderRadius = "50%"; /* Round Buttons */
                            }}
                        }}
                    </script>""", unsafe_allow_html=True)
    # CONTAINER CARD END

    # --- RADAR ---
    st.markdown('<div class="section-header">Stats</div>', unsafe_allow_html=True)
    st.markdown('<div class="ios-card">', unsafe_allow_html=True)
    
    f_df = df.copy()
    filter_txt = "Lifetime"
    if st.session_state.cal_date:
        f_df = df[df['Date'].dt.date == st.session_state.cal_date]
        filter_txt = f"{st.session_state.cal_date.strftime('%b %d')}"
        if st.button("Clear Filter", use_container_width=True):
            st.session_state.cal_date = None
            st.rerun()
            
    st.markdown(f"<div style='text-align:center; font-size:14px; color:#8E8E93; margin-bottom:10px;'>{filter_txt}</div>", unsafe_allow_html=True)

    if not f_df.empty:
        muscles = f_df.groupby('Muscle')['Сет'].count().reset_index()
        target = ["ГРУДЬ", "СПИНА", "НОГИ", "РУКИ", "ПЛЕЧИ", "ПРЕСС"]
        radar = pd.DataFrame({"Muscle": target}).merge(muscles, on="Muscle", how="left").fillna(0)
        
        fig = go.Figure(data=go.Scatterpolar(
            r=radar['Сет'], theta=radar['Muscle'], fill='toself',
            line=dict(color=IOS_BLUE, width=2),
            fillcolor='rgba(10, 132, 255, 0.2)',
            marker=dict(size=4)
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=False, linecolor='#333'),
                angularaxis=dict(linecolor='#333', tickfont=dict(color="#8E8E93", size=11, weight="bold")),
                bgcolor='rgba(0,0,0,0)'
            ),
            showlegend=False, height=280, margin=dict(l=30, r=30, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)', font=dict(family="-apple-system")
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
    else: st.info("No data.")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- LIST ---
    if not f_df.empty:
        st.markdown('<div class="section-header">Recent</div>', unsafe_allow_html=True)
        show = f_df.sort_values(by=['Date', 'Сет'], ascending=[False, True]).copy()
        show['Date'] = show['Date'].dt.strftime('%d.%m')
        st.dataframe(show[['Date', 'Сет', 'Упражнение', 'Вес (кг)', 'Повт']], use_container_width=True, hide_index=True)

elif selected == "Logbook":
    st.markdown('<div class="section-header">New Entry</div>', unsafe_allow_html=True)
    st.markdown('<div class="ios-card">', unsafe_allow_html=True)
    with st.form("add"):
        d = st.date_input("Date")
        c1, c2 = st.columns([1,2])
        with c1: s = st.text_input("Set", "1")
        with c2: e = st.text_input("Exercise")
        c3, c4, c5 = st.columns(3)
        with c3: p = st.number_input("Reps", 1)
        with c4: w = st.number_input("Weight", step=2.5)
        with c5: r = st.number_input("RPE", 1)
        if st.form_submit_button("Save", use_container_width=True):
            try:
                sheet.append_row([str(d), s, e, p, w, r, w*r, "", ""])
                st.success("Saved")
                st.rerun()
            except Exception as ex: st.error(f"Error: {ex}")
    st.markdown('</div>', unsafe_allow_html=True)

elif selected == "Coach":
    st.markdown('<div class="section-header">AI Coach</div>', unsafe_allow_html=True)
    st.markdown('<div class="ios-card">', unsafe_allow_html=True)
    if "msg" not in st.session_state: st.session_state.msg = []
    for m in st.session_state.msg: st.chat_message(m["role"]).markdown(m["content"])
    if q := st.chat_input("Ask..."):
        st.session_state.msg.append({"role": "user", "content": q})
        st.chat_message("user").markdown(q)
        try:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
            ans = model.generate_content(f"Role: Army Drill Sergeant. User Rank: {rank['title']}. Q: {q}").text
            st.chat_message("assistant").markdown(ans)
            st.session_state.msg.append({"role": "assistant", "content": ans})
        except: st.error("Offline")
    st.markdown('</div>', unsafe_allow_html=True)
