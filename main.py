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

BASETICKERS = ['HSI', 'SPY', 'QQQ', '^IXIC', 'BABA', 'PDD', 'JD', 'BIDU', 'NIO', 'XPEV', 'LI', 'MSTR', 'PFE', 'LITE', 'UNH', 'UBER', 'LLY', 'ADBE', 'CRM', 'ORCL', 'PYPL']
HSICOMP = ['0700.HK', '9988.HK', '3690.HK', '0005.HK', '0941.HK', '1299.HK', '0883.HK', '0388.HK', '2318.HK', '0001.HK', '0002.HK', '0003.HK', '0011.HK', '0016.HK', '0027.HK', '0066.HK', '0386.HK', '0857.HK', '0939.HK', '0981.HK', '0992.HK', '1088.HK', '1093.HK', '1109.HK', '1113.HK', '1398.HK', '1810.HK', '1928.HK', '2020.HK', '2269.HK', '2319.HK', '2388.HK', '2628.HK', '3988.HK', '9618.HK', '9999.HK', '2015.HK', '0288.HK', '2331.HK']
DJICOMP = ['AAPL', 'AMGN', 'AXP', 'BA', 'CAT', 'CRM', 'CSCO', 'CVX', 'DIS', 'DOW', 'GS', 'HD', 'HON', 'IBM', 'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE', 'PG', 'TRV', 'UNH', 'V', 'VZ', 'WMT']
NDXCOMP = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'AVGO', 'COST', 'PEP', 'TMUS', 'CSCO', 'NFLX', 'AMD', 'INTC', 'QCOM', 'TXN', 'AMGN', 'INTU', 'AMAT', 'ISRG', 'MDLZ', 'BKNG', 'SBUX', 'GILD', 'ADP', 'VRTX', 'REGN', 'LRCX', 'ADI', 'PANW', 'SNPS', 'KLAC', 'CDNS', 'MAR', 'CRWD', 'ORLY', 'FTNT', 'CTAS', 'NXPI', 'PCAR', 'ROST', 'PAYX', 'MNST', 'MRVL', 'CEG', 'DXCM', 'KDP', 'CPRT', 'MSTR', 'ARM']
SPXCOMP = list(set(DJICOMP + NDXCOMP + ['BRK-B', 'LLY', 'XOM', 'MA', 'ABBV', 'BAC', 'TMO', 'ABT', 'CMCSA', 'PFE', 'T', 'DHR', 'NEE', 'PM', 'RTX', 'UNP', 'BMY', 'LOW', 'COP', 'SPGI', 'GE', 'PLD', 'MDT', 'CAT', 'CVS', 'BLK', 'DE', 'SYK', 'C', 'NOW', 'TJX', 'ZTS', 'BSX', 'FI', 'PGR', 'MMC', 'SCHW', 'LMT', 'CB', 'UBER']))
SECTORETFS = {'XLK': '科技', 'XLF': '金融', 'XLV': '醫療', 'XLE': '能源', 'XLB': '材料', 'XLI': '工業', 'XLY': '可選消費', 'XLP': '必選消費', 'XLU': '公用事業', 'XLC': '通訊', 'XLRE': '房地產'}

GANNANCHORS = [
    {'market': '美股', 'date': '2020-03-23', 'type': '底', 'desc': '疫情底'},
    {'market': '美股', 'date': '2022-10-13', 'type': '底', 'desc': '通膨底'},
    {'market': '港股', 'date': '2022-10-31', 'type': '底', 'desc': '清零底'},
    {'market': '美股', 'date': '2023-10-27', 'type': '底', 'desc': 'AI起漲'},
    {'market': '港股', 'date': '2024-05-20', 'type': '頂', 'desc': '19,706頂'},
    {'market': '美股', 'date': '2024-08-05', 'type': '底', 'desc': 'VIX底'},
    {'market': '美股', 'date': '2024-11-05', 'type': '底', 'desc': '大選底'},
    {'market': '港股', 'date': '2026-01-27', 'type': '底', 'desc': '45天頂'}
]
GANNCYCLES = [13, 21, 34, 45, 55, 89, 90, 120, 144, 180, 233, 240, 360]

def gettopturnoverbatch(pool, n):
    try:
        df = yf.download(pool, period='5d', progress=False, auto_adjust=False)
        turnovers = {}
        if isinstance(df.columns, pd.MultiIndex):
            for t in pool:
                if t in df['Close']:
                    try:
                        closeval = df['Close'][t].dropna().iloc[-1]
                        volval = df['Volume'][t].dropna().iloc[-1]
                        turnovers[t] = float(closeval) * float(volval)
                    except: pass
        else:
            if not df.empty and 'Close' in df and 'Volume' in df:
                turnovers[pool[0]] = float(df['Close'].iloc[-1]) * float(df['Volume'].iloc[-1])
        sortedtickers = sorted(turnovers.items(), key=lambda x: x[1], reverse=True)
        return [k for k, v in sortedtickers[:n]]
    except Exception:
        return pool[:n]

def getdynamictopturnovertickers():
    tophsi = gettopturnoverbatch(HSICOMP, 20)
    topndx = gettopturnoverbatch(NDXCOMP, 20)
    topspx = gettopturnoverbatch(SPXCOMP, 30)
    topdji = gettopturnoverbatch(DJICOMP, 20)
    return tophsi, topndx, topspx, topdji

