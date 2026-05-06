import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
import plotly.graph_objects as go
import warnings
import os
import time
import logging

warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

# ==========================================
# 1. 核心參數與名單設定
# ==========================================
BASE_TICKERS = [
    '^HSI', 'SPY', 'QQQ', '^IXIC',
    'BABA', 'PDD', 'JD', 'BIDU', 'NIO', 'XPEV', 'LI',
    'MSTR', 'PFE', 'LITE', 'UNH', 'UBER', 'LLY',
    'ADBE', 'CRM', 'ORCL', 'PYPL'
]

HSI_COMP = ['0700.HK', '9988.HK', '3690.HK', '0005.HK', '0941.HK', '1299.HK', '0883.HK', '0388.HK', '2318.HK', '0001.HK', '0002.HK', '0003.HK', '0011.HK', '0016.HK', '0027.HK', '0066.HK', '0386.HK', '0857.HK', '0939.HK', '0981.HK', '0992.HK', '1088.HK', '1093.HK', '1109.HK', '1113.HK', '1398.HK', '1810.HK', '1928.HK', '2020.HK', '2269.HK', '2319.HK', '2388.HK', '2628.HK', '3988.HK', '9618.HK', '9999.HK', '2015.HK', '0288.HK', '2331.HK']
DJI_COMP = ['AAPL', 'AMGN', 'AXP', 'BA', 'CAT', 'CRM', 'CSCO', 'CVX', 'DIS', 'DOW', 'GS', 'HD', 'HON', 'IBM', 'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE', 'PG', 'TRV', 'UNH', 'V', 'VZ', 'WMT']
NDX_COMP = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'AVGO', 'COST', 'PEP', 'TMUS', 'CSCO', 'NFLX', 'AMD', 'INTC', 'QCOM', 'TXN', 'AMGN', 'INTU', 'AMAT', 'ISRG', 'MDLZ', 'BKNG', 'SBUX', 'GILD', 'ADP', 'VRTX', 'REGN', 'LRCX', 'ADI', 'PANW', 'SNPS', 'KLAC', 'CDNS', 'MAR', 'CRWD', 'ORLY', 'FTNT', 'CTAS', 'NXPI', 'PCAR', 'ROST', 'PAYX', 'MNST', 'MRVL', 'CEG', 'DXCM', 'KDP', 'CPRT', 'MSTR', 'ARM']
SPX_COMP = list(set(DJI_COMP + NDX_COMP + ['BRK-B', 'LLY', 'XOM', 'MA', 'ABBV', 'BAC', 'TMO', 'ABT', 'CMCSA', 'PFE', 'T', 'DHR', 'NEE', 'PM', 'RTX', 'UNP', 'BMY', 'LOW', 'COP', 'SPGI', 'GE', 'PLD', 'MDT', 'CAT', 'CVS', 'BLK', 'DE', 'SYK', 'C', 'NOW', 'TJX', 'ZTS', 'BSX', 'FI', 'PGR', 'MMC', 'SCHW', 'LMT', 'CB', 'UBER']))

SECTOR_ETFS = {
    'XLK': '科技', 'XLF': '金融', 'XLV': '醫療', 'XLE': '能源', 
    'XLB': '材料', 'XLI': '工業', 'XLY': '非必需消費', 
    'XLP': '必需消費', 'XLU': '公用事業', 'XLC': '通訊', 'XLRE': '房地產'
}

GANN_ANCHORS = [
    {'market': '美股 (標普)', 'date': '2020-03-23', 'type': '🔥超重要世代底', 'desc': '疫情熔斷大底，世代級別週期起點。'},
    {'market': '美股 (標普)', 'date': '2022-10-13', 'type': '加息恐慌大底', 'desc': '美國通脹見頂引發的熊市大底。'},
    {'market': '港股 (恒指)', 'date': '2022-10-31', 'type': '🔥歷史估值大底', 'desc': '外資恐慌性拋售的終極低點。'},
    {'market': '美股 (標普)', 'date': '2023-10-27', 'type': 'AI主升浪起點', 'desc': 'AI狂潮波段起點，科技股參考價值極高。'},
    {'market': '港股 (恒指)', 'date': '2024-05-20', 'type': '重要中期頂部', 'desc': '19,706點中期高位，推算下一波主升。'},
    {'market': '全球 (宏觀)', 'date': '2024-08-05', 'type': '🔥日圓套息平倉', 'desc': 'VIX單日閃崩，流動性恐慌錨點。'},
    {'market': '全球 (政治)', 'date': '2024-11-05', 'type': '🔥美國總統大選', 'desc': '川普當選日，關稅與利率週期起點。'},
    {'market': '港/美 (短線)', 'date': '2026-01-27', 'type': '近期極端高點', 'desc': '年初高點，用於推算第4浪尾聲與第5浪啟動。'}
]
GANN_CYCLES = [13, 21, 34, 45, 55, 89, 90, 120, 144, 180, 233, 240, 360]

def get_top_turnover_batch(pool, n):
    try:
        df = yf.download(pool, period='5d', progress=False, auto_adjust=False)
        turnovers = {}
        if isinstance(df.columns, pd.MultiIndex):
            for t in pool:
                if t in df['Close']:
                    try:
                        close_val = df['Close'][t].dropna().iloc[-1]
                        vol_val = df['Volume'][t].dropna().iloc[-1]
                        turnovers[t] = float(close_val) * float(vol_val)
                    except: pass
        else:
            if not df.empty and 'Close' in df and 'Volume' in df:
                turnovers[pool[0]] = float(df['Close'].iloc[-1]) * float(df['Volume'].iloc[-1])
        sorted_tickers = sorted(turnovers.items(), key=lambda x: x[1], reverse=True)
        return [k for k, v in sorted_tickers[:n]]
    except Exception:
        return pool[:n]

def get_dynamic_top_turnover_tickers():
    print("🔍 [1/7] 批次掃描四大指數成分股熱錢流向...")
    top_hsi = get_top_turnover_batch(HSI_COMP, 20)
    top_ndx = get_top_turnover_batch(NDX_COMP, 20)
    top_spx = get_top_turnover_batch(SPX_COMP, 30)
    top_dji = get_top_turnover_batch(DJI_COMP, 20)
    return top_hsi, top_ndx, top_spx, top_dji

