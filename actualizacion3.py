import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import telebot
import schedule
import time
from threading import Thread

# --- 1. CONFIGURACIÓN Y CREDENCIALES ---
TOKEN = "8753793977:AAFWryLt1fVxGgJrW1JpDz40NiryFY9N9rs"
CHAT_ID = "8631491166"
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

# --- 2. MOTOR DE BÚSQUEDA DEL PUNTO PERFECTO ---
def buscar_punto_perfecto(ticker):
    try:
        data = yf.download(ticker, period="2y", interval="1wk", progress=False)
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
        
        sl_val = float(mejor_bt['MA'].iloc[-1])
        p_act = float(mejor_bt['P'].iloc[-1])
        
        return {
            "ma_opt": mejor_ma, "retorno": (mejor_retorno - 1) * 100,
            "escudo": "✅ OK" if p_act > sl_val else "❌ ROTO",
            "sl_ars": (sl_val * CCL_REF) / RATIOS[ticker]
        }
    except: return None

# --- 3. LÓGICA DE TELEGRAM Y AUTOMATIZACIÓN ---
def generar_ranking_msg():
    res_list = []
    for t in RATIOS.keys():
        r = buscar_punto_perfecto(t)
        if r: res_list.append({**r, "t": t})
    
    res_list = sorted(res_list, key=lambda x: x['retorno'], reverse=True)
    msg = "🏆 *RANKING TOP 10 SEMANAL*\n\n"
    for i, r in enumerate(res_list[:10], 1):
        msg += f"{i}. *{r['t']}* (MA{r['ma_opt']}): {r['escudo']}\n"
        msg += f"💰 Ret: {r['retorno']:.1f}% | 🛡️ SL: ${r['sl_ars']:,.0f}\n"
        msg += "--------------------------\n"
    return msg

@bot.message_handler(commands=['radar'])
def radar_manual(message):
    bot.send_message(CHAT_ID, "🧠 *SIIA v42.1*: Ejecutando optimización exhaustiva...")
    bot.send_message(CHAT_ID, generar_ranking_msg(), parse_mode="Markdown")

def tarea_programada():
    msg = "📅 *REPORTE AUTOMÁTICO DE LUNES*\n" + generar_ranking_msg()
    bot.send_message(CHAT_ID, msg, parse_mode="Markdown")

def run_scheduler():
    schedule.every().monday.at("11:00").do(tarea_programada)
    while True:
        schedule.run_pending()
        time.sleep(60)

# --- 4. INICIO DE HILOS Y STREAMLIT ---
if "hilos_iniciados" not in st.session_state:
    Thread(target=lambda: bot.polling(none_stop=True), daemon=True).start()
    Thread(target=run_scheduler, daemon=True).start()
    st.session_state.hilos_iniciados = True

st.title("🧠 SIIA-DEPREDADOR v42.1: Gestión Total")
if st.button("🚀 ACTUALIZAR DASHBOARD"):
    # ... (Misma lógica de tabla de actualizacion2.py) ...
    st.success("Dashboard actualizado y Sincronizado con Telegram")