def getmacroandsectors():
    macro = {'dxy': {}, 'us10y': {}, 'spypcr': {}}
    try:
        dfdxy = yf.download('DX-Y.NYB', period='1y', progress=False, auto_adjust=False)
        df10y = yf.download('^TNX', period='1y', progress=False, auto_adjust=False)
        if isinstance(dfdxy.columns, pd.MultiIndex): dfdxy.columns = dfdxy.columns.droplevel(1)
        if isinstance(df10y.columns, pd.MultiIndex): df10y.columns = df10y.columns.droplevel(1)
        dxynow = float(dfdxy['Close'].iloc[-1])
        y10now = float(df10y['Close'].iloc[-1])
        dxyspark = makesparkbar(dfdxy['Close'].tail(10), 'info')
        y10spark = makesparkbar(df10y['Close'].tail(10), 'danger')
        macro['dxy'] = {'val': f"{dxynow:.2f}", 'chg': (dxynow-float(dfdxy['Close'].iloc[-6]))/1100, 'context': f"10日趨勢<br>{dxyspark}"}
        macro['us10y'] = {'val': f"{y10now:.3f}%", 'chg': (y10now-float(df10y['Close'].iloc[-6]))/1100, 'context': f"10日趨勢<br>{y10spark}"}
        spy = yf.Ticker('SPY')
        opts = spy.options
        if opts:
            chain = spy.option_chain(opts[0])
            pvol, cvol = chain.puts['volume'].sum(), chain.calls['volume'].sum()
            pcr = pvol / cvol if cvol > 0 else 1
            macro['spypcr'] = {'val': f"{pcr:.2f}", 'status': '風險偏好低' if pcr > 1.2 else '風險偏好高' if pcr < 0.7 else '中性'}
        else: macro['spypcr'] = {'val': 'N/A', 'status': '-'}
    except: pass
    sectorsperf = []
    for sym, name in SECTORETFS.items():
        try:
            df = yf.download(sym, period='10d', progress=False, auto_adjust=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
                ret = (float(df['Close'].iloc[-1]) / float(df['Close'].iloc[0]) - 1) * 100
                sectorsperf.append({'sym': sym, 'name': name, 'ret': ret})
        except: pass
    sectorsperf.sort(key=lambda x: x['ret'], reverse=True)
    return macro, sectorsperf

def makesparkbar(series, colorclass):
    try:
        vals = [float(x) for x in series if pd.notna(x)]
        if not vals: return ""
        vmin, vmax = min(vals), max(vals)
        rng = vmax - vmin if vmax != vmin else 1
        bars = ""
        for v in vals:
            h = max(5, (v - vmin) / rng * 100)
            ccolor = 'danger' if colorclass == 'auto' and v < vals[0] else 'success' if colorclass == 'auto' else colorclass
            bars += f"<div style='display:inline-block; flex:1; margin:0 1px; height:{h}%; background-color: var(--bs-{ccolor}); border-radius:1px;' title='{v:.2f}'></div>"
        return f"<div style='height:30px; width:100%; display:flex; align-items:flex-end; margin-top:5px; background: rgba(255,255,255,0.03); padding: 2px; border-radius:3px;'>{bars}</div>"
    except: return ""

def getmarketsentiment():
    ussentiment = {'vix': {'val': 'N/A', 'status': '', 'color': 'secondary', 'context': ''}, 'spyrsi': {'val': 'N/A', 'status': '', 'color': 'secondary', 'context': ''}, 'spyvolchg': {'val': 'N/A', 'status': '', 'color': 'secondary', 'context': ''}}
    hksentiment = {'hsirsi': {'val': 'N/A', 'status': '', 'color': 'secondary', 'context': ''}, 'hsidist': {'val': 'N/A', 'status': '', 'color': 'secondary', 'context': ''}, 'hsivolchg': {'val': 'N/A', 'status': '', 'color': 'secondary', 'context': ''}, 'southbound': {'val': 'Proxy估算', 'status': '', 'color': 'secondary', 'context': ''}}
    try:
        hsceidf = yf.download('2828.HK', period='15d', progress=False).ffill()
        hsidf = yf.download('2800.HK', period='15d', progress=False).ffill()
        hsiidx = yf.download('^HSI', period='60d', progress=False).ffill()
        if isinstance(hsceidf.columns, pd.MultiIndex): hsceidf.columns = hsceidf.columns.droplevel(1)
        if isinstance(hsidf.columns, pd.MultiIndex): hsidf.columns = hsidf.columns.droplevel(1)
        if isinstance(hsiidx.columns, pd.MultiIndex): hsiidx.columns = hsiidx.columns.droplevel(1)
        
        if 'Volume' in hsceidf and 'Volume' in hsidf:
            hsceivol = hsceidf['Volume'].replace(0, pd.NA).dropna()
            hsivol = hsidf['Volume'].replace(0, pd.NA).dropna()
            if len(hsceivol) >= 5 and len(hsivol) >= 5:
                hsceivr = float(hsceivol.iloc[-1]) / (float(hsceivol.rolling(5).mean().iloc[-1]) + 1e-8)
                hsivr = float(hsivol.iloc[-1]) / (float(hsivol.rolling(5).mean().iloc[-1]) + 1e-8)
                sbratio = hsceivr / (hsivr + 1e-8)
                if sbratio > 1.2: hksentiment['southbound'] = {'val': '流入', 'status': '買盤強', 'color': 'danger', 'context': '國企/恒指量比>1.2'}
                elif sbratio < 0.8: hksentiment['southbound'] = {'val': '流出', 'status': '賣盤增', 'color': 'info text-dark', 'context': '國企/恒指量比<0.8'}
                else: hksentiment['southbound'] = {'val': '持平', 'status': '觀望', 'color': 'success', 'context': '國企/恒指量比正常'}
        
        if not hsiidx.empty:
            closepx = hsiidx['Close']
            biasseries = (closepx / closepx.rolling(20).mean() - 1) * 100
            bias = float(biasseries.iloc[-1])
            hksentiment['hsidist'] = {'val': f"{bias:.2f}%", 'color': 'danger' if bias > 5 else 'success' if bias < -5 else 'warning text-dark', 'status': '超買' if bias > 5 else '超賣' if bias < -5 else '中性', 'context': f"10日趨勢<br>{makesparkbar(biasseries.tail(10), 'info')}"}
            delta = closepx.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = -delta.clip(upper=0).rolling(14).mean()
            rsiseries = 100 - (100 / (1 + gain / (loss + 1e-8)))
            rsinow = float(rsiseries.iloc[-1])
            hksentiment['hsirsi'] = {'val': f"{rsinow:.1f}", 'color': 'danger' if rsinow > 70 else 'success' if rsinow < 30 else 'primary', 'status': '過熱' if rsinow > 70 else '超賣' if rsinow < 30 else '健康', 'context': f"10日趨勢<br>{makesparkbar(rsiseries.tail(10), 'primary')}"}
        
        if 'Volume' in hsidf:
            hvol = hsidf['Volume'].replace(0, pd.NA).dropna()
            if len(hvol) >= 5:
                vrserieshk = hvol / hvol.rolling(5).mean()
                vr = float(vrserieshk.iloc[-1])
                hksentiment['hsivolchg'] = {'val': f"{vr:.2f}x", 'color': 'danger' if vr > 1.3 else 'info text-dark' if vr < 0.8 else 'success', 'status': '放量' if vr > 1.3 else '縮量' if vr < 0.8 else '平穩', 'context': f"10日趨勢<br>{makesparkbar(vrserieshk.tail(10), 'success')}"}
    except Exception as e: print(f"HK Data Error: {e}")

    try:
        vdf = yf.download('^VIX', period='1y', progress=False, auto_adjust=False)
        if not vdf.empty:
            if isinstance(vdf.columns, pd.MultiIndex): vdf.columns = vdf.columns.droplevel(1)
            vval = float(vdf['Close'].iloc[-1])
            vmin, vmax = float(vdf['Low'].min()), float(vdf['High'].max())
            vpct = (vval - vmin) / (vmax - vmin + 1e-8) * 100
            ussentiment['vix']['val'] = f"{vval:.2f}"
            ussentiment['vix']['color'] = 'success' if vval < 20 else 'danger' if vval > 30 else 'warning text-dark'
            ussentiment['vix']['status'] = '安全' if vval < 20 else '恐慌' if vval > 30 else '警戒'
            ussentiment['vix']['context'] = f"10日趨勢<br>{makesparkbar(vdf['Close'].tail(10), 'warning')}<br>1年區間: {vmin:.1f} - {vmax:.1f} (分位數: {vpct:.1f}%)"
    except: pass

    for tsym, sdict in [('SPY', ussentiment)]:
        try:
            dfidx = yf.download(tsym, period='1y', progress=False, auto_adjust=False)
            if not dfidx.empty:
                if isinstance(dfidx.columns, pd.MultiIndex): dfidx.columns = dfidx.columns.droplevel(1)
                delta = dfidx['Close'].diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = -delta.clip(upper=0).rolling(14).mean()
                rsiseries = 100 - (100 / (1 + gain / (loss + 1e-8)))
                rsinow = float(rsiseries.iloc[-1])
                rsimin, rsimax = float(rsiseries.min()), float(rsiseries.max())
                rsipct = (rsinow - rsimin) / (rsimax - rsimin + 1e-8) * 100
                sdict['spyrsi']['val'] = f"{rsinow:.1f}"
                sdict['spyrsi']['color'] = 'danger' if rsinow > 70 else 'success' if rsinow < 30 else 'primary'
                sdict['spyrsi']['status'] = '過熱' if rsinow > 70 else '超賣' if rsinow < 30 else '健康'
                sdict['spyrsi']['context'] = f"10日趨勢<br>{makesparkbar(rsiseries.tail(10), 'primary')}<br>1年區間: {rsimin:.1f} - {rsimax:.1f} (分位數: {rsipct:.1f}%)"
                
                volma5series = dfidx['Volume'].rolling(5).mean()
                vrseries = dfidx['Volume'] / volma5series
                vr = float(vrseries.iloc[-1])
                vrmin, vrmax = float(vrseries.dropna().min()), float(vrseries.dropna().max())
                vrpct = (vr - vrmin) / (vrmax - vrmin + 1e-8) * 100
                if not pd.isna(vr):
                    sdict['spyvolchg']['val'] = f"{vr:.2f}x"
                    sdict['spyvolchg']['color'] = 'danger' if vr > 1.3 else 'info text-dark' if vr < 0.8 else 'success'
                    sdict['spyvolchg']['status'] = '放量' if vr > 1.3 else '縮量' if vr < 0.8 else '平穩'
                    sdict['spyvolchg']['context'] = f"10日趨勢<br>{makesparkbar(vrseries.tail(10), 'success')}<br>1年區間: {vrmin:.1f}x - {vrmax:.1f}x (分位數: {vrpct:.1f}%)"
        except: pass
    return ussentiment, hksentiment

def getoptionspcr(ticker):
    try:
        tk = yf.Ticker(ticker)
        opts = tk.options
        if not opts: return None
        chain = tk.option_chain(opts[0])
        cv = chain.calls['volume'].sum()
        pv = chain.puts['volume'].sum()
        if cv > 0: return pv / cv
    except: return None

def calcscores(r):
    tscore, vitems = 0, 0
    if pd.notna(r.get('rsi')): vitems+=1; tscore += 25 if r['rsi']<30 else 15 if r['rsi']<45 else 0
    if pd.notna(r.get('wr')): vitems+=1; tscore += 25 if r['wr']>80 else 15 if r['wr']>60 else 0
    if pd.notna(r.get('cci')): vitems+=1; tscore += 25 if r['cci']<-100 else 15 if r['cci']<0 else 0
    if pd.notna(r.get('kdjj')): vitems+=1; tscore += 25 if r['kdjj']<20 else 15 if r['kdjj']<50 else 0
    tscore = min(tscore * (4 / max(vitems, 1)), 100)
    
    fscore, vitems = 0, 0
    if pd.notna(r.get('vr')): vitems+=1; fscore += 40 if r['vr']>70 else 20 if r['vr']<100 else 0
    if pd.notna(r.get('mfi')): vitems+=1; fscore += 30 if r['mfi']<30 else 15 if r['mfi']<50 else 0
    if pd.notna(r.get('drawdownswing')): vitems+=1; fscore += 30 if r['drawdownswing']<-20 else 15 if r['drawdownswing']<-10 else 0
    fscore = min(fscore * (3 / max(vitems, 1)), 100)
    
    bscore, vitems = 0, 0
    if pd.notna(r.get('pe')) and r['pe']>0: vitems+=1; bscore += 15 if r['pe']<15 else 10 if r['pe']<25 else 0
    if pd.notna(r.get('pb')) and r['pb']>0: vitems+=1; bscore += 15 if r['pb']<1.2 else 10 if r['pb']<2 else 0
    if pd.notna(r.get('roe')) and r['roe']>15: vitems+=1; bscore += 20
    if pd.notna(r.get('fcfyield')) and r['fcfyield']>4: vitems+=1; bscore += 20
    if pd.notna(r.get('debteq')) and r['debteq']<0.5: vitems+=1; bscore += 15
    bscore = min(bscore * (4 / max(vitems, 1)), 100)
    tot = int(tscore*0.4 + fscore*0.4 + bscore*0.2)
    return min(tscore, 100), min(fscore, 100), min(bscore, 100), tot

def addcommonindicators(df):
    df = df.copy()
    df['VolMA5'] = df['Volume'].rolling(5).mean()
    df['VolRatio'] = df['Volume'] / (df['VolMA5'] + 1e-8)
    df['52WHigh'] = df['High'].rolling(252).max()
    df['Drawdown'] = (df['Close'] - df['52WHigh']) / (df['52WHigh'] + 1e-8) * 100
    df['OBV'] = np.sign(df['Close'].diff().fillna(0)) * df['Volume']
    df['OBV'] = df['OBV'].cumsum()
    df['TR'] = pd.concat([df['High'] - df['Low'], (df['High'] - df['Close'].shift(1)).abs(), (df['Low'] - df['Close'].shift(1)).abs()], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(14).mean()
    rollhigh = df['High'].rolling(10).max()
    rolllow = df['Low'].rolling(10).min()
    df['MaxDD10d'] = (rolllow - rollhigh) / (rollhigh + 1e-8) * 100
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain / (loss + 1e-8)))
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    tpsma = tp.rolling(20).mean()
    md = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=False)
    df['CCI'] = (tp - tpsma) / (0.015 * md + 1e-8)
    lowmin = df['Low'].rolling(9).min()
    highmax = df['High'].rolling(9).max()
    df['RSV'] = (df['Close'] - lowmin) / (highmax - lowmin + 1e-8) * 100
    df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']
    hh14, ll14 = df['High'].rolling(14).max(), df['Low'].rolling(14).min()
    df['WR'] = (hh14 - df['Close']) / (hh14 - ll14 + 1e-8) * 100
    moneyflow = tp * df['Volume']
    possum = moneyflow.where(tp > tp.shift(1), 0.0).rolling(14).sum()
    negsum = moneyflow.where(tp < tp.shift(1), 0.0).rolling(14).sum()
    df['MFI'] = 100 - (100 / (1 + possum / (negsum + 1e-8)))
    chg = df['Close'].diff().fillna(0)
    upvol = df['Volume'].where(chg > 0, 0).rolling(26).sum()
    downvol = df['Volume'].where(chg < 0, 0).rolling(26).sum()
    flatvol = df['Volume'].where(chg == 0, 0).rolling(26).sum()
    df['VR'] = (upvol + 0.5 * flatvol) / (downvol + 0.5 * flatvol + 1e-8) * 100
    df['Ret5d'] = df['Close'].pct_change(5) * 100
    return df