def get_macro_and_sectors():
    print("🌍 [2/7] 獲取宏觀環境、期權籌碼與板塊輪動...")
    macro = {'dxy': {}, 'us10y': {}, 'spy_pcr': {}}
    try:
        df_dxy = yf.download('DX-Y.NYB', period='1y', progress=False, auto_adjust=False)
        df_10y = yf.download('^TNX', period='1y', progress=False, auto_adjust=False)
        if isinstance(df_dxy.columns, pd.MultiIndex): df_dxy.columns = df_dxy.columns.droplevel(1)
        if isinstance(df_10y.columns, pd.MultiIndex): df_10y.columns = df_10y.columns.droplevel(1)
        
        
        dxy_now = float(df_dxy['Close'].iloc[-1])
        y10_now = float(df_10y['Close'].iloc[-1])
        dxy_spark = make_sparkbar(df_dxy['Close'].tail(10), 'info')
        y10_spark = make_sparkbar(df_10y['Close'].tail(10), 'danger')
        macro['dxy'] = {'val': f"{dxy_now:.2f}", 'chg': (dxy_now/float(df_dxy['Close'].iloc[-6])-1)*100, 'context': f"近10日趨勢{dxy_spark}"}
        macro['us10y'] = {'val': f"{y10_now:.3f}%", 'chg': (y10_now/float(df_10y['Close'].iloc[-6])-1)*100, 'context': f"近10日趨勢{y10_spark}"}
        
        spy = yf.Ticker('SPY')
        opts = spy.options
        if opts:
            chain = spy.option_chain(opts[0])
            p_vol, c_vol = chain.puts['volume'].sum(), chain.calls['volume'].sum()
            pcr = p_vol / c_vol if c_vol > 0 else 1
            macro['spy_pcr'] = {'val': f"{pcr:.2f}", 'status': '極度恐慌' if pcr > 1.2 else '貪婪樂觀' if pcr < 0.7 else '情緒中性'}
        else: macro['spy_pcr'] = {'val': 'N/A', 'status': '-'}
    except: pass

    sectors_perf = []
    for sym, name in SECTOR_ETFS.items():
        try:
            df = yf.download(sym, period='10d', progress=False, auto_adjust=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
                ret = (float(df['Close'].iloc[-1]) / float(df['Close'].iloc[0]) - 1) * 100
                sectors_perf.append({'sym': sym, 'name': name, 'ret': ret})
        except: pass
    sectors_perf.sort(key=lambda x: x['ret'], reverse=True)
    return macro, sectors_perf


def make_sparkbar(series, color_class):
    try:
        vals = [float(x) for x in series if pd.notna(x)]
        if not vals: return ""
        v_min, v_max = min(vals), max(vals)
        rng = v_max - v_min if v_max != v_min else 1
        bars = ""
        for v in vals:
            h = max(5, ((v - v_min) / rng) * 100)
            c_color = 'danger' if color_class == 'auto' and v < vals[0] else 'success' if color_class == 'auto' else color_class
            bars += f"<div style='display:inline-block; flex:1; margin:0 1px; height:{h}%; background-color: var(--bs-{c_color}); border-radius:1px;' title='{v:.2f}'></div>"
        return f"<div style='height:30px; width:100%; display:flex; align-items:flex-end; margin-top:5px; background: rgba(255,255,255,0.03); padding: 2px; border-radius:3px;'>{bars}</div>"
    except: return ""

def get_market_sentiment():
    print("📡 [3/7] 計算大盤情緒熱度與北水 Proxy...")
    us_sentiment = {
        'vix': {'val': 'N/A', 'status': '', 'color': 'secondary', 'context': '無數據'},
        'spy_rsi': {'val': 'N/A', 'status': '動能', 'color': 'secondary', 'context': '無數據'},
        'spy_vol_chg': {'val': 'N/A', 'status': '量能變化', 'color': 'secondary', 'context': '無數據'}
    }
    hk_sentiment = {
        'hsi_rsi': {'val': 'N/A', 'status': '動能', 'color': 'secondary', 'context': '無數據'},
        'hsi_dist': {'val': 'N/A', 'status': '乖離率', 'color': 'secondary', 'context': '無數據'},
        'hsi_vol_chg': {'val': 'N/A', 'status': '量能變化', 'color': 'secondary', 'context': '無數據'},
        'southbound': {'val': 'Proxy估算', 'status': '無原生數據', 'color': 'secondary', 'context': '使用國企/恆指相對量能估算'}
    }

    try:
        hscei_df = yf.download('2828.HK', period='15d', progress=False).ffill()
        hsi_df = yf.download('2800.HK', period='15d', progress=False).ffill()
        hsi_idx = yf.download('^HSI', period='60d', progress=False).ffill()

        if isinstance(hscei_df.columns, pd.MultiIndex): hscei_df.columns = hscei_df.columns.droplevel(1)
        if isinstance(hsi_df.columns, pd.MultiIndex): hsi_df.columns = hsi_df.columns.droplevel(1)
        if isinstance(hsi_idx.columns, pd.MultiIndex): hsi_idx.columns = hsi_idx.columns.droplevel(1)

        if 'Volume' in hscei_df and 'Volume' in hsi_df:
            hscei_vol = hscei_df['Volume'].replace(0, pd.NA).dropna()
            hsi_vol = hsi_df['Volume'].replace(0, pd.NA).dropna()
            if len(hscei_vol) >= 5 and len(hsi_vol) >= 5:
                hscei_vr = float(hscei_vol.iloc[-1]) / (float(hscei_vol.rolling(5).mean().iloc[-1]) + 1e-8)
                hsi_vr = float(hsi_vol.iloc[-1]) / (float(hsi_vol.rolling(5).mean().iloc[-1]) + 1e-8)
                sb_ratio = hscei_vr / (hsi_vr + 1e-8)
                if sb_ratio > 1.2: hk_sentiment['southbound'] = {'val': '內地資金湧入', 'status': '活躍', 'color': 'danger', 'context': '國企成交放大'}
                elif sb_ratio < 0.8: hk_sentiment['southbound'] = {'val': '內地資金靜默', 'status': '萎縮', 'color': 'info text-dark', 'context': '國企交投冷清'}
                else: hk_sentiment['southbound'] = {'val': '兩地資金均勢', 'status': '平穩', 'color': 'success', 'context': '恆指國企交投正常'}

        if not hsi_idx.empty:
            close_px = hsi_idx['Close']
            bias_series = ((close_px / close_px.rolling(20).mean()) - 1) * 100
            bias = float(bias_series.iloc[-1])
            hk_sentiment['hsi_dist'] = {'val': f"{bias:+.2f}%", 'color': 'danger' if bias > 5 else 'success' if bias < -5 else 'warning text-dark', 'status': '正乖離過大' if bias > 5 else '負乖離偏高' if bias < -5 else '貼近均線', 'context': f"近10日趨勢{make_sparkbar(bias_series.tail(10), 'info')}"}

            delta = close_px.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rsi_series = 100 - (100 / (1 + gain / (loss + 1e-8)))
            rsi_now = float(rsi_series.iloc[-1])
            hk_sentiment['hsi_rsi'] = {'val': f"{rsi_now:.1f}", 'color': 'danger' if rsi_now > 70 else 'success' if rsi_now < 30 else 'primary', 'status': '短線過熱' if rsi_now > 70 else '短線超賣' if rsi_now < 30 else '中性區間', 'context': f"近10日趨勢{make_sparkbar(rsi_series.tail(10), 'primary')}"}

        if 'Volume' in hsi_df:
            h_vol = hsi_df['Volume'].replace(0, pd.NA).dropna()
            if len(h_vol) >= 5:
                vr_series_hk = h_vol / h_vol.rolling(5).mean()
                vr = float(vr_series_hk.iloc[-1])
                hk_sentiment['hsi_vol_chg'] = {'val': f"{vr:.2f}x", 'color': 'danger' if vr > 1.3 else 'info text-dark' if vr < 0.8 else 'success', 'status': '狂熱(拋壓增)' if vr > 1.3 else '萎縮(動能減)' if vr < 0.8 else '量能健康', 'context': f"近10日趨勢{make_sparkbar(vr_series_hk.tail(10), 'success')}"}
    except Exception as e: print(f"HK Data Error: {e}")

    try:
        vdf = yf.download('^VIX', period='1y', progress=False, auto_adjust=False)
        if not vdf.empty:
            if isinstance(vdf.columns, pd.MultiIndex): vdf.columns = vdf.columns.droplevel(1)
            v_val = float(vdf['Close'].iloc[-1])
            v_min, v_max = float(vdf['Low'].min()), float(vdf['High'].max())
            v_pct = (v_val - v_min) / (v_max - v_min + 1e-8) * 100
            us_sentiment['vix']['val'] = f"{v_val:.2f}"
            us_sentiment['vix']['color'] = 'success' if v_val < 20 else 'danger' if v_val >= 30 else 'warning text-dark'
            us_sentiment['vix']['status'] = '平穩/偏樂觀' if v_val < 20 else '明顯恐慌' if v_val >= 30 else '波動加劇'
            us_sentiment['vix']['context'] = f"近10日趨勢{make_sparkbar(vdf['Close'].tail(10), 'warning')}<br>1年區間: {v_min:.1f} ~ {v_max:.1f} (分位數: {v_pct:.1f}%)"
    except: pass

    for t_sym, s_dict in [('SPY', us_sentiment)]:
        try:
            df_idx = yf.download(t_sym, period='1y', progress=False, auto_adjust=False)
            if not df_idx.empty:
                if isinstance(df_idx.columns, pd.MultiIndex): df_idx.columns = df_idx.columns.droplevel(1)
                delta = df_idx['Close'].diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = (-delta.clip(upper=0)).rolling(14).mean()
                rsi_series = 100 - (100 / (1 + gain / (loss + 1e-8)))
                rsi_now = float(rsi_series.iloc[-1])
                rsi_min, rsi_max = float(rsi_series.min()), float(rsi_series.max())
                rsi_pct = (rsi_now - rsi_min) / (rsi_max - rsi_min + 1e-8) * 100
                s_dict['spy_rsi']['val'] = f"{rsi_now:.1f}"
                s_dict['spy_rsi']['color'] = 'danger' if rsi_now > 70 else 'success' if rsi_now < 30 else 'primary'
                s_dict['spy_rsi']['status'] = '短線過熱' if rsi_now > 70 else '短線超賣' if rsi_now < 30 else '中性區間'
                s_dict['spy_rsi']['context'] = f"近10日趨勢{make_sparkbar(rsi_series.tail(10), 'primary')}<br>1年區間: {rsi_min:.1f} ~ {rsi_max:.1f} (分位數: {rsi_pct:.1f}%)"

                vol_ma5_series = df_idx['Volume'].rolling(5).mean()
                vr_series = df_idx['Volume'] / vol_ma5_series
                vr = float(vr_series.iloc[-1])
                vr_min, vr_max = float(vr_series.dropna().min()), float(vr_series.dropna().max())
                vr_pct = (vr - vr_min) / (vr_max - vr_min + 1e-8) * 100
                if not pd.isna(vr):
                    s_dict['spy_vol_chg']['val'] = f"{vr:.2f}x"
                    s_dict['spy_vol_chg']['color'] = 'danger' if vr > 1.3 else 'info text-dark' if vr < 0.8 else 'success'
                    s_dict['spy_vol_chg']['status'] = '交投狂熱(拋壓增)' if vr > 1.3 else '觀望萎縮(動能減)' if vr < 0.8 else '量能健康'
                    s_dict['spy_vol_chg']['context'] = f"近10日趨勢{make_sparkbar(vr_series.tail(10), 'success')}<br>1年區間: {vr_min:.1f}x ~ {vr_max:.1f}x (分位數: {vr_pct:.1f}%)"
        except: pass
    return us_sentiment, hk_sentiment


def get_options_pcr(ticker):
    try:
        tk = yf.Ticker(ticker)
        opts = tk.options
        if not opts: return None
        chain = tk.option_chain(opts[0])
        cv = chain.calls['volume'].sum()
        pv = chain.puts['volume'].sum()
        if cv > 0: return pv / cv
    except: return None


def calc_scores(r):
    t_score, v_items = 0, 0
    if pd.notna(r.get('rsi')): v_items+=1; t_score += 25 if r['rsi']<30 else 15 if r['rsi']<45 else 0
    if pd.notna(r.get('wr')): v_items+=1; t_score += 25 if r['wr']>80 else 15 if r['wr']>60 else 0
    if pd.notna(r.get('cci')): v_items+=1; t_score += 25 if r['cci']<-100 else 15 if r['cci']<0 else 0
    if pd.notna(r.get('kdj_j')): v_items+=1; t_score += 25 if r['kdj_j']<20 else 15 if r['kdj_j']<50 else 0
    t_score = min(t_score * (4 / max(v_items, 1)), 100)

    f_score, v_items = 0, 0
    if pd.notna(r.get('vr')): v_items+=1; f_score += 40 if r['vr']<70 else 20 if r['vr']<100 else 0
    if pd.notna(r.get('mfi')): v_items+=1; f_score += 30 if r['mfi']<30 else 15 if r['mfi']<50 else 0
    if pd.notna(r.get('drawdown_swing')): v_items+=1; f_score += 30 if r['drawdown_swing']<-20 else 15 if r['drawdown_swing']<-10 else 0
    f_score = min(f_score * (3 / max(v_items, 1)), 100)

    b_score, v_items = 0, 0
    if pd.notna(r.get('pe')) and r['pe']>0: v_items+=1; b_score += 15 if r['pe']<15 else 10 if r['pe']<25 else 0
    if pd.notna(r.get('pb')) and r['pb']>0: v_items+=1; b_score += 15 if r['pb']<1.2 else 10 if r['pb']<2 else 0
    if pd.notna(r.get('roe')) and r['roe']>15: v_items+=1; b_score += 20
    if pd.notna(r.get('fcf_yield')) and r['fcf_yield']>4: v_items+=1; b_score += 20
    if pd.notna(r.get('debt_eq')) and r['debt_eq']<0.5: v_items+=1; b_score += 15
    b_score = min(b_score * (4 / max(v_items, 1)), 100)

    tot = int(t_score*0.4 + f_score*0.4 + b_score*0.2)
    return min(t_score, 100), min(f_score, 100), min(b_score, 100), tot

def add_common_indicators(df):
    df = df.copy()
    df['Vol_MA5'] = df['Volume'].rolling(5).mean()
    df['Vol_Ratio'] = df['Volume'] / (df['Vol_MA5'] + 1e-8)
    df['52W_High'] = df['High'].rolling(252).max()
    df['Drawdown'] = (df['Close'] - df['52W_High']) / (df['52W_High'] + 1e-8) * 100
    
    df['OBV'] = (np.sign(df['Close'].diff().fillna(0)) * df['Volume']).cumsum()
    
    df['TR'] = pd.concat([df['High'] - df['Low'], (df['High'] - df['Close'].shift(1)).abs(), (df['Low'] - df['Close'].shift(1)).abs()], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(14).mean()

    roll_high = df['High'].rolling(10).max()
    roll_low = df['Low'].rolling(10).min()
    df['Max_DD_10d'] = (roll_low - roll_high) / (roll_high + 1e-8) * 100

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain / (loss + 1e-8)))

    tp = (df['High'] + df['Low'] + df['Close']) / 3
    tp_sma = tp.rolling(20).mean()
    md = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=False)
    df['CCI'] = (tp - tp_sma) / (0.015 * md + 1e-8)

    low_min = df['Low'].rolling(9).min()
    high_max = df['High'].rolling(9).max()
    df['RSV'] = (df['Close'] - low_min) / (high_max - low_min + 1e-8) * 100
    df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']

    hh14, ll14 = df['High'].rolling(14).max(), df['Low'].rolling(14).min()
    df['WR'] = (hh14 - df['Close']) / (hh14 - ll14 + 1e-8) * 100

    money_flow = tp * df['Volume']
    pos_sum = money_flow.where(tp > tp.shift(1), 0.0).rolling(14).sum()
    neg_sum = money_flow.where(tp < tp.shift(1), 0.0).rolling(14).sum()
    df['MFI'] = 100 - (100 / (1 + pos_sum / (neg_sum + 1e-8)))

    chg = df['Close'].diff().fillna(0)
    up_vol = df['Volume'].where(chg > 0, 0).rolling(26).sum()
    down_vol = df['Volume'].where(chg < 0, 0).rolling(26).sum()
    flat_vol = df['Volume'].where(chg == 0, 0).rolling(26).sum()
    df['VR'] = (up_vol + 0.5 * flat_vol) / (down_vol + 0.5 * flat_vol + 1e-8) * 100

    df['Ret_5d'] = df['Close'].pct_change(5) * 100
    return df

