import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import os

# --- KONFIGURACIJA ---
GOOGLE_API_KEY = "AIzaSyCtPv1jjWxjwjyi2AedIb-jKDjpzdHaSyY"
genai.configure(api_key=GOOGLE_API_KEY)

# Model koji se pokazao kao najstabilniji za tvoj nalog
model = genai.GenerativeModel('gemini-flash-latest')

DATA_FILE = "podaci_logistika.json"

st.set_page_config(page_title="AI Logističar Srbija", layout="wide", page_icon="🚛")

# --- FUNKCIJE ZA PODATKE ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {"vozila": [], "dostave": [], "baza": "Beograd", "gorivo": 200}
    return {"vozila": [], "dostave": [], "baza": "Beograd", "gorivo": 200}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

if 'app_data' not in st.session_state:
    st.session_state.app_data = load_data()

# --- HEADER ---
st.title("🚚 Pametni AI Dispečer: Srbija")
st.markdown("Automatska kalkulacija kilometraže, težine i vremena putovanja.")

# --- SIDEBAR: KONFIGURACIJA ---
with st.sidebar:
    st.header("⚙️ Osnovna podešavanja")
    
    st.session_state.app_data["baza"] = st.text_input("Početna tačka (Baza)", value=st.session_state.app_data.get("baza", "Beograd"))
    st.session_state.app_data["gorivo"] = st.number_input("Cena goriva (RSD/L)", value=st.session_state.app_data.get("gorivo", 200))
    
    st.markdown("---")
    st.header("🚛 Garaža (Vozni park)")
    with st.form("dodaj_vozilo"):
        ime_v = st.text_input("Naziv vozila", placeholder="npr. Mercedes Atego")
        potrosnja_v = st.number_input("Potrošnja (L/100km)", min_value=1.0, value=15.0)
        kapacitet_p = st.number_input("Kapacitet (Paleta)", min_value=1, value=15)
        nosivost_kg = st.number_input("Nosivost (kg)", min_value=1, value=5000)
        submit_v = st.form_submit_button("Dodaj vozilo")
        
        if submit_v and ime_v:
            new_v = {"ime": ime_v, "potrosnja": potrosnja_v, "palete": kapacitet_p, "nosivost": nosivost_kg}
            st.session_state.app_data["vozila"].append(new_v)
            save_data(st.session_state.app_data)
            st.success(f"Vozilo {ime_v} dodato!")

    if st.session_state.app_data["vozila"]:
        st.write("### Trenutna flota:")
        for i, v in enumerate(st.session_state.app_data["vozila"]):
            st.info(f"**{v['ime']}**\n\n{v['palete']} pal | {v['nosivost']}kg | {v['potrosnja']}L/100km")
        if st.button("🗑️ Obriši sva vozila"):
            st.session_state.app_data["vozila"] = []
            save_data(st.session_state.app_data)
            st.rerun()

# --- GLAVNI EKRAN: DESTINACIJE ---
col_u1, col_u2 = st.columns([1, 2])

with col_u1:
    st.header("📍 Nova Destinacija")
    with st.container(border=True):
        grad = st.text_input("Grad istovara", placeholder="npr. Kragujevac")
        # MIN_VALUE JE SADA 0 DA NE BI BILO OBAVEZNO
        p_dostava = st.number_input("Broj paleta (opciono)", min_value=0, value=0)
        t_dostava = st.number_input("Težina robe (kg)", min_value=1, value=500)
        
        if st.button("➕ Dodaj u plan"):
            if grad:
                new_d = {"grad": grad, "palete": p_dostava, "tezina": t_dostava}
                st.session_state.app_data["dostave"].append(new_d)
                save_data(st.session_state.app_data)
                st.toast(f"Dodato: {grad}")
                st.rerun()
            else:
                st.warning("Unesite grad!")

with col_u2:
    st.header("📝 Lista isporuka")
    if st.session_state.app_data["dostave"]:
        # Prikazujemo "N/A" ako je broj paleta 0 radi lepšeg izgleda
        df_show = pd.DataFrame(st.session_state.app_data["dostave"])
        st.table(df_show)
        if st.button("🗑️ Obriši sve dostave"):
            st.session_state.app_data["dostave"] = []
            save_data(st.session_state.app_data)
            st.rerun()
    else:
        st.write("Nema unetih destinacija.")

st.markdown("---")

# --- LOGIKA OPTIMIZACIJE ---
if st.button("🚀 GENERIŠI OPTIMALNI PLAN RUTA", use_container_width=True):
    if not st.session_state.app_data["vozila"] or not st.session_state.app_data["dostave"]:
        st.error("Prvo unesi barem jedno vozilo i jednu destinaciju!")
    else:
        with st.spinner("AI planira rute, računa kilometre i vreme putovanja..."):
            
            prompt = f"""
            Ti si profesionalni logistički dispečer za Srbiju.
            POČETNA TAČKA (BAZA): {st.session_state.app_data['baza']}
            CENA GORIVA: {st.session_state.app_data['gorivo']} RSD/L.
            
            VOZILA: {st.session_state.app_data['vozila']}
            DOSTAVE: {st.session_state.app_data['dostave']}
            
            ZADATAK:
            1. Proceni kilometražu i VREME PUTOVANJA (sate) uzimajući u obzir realne uslove na putevima u Srbiji za kamione.
            2. Ako je broj paleta 0, smatraj da ta roba ne zauzima paletna mesta već samo doprinosi ukupnoj težini.
            3. Napravi optimalne rute: ne dozvoli pretovar vozila preko NOSIVOSTI (kg) ili KAPACITETA PALETA.
            4. Za svako vozilo ispiši:
               - **Ruta**: (Baza -> Mesto -> Baza)
               - **Kilometraža i Vreme**: Koliko km i koliko je to sati vožnje.
               - **Trošak**: Izračunaj gorivo (km * potrošnja/100 * cena).
               - **Iskorišćenost**: % težine i % paleta.
            5. Ukoliko neko vozilo ostane slobodno, napomeni to.

            Odgovori na SRPSKOM jeziku, koristi TABELE i BOLD za ključne podatke.
            """
            
            try:
                response = model.generate_content(prompt)
                st.success("Planiranje završeno!")
                st.markdown("---")
                st.subheader("📋 Finalni Plan i Analiza Troškova")
                st.markdown(response.text)
                save_data(st.session_state.app_data)
            except Exception as e:
                st.error(f"AI Greška: {e}")