def getweeklydf(df):
    w = df[['Open', 'High', 'Low', 'Close', 'Volume']].resample('W-FRI').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    return addcommonindicators(w)

def trainaimodels(df):
    dfml = df.dropna().copy()
    if len(dfml) < 130: return None, 0
    features = ['RSI', 'CCI', 'J', 'WR', 'MFI', 'Drawdown', 'VolRatio', 'VR', 'Ret5d']
    X = dfml[features][:-10]
    yclf = (dfml['Close'].shift(-5) > dfml['Close'] * 1.02)[:-10].astype(int)
    rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    rf.fit(X, yclf)
    buyprob = rf.predict_proba(dfml.iloc[[-1]][features])[0][1] * 100
    return dict(zip(features, rf.feature_importances_)), buyprob

def getsubscores(r):
    tscore = sum([15 if r['rsi']<30 else 0, 10 if r['cci']<-100 else 0, 15 if r['kdjj']<0 else 0, 15 if r['wr']>80 else 0, 20 if pd.notna(r['weeklyk']) and r['weeklyk']<20 and r['weeklyd']<20 else 0, 10 if pd.notna(r['weeklywr']) and r['weeklywr']>80 else 0])
    fscore = sum([30 if r['mfi']<20 else 15 if r['mfi']<30 else 0, 20 if r['vr']<40 else 0, 20 if pd.notna(r['weeklymfi']) and r['weeklymfi']<30 else 0])
    bscore, vitems = 0, 0
    if pd.notna(r['pe']) and r['pe']>0: vitems+=1; bscore += 15 if r['pe']<15 else 10 if r['pe']<25 else 0
    if pd.notna(r['pb']) and r['pb']>0: vitems+=1; bscore += 15 if r['pb']<1.2 else 10 if r['pb']<2 else 0
    if pd.notna(r['peg']) and r['peg']>0: vitems+=1; bscore += 15 if r['peg']<1.0 else 10 if r['peg']<0.8 else 0
    if pd.notna(r['divyield']) and r['divyield']>0: vitems+=1; bscore += 15 if r['divyield']>4 else 10 if r['divyield']>6 else 0
    bscore = min(bscore * (4 / vitems), 100) if vitems > 0 else 0
    return min(tscore, 100), min(fscore, 100), min(bscore, 100), int(tscore*0.4 + fscore*0.4 + bscore*0.2)