def get_weekly_df(df):
    w = df[['Open', 'High', 'Low', 'Close', 'Volume']].resample('W-FRI').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    return add_common_indicators(w)

def train_ai_models(df):
    df_ml = df.dropna().copy()
    if len(df_ml) < 130: return None, 0
    features = ['RSI', 'CCI', 'J', 'WR', 'MFI', 'Drawdown', 'Vol_Ratio', 'VR', 'Ret_5d']
    X = df_ml[features][:-10]
    y_clf = (df_ml['Close'].shift(-5) > df_ml['Close'] * 1.02)[:-10].astype(int)
    rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    rf.fit(X, y_clf)
    buy_prob = rf.predict_proba(df_ml.iloc[-1:][features])[0][1] * 100
    return dict(zip(features, rf.feature_importances_)), buy_prob

def get_sub_scores(r):
    t_score = sum([15 if r['rsi']<30 else 0, 10 if r['cci']<-100 else 0, 15 if r['kdj_j']<0 else 0, 15 if r['wr']>80 else 0, 20 if pd.notna(r['weekly_k']) and r['weekly_k']<20 and r['weekly_d']<20 else 0, 10 if pd.notna(r['weekly_wr']) and r['weekly_wr']>80 else 0])
    f_score = sum([30 if r['mfi']<20 else 15 if r['mfi']<30 else 0, 20 if r['vr']<40 else 0, 20 if pd.notna(r['weekly_mfi']) and r['weekly_mfi']<30 else 0])
    b_score, v_items = 0, 0
    if pd.notna(r['pe']) and r['pe']>0: v_items+=1; b_score += 15 if r['pe']<15 else 10 if r['pe']<25 else 0
    if pd.notna(r['pb']) and r['pb']>0: v_items+=1; b_score += 15 if r['pb']<1.2 else 10 if r['pb']<2 else 0
    if pd.notna(r['peg']) and r['peg']>0: v_items+=1; b_score += 15 if r['peg']<1.0 else 10 if r['peg']<0.8 else 0
    if pd.notna(r['div_yield']) and r['div_yield']>0: v_items+=1; b_score += 15 if r['div_yield']>4 else 10 if r['div_yield']>6 else 0
    b_score = min(b_score * (4 / v_items), 100) if v_items > 0 else 0
    return min(t_score, 100), min(f_score, 100), min(b_score, 100), int(t_score*0.4 + f_score*0.4 + b_score*0.2)

def fmt_num(x, nd=1):
    return str(round(float(x), nd)) if not pd.isna(x) else 'N/A'

