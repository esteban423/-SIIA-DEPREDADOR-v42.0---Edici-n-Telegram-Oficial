import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import telebot
import schedule
import time
from threading import Thread

# --- 1. CONFIGURACIÓN, CREDENCIALES Y SEGURIDAD ---
TOKEN = "8753793977:AAFWryLt1fVxGgJrW1JpDz40NiryFY9N9rs"
CHAT_ID_AUTORIZADO = 8631491166  # Solo vos podés usar el bot
CLAVE_WEB = "35875e" # CAMBIÁ ESTO POR TU CLAVE PARA STREAMLIT
bot = telebot.TeleBot(TOKEN)

RATIOS = {
    "NVDA": 24.0, "AAPL": 20.0, "MSFT": 30.0, "META": 24.0, "AMZN": 144.0,
    "GOOGL": 58.0, "TSLA": 15.0, "NFLX": 48.0, "MELI": 120.0, "AVGO": 100.0,
    "BRK-B": 22.0, "KO": 5.0, "WMT": 18.0, "COST": 48.0, "PG": 15.0,
    "JNJ": 15.0, "UNH": 30.0, "XOM": 10.0, "CVX": 16.0, 
    "GE": 8.0, "DE": 40.0, "CAT": 20.0, "JPM": 15.0, "V": 18.0, "MA": 33.0,
    "BAC": 4.0, "HD": 10.0, "NKE": 3.0, "DIS": 12.0, "ADBE": 44.0,
    "SPY": 20.0, "QQQ": 20.0, "DIA": 20.0, "XLE": 2.0, "XLF": 2.0,
    "IWM": 10.0, "GDX": 10.0
}
COSTO_IOL = 0.005605 
CCL_REF = 1469

# --- 2. MOTOR DE OPTIMIZACIÓN EXHAUSTIVA ---
def buscar_punto_perfecto(ticker):
    try:
        data = yf.download(ticker, period="2y", interval="1wk", progress=False)
        if data.empty: return None
        df_p = data['Close'].iloc[:, 0] if isinstance(data['Close'], pd.DataFrame) else data['Close']
        mejor_ma, mejor_retorno, mejor_bt = 0, -999, None
        
        for ma in range(10, 51):
            bt = pd.DataFrame(index=df_p.index)
            bt['P'] = df_p.values
            bt['MA'] = bt['P'].rolling(ma).mean()
            bt['S'] = np.where(bt['P'] > bt['MA'], 1, 0)
            bt['Ret'] = bt['P'].pct_change()
            bt['Trades'] = bt['S'].diff().abs().fillna(0)
            bt['Neto'] = (bt['Ret'] * bt['S'].shift(1)) - (bt['Trades'] * COSTO_IOL)
            final_ret = (1 + bt['Neto'].fillna(0)).cumprod().iloc[-1]
            if final_ret > mejor_retorno:
                mejor_retorno, mejor_ma, mejor_bt = final_ret, ma, bt
        
        p_act = float(mejor_bt['P'].iloc[-1])
        sl_val = float(mejor_bt['MA'].iloc[-1])
        
        return {
            "ma_opt": mejor_ma, "retorno": (mejor_retorno - 1) * 100,
            "escudo": "✅ OK" if p_act > sl_val else "❌ ROTO",
            "sl_ars": (sl_val * CCL_REF) / RATIOS[ticker],
            "p_ars": (p_act * CCL_REF) / RATIOS[ticker]
        }
    except: return None

# --- 3. LÓGICA DE TELEGRAM CON FILTRO DE USUARIO ---
@bot.message_handler(func=lambda message: message.from_user.id != CHAT_ID_AUTORIZADO)
def rechazar_acceso(message):
    bot.reply_to(message, "🚫 Acceso denegado. Este sistema es privado.")
    bot.send_message(CHAT_ID_AUTORIZADO, f"⚠️ Intento de acceso no autorizado de ID: {message.from_user.id}")

@bot.message_handler(commands=['radar'])
def telegram_radar(message):
    bot.send_message(CHAT_ID_AUTORIZADO, "🧠 Ejecutando escaneo para el Ranking Top 10...")
    res_list = []
    for t in RATIOS.keys():
        r = buscar_punto_perfecto(t)
        if r: res_list.append({**r, "t": t})
    
    res_list = sorted(res_list, key=lambda x: x['retorno'], reverse=True)
    msg = "🏆 *RANKING TOP 10 - PUNTOS PERFECTOS*\n\n"
    for i, r in enumerate(res_list[:10], 1):
        msg += f"{i}. *{r['t']}* (MA{r['ma_opt']}): {r['escudo']}\n"
        msg += f"💰 Retorno: {r['retorno']:.1f}% | 🛡️ SL: ${r['sl_ars']:,.0f}\n"
        msg += "--------------------------\n"
    bot.send_message(CHAT_ID_AUTORIZADO, msg, parse_mode="Markdown")

# --- 4. INTERFAZ STREAMLIT CON CLAVE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Acceso Restringido")
        pw = st.text_input("Ingrese la clave del Sistema SIIA", type="password")
        if st.button("Entrar"):
            if pw == CLAVE_WEB:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Clave incorrecta")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SIIA v43.0 - Dashboard Privado", layout="wide")
    st.title("🧠 SIIA-DEPREDADOR v43.0: Gestión Total")

    if "threads_iniciados" not in st.session_state:
        Thread(target=lambda: bot.polling(none_stop=True), daemon=True).start()
        st.session_state.threads_iniciados = True

    if st.button("🚀 ACTUALIZAR RANKING (37 ACTIVOS)"):
        resultados = []
        barra = st.progress(0)
        status = st.empty()
        
        for i, (t, r) in enumerate(RATIOS.items()):
            status.text(f"Analizando {t}...")
            res = buscar_punto_perfecto(t)
            if res:
                resultados.append({
                    "Ticker": t, "MA Opt": res['ma_opt'], "Retorno %": round(res['retorno'], 2),
                    "Escudo": res['escudo'], "Precio ARS": round(res['p_ars'], 2), 
                    "Stop Loss ARS": round(res['sl_ars'], 2)
                })
            barra.progress((i + 1) / len(RATIOS))
        
        status.text("✅ Proceso completado.")
        df = pd.DataFrame(resultados).sort_values("Retorno %", ascending=False)
        st.dataframe(df, use_container_width=True)

