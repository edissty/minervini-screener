# ============================================
# MINERVINI PRO SCREENER - MULTITHREADING VERSION
# Versi 5.2 - PERBAIKAN TOTAL RS RATING & SINKRONISASI
# ============================================

import yfinance as yf
import pandas as pd
import numpy as np
import time
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from curl_cffi import requests

class MinerviniScreenerPro:
    def __init__(self, min_turnover=200_000_000, max_workers=15):
        self.index_data = None
        self.min_turnover = min_turnover
        self.max_workers = max_workers
        self.lock = Lock()
        self.results = []
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)

    def fix_data_alignment(self, df):
        """Menghapus timezone dan menormalkan waktu ke 00:00:00"""
        if df is None or df.empty:
            return None
        df = df.copy()
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.index = df.index.normalize()
        # Hapus duplikat index jika ada
        df = df[~df.index.duplicated(keep='last')]
        return df

    def fetch_ihsg_data(self):
        """Mengambil data IHSG dengan pembersihan index yang ketat"""
        try:
            self.logger.info("📊 Downloading IHSG Benchmark (^JKSE)...")
            session = requests.Session()
            session.impersonate = "chrome120"
            
            data = yf.download("^JKSE", period="2y", interval="1d", progress=False, session=session)
            if not data.empty:
                self.index_data = self.fix_data_alignment(data)
                self.logger.info(f"✅ IHSG Loaded: {len(self.index_data)} days")
                return True
        except Exception as e:
            self.logger.error(f"❌ Error IHSG: {e}")
        return False

    def calculate_rs_rating(self, stock_df):
        """
        Logika RS Rating yang diperbaiki:
        Menggunakan Reindex + Ffill untuk sinkronisasi tanggal yang tidak pas
        """
        if self.index_data is None or stock_df is None:
            return 0.0, 0.0
        
        try:
            # 1. Bersihkan data
            s_data = self.fix_data_alignment(stock_df)
            i_data = self.index_data # Sudah bersih dari fetch_ihsg_data
            
            # 2. Ambil irisan tanggal (Intersection)
            # Karena IHSG dan Saham mungkin punya hari libur berbeda di data Yahoo
            common_start = max(s_data.index[0], i_data.index[0])
            common_end = min(s_data.index[-1], i_data.index[-1])
            
            # 3. Reindex Saham ke tanggal IHSG agar apple-to-apple
            # Gunakan ffill untuk mengisi gap (hari libur/data bolong)
            s_close = s_data['Close'].reindex(i_data.index).ffill()
            i_close = i_data['Close']
            
            # Filter hanya periode yang tumpang tindih
            s_close = s_close[common_start:common_end]
            i_close = i_close[common_start:common_end]

            if len(s_close) < 150:
                return 0.0, 0.0

            # 4. Hitung Weighted Performance (Minervini Style)
            # Performa 1 tahun terakhir dengan bobot lebih besar pada data baru
            def get_perf(series, p):
                return (series.iloc[-1] / series.iloc[-p]) if len(series) >= p else 1.0

            # Bobot: 40% (1thn), 20% (6bln), 20% (3bln), 20% (1bln)
            # Menggunakan estimasi hari bursa: 252, 126, 63, 21
            periods = [min(len(s_close), x) for x in [252, 126, 63, 21]]
            weights = [0.4, 0.2, 0.2, 0.2]
            
            s_score = sum(get_perf(s_close, p) * w for p, w in zip(periods, weights))
            i_score = sum(get_perf(i_close, p) * w for p, w in zip(periods, weights))
            
            # RS Ratio > 1 artinya outperform IHSG
            rs_ratio = s_score / i_score if i_score > 0 else 0
            
            # Kalkulasi RS Score (Skala 1-99)
            # Saham yang outperform IHSG 20% (1.2) akan mendapat score tinggi
            rs_score = (rs_ratio - 0.5) * 100 # Normalisasi sederhana
            rs_score = max(1, min(99, rs_score))
            
            return round(rs_ratio, 3), round(rs_score, 1)

        except Exception as e:
            return 0.0, 0.0

    def process_one_ticker(self, ticker):
        """Logika per saham"""
        try:
            # 1. Fetch Data
            symbol = f"{ticker}.JK" if not ticker.endswith(".JK") else ticker
            session = requests.Session()
            session.impersonate = "chrome120"
            
            df = yf.download(symbol, period="2y", interval="1d", progress=False, session=session, timeout=10)
            if df.empty or len(df) < 150:
                return None

            df = self.fix_data_alignment(df)
            
            # 2. Likuiditas (Min 200 Juta Turnover)
            avg_turnover = (df['Close'] * df['Volume']).tail(20).mean()
            if avg_turnover < self.min_turnover:
                return None

            # 3. Kalkulasi RS & Indikator
            rs_ratio, rs_score = self.calculate_rs_rating(df)
            
            price = df['Close'].iloc[-1]
            ma50 = df['Close'].rolling(50).mean().iloc[-1]
            ma150 = df['Close'].rolling(150).mean().iloc[-1]
            ma200 = df['Close'].rolling(200).mean().iloc[-1]
            ma200_prev = df['Close'].rolling(200).mean().iloc[-22] # 1 bulan lalu
            
            low_52 = df['Low'].tail(252).min()
            high_52 = df['High'].tail(252).max()

            # 4. Kriteria Minervini
            c1 = price > ma150 and price > ma200
            c2 = ma150 > ma200
            c3 = ma200 > ma200_prev  # MA200 Trending Up
            c4 = ma50 > ma150 and ma50 > ma200
            c5 = price > ma50
            c6 = price > (low_52 * 1.30)
            c7 = price > (high_52 * 0.75)
            c8 = rs_score > 70

            score = sum([c1, c2, c3, c4, c5, c6, c7, c8])

            if score >= 7: # Hanya ambil yang hampir sempurna atau sempurna
                return {
                    'Ticker': ticker.replace('.JK', ''),
                    'Price': int(price),
                    'Score': f"{score}/8",
                    'RS_Ratio': rs_ratio,
                    'RS_Score': rs_score,
                    'Turnover_M': round(avg_turnover/1e6, 2),
                    'C8_RS': '✓' if c8 else '✗'
                }
        except:
            return None
        return None

    def screen(self, tickers):
        if not self.fetch_ihsg_data():
            return pd.DataFrame()

        results = []
        self.logger.info(f"🚀 Screening {len(tickers)} saham...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_ticker = {executor.submit(self.process_one_ticker, t): t for t in tickers}
            
            for future in as_completed(future_to_ticker):
                res = future.result()
                if res:
                    results.append(res)
                    print(f"✅ Found: {res['Ticker']} (RS: {res['RS_Score']})")

        df = pd.DataFrame(results)
        if not df.empty:
            df = df.sort_values(by=['RS_Score', 'RS_Ratio'], ascending=False)
        return df

# --- CARA PAKAI ---
if __name__ == "__main__":
    # Contoh list saham (nanti ambil dari config Anda)
    my_list = ["BBRI", "TLKM", "ASII", "ADRO", "BBNI", "GOTO", "BRIS", "PTBA"]
    
    screener = MinerviniScreenerPro(max_workers=10)
    hasil = screener.screen(my_list)
    
    print("\n--- HASIL SCREENING ---")
    print(hasil.to_string())