def main():
    os.makedirs("output", exist_ok=True)
    top_hsi, top_ndx, top_spx, top_dji = get_dynamic_top_turnover_tickers()
    all_tickers = list(dict.fromkeys(BASE_TICKERS + top_hsi + top_ndx + top_spx + top_dji))

    macro_data, sectors_perf = get_macro_and_sectors()
    us_sent, hk_sent = get_market_sentiment()
    
    results, whale_traces, price_history = [], [], {}
    anomalies_7days = []

    risk_status = "🟡 震盪觀望"
    risk_color = "warning"
    if macro_data.get('dxy', {}).get('chg', 0) > 1 or macro_data.get('us10y', {}).get('chg', 0) > 3:
        risk_status = "🔴 逆風局 (Risk-Off) - 資金抽離，嚴控倉位"
        risk_color = "danger"
    elif macro_data.get('dxy', {}).get('chg', 0) < -0.5 and macro_data.get('us10y', {}).get('chg', 0) < -1:
        risk_status = "🟢 順風局 (Risk-On) - 流動性寬鬆，適合波段佈局"
        risk_color = "success"

    print("🌊 [4/7] 繪製大盤波浪走勢圖...")
    charts_html = ''
    hk_wave = "<b>港股：</b>大型第4浪尾聲或浪5前夕。第4浪屬主升浪後的整理洗盤，表現為橫行磨時間；守住頸線則有望走第5浪。"
    us_wave = "<b>美股：</b>第5浪延伸。牛市最後一段仍可創新高，但風險同步放大；一旦完成通常進入ABC修正，需緊盯情緒指標。"
    for idx_ticker, title in [('^HSI', '恒生指數 (波浪結構)'), ('SPY', 'S&P 500 (波浪結構)')]:
        try:
            df_idx = yf.download(idx_ticker, period='5y', progress=False, auto_adjust=False)
            if df_idx.empty: continue
            if isinstance(df_idx.columns, pd.MultiIndex): df_idx.columns = df_idx.columns.droplevel(1)
            fig = go.Figure(data=[go.Candlestick(x=df_idx.index, open=df_idx['Open'], high=df_idx['High'], low=df_idx['Low'], close=df_idx['Close'])])
            
            fig.update_layout(
                title=dict(text=title, font=dict(color='#e2e8f0')),
                height=300, margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor='#1e293b', plot_bgcolor='#1e293b',
                xaxis=dict(gridcolor='#334155', tickfont=dict(color='#94a3b8'), range=[datetime.now() - timedelta(days=730), datetime.now() + timedelta(days=30)]),
                yaxis=dict(gridcolor='#334155', tickfont=dict(color='#94a3b8'))
            )
            charts_html += f"<div class='col-xl-6 mb-2'>{fig.to_html(full_html=False, include_plotlyjs='cdn')}</div>"
        except: pass

    print(f"📊 [5/7] 深度掃描個股指標、基本面、與期權籌碼 (共 {len(all_tickers)} 檔標的，請耐心等候)...")
    for i, ticker in enumerate(all_tickers, start=1):
        try:
            tk = yf.Ticker(ticker)
            df = yf.download(ticker, period='2y', progress=False, auto_adjust=False)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            
            if ticker in BASE_TICKERS: price_history[ticker] = df['Close'].tail(30)
            
            df = add_common_indicators(df.dropna())
            wdf = get_weekly_df(df)
            
            info = {}
            earnings_date = "N/A"
            if not ticker.startswith('^'):  
                try: info = tk.info
                except: pass
                try:
                    cal = tk.get_calendar()
                    if isinstance(cal, dict) and 'Earnings Date' in cal:
                        earnings_date = pd.to_datetime(cal['Earnings Date'][0]).strftime('%Y-%m-%d')
                    elif isinstance(cal, pd.DataFrame) and not cal.empty and 'Earnings Date' in cal.index:
                        earnings_date = pd.to_datetime(cal.loc['Earnings Date'][0]).strftime('%Y-%m-%d')
                except: pass

            pcr = None
            if ticker in BASE_TICKERS and not ticker.startswith('^'):
                pcr = get_options_pcr(ticker)

            imp_res = train_ai_models(df)
            buy_prob = imp_res[1] if imp_res else 0

            
            
            curr_price = float(df['Close'].iloc[-1])
            atr_val = float(df['ATR'].iloc[-1])

            # --- 裴洛西內部人/公司高層籌碼雷達 ---
            insider_signal = ""
            try:
                ip = tk.insider_purchases
                if ip is not None and not ip.empty:
                    p_row = ip[ip['Insider Purchases Last 6m'] == 'Purchases']
                    s_row = ip[ip['Insider Purchases Last 6m'] == 'Sales']
                    n_row = ip[ip['Insider Purchases Last 6m'] == 'Net Shares Purchased (Sold)']
                    purchases = int(p_row['Trans'].iloc[0]) if not p_row.empty and pd.notna(p_row['Trans'].iloc[0]) else 0
                    sales = int(s_row['Trans'].iloc[0]) if not s_row.empty and pd.notna(s_row['Trans'].iloc[0]) else 0
                    net_shares = float(n_row['Shares'].iloc[0]) if not n_row.empty and pd.notna(n_row['Shares'].iloc[0]) else 0
                    if purchases > sales and net_shares > 0:
                        insider_signal = f"<div class='badge bg-danger mt-1'>🚨內部人加碼(+{purchases}筆)</div>"
                    elif sales > max(1, purchases * 2):
                        insider_signal = f"<div class='badge bg-dark text-warning mt-1'>⚠️內部人倒貨(-{sales}筆)</div>"
            except:
                pass

            # --- 巴菲特護城河與現金流雷達 ---
            roe_val = float((info.get('returnOnEquity') or 0) * 100)
            debt_eq = float((info.get('debtToEquity') or 100) / 100)
            op_margin = float((info.get('operatingMargins') or 0) * 100)
            fcf = float(info.get('freeCashflow') or 0)
            market_cap = float(info.get('marketCap') or 0)
            fcf_yield = (fcf / market_cap) * 100 if market_cap > 0 else np.nan
            buffett_tags = []
            if roe_val > 15: buffett_tags.append('高ROE')
            if debt_eq < 0.5: buffett_tags.append('低負債')
            if op_margin > 15: buffett_tags.append('高毛利')
            if pd.notna(fcf_yield) and fcf_yield > 4: buffett_tags.append('現金牛')
            buffett_badge = f"<div class='mt-1' style='font-size:0.7rem; color:#f59e0b;'>護城河: {','.join(buffett_tags) if buffett_tags else '無'}</div>"

            # 3年長線高低點 (756個交易日)
            h2y = float(df['High'].rolling(756, min_periods=1).max().iloc[-1])
            l2y = float(df['Low'].rolling(756, min_periods=1).min().iloc[-1])
            diff2y = h2y - l2y
            fib2y = {'236': h2y - 0.236*diff2y, '382': h2y - 0.382*diff2y, '500': h2y - 0.5*diff2y, '618': h2y - 0.618*diff2y, '786': h2y - 0.786*diff2y}

            # 波段高低點 (120天)
            lookback_days = min(120, len(df))
            recent_df = df.tail(lookback_days)
            recent_high = float(recent_df['High'].max())
            recent_low = float(recent_df['Low'].min())
            diff_swing = recent_high - recent_low
            fib_swing = {'236': recent_high - 0.236*diff_swing, '382': recent_high - 0.382*diff_swing, '500': recent_high - 0.5*diff_swing, '618': recent_high - 0.618*diff_swing, '786': recent_high - 0.786*diff_swing}

            ma50 = float(df['Close'].rolling(50, min_periods=1).mean().iloc[-1])

            # 分離字串
            swing_fib_str = f"<small class='text-muted'>23.6%: {fib_swing['236']:.1f}<br>38.2%: {fib_swing['382']:.1f}<br>50.0%: {fib_swing['500']:.1f}<br>61.8%: {fib_swing['618']:.1f}<br>78.6%: {fib_swing['786']:.1f}</small>"

            macro_fib_str = f"<small class='text-primary'>23.6%: {fib2y['236']:.1f}<br>38.2%: {fib2y['382']:.1f}<br>50.0%: {fib2y['500']:.1f}<br>61.8%: {fib2y['618']:.1f}<br>78.6%: {fib2y['786']:.1f}</small>"

            if abs(fib_swing['618'] - ma50) / (ma50 + 1e-8) < 0.02:
                swing_fib_str += "<br><span class='badge bg-warning text-dark mt-1'>0.618與50MA共振</span>"
            elif abs(fib_swing['500'] - ma50) / (ma50 + 1e-8) < 0.02:
                swing_fib_str += "<br><span class='badge bg-warning text-dark mt-1'>0.5與50MA共振</span>"

            if abs(fib2y['618'] - ma50) / (ma50 + 1e-8) < 0.02:
                macro_fib_str += "<br><span class='badge bg-info text-dark mt-1'>0.618與50MA共振</span>"
            elif abs(fib2y['500'] - ma50) / (ma50 + 1e-8) < 0.02:
                macro_fib_str += "<br><span class='badge bg-info text-dark mt-1'>0.5與50MA共振</span>"

            drop_from_high_2y = (curr_price - h2y) / (h2y + 1e-8) * 100
            drop_from_swing_high = (curr_price - recent_high) / (recent_high + 1e-8) * 100

            res = {
                'ticker': ticker, 'source': '核心池' if ticker in BASE_TICKERS else '四大指數熱門',
                'price': curr_price, 'change': float(df['Close'].pct_change().iloc[-1]*100),
                'rsi': float(df['RSI'].iloc[-1]), 'cci': float(df['CCI'].iloc[-1]), 'kdj_k': float(df['K'].iloc[-1]), 'kdj_d': float(df['D'].iloc[-1]), 'kdj_j': float(df['J'].iloc[-1]),
                'wr': float(df['WR'].iloc[-1]), 'mfi': float(df['MFI'].iloc[-1]), 'vr': float(df['VR'].iloc[-1]),
                'drawdown_2y': drop_from_high_2y, 'drawdown_swing': drop_from_swing_high, 
                'swing_fib_str': swing_fib_str, 'macro_fib_str': macro_fib_str,
                'max_dd_10d': float(df['Max_DD_10d'].iloc[-1]),
                'weekly_k': float(wdf['K'].iloc[-1]) if len(wdf) else np.nan, 'weekly_d': float(wdf['D'].iloc[-1]) if len(wdf) else np.nan,
                'weekly_wr': float(wdf['WR'].iloc[-1]) if len(wdf) else np.nan, 'weekly_mfi': float(wdf['MFI'].iloc[-1]) if len(wdf) else np.nan,
                'weekly_vr': float(wdf['VR'].iloc[-1]) if len(wdf) else np.nan,
                'pe': info.get('trailingPE') or info.get('forwardPE'), 'pb': info.get('priceToBook'), 
                'peg': info.get('pegRatio'), 'div_yield': (info.get('trailingAnnualDividendYield') or 0)*100,
                'roe': roe_val, 'beta': info.get('beta'), 'fcf_yield': fcf_yield, 'debt_eq': debt_eq,
                'stop_loss': curr_price - (2 * atr_val), 'earnings': earnings_date, 'pcr': pcr if 'pcr' in locals() else None,
                'ai_buy_prob': buy_prob, 'insider_signal': insider_signal, 'buffett_badge': buffett_badge
            }


            res['t_score'], res['f_score'], res['b_score'], res['tot_score'] = get_sub_scores(res)
            results.append(res)

            obv_divergence = False
            if len(df) > 20:
                price_20 = df['Close'][-20:].tolist()
                obv_20 = df['OBV'][-20:].tolist()
                p_slope = np.polyfit(range(20), price_20, 1)[0]
                o_slope = np.polyfit(range(20), obv_20, 1)[0]
                if p_slope <= 0.01 and o_slope > 0:
                    obv_divergence = True

            vol_history = []
            recent_7d_anomalies = []
            spike_dates_info = [] 
            low_dates_info = []   
            
            buy_vwap_num, buy_vwap_den = 0, 0
            sell_vwap_num, sell_vwap_den = 0, 0
            buy_spike_count, sell_spike_count, low_count = 0, 0, 0

            lookback = min(22, len(df))
            for d in range(lookback):
                vol_r = float(df['Vol_Ratio'].iloc[-(d + 1)])
                vol_history.append(vol_r)
                date_str = df.index[-(d+1)].strftime('%m-%d')
                is_green = float(df['Close'].iloc[-(d+1)]) >= float(df['Open'].iloc[-(d+1)])
                
                tp = (float(df['High'].iloc[-(d+1)]) + float(df['Low'].iloc[-(d+1)]) + float(df['Close'].iloc[-(d+1)])) / 3
                v_val = float(df['Volume'].iloc[-(d+1)])
                
                if vol_r > 1.3:
                    if is_green:
                        buy_spike_count += 1
                        spike_dates_info.append(f"<span class='text-success fw-bold'>{date_str}({vol_r:.1f}x)</span>")
                        buy_vwap_num += tp * v_val
                        buy_vwap_den += v_val
                    else:
                        sell_spike_count += 1
                        spike_dates_info.append(f"<span class='text-danger'>{date_str}({vol_r:.1f}x)</span>")
                        sell_vwap_num += tp * v_val
                        sell_vwap_den += v_val
                elif vol_r < 0.8:
                    low_count += 1
                    low_dates_info.append(f"{date_str}({vol_r:.1f}x)")
                
                if d < 7:
                    if vol_r > 1.3: 
                        c_color = 'success' if is_green else 'danger'
                        recent_7d_anomalies.append(f"<span class='badge bg-{c_color} mb-1'>{d}天前 {'買入' if is_green else '拋售'}爆量({vol_r:.1f}x)</span>")
                        anomalies_7days.append({'ticker': ticker, 'type': '爆量', 'ratio': vol_r, 'day': d, 'date': date_str, 'is_green': is_green})
                    elif vol_r < 0.8: 
                        recent_7d_anomalies.append(f"<span class='badge bg-info text-dark mb-1'>{d}天前 地量({vol_r:.1f}x)</span>")
                        anomalies_7days.append({'ticker': ticker, 'type': '地量', 'ratio': vol_r, 'day': d, 'date': date_str})

            buy_vwap = (buy_vwap_num / buy_vwap_den) if buy_vwap_den > 0 else 0
            sell_vwap = (sell_vwap_num / sell_vwap_den) if sell_vwap_den > 0 else 0
            
            cost_str = ""
            if buy_vwap > 0: cost_str += f"<span class='text-success fw-bold d-block mt-1'>🟢 大戶買入均價約: {buy_vwap:.2f}</span>"
            if sell_vwap > 0: cost_str += f"<span class='text-danger fw-bold d-block'>🔴 大戶派發均價約: {sell_vwap:.2f}</span>"

            near_bottom = res['drawdown_swing'] < -15
            trace_type, summary, conclusion, priority = "", "", "", 0
            spike_dates_str = ", ".join(spike_dates_info[::-1])
            low_dates_str = ", ".join(low_dates_info[::-1])

            is_weekly_spike = len(wdf) >= 2 and float(wdf['VR'].iloc[-1]) > 130 and res['drawdown_swing'] < -20

            if is_weekly_spike and obv_divergence and res['weekly_k'] < 25 and buy_spike_count >= 1:
                trace_type = "<span class='badge bg-danger fs-6 py-2'>💎 週線級別超級建倉 (極高勝率)</span>"
                summary = f"週線爆量 + OBV 底背離"
                conclusion = f"股價長線超賣，週線出現真實買盤大爆量且 OBV 逆勢抬升。<br>{cost_str}"
                priority = 900
            elif near_bottom and buy_spike_count >= 1 and (res['mfi'] < 45 or res['rsi'] < 45 or res['kdj_j'] < 20):
                trace_type = "<span class='badge bg-danger fs-6 py-2'>🐋 底部恐慌吸籌 (早期預警)</span>"
                summary = f"深跌區真實買盤 <b class='text-success'>{buy_spike_count}</b> 次"
                obv_msg = "<br><span class='text-success'>✅ 檢測到 OBV 底背離 (吸籌鐵證)</span>" if obv_divergence else ""
                conclusion = f"左側尋底雷達觸發！股價回撤且出現大戶試探性買盤。<br><span class='mt-1 d-block'>📅 <b>近期爆量：</b>{spike_dates_str}</span>{cost_str}{obv_msg}"
                priority = 999
            # 【全新增加：捕捉 Meta 這種右側強勢突破爆量】
            elif res['drawdown_swing'] >= -15 and buy_spike_count >= 1 and res['rsi'] >= 50:
                trace_type = "<span class='badge bg-info text-dark fs-6 py-2'>🚀 強勢突破爆量 (右側追擊)</span>"
                summary = f"強勢區大戶追買 <b class='text-success'>{buy_spike_count}</b> 次"
                conclusion = f"股價距離前高不遠（無深幅回撤），卻依然出現大戶真金白銀追價買進（常為財報超預期或突破型態）。<br><span class='mt-1 d-block'>📅 <b>近期爆量：</b>{spike_dates_str}</span>{cost_str}<br><span class='text-muted'>💡 右側順勢策略：切記以大戶買入均價作為防守停損點。</span>"
                priority = 80
            elif res['rsi'] < 50 and low_count >= 6:
                trace_type = "<span class='badge bg-purple fs-6 py-2'>🕵️‍♂️ 極限縮量洗盤 (窒息量)</span>"
                summary = f"近1個月地量 <b class='text-purple'>{low_count}</b> 次"
                obv_msg = "<br><span class='text-success'>✅ 橫盤/下跌中 OBV 抬升</span>" if obv_divergence else ""
                conclusion = f"出現「窒息量」，拋壓枯竭。<br><span class='text-info mt-1 d-block'>📅 <b>地量日：</b>{low_dates_str}</span>{obv_msg}"
                priority = 9000
            elif res['rsi'] > 65 and sell_spike_count >= 2:
                trace_type = "<span class='badge bg-warning text-dark fs-6 py-2'>⚠️ 高位放量大跌 (派發)</span>"
                summary = f"高位區倒貨 <b class='text-dark'>{sell_spike_count}</b> 次"
                conclusion = f"股價相對高位出現大陰線出貨。<br><span class='mt-1 d-block'>📅 <b>爆量日：</b>{spike_dates_str}</span>{cost_str}<br>主力趁利多派發籌碼，需嚴格停損。"
                priority = 40
            
            if trace_type:
                whale_traces.append({
                    'ticker': ticker, 'source': res['source'],
                    'type': trace_type, 'summary': summary, 'conclusion': conclusion,
                    'recent_7d': " ".join(recent_7d_anomalies) or "<span class='text-muted small'>近7日平穩</span>",
                    'priority': priority, 'score': res['tot_score']
                })
        except: pass

    print("🕸️ [6/7] 計算投資組合系統性風險與相關性...")
    corr_warnings = []
    if len(price_history) > 2:
        df_pr = pd.DataFrame(price_history)
        df_pr = df_pr.ffill().bfill()
        corr_matrix = df_pr.corr()
        checked = set()
        for c1 in corr_matrix.columns:
            for c2 in corr_matrix.columns:
                if c1 != c2 and tuple(sorted([c1, c2])) not in checked:
                    checked.add(tuple(sorted([c1, c2])))
                    val = corr_matrix.loc[c1, c2]
                    if val > 0.85:
                        corr_warnings.append(f"<span class='badge bg-danger mb-1'>{c1} 🤝 {c2} (相關性 {val:.2f})</span>")

    print("🎨 [7/7] 渲染終極暗黑版 HTML 模塊...")
    results.sort(key=lambda x: x['tot_score'], reverse=True)
    whale_traces.sort(key=lambda x: (x['priority'], x['score']), reverse=True)

    macro_html = f"""
    
<div class='alert alert-secondary bg-dark text-light border-secondary mb-3'>
    <h6 class='fw-bold text-info mb-2'>🧭 宏觀指標與雷達白話解讀：</h6>
    <div class='row small'>
        <div class='col-md-4'>
            <ul class='mb-0 ps-3'>
                <li><strong class='text-warning'>美元指數 (DXY)：</strong><br>美元升值代表資金撤出風險資產，股市易跌；貶值則代表資金寬鬆，利多股市。</li>
                <li><strong class='text-warning'>美10年期殖利率：</strong><br>無風險利率指標。高於 4.3% 壓抑科技股估值；回落則有利大盤上漲。</li>
            </ul>
        </div>
        <div class='col-md-4'>
            <ul class='mb-0 ps-3'>
                <li><strong class='text-warning'>美股期權情緒 (SPY PCR)：</strong><br>大於 1.2 代表機構瘋狂買 Put 避險(極恐慌，常為底部)；小於 0.7 代表市場極貪婪。</li>
                <li><strong class='text-warning'>大盤量能熱度：</strong><br>VR > 1.3 代表交投狂熱(短線易見頂)；< 0.8 代表縮量觀望(拋壓枯竭)。</li>
            </ul>
        </div>
        <div class='col-md-4'>
            <ul class='mb-0 ps-3'>
                <li><strong class='text-warning'>VIX 恐慌指數：</strong><br>低於 20 市場安心；飆破 30 代表極度恐慌，通常伴隨股災，但也是逆向買點。</li>
                <li><strong class='text-warning'>港股北水活躍度：</strong><br>> 1.2 代表內地資金大舉湧入國企股；< 0.8 代表交投靜默。</li>
            </ul>
        </div>
    </div>
</div>

    <div class='row'>
        <div class='col-md-4'><div class='card border-{risk_color} mb-3 bg-dark'><div class='card-header bg-{risk_color} text-white fw-bold'>🧭 宏觀環境判定</div><div class='card-body text-center d-flex align-items-center justify-content-center'><h5 class='fw-bold text-{risk_color} mb-0'>{risk_status}</h5></div></div></div>
        <div class='col-md-4'><div class='card border-secondary mb-3 bg-dark'><div class='card-header bg-secondary text-white fw-bold'>💵 跨資產流動性 (資金水龍頭)</div><div class='card-body py-2'><ul class='list-group list-group-flush'>
            <li class='list-group-item text-white bg-dark px-0 py-1'>
                <div class='d-flex justify-content-between'><span>美元指數 (DXY)</span><span class='fw-bold {'text-danger' if macro_data.get('dxy',{}).get('chg',0)>0 else 'text-success'}'>{macro_data.get('dxy',{}).get('val','N/A')} ({fmt_num(macro_data.get('dxy',{}).get('chg','N/A'))}%)</span></div>
                <div class='text-info mt-1' style='font-size:0.75rem;'>📊 {macro_data.get('dxy',{}).get('context','')}</div>
            </li>
            <li class='list-group-item text-white bg-dark px-0 py-1 border-bottom-0'>
                <div class='d-flex justify-content-between'><span>美10年期殖利率</span><span class='fw-bold {'text-danger' if macro_data.get('us10y',{}).get('chg',0)>0 else 'text-success'}'>{macro_data.get('us10y',{}).get('val','N/A')} ({fmt_num(macro_data.get('us10y',{}).get('chg','N/A'))}%)</span></div>
                <div class='text-info mt-1' style='font-size:0.75rem;'>📊 {macro_data.get('us10y',{}).get('context','')}</div>
            </li>
        </ul></div></div></div>
        <div class='col-md-4'><div class='card border-dark mb-3 bg-dark'><div class='card-header bg-dark text-white fw-bold border-secondary'>🎭 美股期權情緒 (SPY PCR)</div><div class='card-body text-center py-2'>
            <h4 class='fw-bold mb-1 text-light'>{macro_data.get('spy_pcr',{}).get('val','N/A')}</h4>
            <span class='badge bg-warning text-dark fs-6'>{macro_data.get('spy_pcr',{}).get('status','')}</span>
        </div></div></div>
    </div>
    """

    sentiment_html = f"""
    <div class='row mt-2'>
        <div class='col-md-6'><div class='card border-primary mb-3 bg-dark'><div class='card-header bg-primary text-white fw-bold'>🇺🇸 美股大盤真實熱度</div><div class='card-body'><ul class='list-group list-group-flush'>
            <li class='list-group-item d-flex justify-content-between align-items-center text-white bg-dark'><div><div class='fw-bold'>VIX 恐慌指數</div><div style='font-size:0.75rem; color:#94a3b8;'>{us_sent['vix']['context']}</div></div><span class='badge bg-{us_sent['vix']['color']} fs-6'>{us_sent['vix']['val']} ({us_sent['vix']['status']})</span></li>
            <li class='list-group-item d-flex justify-content-between align-items-center text-white bg-dark'><div><div class='fw-bold'>S&P 500 RSI(14)</div><div style='font-size:0.75rem; color:#94a3b8;'>{us_sent['spy_rsi']['context']}</div></div><span class='badge bg-{us_sent['spy_rsi']['color']} fs-6'>{us_sent['spy_rsi']['val']} ({us_sent['spy_rsi']['status']})</span></li>
            <li class='list-group-item d-flex justify-content-between align-items-center text-white bg-dark'><div><div class='fw-bold'>S&P 500 量能熱度</div><div style='font-size:0.75rem; color:#94a3b8;'>{us_sent['spy_vol_chg']['context']}</div></div><span class='badge bg-{us_sent['spy_vol_chg']['color']} fs-6'>{us_sent['spy_vol_chg']['val']} ({us_sent['spy_vol_chg']['status']})</span></li>
        </ul></div></div></div>
        <div class='col-md-6'><div class='card border-danger mb-3 bg-dark'><div class='card-header bg-danger text-white fw-bold'>🇭🇰 港股大盤真實熱度 (含北水 Proxy)</div><div class='card-body'><ul class='list-group list-group-flush'>
            <li class='list-group-item d-flex justify-content-between align-items-center text-white bg-dark'><div><div class='fw-bold'>北水活躍度 (國企/恆指相對量能)</div><div style='font-size:0.75rem; color:#94a3b8;'>{hk_sent['southbound']['context']}</div></div><span class='badge bg-{hk_sent['southbound']['color']} fs-6'>{hk_sent['southbound']['val']} ({hk_sent['southbound']['status']})</span></li>
            <li class='list-group-item d-flex justify-content-between align-items-center text-white bg-dark'><div><div class='fw-bold'>恒指 20日乖離率</div><div style='font-size:0.75rem; color:#94a3b8;'>{hk_sent['hsi_dist']['context']}</div></div><span class='badge bg-{hk_sent['hsi_dist']['color']} fs-6'>{hk_sent['hsi_dist']['val']} ({hk_sent['hsi_dist']['status']})</span></li>
            <li class='list-group-item d-flex justify-content-between align-items-center text-white bg-dark'><div><div class='fw-bold'>大市量能熱度</div><div style='font-size:0.75rem; color:#94a3b8;'>{hk_sent['hsi_vol_chg']['context']}</div></div><span class='badge bg-{hk_sent['hsi_vol_chg']['color']} fs-6'>{hk_sent['hsi_vol_chg']['val']} ({hk_sent['hsi_vol_chg']['status']})</span></li>
        </ul></div></div></div>
    </div>"""

    sector_html = "".join([f"<div class='d-inline-block text-center mx-2 mb-2'><span class='badge fs-6 {'bg-success' if s['ret']>0 else 'bg-danger'}'>{s['name']} ({s['sym']})<br>{fmt_num(s['ret'])}%</span></div>" for s in sectors_perf]) or "暫無數據"

    buy_signals = [r for r in results if r.get('ai_buy_prob', 0) > 60]
    buy_html = ' '.join([f"<span class='badge bg-success fs-6 m-1'>{r['ticker']} ({fmt_num(r['ai_buy_prob'])}%)</span>" for r in buy_signals]) or '<span class="text-light">目前未有高勝率買入信號</span>'

    vol_radar_html = ""
    for d in range(7):
        items = [a for a in anomalies_7days if a['day']==d]
        if items:
            vol_radar_html += f"<div class='mb-2'><b>{'今日' if d==0 else f'{d}天前'} ({items[0]['date']}):</b> " + " ".join([f"<span class='badge {'bg-success' if a.get('is_green') else 'bg-danger' if a['type']=='爆量' else 'bg-info text-dark'} m-1'>{a['ticker']} {a['type']} {fmt_num(a['ratio'])}x</span>" for a in items]) + "</div>"
    if not vol_radar_html: vol_radar_html = '<span class="text-light">近7天無顯著異常成交量</span>'

    

    bottom_c = sum(1 for w in whale_traces if '底部' in w['type'] or '建倉' in w['type'])
    break_c = sum(1 for w in whale_traces if '突破' in w['type'])
    wash_c = sum(1 for w in whale_traces if '縮量' in w['type'])
    dump_c = sum(1 for w in whale_traces if '高位' in w['type'] or '派發' in w['type'])

    if bottom_c + break_c > dump_c * 1.5:
        ai_msg = "<div class='alert alert-success border-success text-success bg-dark fw-bold mb-3'>🟢 【AI 資金流向判定】：目前大戶積極吸籌與追價突破的標的明顯多於派發，整體籌碼結構偏多，建議逢低佈局或順勢參與突破。</div>"
    elif dump_c > bottom_c + break_c:
        ai_msg = "<div class='alert alert-danger border-danger text-danger bg-dark fw-bold mb-3'>🔴 【AI 資金流向判定】：高位放量倒貨的標的顯著增加，大戶正在撤退，請務必提高警覺，嚴控倉位並設好停損。</div>"
    else:
        ai_msg = "<div class='alert alert-warning border-warning text-warning bg-dark fw-bold mb-3'>🟡 【AI 資金流向判定】：多空籌碼交戰中，大戶動作分歧，建議以個股獨立邏輯操作。</div>"

    whale_rows = "".join([f"<tr><td class='fw-bold text-center'>{w['ticker']}</td><td class='text-center'>{w['type']}</td><td class='text-center'>{w['summary']}</td><td class='text-start'>{w['conclusion']}</td><td class='text-center'>{w['recent_7d']}</td></tr>" for w in whale_traces])

    
    
    def whl(val, condition):
        if pd.isna(val): return 'N/A'
        return f"<span class='text-danger fw-bold'>{fmt_num(val)}</span>" if condition else fmt_num(val)

    weekly_rows = "".join([f"<tr><td class='fw-bold'>{r['ticker']}</td><td class='fw-bold text-danger'>{r['tot_score']}</td><td>{whl(r['weekly_k'], r['weekly_k']<25)} / {fmt_num(r['weekly_d'])}</td><td>{whl(r['weekly_wr'], r['weekly_wr']>75)}</td><td>{whl(r['weekly_mfi'], r['weekly_mfi']<35)}</td><td>Beta:{fmt_num(r['beta'])}</td></tr>" for r in results if (r['source'] == '核心池' or (pd.notna(r['weekly_k']) and r['weekly_k']<25) or (pd.notna(r['weekly_wr']) and r['weekly_wr']>75) or (pd.notna(r['weekly_mfi']) and r['weekly_mfi']<35))])
    all_future_turnarounds = []
    for a in GANN_ANCHORS:
        base_date = datetime.strptime(a['date'], '%Y-%m-%d')
        days_passed = (datetime.now() - base_date).days
        future_cycles = [c for c in GANN_CYCLES if c > days_passed]
        for next_cycle in future_cycles[:2]:
            target_date = base_date + timedelta(days=next_cycle)
            days_left = (target_date - datetime.now()).days
            all_future_turnarounds.append({
                'market': a['market'], 'type': a['type'], 'desc': a['desc'], 'base_date': a['date'],
                'target_date': target_date, 'days_left': days_left, 'cycle': next_cycle,
                'c_type': "斐波那契" if next_cycle in [13, 21, 34, 55, 89, 144, 233] else "江恩"
            })
    all_future_turnarounds.sort(key=lambda x: x['days_left'])
    
    gann_rows = ""
    for t in all_future_turnarounds:
        urgency = "<span class='badge bg-danger'>🔴 警戒</span>" if t['days_left'] <= 7 else "<span class='badge bg-warning text-dark'>🟡 觀察</span>" if t['days_left'] <= 15 else "<span class='badge bg-success'>🟢 順勢</span>"
        gann_rows += f"<tr><td class='fw-bold text-start'>{t['market']}<br><span>{t['type']}</span></td><td>{t['base_date']}</td><td><span class='fw-bold text-info fs-6'>{t['target_date'].strftime('%Y-%m-%d')}</span><br><small>距 {t['days_left']} 天</small></td><td>{t['cycle']}天<br><small class='text-light opacity-75'>({t['c_type']})</small></td><td>{urgency}</td><td class='text-start'><small>{t['desc']}</small></td></tr>"

    def hl(val, condition, fmt='{:.1f}'): 
        if pd.isna(val): return 'N/A'
        v_str = fmt.format(val)
        return f"<span class='text-danger fw-bold fs-6'>{v_str}</span>" if condition else v_str

    table_rows = "".join([f"<tr><td class='fw-bold'>{r['ticker']}<br>{r.get('insider_signal','')}</td><td>{fmt_num(r['price'],2)} <span class='{'text-success' if r['change']>0 else 'text-danger'}'>({fmt_num(r['change'])}%)</span></td><td class='fw-bold text-danger'>{fmt_num(r['stop_loss'],2)}</td><td class='{'text-danger fw-bold' if r['earnings']!='N/A' else ''}'>{r['earnings']}</td><td class='fs-5 fw-bold text-primary'>{r['tot_score']}{r.get('buffett_badge','')}</td><td>{hl(r['rsi'], r['rsi']<30)}</td><td>{hl(r['wr'], r['wr']>80)}</td><td>{hl(r['vr'], r['vr']<70)}</td><td class='text-danger fw-bold'>{fmt_num(r['drawdown_swing'])}%</td><td>{r['swing_fib_str']}</td><td class='text-danger fw-bold'>{fmt_num(r['drawdown_2y'])}%</td><td>{r['macro_fib_str']}</td><td>{fmt_num(r['pe'])}</td><td>{fmt_num(r['roe'])}%</td><td>{fmt_num(r.get('fcf_yield'),1)}%</td></tr>" for r in results])

    html = f"""<!DOCTYPE html>
<html lang='zh-HK'>
<head><meta charset='UTF-8'><meta http-equiv="refresh" content="3600"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>華爾街級機構投研工作站</title>
<link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'>
<link href='https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css' rel='stylesheet'>
<style>
body {{ background:#0f172a; color:#e2e8f0; font-family:Segoe UI,Tahoma,sans-serif; font-size:0.9rem; }}
.panel {{ background:#1e293b; border-radius:10px; padding:20px; margin-bottom:20px; border:1px solid #334155; box-shadow:0 4px 6px -1px rgba(0,0,0,0.5); }}
.table {{ color:#e2e8f0; margin-bottom:0!important; }} .table-light {{ background:#334155; color:#fff; }}
table.dataTable>thead>tr>th {{ border-bottom: 2px solid #475569; color: #94a3b8; }}
.table-hover tbody tr:hover {{ background-color:#334155; color:#fff; box-shadow: inset 0 0 0 9999px rgba(255, 255, 255, 0.05); }}
.bg-danger {{ background-color:#ef4444!important; }} .text-danger {{ color:#ef4444!important; }}
.bg-success {{ background-color:#22c55e!important; }} .text-success {{ color:#22c55e!important; }}
.bg-warning {{ background-color:#f59e0b!important; }} .text-warning {{ color:#f59e0b!important; }}
.bg-purple {{ background-color:#8b5cf6!important; color:#ffffff!important; }}
.text-purple {{ color:#a855f7!important; }}
.info-box {{ background:#334155; border-left:4px solid #3b82f6; padding:12px; margin-bottom:15px; border-radius:4px; line-height: 1.6; color:#e2e8f0; }}
div.dataTables_wrapper div.dataTables_filter input, div.dataTables_wrapper div.dataTables_length select {{ background-color: #0f172a; border: 1px solid #475569; color: #fff; }}
.page-item .page-link {{ background-color: #1e293b; border-color: #334155; color: #e2e8f0; }}
.page-item.active .page-link {{ background-color: #3b82f6; border-color: #3b82f6; }}
.page-item.disabled .page-link {{ background-color: #0f172a; border-color: #334155; color: #475569; }}
</style>
</head>
<body class='p-4'>
<div class='container-fluid'>
<h2 class='mb-2 fw-bold text-white'>🏢 華爾街級機構投研工作站 <span class="badge bg-primary fs-6 align-middle">Ultimate Terminal</span></h2>
<div class='text-light mb-4 opacity-75'>最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 共掃描 {len(all_tickers)} 檔活躍標的</div>

<div class='panel border-top-0 border-start-0 border-end-0' style='border-bottom:3px solid #3b82f6;'>
    <h5 class='text-primary fw-bold mb-3'>🌍 宏觀控制台與大盤熱度雷達</h5>
    {macro_html}
    {sentiment_html}
    <div class='mt-3 pt-3 border-top border-secondary'>
        <h6 class='fw-bold text-light mb-3'>🎡 美股 11 大板塊資金輪動 (近10日動能)</h6>
        <div class='p-3 bg-dark rounded border border-secondary text-center'>{sector_html}</div>
    </div>
</div>

<div class='panel border-top-0 border-start-0 border-end-0' style='border-bottom:3px solid #ef4444;'>
    <h5 class='text-danger fw-bold mb-2'>🛡️ 投資組合風險警告</h5>
    <div class='info-box border-danger'><b>⚠️ 系統風險提示：</b> 以下自選股歷史走勢高度重疊 (相關性 > 0.85)，若同時重倉將面臨極大同向下跌風險。</div>
    <div>{" ".join(corr_warnings) if corr_warnings else "<span class='text-success'>✅ 當前自選股板塊分散，無高度重疊風險。</span>"}</div>
</div>

<div class='panel border-top-0 border-start-0 border-end-0' style='border-bottom:3px solid #0dcaf0;'>
    <h5 class='text-info fw-bold mb-3'>🌊 宏觀波浪圖解與位置</h5>
    <div class='row mb-2'>{charts_html}</div>
</div>

<div class='row'>
    <div class='col-xl-6'>
        <div class='panel h-100 border-top-0 border-start-0 border-end-0' style='border-bottom:3px solid #f97316;'>
            <h5 class='fw-bold mb-3' style='color:#f97316;'>🤖 短線高勝率買入信號</h5>
            <div class='info-box border-warning'>基於機器學習演算法，預測未來 5 天看漲機率 > 60% 之標的。</div>
            <div class='mt-2'>{buy_html}</div>
        </div>
    </div>
    <div class='col-xl-6'>
        <div class='panel h-100 border-top-0 border-start-0 border-end-0' style='border-bottom:3px solid #ec4899;'>
            <h5 class='fw-bold mb-3' style='color:#ec4899;'>📡 近7日異常成交量雷達</h5>
            <div class='p-3 bg-dark border border-secondary rounded' style='max-height:200px; overflow-y:auto;'>{vol_radar_html}</div>
        </div>
    </div>
</div>

<div class='panel border-top-0 border-start-0 border-end-0 mt-4' style='border-bottom:3px solid #a855f7;'>
    <h5 class='text-purple fw-bold mb-3' style='color:#a855f7;'>🐋 期權籌碼與 AI 莊家痕跡追蹤</h5>
    <div class='info-box' style='border-left-color:#a855f7;'>
        <b>💡 莊家痕跡 AI 判定邏輯：</b> 已大幅調降「底部恐慌吸籌」的觸發門檻（回撤>15% 且出現 1 次買盤爆量即預警），作為極左側的早期尋底雷達。同時新增<b>「🚀 強勢突破爆量」</b>，捕捉右側主升浪的追價大戶。<br>
        <b>📊 大戶成本追蹤：</b> 自動為你計算近期「大陽線(買貨)」與「大陰線(出貨)」的 VWAP (成交量加權均價)，精準定位莊家成本防線。

    </div>
    {ai_msg}
    <div class='table-responsive'>
        <table class='table table-bordered table-hover align-middle interactive-dt'>
            <thead class='table-light'><tr><th>股票</th><th>AI 痕跡判定</th><th>期權/量能特徵</th><th>深度總結 (含大戶成本)</th><th>近期觸發明細</th></tr></thead>
            <tbody>{whale_rows}</tbody>
        </table>
    </div>
</div>

<div class='panel border-top-0 border-start-0 border-end-0' style='border-bottom:3px solid #22c55e;'>
    <h5 class='text-success fw-bold mb-3'>📅 週線左側買入信號 (中長線底層建倉)</h5>
    <div class='info-box border-success'>
        <b>📘 週線指標意義 (符合極端條件以 <span class='text-danger fw-bold'>紅色</span> 高亮)：</b><br>
        • <b>週 K/D (&lt;25)：</b> 代表長達數月的「下跌動能」已經觸底耗盡。<br>
        • <b>週 WR (&gt;75)：</b> 威廉指標。代表中長線籌碼極度恐慌，歷史上極易形成黃金坑。<br>
        • <b>週 MFI (&lt;35)：</b> 資金流量指標。代表長線賣壓枯竭，已經沒有人想賣了。
    </div>
    <div class='table-responsive'>
        <table class='table table-hover align-middle text-center interactive-dt'>
            <thead><tr><th class='text-start'>股票</th><th>總低估分</th><th>週K/D (&lt;25)</th><th>週WR (&gt;75)</th><th>週MFI (&lt;35)</th><th>Beta</th></tr></thead>
            <tbody>{weekly_rows}</tbody>
        </table>
    </div>
</div>

<div class='panel border-top-0 border-start-0 border-end-0' style='border-bottom:3px solid #eab308;'>
    <h5 class='fw-bold mb-3' style='color:#eab308;'>⏳ 費氏數列 / 江恩輪中輪 轉勢日曆</h5>
    <div class='table-responsive'>
        <table class='table table-hover align-middle text-center interactive-dt'>
            <thead><tr><th>市場板塊</th><th>錨點</th><th>下個轉勢窗</th><th>週期</th><th>狀態</th><th class='text-start'>理據</th></tr></thead>
            <tbody>{gann_rows}</tbody>
        </table>
    </div>
</div>

<div class='panel border-top-0 border-start-0 border-end-0' style='border-bottom:3px solid #0ea5e9;'>
    <h5 class='fw-bold mb-3' style='color:#0ea5e9;'>🔥 個股深度掃描矩陣 (支援點擊表頭排序與搜尋)</h5>
    
    <div class='info-box border-info'>
        <b>📘 核心指標與深度矩陣解讀：</b><br>
        • <b class='text-warning'>波段 vs 3年回撤%：</b> 分別計算過去 120 天(波段)與 3 年(長線)的最高點，衡量當前股價下跌幅度。<br>
        • <b class='text-warning'>雙重斐波那契共振：</b> 若黃金分割價位與 50MA 差距 <2%，系統會亮起黃/藍色<b class='text-info'>共振警告</b>，為極佳支撐買點。<br>
        • <b class='text-warning'>ROE (股東權益報酬率)：</b> 衡量公司賺錢效率。ROE > 15% 代表護城河深厚、基本面優良 (巴菲特最愛指標)。<br>
        • <b class='text-warning'>PE (本益比)：</b> 衡量回本年限，越低代表股價越便宜。<br>
        • <b class='text-warning'>PCR (期權情緒)：</b> 顯示在上方宏觀面板。>1.2代表機構瘋狂買 Put 避險(底部徵兆)；<0.7代表極度貪婪(見頂徵兆)。<br>
        • <b class='text-warning'>FCF殖利率：</b> 企業自由現金流 / 市值，越高代表真正賺到手的現金越多；若為負值代表公司現金流壓力較大。<br>
        • <b class='text-warning'>內部人雷達：</b> 股票名稱下方若出現紅色標籤，代表近6個月內部人淨買入偏多；黃色標籤代表倒貨風險。<br>
        • <b class='text-warning'>技術指標：</b> <b>RSI:</b> &lt;30為超賣。<b>WR:</b> &gt;80為恐慌超賣。<b>VR:</b> &lt;70為無人問津(窒息量)。
    </div>

    <div class='table-responsive'>
        <table class='table table-bordered table-hover align-middle text-center interactive-dt' style='white-space:nowrap;'>
            <thead><tr><th class='text-start'>股票</th><th>現價(%)</th><th class='bg-danger text-white'>防守停損</th><th class='bg-warning text-dark'>財報日</th><th class='bg-primary text-white'>低估分</th><th>RSI</th><th>WR</th><th>VR</th><th>波段回撤%</th><th>波段斐波那契</th><th>3年回撤%</th><th>3年長線斐波那契</th><th>PE</th><th>ROE</th><th>FCF殖利率</th></tr></thead>
            <tbody>{table_rows}</tbody>
        </table>
    </div>
</div>

</div>

<!-- DataTables Scripts -->
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
<script>
    $(document).ready(function() {{
        $('.interactive-dt').DataTable({{
            "pageLength": 25,
            "order": [], // 不強制初始排序，保留 Python 算好的 AI 分數順序
            "language": {{
                "search": "🔍 搜尋股票:",
                "lengthMenu": "每頁顯示 _MENU_ 檔",
                "info": "顯示 _START_ 到 _END_ 檔，共 _TOTAL_ 檔",
                "infoEmpty": "顯示 0 檔",
                "zeroRecords": "查無符合的資料",
                "paginate": {{ "next": "下一頁", "previous": "上一頁" }}
            }}
        }});
    }});
</script>
</body></html>"""

    with open('output/turnaround_dashboard.html', 'w', encoding='utf-8') as f: f.write(html)

if __name__ == "__main__":
    try:
        print(f"--- 開始更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        main()
        print("更新完成。")
    except Exception as e:
        print(f"執行時發生錯誤: {e}")
        raise