def fmtnum(x, nd=1): return str(round(float(x), nd)) if not pd.isna(x) else "N/A"

def main():
    os.makedirs('docs', exist_ok=True)
    tophsi, topndx, topspx, topdji = getdynamictopturnovertickers()
    alltickers = list(dict.fromkeys(BASETICKERS + tophsi + topndx + topspx + topdji))
    macrodata, sectorsperf = getmacroandsectors()
    ussent, hksent = getmarketsentiment()
    results, whaletraces, pricehistory = [], [], {}
    anomalies7days = []
    
    riskstatus = "中性"
    riskcolor = "warning"
    if macrodata.get('dxy', {}).get('chg', 0) > 1 or macrodata.get('us10y', {}).get('chg', 0) > 3:
        riskstatus = "Risk-Off (緊縮)"
        riskcolor = "danger"
    elif macrodata.get('dxy', {}).get('chg', 0) < -0.5 and macrodata.get('us10y', {}).get('chg', 0) < -1:
        riskstatus = "Risk-On (寬鬆)"
        riskcolor = "success"

    chartshtml = ""
    for idxticker, title in [('^HSI', '恒生指數'), ('SPY', 'SP 500')]:
        try:
            dfidx = yf.download(idxticker, period='5y', progress=False, auto_adjust=False)
            if dfidx.empty: continue
            if isinstance(dfidx.columns, pd.MultiIndex): dfidx.columns = dfidx.columns.droplevel(1)
            fig = go.Figure(data=[go.Candlestick(x=dfidx.index, open=dfidx['Open'], high=dfidx['High'], low=dfidx['Low'], close=dfidx['Close'])])
            fig.update_layout(title=dict(text=title, font=dict(color='#e2e8f0')), height=300, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='#1e293b', plot_bgcolor='#1e293b', xaxis=dict(gridcolor='#334155', tickfont=dict(color='#94a3b8'), range=[datetime.now() - timedelta(days=730), datetime.now() + timedelta(days=30)]), yaxis=dict(gridcolor='#334155', tickfont=dict(color='#94a3b8')))
            chartshtml += f"<div class='col-xl-6 mb-2'>{fig.to_html(full_html=False, include_plotlyjs='cdn')}</div>"
        except: pass

    for i, ticker in enumerate(alltickers, start=1):
        try:
            tk = yf.Ticker(ticker)
            df = yf.download(ticker, period='2y', progress=False, auto_adjust=False)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            if ticker in BASETICKERS: pricehistory[ticker] = df['Close'].tail(30)
            df = addcommonindicators(df).dropna()
            wdf = getweeklydf(df)
            info = {}
            earningsdate = "N/A"
            if not ticker.startswith('^'):
                try: info = tk.info
                except: pass
                try:
                    cal = tk.get_calendar()
                    if isinstance(cal, dict) and 'Earnings Date' in cal: earningsdate = pd.to_datetime(cal['Earnings Date'][0]).strftime('%Y-%m-%d')
                    elif isinstance(cal, pd.DataFrame) and not cal.empty and 'Earnings Date' in cal.index: earningsdate = pd.to_datetime(cal.loc['Earnings Date'].iloc[0]).strftime('%Y-%m-%d')
                except: pass
            pcr = None
            if ticker in BASETICKERS and not ticker.startswith('^'): pcr = getoptionspcr(ticker)
            impres = trainaimodels(df)
            buyprob = impres[1] if impres else 0
            currprice = float(df['Close'].iloc[-1])
            atrval = float(df['ATR'].iloc[-1])

            insidersignal = ""
            try:
                ip = tk.insider_purchases
                if ip is not None and not ip.empty:
                    prow = ip[ip['Insider Purchases'] == 'Last 6m Purchases']
                    srow = ip[ip['Insider Purchases'] == 'Last 6m Sales']
                    nrow = ip[ip['Insider Purchases'] == 'Last 6m Net Shares Purchased (Sold)']
                    purchases = int(prow['Trans'].iloc[0]) if not prow.empty and pd.notna(prow['Trans'].iloc[0]) else 0
                    sales = int(srow['Trans'].iloc[0]) if not srow.empty and pd.notna(srow['Trans'].iloc[0]) else 0
                    netshares = float(nrow['Shares'].iloc[0]) if not nrow.empty and pd.notna(nrow['Shares'].iloc[0]) else 0
                    if purchases > sales and netshares > 0: insidersignal = f"<div class='badge bg-danger mt-1'>內部買入:{purchases}筆</div>"
                    elif sales > max(1, purchases * 2): insidersignal = f"<div class='badge bg-dark text-warning mt-1'>內部拋售:-{sales}筆</div>"
            except: pass

            roeval = float(info.get('returnOnEquity') or 0) * 100
            debteq = float(info.get('debtToEquity') or 100) / 100
            opmargin = float(info.get('operatingMargins') or 0) * 100
            fcf = float(info.get('freeCashflow') or 0)
            marketcap = float(info.get('marketCap') or 0)
            fcfyield = (fcf / marketcap) * 100 if marketcap > 0 else np.nan
            buffetttags = []
            if roeval > 15: buffetttags.append('高ROE')
            if debteq < 0.5: buffetttags.append('低債')
            if opmargin > 15: buffetttags.append('高潤')
            if pd.notna(fcfyield) and fcfyield > 4: buffetttags.append('強現')
            buffettbadge = f"<div class='mt-1' style='font-size:0.7rem; color:#f59e0b;'>{','.join(buffetttags)}</div>" if buffetttags else "<div></div>"

            h2y = float(df['High'].rolling(756, min_periods=1).max().iloc[-1])
            l2y = float(df['Low'].rolling(756, min_periods=1).min().iloc[-1])
            diff2y = h2y - l2y
            fib2y = {236: h2y - 0.236*diff2y, 382: h2y - 0.382*diff2y, 500: h2y - 0.5*diff2y, 618: h2y - 0.618*diff2y, 786: h2y - 0.786*diff2y}

            lookbackdays = min(120, len(df))
            recentdf = df.tail(lookbackdays)
            recenthigh = float(recentdf['High'].max())
            recentlow = float(recentdf['Low'].min())
            diffswing = recenthigh - recentlow
            fibswing = {236: recenthigh - 0.236*diffswing, 382: recenthigh - 0.382*diffswing, 500: recenthigh - 0.5*diffswing, 618: recenthigh - 0.618*diffswing, 786: recenthigh - 0.786*diffswing}
            ma50 = float(df['Close'].rolling(50, min_periods=1).mean().iloc[-1])

            swingfibstr = f"<small class='text-muted'>23.6%: {fibswing[236]:.1f}<br>38.2%: {fibswing[382]:.1f}<br>50.0%: {fibswing[500]:.1f}<br>61.8%: {fibswing[618]:.1f}<br>78.6%: {fibswing[786]:.1f}</small>"
            macrofibstr = f"<small class='text-primary'>23.6%: {fib2y[236]:.1f}<br>38.2%: {fib2y[382]:.1f}<br>50.0%: {fib2y[500]:.1f}<br>61.8%: {fib2y[618]:.1f}<br>78.6%: {fib2y[786]:.1f}</small>"
            if abs(fibswing[618] - ma50) / (ma50 + 1e-8) < 0.02: swingfibstr += "<br><span class='badge bg-warning text-dark mt-1'>0.618=50MA(強撐)</span>"
            elif abs(fibswing[500] - ma50) / (ma50 + 1e-8) < 0.02: swingfibstr += "<br><span class='badge bg-warning text-dark mt-1'>0.5=50MA(中撐)</span>"
            if abs(fib2y[618] - ma50) / (ma50 + 1e-8) < 0.02: macrofibstr += "<br><span class='badge bg-info text-dark mt-1'>0.618=50MA(大底)</span>"
            elif abs(fib2y[500] - ma50) / (ma50 + 1e-8) < 0.02: macrofibstr += "<br><span class='badge bg-info text-dark mt-1'>0.5=50MA(中底)</span>"

            dropfromhigh2y = (currprice - h2y) / (h2y + 1e-8) * 100
            dropfromswinghigh = (currprice - recenthigh) / (recenthigh + 1e-8) * 100

            res = {
                'ticker': ticker, 'source': '基本池' if ticker in BASETICKERS else '異動池',
                'price': currprice, 'change': float(df['Close'].pct_change().iloc[-1])*100,
                'rsi': float(df['RSI'].iloc[-1]), 'cci': float(df['CCI'].iloc[-1]),
                'kdjk': float(df['K'].iloc[-1]), 'kdjd': float(df['D'].iloc[-1]), 'kdjj': float(df['J'].iloc[-1]),
                'wr': float(df['WR'].iloc[-1]), 'mfi': float(df['MFI'].iloc[-1]), 'vr': float(df['VR'].iloc[-1]),
                'drawdown2y': dropfromhigh2y, 'drawdownswing': dropfromswinghigh,
                'swingfibstr': swingfibstr, 'macrofibstr': macrofibstr,
                'maxdd10d': float(df['MaxDD10d'].iloc[-1]),
                'weeklyk': float(wdf['K'].iloc[-1]) if len(wdf) else np.nan, 'weeklyd': float(wdf['D'].iloc[-1]) if len(wdf) else np.nan,
                'weeklywr': float(wdf['WR'].iloc[-1]) if len(wdf) else np.nan, 'weeklymfi': float(wdf['MFI'].iloc[-1]) if len(wdf) else np.nan,
                'weeklyvr': float(wdf['VR'].iloc[-1]) if len(wdf) else np.nan,
                'pe': info.get('trailingPE') or info.get('forwardPE'), 'pb': info.get('priceToBook'), 'peg': info.get('pegRatio'),
                'divyield': (info.get('trailingAnnualDividendYield') or 0)*100, 'roe': roeval, 'beta': info.get('beta'),
                'fcfyield': fcfyield, 'debteq': debteq, 'stoploss': currprice - 2 * atrval,
                'earnings': earningsdate, 'pcr': pcr if 'pcr' in locals() else None,
                'aibuyprob': buyprob, 'insidersignal': insidersignal, 'buffettbadge': buffettbadge
            }
            restscore, resfscore, resbscore, restotscore = getsubscores(res)
            results.append(res)

            obvdivergence = False
            if len(df) >= 20:
                price20 = df['Close'][-20:].tolist()
                obv20 = df['OBV'][-20:].tolist()
                pslope = np.polyfit(range(20), price20, 1)[0]
                oslope = np.polyfit(range(20), obv20, 1)[0]
                if pslope < -0.01 and oslope > 0: obvdivergence = True

            volhistory = []
            recent7danomalies = []
            spikedatesinfo = []
            lowdatesinfo = []
            buyvwapnum, buyvwapden = 0, 0
            sellvwapnum, sellvwapden = 0, 0
            buyspikecount, sellspikecount, lowcount = 0, 0, 0
            lookback = min(22, len(df))
            for d in range(lookback):
                volr = float(df['VolRatio'].iloc[-(d + 1)])
                volhistory.append(volr)
                datestr = df.index[-(d + 1)].strftime('%m-%d')
                isgreen = float(df['Close'].iloc[-(d + 1)]) > float(df['Open'].iloc[-(d + 1)])
                tp = (float(df['High'].iloc[-(d + 1)]) + float(df['Low'].iloc[-(d + 1)]) + float(df['Close'].iloc[-(d + 1)])) / 3
                vval = float(df['Volume'].iloc[-(d + 1)])
                if volr > 1.3:
                    if isgreen:
                        buyspikecount += 1
                        spikedatesinfo.append(f"<span class='text-success fw-bold'>{datestr}({volr:.1f}x)</span>")
                        buyvwapnum += tp * vval
                        buyvwapden += vval
                    else:
                        sellspikecount += 1
                        spikedatesinfo.append(f"<span class='text-danger'>{datestr}({volr:.1f}x)</span>")
                        sellvwapnum += tp * vval
                        sellvwapden += vval
                elif volr < 0.8:
                    lowcount += 1
                    lowdatesinfo.append(f"{datestr}({volr:.1f}x)")
                if d < 7:
                    if volr > 1.3:
                        ccolor = 'success' if isgreen else 'danger'
                        recent7danomalies.append(f"<span class='badge bg-{ccolor} mb-1'>{d}天前 {isgreen} {volr:.1f}x</span>")
                        anomalies7days.append({'ticker': ticker, 'type': '放量', 'ratio': volr, 'day': d, 'date': datestr, 'isgreen': isgreen})
                    elif volr < 0.8:
                        recent7danomalies.append(f"<span class='badge bg-info text-dark mb-1'>{d}天前 縮量 {volr:.1f}x</span>")
                        anomalies7days.append({'ticker': ticker, 'type': '縮量', 'ratio': volr, 'day': d, 'date': datestr})

            buyvwap = buyvwapnum / buyvwapden if buyvwapden > 0 else 0
            sellvwap = sellvwapnum / sellvwapden if sellvwapden > 0 else 0
            coststr = ""
            if buyvwap > 0: coststr += f"<span class='text-success fw-bold d-block mt-1'>資金建倉成本: ~{buyvwap:.2f}</span>"
            if sellvwap > 0: coststr += f"<span class='text-danger fw-bold d-block'>資金派發成本: ~{sellvwap:.2f}</span>"

            nearbottom = res['drawdownswing'] < -15
            tracetype, summary, conclusion, priority = "", "", "", 0
            spikedatesstr = ", ".join(spikedatesinfo[::-1])
            lowdatesstr = ", ".join(lowdatesinfo[::-1])
            isweeklyspike = len(wdf) >= 2 and float(wdf['VR'].iloc[-1]) > 130 and res['drawdownswing'] < -20

            if isweeklyspike and obvdivergence and res['weeklyk'] < 25 and buyspikecount >= 1:
                tracetype = "<span class='badge bg-danger fs-6 py-2'>💎 週線史詩級異動</span>"
                summary = f"週線天量 + OBV底背離 + 月內重挫"
                conclusion = f"極罕見！大主力長線抄底OBV背離<br>{coststr}"
                priority = 900
            elif nearbottom and buyspikecount >= 1 and (res['mfi'] < 45 or res['rsi'] < 45 or res['kdjj'] < 20):
                tracetype = "<span class='badge bg-danger fs-6 py-2'>🔥 主力暴力洗盤吸籌</span>"
                summary = f"波段大跌後出現 <b class='text-success'>{buyspikecount}</b> 次爆量陽線"
                obvmsg = "<br><span class='text-success'>★ OBV底背離 (資金隱蔽吸籌)</span>" if obvdivergence else ""
                conclusion = f"左側抄底買點！恐慌盤湧出但被主力全部吃下<br><span class='mt-1 d-block'><b>爆量日:</b> {spikedatesstr}</span>{coststr}{obvmsg}"
                priority = 999
            elif res['drawdownswing'] < -15 and buyspikecount >= 1 and res['rsi'] < 50:
                tracetype = "<span class='badge bg-info text-dark fs-6 py-2'>📊 底部資金初現</span>"
                summary = f"跌深後出現 <b class='text-success'>{buyspikecount}</b> 次放量買盤"
                conclusion = f"初步止跌跡象，可加入觀察清單<br><span class='mt-1 d-block'><b>爆量日:</b> {spikedatesstr}</span>{coststr}<br><span class='text-muted'>建議等待縮量確認</span>"
                priority = 80
            elif res['rsi'] < 50 and lowcount >= 6:
                tracetype = "<span class='badge bg-purple fs-6 py-2'>🧊 絕對冰點地量</span>"
                summary = f"近1個月出現 <b class='text-purple'>{lowcount}</b> 次極度縮量"
                obvmsg = "<br><span class='text-success'>★ OBV底背離 (籌碼鎖定極好)</span>" if obvdivergence else ""
                conclusion = f"跌無可跌！賣盤完全枯竭，隨時一根大陽線變盤<br><span class='text-info mt-1 d-block'><b>地量日:</b> {lowdatesstr}</span>{obvmsg}"
                priority = 9000
            elif res['rsi'] > 65 and sellspikecount >= 2:
                tracetype = "<span class='badge bg-warning text-dark fs-6 py-2'>⚠️ 高檔主力派發</span>"
                summary = f"高位出現 <b class='text-dark'>{sellspikecount}</b> 次放量陰線"
                conclusion = f"主力高位出貨跡象明顯，建議獲利了結或減倉<br><span class='mt-1 d-block'><b>爆量日:</b> {spikedatesstr}</span>{coststr}<br>"
                priority = -40

            if tracetype:
                whaletraces.append({
                    'ticker': ticker, 'source': res['source'], 'type': tracetype,
                    'summary': summary, 'conclusion': conclusion,
                    'recent7d': "<br>".join(recent7danomalies) or "<span class='text-muted small'>近7天無異常</span>",
                    'priority': priority, 'score': restotscore
                })
        except: pass

    corrwarnings = []
    if len(pricehistory) > 2:
        dfpr = pd.DataFrame(pricehistory)
        dfpr = dfpr.ffill().bfill()
        corrmatrix = dfpr.corr()
        checked = set()
        for c1 in corrmatrix.columns:
            for c2 in corrmatrix.columns:
                if c1 != c2 and tuple(sorted([c1, c2])) not in checked:
                    checked.add(tuple(sorted([c1, c2])))
                    val = corrmatrix.loc[c1, c2]
                    if val > 0.85: corrwarnings.append(f"<span class='badge bg-danger mb-1'>{c1} 與 {c2} ({val:.2f})</span>")

    results.sort(key=lambda x: x['totscore'], reverse=True)
    whaletraces.sort(key=lambda x: (x['priority'], x['score']), reverse=True)

    macrohtml = f"""
    <div class='alert alert-secondary bg-dark text-light border-secondary mb-3'>
        <h6 class='fw-bold text-info mb-2'>🌎 全球總經資金流向</h6>
        <div class='row small'>
            <div class='col-md-4'>
                <ul class='mb-0 ps-3'>
                    <li><strong class='text-warning'>美元指數 (DXY):</strong><br>破105外資流出新興，破103資金流入</li>
                    <li><strong class='text-warning'>美債10年期:</strong><br>高於4.3%壓抑科技股估值</li>
                </ul>
            </div>
            <div class='col-md-4'>
                <ul class='mb-0 ps-3'>
                    <li><strong class='text-warning'>SPY PCR:</strong><br>> 1.2極度悲觀(買點), < 0.7極度樂觀(賣點)</li>
                    <li><strong class='text-warning'>恒指放量/縮量:</strong><br>VR>1.3為放量，<0.8為地量</li>
                </ul>
            </div>
            <div class='col-md-4'>
                <ul class='mb-0 ps-3'>
                    <li><strong class='text-warning'>VIX 恐慌指數:</strong><br>>20為恐慌區，>30為極度恐慌區</li>
                    <li><strong class='text-warning'>港股南北水Proxy:</strong><br>國企/恒指量比>1.2(流入)，<0.8(流出)</li>
                </ul>
            </div>
        </div>
    </div>
    <div class='row'>
        <div class='col-md-4'><div class='card border-{riskcolor} mb-3 bg-dark'><div class='card-header bg-{riskcolor} text-white fw-bold'>🌐 總體大環境狀態</div><div class='card-body text-center d-flex align-items-center justify-content-center'><h5 class='fw-bold text-{riskcolor} mb-0'>{riskstatus}</h5></div></div></div>
        <div class='col-md-4'><div class='card border-secondary mb-3 bg-dark'><div class='card-header bg-secondary text-white fw-bold'>💱 雙殺指標 (美元/美債)</div><div class='card-body py-2'><ul class='list-group list-group-flush'>
            <li class='list-group-item text-white bg-dark px-0 py-1'>
                <div class='d-flex justify-content-between'><span>DXY 美元</span><span class='fw-bold {"text-danger" if macrodata.get("dxy",{}).get("chg",0)>0 else "text-success"}'>{macrodata.get("dxy",{}).get("val","N/A")} ({fmtnum(macrodata.get("dxy",{}).get("chg","N/A"))}%)</span></div>
                <div class='text-info mt-1' style='font-size:0.75rem;'>{macrodata.get("dxy",{}).get("context","")}</div>
            </li>
            <li class='list-group-item text-white bg-dark px-0 py-1 border-bottom-0'>
                <div class='d-flex justify-content-between'><span>10年期美債</span><span class='fw-bold {"text-danger" if macrodata.get("us10y",{}).get("chg",0)>0 else "text-success"}'>{macrodata.get("us10y",{}).get("val","N/A")} ({fmtnum(macrodata.get("us10y",{}).get("chg","N/A"))}%)</span></div>
                <div class='text-info mt-1' style='font-size:0.75rem;'>{macrodata.get("us10y",{}).get("context","")}</div>
            </li>
        </ul></div></div></div>
        <div class='col-md-4'><div class='card border-dark mb-3 bg-dark'><div class='card-header bg-dark text-white fw-bold border-secondary'>🇺🇸 SPY PCR (期權避險)</div><div class='card-body text-center py-2'>
            <h4 class='fw-bold mb-1 text-light'>{macrodata.get("spypcr",{}).get("val","N/A")}</h4>
            <span class='badge bg-warning text-dark fs-6'>{macrodata.get("spypcr",{}).get("status","")}</span>
        </div></div></div>
    </div>
    """

    sentimenthtml = f"""
    <div class='row mt-2'>
        <div class='col-md-6'><div class='card border-primary mb-3 bg-dark'><div class='card-header bg-primary text-white fw-bold'>🇺🇸 美股情緒指標</div><div class='card-body'><ul class='list-group list-group-flush'>
            <li class='list-group-item d-flex justify-content-between align-items-center text-white bg-dark'><div><div class='fw-bold'>VIX 恐慌指數</div><div style='font-size:0.75rem; color:#94a3b8;'>{ussent['vix']['context']}</div></div><span class='badge bg-{ussent['vix']['color']} fs-6'>{ussent['vix']['val']} {ussent['vix']['status']}</span></li>
            <li class='list-group-item d-flex justify-content-between align-items-center text-white bg-dark'><div><div class='fw-bold'>S&P 500 RSI(14)</div><div style='font-size:0.75rem; color:#94a3b8;'>{ussent['spyrsi']['context']}</div></div><span class='badge bg-{ussent['spyrsi']['color']} fs-6'>{ussent['spyrsi']['val']} {ussent['spyrsi']['status']}</span></li>
            <li class='list-group-item d-flex justify-content-between align-items-center text-white bg-dark'><div><div class='fw-bold'>S&P 500 成交量比</div><div style='font-size:0.75rem; color:#94a3b8;'>{ussent['spyvolchg']['context']}</div></div><span class='badge bg-{ussent['spyvolchg']['color']} fs-6'>{ussent['spyvolchg']['val']} {ussent['spyvolchg']['status']}</span></li>
        </ul></div></div></div>
        <div class='col-md-6'><div class='card border-danger mb-3 bg-dark'><div class='card-header bg-danger text-white fw-bold'>🇭🇰 港股情緒指標 (Proxy)</div><div class='card-body'><ul class='list-group list-group-flush'>
            <li class='list-group-item d-flex justify-content-between 
