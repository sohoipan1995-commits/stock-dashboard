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
        
        dxy_now, dxy_old = float(df_dxy['Close'].iloc[-1]), float(df_dxy['Close'].iloc[-6])
        dxy_min, dxy_max = float(df_dxy['Low'].min()), float(df_dxy['High'].max())
        dxy_pct = (dxy_now - dxy_min) / (dxy_max - dxy_min + 1e-8) * 100
        
        y10_now, y10_old = float(df_10y['Close'].iloc[-1]), float(df_10y['Close'].iloc[-6])
        y10_min, y10_max = float(df_10y['Low'].min()), float(df_10y['High'].max())
        y10_pct = (y10_now - y10_min) / (y10_max - y10_min + 1e-8) * 100
        
        macro['dxy'] = {'val': f"{dxy_now:.2f}", 'chg': (dxy_now/dxy_old-1)*100, 'context': f"1年區間: {dxy_min:.1f} ~ {dxy_max:.1f} (分位數: {dxy_pct:.1f}%)"}
        macro['us10y'] = {'val': f"{y10_now:.3f}%", 'chg': (y10_now/y10_old-1)*100, 'context': f"1年區間: {y10_min:.2f} ~ {y10_max:.2f} (分位數: {y10_pct:.1f}%)"}
        
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
        hscei_df = yf.download('2828.HK', period='5d', progress=False, auto_adjust=False)
        hsi_df = yf.download('2800.HK', period='5d', progress=False, auto_adjust=False)
        if not hscei_df.empty and not hsi_df.empty:
            hscei_vol = float(hscei_df['Volume'].iloc[-1]) / float(hscei_df['Volume'].rolling(5).mean().iloc[-1] + 1e-8)
            hsi_vol = float(hsi_df['Volume'].iloc[-1]) / float(hsi_df['Volume'].rolling(5).mean().iloc[-1] + 1e-8)
            sb_ratio = hscei_vol / (hsi_vol + 1e-8)
            if sb_ratio > 1.2:
                hk_sentiment['southbound'] = {'val': '內地資金湧入', 'status': '活躍 (Proxy)', 'color': 'danger', 'context': '國企股成交明顯放大'}
            elif sb_ratio < 0.8:
                hk_sentiment['southbound'] = {'val': '內地資金靜默', 'status': '萎縮 (Proxy)', 'color': 'info text-dark', 'context': '國企股交投冷清'}
            else:
                hk_sentiment['southbound'] = {'val': '兩地資金均勢', 'status': '平穩 (Proxy)', 'color': 'success', 'context': '恆指國企交投比例正常'}
    except: pass

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
            us_sentiment['vix']['context'] = f"1年區間: {v_min:.1f} ~ {v_max:.1f} (分位數: {v_pct:.1f}%)"
    except: pass

    for t_sym, s_dict in [('SPY', us_sentiment), ('^HSI', hk_sentiment)]:
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
                
                key_prefix = 'spy' if t_sym == 'SPY' else 'hsi'
                s_dict[f'{key_prefix}_rsi']['val'] = f"{rsi_now:.1f}"
                s_dict[f'{key_prefix}_rsi']['color'] = 'danger' if rsi_now > 70 else 'success' if rsi_now < 30 else 'primary'
                s_dict[f'{key_prefix}_rsi']['status'] = '短線過熱' if rsi_now > 70 else '短線超賣' if rsi_now < 30 else '中性區間'
                s_dict[f'{key_prefix}_rsi']['context'] = f"1年區間: {rsi_min:.1f} ~ {rsi_max:.1f} (分位數: {rsi_pct:.1f}%)"
                
                if t_sym == '^HSI':
                    bias_series = ((df_idx['Close'] / df_idx['Close'].rolling(20).mean()) - 1) * 100
                    bias = float(bias_series.iloc[-1])
                    b_min, b_max = float(bias_series.min()), float(bias_series.max())
                    b_pct = (bias - b_min) / (b_max - b_min + 1e-8) * 100
                    s_dict['hsi_dist']['val'] = f"{bias:+.2f}%"
                    s_dict['hsi_dist']['color'] = 'danger' if bias > 5 else 'success' if bias < -5 else 'warning text-dark'
                    s_dict['hsi_dist']['status'] = '正乖離過大' if bias > 5 else '負乖離偏高' if bias < -5 else '貼近均線'
                    s_dict['hsi_dist']['context'] = f"1年區間: {b_min:.1f}% ~ {b_max:.1f}% (分位數: {b_pct:.1f}%)"

                vol_ma5_series = df_idx['Volume'].rolling(5).mean()
                vr_series = df_idx['Volume'] / vol_ma5_series
                vr = float(vr_series.iloc[-1])
                vr_min, vr_max = float(vr_series.dropna().min()), float(vr_series.dropna().max())
                vr_pct = (vr - vr_min) / (vr_max - vr_min + 1e-8) * 100
                
                if not pd.isna(vr):
                    s_dict[f'{key_prefix}_vol_chg']['val'] = f"{vr:.2f}x"
                    s_dict[f'{key_prefix}_vol_chg']['color'] = 'danger' if vr > 1.3 else 'info text-dark' if vr < 0.8 else 'success'
                    s_dict[f'{key_prefix}_vol_chg']['status'] = '交投狂熱(拋壓增)' if vr > 1.3 else '觀望萎縮(動能減)' if vr < 0.8 else '量能健康'
                    s_dict[f'{key_prefix}_vol_chg']['context'] = f"1年區間: {vr_min:.1f}x ~ {vr_max:.1f}x (分位數: {vr_pct:.1f}%)"
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
    # 輸出到 docs 資料夾供 GitHub Pages 讀取
    os.makedirs("docs", exist_ok=True) 
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
            
            res = {
                'ticker': ticker, 'source': '核心池' if ticker in BASE_TICKERS else '四大指數熱門',
                'price': curr_price, 'change': float(df['Close'].pct_change().iloc[-1]*100),
                'rsi': float(df['RSI'].iloc[-1]), 'cci': float(df['CCI'].iloc[-1]), 'kdj_k': float(df['K'].iloc[-1]), 'kdj_d': float(df['D'].iloc[-1]), 'kdj_j': float(df['J'].iloc[-1]),
                'wr': float(df['WR'].iloc[-1]), 'mfi': float(df['MFI'].iloc[-1]), 'vr': float(df['VR'].iloc[-1]),
                'drawdown': float(df['Drawdown'].iloc[-1]), 'max_dd_10d': float(df['Max_DD_10d'].iloc[-1]),
                'weekly_k': float(wdf['K'].iloc[-1]) if len(wdf) else np.nan, 'weekly_d': float(wdf['D'].iloc[-1]) if len(wdf) else np.nan,
                'weekly_wr': float(wdf['WR'].iloc[-1]) if len(wdf) else np.nan, 'weekly_mfi': float(wdf['MFI'].iloc[-1]) if len(wdf) else np.nan,
                'weekly_vr': float(wdf['VR'].iloc[-1]) if len(wdf) else np.nan,
                'pe': info.get('trailingPE') or info.get('forwardPE'), 'pb': info.get('priceToBook'), 
                'peg': info.get('pegRatio'), 'div_yield': (info.get('trailingAnnualDividendYield') or 0)*100,
                'roe': (info.get('returnOnEquity') or 0)*100, 'beta': info.get('beta'),
                'stop_loss': curr_price - (2 * atr_val), 'earnings': earnings_date, 'pcr': pcr,
                'ai_buy_prob': buy_prob
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

            near_bottom = res['drawdown'] < -15
            trace_type, summary, conclusion, priority = "", "", "", 0
            spike_dates_str = ", ".join(spike_dates_info[::-1])
            low_dates_str = ", ".join(low_dates_info[::-1])

            is_weekly_spike = len(wdf) >= 2 and float(wdf['VR'].iloc[-1]) > 130 and res['drawdown'] < -20

            # ====== 權重排序調整 (Priority) ======
            if is_weekly_spike and obv_divergence and res['weekly_k'] < 25 and buy_spike_count >= 1:
                trace_type = "<span class='badge bg-danger fs-6 py-2'>💎 週線級別超級建倉 (極高勝率)</span>"
                summary = f"週線爆量 + OBV 底背離"
                conclusion = f"股價長線超賣，週線出現真實買盤大爆量且 OBV 逆勢抬升。<br>{cost_str}"
                priority = 6 
            elif near_bottom and buy_spike_count >= 1 and (res['mfi'] < 45 or res['rsi'] < 45 or res['kdj_j'] < 20):
                trace_type = "<span class='badge bg-danger fs-6 py-2'>🐋 底部恐慌吸籌 (早期預警)</span>"
                summary = f"深跌區真實買盤 <b class='text-success'>{buy_spike_count}</b> 次"
                obv_msg = "<br><span class='text-success'>✅ 檢測到 OBV 底背離 (吸籌鐵證)</span>" if obv_divergence else ""
                conclusion = f"左側尋底雷達觸發！股價回撤且出現大戶試探性買盤。<br><span class='mt-1 d-block'>📅 <b>近期爆量：</b>{spike_dates_str}</span>{cost_str}{obv_msg}"
                priority = 5
            elif res['rsi'] < 50 and low_count >= 6:
                trace_type = "<span class='badge bg-purple fs-6 py-2'>🕵️‍♂️ 極限縮量洗盤 (窒息量)</span>"
                summary = f"近1個月地量 <b class='text-purple'>{low_count}</b> 次"
                obv_msg = "<br><span class='text-success'>✅ 橫盤/下跌中 OBV 抬升</span>" if obv_divergence else ""
                conclusion = f"出現「窒息量」，拋壓枯竭。<br><span class='text-info mt-1 d-block'>📅 <b>地量日：</b>{low_dates_str}</span>{obv_msg}"
                priority = 4
            elif res['drawdown'] >= -15 and buy_spike_count >= 1 and res['rsi'] >= 50:
                trace_type = "<span class='badge bg-info text-dark fs-6 py-2'>🚀 強勢突破爆量 (右側追擊)</span>"
                summary = f"強勢區大戶追買 <b class='text-success'>{buy_spike_count}</b> 次"
                conclusion = f"股價距離前高不遠（無深幅回撤），卻依然出現大戶真金白銀追價買進。<br><span class='mt-1 d-block'>📅 <b>近期爆量：</b>{spike_dates_str}</span>{cost_str}<br><span class='text-muted'>💡 右側順勢策略：切記以大戶買入均價作為防守停損點。</span>"
                priority = 3
            elif res['rsi'] > 65 and sell_spike_count >= 2:
                trace_type = "<span class='badge bg-warning text-dark fs-6 py-2'>⚠️ 高位放量大跌 (派發)</span>"
                summary = f"高位區倒貨 <b class='text-dark'>{sell_spike_count}</b> 次"
                conclusion = f"股價相對高位出現大陰線出貨。<br><span class='mt-1 d-block'>📅 <b>爆量日：</b>{spike_dates_str}</span>{cost_str}<br>主力趁利多派發籌碼，需嚴格停損。"
                priority = 2
            
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

    whale_rows = "".join([f"<tr><td class='fw-bold text-center'>{w['ticker']}</td><td class='text-center'>{w['type']}</td><td class='text-center'>{w['summary']}</td><td class='text-start'>{w['conclusion']}</td><td class='text-center'>{w['recent_7d']}</td></tr>" for w in whale_traces])
    
    # 【已修復】改用安全的寫法避免 f-string backslash 報錯
    weekly_rows_list = []
    for r in results:
        if r['source'] == '核心池' or (pd.notna(r['weekly_k']) and r['weekly_k']<25) or (pd.notna(r['weekly_wr']) and r['weekly_wr']>75) or (pd.notna(r['weekly_mfi']) and r['weekly_mfi']<35):
            k_html = f"<span class='text-danger fw-bold fs-6'>{fmt_num(r['weekly_k'])}</span>" if pd.notna(r['weekly_k']) and r['weekly_k']<25 else fmt_num(r['weekly_k'])
            wr_html = f"<span class='text-danger fw-bold fs-6'>{fmt_num(r['weekly_wr'])}</span>" if pd.notna(r['weekly_wr']) and r['weekly_wr']>75 else fmt_num(r['weekly_wr'])
            mfi_html = f"<span class='text-danger fw-bold fs-6'>{fmt_num(r['weekly_mfi'])}</span>" if pd.notna(r['weekly_mfi']) and r['weekly_mfi']<35 else fmt_num(r['weekly_mfi'])
            row = f"<tr><td class='fw-bold'>{r['ticker']}</td><td class='fw-bold text-danger'>{r['tot_score']}</td><td>{k_html} / {fmt_num(r['weekly_d'])}</td><td>{wr_html}</td><td>{mfi_html}</td><td>Beta:{fmt_num(r['beta'])}</td></tr>"
            weekly_rows_list.append(row)
    weekly_rows = "".join(weekly_rows_list)
    
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

    table_rows = "".join([f"<tr><td class='fw-bold'>{r['ticker']}</td><td>{fmt_num(r['price'],2)} <span class='{'text-success' if r['change']>0 else 'text-danger'}'>({fmt_num(r['change'])}%)</span></td><td class='fw-bold text-danger'>{fmt_num(r['stop_loss'],2)}</td><td class='{'text-danger fw-bold' if r['earnings']!='N/A' else ''}'>{r['earnings']}</td><td class='fs-5 fw-bold text-primary'>{r['tot_score']}</td><td>{hl(r['rsi'], r['rsi']<30)}</td><td>{hl(r['wr'], r['wr']>80)}</td><td>{hl(r['vr'], r['vr']<70)}</td><td class='text-danger fw-bold'>{fmt_num(r['max_dd_10d'])}%</td><td>{fmt_num(r['pe'])}</td><td>{fmt_num(r['roe'])}%</td><td>{fmt_num(r['div_yield'])}%</td><td>{hl(r['pcr'], r['pcr'] and r['pcr']>1.2, '{:.2f}')}</td></tr>" for r in results])

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
        <b>📘 核心指標白話解讀：</b><br>
        • <b class='text-primary'>總低估分 (滿分100)：</b> 包含 40%技術超賣 + 40%資金枯竭 + 20%基本面便宜。分數越高代表左側抄底贏面越大。<br>
        • <b class='text-danger'>防守停損：</b> 基於 ATR 計算的動態防守底線，若收盤跌穿應嚴格執行紀律。<br>
        • <b>RSI：</b> &lt;30為超賣(紅)。 <b>WR：</b> &gt;80為恐慌(紅)。 <b>VR：</b> &lt;70為無人問津(紅)。
    </div>
    <div class='table-responsive'>
        <table class='table table-bordered table-hover align-middle text-center interactive-dt' style='white-space:nowrap;'>
            <thead><tr><th class='text-start'>股票</th><th>現價(%)</th><th class='bg-danger text-white'>防守停損</th><th class='bg-warning text-dark'>財報日</th><th class='bg-primary text-white'>低估分</th><th>RSI</th><th>WR</th><th>VR</th><th>回撤</th><th>PE</th><th>ROE</th><th>息率</th><th>PCR</th></tr></thead>
            <tbody>{table_rows}</tbody>
        </table>
    </div>
</div>

</div>

<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
<script>
    $(document).ready(function() {{
        $('.interactive-dt').DataTable({{
            "pageLength": 25,
            "order": [], 
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

    with open('docs/index.html', 'w', encoding='utf-8') as f: f.write(html)

if __name__ == '__main__':
    print(f"🚀 開始雲端執行週期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    main()
    print("✅ 執行完畢，HTML 已生成至 docs/index.html")