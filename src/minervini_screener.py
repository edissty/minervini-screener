# ============================================
# MINERVINI PRO SCREENER - MULTITHREADING VERSION
# Versi 5.1 - Dengan Perbaikan Timezone & Error Handling
# ============================================

import yfinance as yf
import pandas as pd
import numpy as np
import time
import random
import logging
import sys
from datetime import datetime, timedelta
from curl_cffi import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import os
import pytz  # Tambahkan ini untuk timezone

class MinerviniScreenerPro:
    """
    Screener saham syariah Indonesia dengan 8 kriteria Minervini + VCP Scoring
    dan Relative Strength vs IHSG yang akurat. Versi Multithreading.
    """
    
    def __init__(self, min_turnover=500_000_000, max_workers=20, log_level=logging.INFO):
        """
        Inisialisasi screener dengan multithreading
        
        Args:
            min_turnover: Minimal turnover (harga * volume) untuk filter likuiditas
            max_workers: Jumlah thread maksimal (default 20, bisa disesuaikan)
            log_level: Level logging (INFO, DEBUG, etc)
        """
        self.criteria_desc = {
            'C1': 'Harga > MA150 & MA200',
            'C2': 'MA150 > MA200',
            'C3': 'MA200 Trending Up (1 bulan)',
            'C4': 'MA50 > MA150 & MA200',
            'C5': 'Harga > MA50',
            'C6': 'Harga > 30% dari Low 52-W',
            'C7': 'Harga dekat High 52-W (dlm 25%)',
            'C8': 'RS Rating > 70 (Top 30% saham)'
        }
        
        self.index_data = None
        self.min_turnover = min_turnover
        self.max_workers = max_workers
        self.setup_logging(log_level)
        
        # Statistik (dengan thread-safe lock)
        self.lock = Lock()
        self.total_saham = 0
        self.saham_lolos = 0
        self.saham_error = []
        self.saham_ok = []
        self.request_count = 0
        self.results = []
        self.start_time = None
        
        # Daftar saham yang valid (untuk filter awal)
        self.valid_tickers = set()
        
    def setup_logging(self, level):
        """Setup logging ke file dan console"""
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('screener.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    # ============================================
    # FUNGSI FIX TIMEZONE
    # ============================================
    def fix_timezone(self, df):
        """Memperbaiki masalah timezone pada dataframe"""
        if df is None or df.empty:
            return df
        
        try:
            # Jika index memiliki timezone, hapus timezone-nya
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            return df
        except:
            return df

    # ============================================
    # FUNGSI FETCH DATA IHSG (DENGAN FIX TIMEZONE)
    # ============================================
    def fetch_ihsg_data(self, force_refresh=False):
        """Mengambil data IHSG sebagai benchmark RS Rating"""
        if self.index_data is not None and not force_refresh:
            self.logger.info("📊 Menggunakan data IHSG dari cache")
            return self.index_data
        
        self.logger.info("📊 Mengambil data benchmark IHSG (^JKSE)...")
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                session = requests.Session()
                session.impersonate = "chrome120"
                
                self.index_data = yf.download(
                    "^JKSE", 
                    period="1y",  # Kurangi jadi 1 tahun
                    interval="1d", 
                    progress=False,
                    session=session
                )
                
                if self.index_data is not None and not self.index_data.empty:
                    # Fix timezone
                    self.index_data = self.fix_timezone(self.index_data)
                    self.logger.info(f"✅ Data IHSG berhasil dimuat ({len(self.index_data)} data points)")
                    return self.index_data
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2
                    time.sleep(wait)
                else:
                    self.logger.error(f"❌ Gagal mengambil data IHSG: {e}")
                    return None
        return None

    # ============================================
    # FUNGSI AMBIL DATA SAHAM (DENGAN ERROR HANDLING LEBIH BAIK)
    # ============================================
    def get_stock_data(self, ticker):
        """Ambil data saham dengan error handling yang lebih baik"""
        max_retries = 1  # Kurangi retry karena banyak error
        
        # Bersihkan ticker
        if '#' in ticker:
            ticker = ticker.split('#')[0].strip()
        
        # Format yang akan dicoba
        if ticker.endswith('.JK'):
            symbol = ticker
            display_name = ticker.replace('.JK', '')
        else:
            symbol = f"{ticker}.JK"
            display_name = ticker
        
        for attempt in range(max_retries):
            try:
                session = requests.Session()
                session.impersonate = "chrome120"
                
                stock = yf.Ticker(symbol, session=session)
                df = stock.history(period="1y", timeout=10)  # Kurangi jadi 1 tahun
                
                if df is not None and not df.empty:
                    # Fix timezone
                    df = self.fix_timezone(df)
                    if len(df) >= 150:  # Kurangi threshold jadi 150 hari
                        return df, display_name, None
                    else:
                        return None, display_name, f"Data {len(df)}/150 hari"
                else:
                    return None, display_name, "Data kosong"
                    
            except Exception as e:
                error_str = str(e).lower()
                if "401" in error_str or "unauthorized" in error_str:
                    return None, display_name, "Unauthorized - mungkin kena block"
                elif "404" in error_str or "not found" in error_str:
                    return None, display_name, "Symbol tidak ditemukan"
                else:
                    return None, display_name, str(e)[:50]
        
        return None, display_name, "Gagal setelah retry"

    # ============================================
    # FUNGSI RS RATING (DENGAN FIX TIMEZONE)
    # ============================================
    def calculate_rs_rating(self, stock_df):
        """RS Rating dengan fix timezone"""
        if self.index_data is None or stock_df is None or len(stock_df) < 50:
            return 1.0, 50.0
        
        try:
            # Fix timezone untuk kedua dataframe
            stock_df = self.fix_timezone(stock_df)
            index_df = self.fix_timezone(self.index_data)
            
            # Gunakan periode yang sama
            end_date = stock_df.index[-1]
            start_date = end_date - pd.Timedelta(days=365)
            
            # Filter IHSG
            idx_filtered = index_df[(index_df.index >= start_date) & 
                                    (index_df.index <= end_date)]
            
            if len(idx_filtered) < 50:
                return 1.0, 50.0
            
            # Cari tanggal yang sama
            common_dates = stock_df.index.intersection(idx_filtered.index)
            if len(common_dates) < 50:
                return 1.0, 50.0
            
            s_price = stock_df.loc[common_dates, 'Close']
            i_price = idx_filtered.loc[common_dates, 'Close']
            
            # Hitung return
            periods = [21, 63, 126]
            weights = [0.2, 0.3, 0.5]
            
            stock_perf = 0
            index_perf = 0
            
            for period, weight in zip(periods, weights):
                if len(s_price) > period:
                    s_ret = (s_price.iloc[-1] / s_price.iloc[-period] - 1)
                    i_ret = (i_price.iloc[-1] / i_price.iloc[-period] - 1)
                    
                    stock_perf += (1 + s_ret) * weight
                    index_perf += (1 + i_ret) * weight
            
            if index_perf <= 0:
                return 1.0, 50.0
            
            rs_ratio = stock_perf / index_perf
            rs_ratio = max(0.5, min(2.0, rs_ratio))
            rs_score = 50 + (rs_ratio - 1.0) * 50
            rs_score = max(1, min(99, rs_score))
            
            return round(rs_ratio, 3), round(rs_score, 1)
            
        except Exception as e:
            self.logger.debug(f"Error RS: {e}")
            return 1.0, 50.0

    # ============================================
    # FUNGSI VCP SCORE (DENGAN FIX)
    # ============================================
    def calculate_vcp_score(self, df):
        """VCP Score dengan fix"""
        if df is None or len(df) < 100:
            return 0, 0, 0
        
        try:
            df = self.fix_timezone(df)
            
            windows = [10, 20, 30]
            tight_scores = []
            
            for w in windows:
                if len(df) < w + 50:
                    continue
                    
                recent_range = (df['High'].iloc[-w:] - df['Low'].iloc[-w:]).mean()
                hist_range = (df['High'].iloc[-(w+50):-w] - df['Low'].iloc[-(w+50):-w]).mean()
                
                if hist_range > 0:
                    ratio = recent_range / hist_range
                    score = max(0, (1 - ratio) * 100)
                    tight_scores.append(min(100, score))
            
            tightness = (sum(tight_scores) / len(tight_scores) * 0.6) if tight_scores else 0
            
            recent_vol = df['Volume'].iloc[-10:].mean()
            hist_vol = df['Volume'].iloc[-50:-10].mean()
            
            vol_dryup = 0
            if hist_vol > 0:
                vol_ratio = recent_vol / hist_vol
                vol_dryup = max(0, (1 - vol_ratio) * 100) * 0.3
                vol_dryup = min(30, vol_dryup)
            
            total = tightness + vol_dryup
            return round(total, 1), round(tightness, 1), round(vol_dryup, 1)
            
        except Exception as e:
            return 0, 0, 0

    # ============================================
    # FUNGSI CEK LIKUIDITAS (DENGAN FIX)
    # ============================================
    def check_liquidity(self, df):
        """Cek likuiditas dengan fix"""
        try:
            df = self.fix_timezone(df)
            avg_turnover = (df['Close'] * df['Volume']).tail(20).mean()
            # Turunkan threshold jadi 200 juta
            is_liquid = avg_turnover >= 200_000_000
            return is_liquid, avg_turnover
        except Exception as e:
            return False, 0

    # ============================================
    # FUNGSI PROCESS ONE TICKER (DENGAN PERBAIKAN)
    # ============================================
    def process_one_ticker(self, ticker, index, total):
        """Fungsi yang akan dijalankan oleh masing-masing thread"""
        result = None
        error_msg = None
        
        # Ambil data
        df, display_name, error = self.get_stock_data(ticker)
        
        if df is None:
            with self.lock:
                self.saham_error.append(display_name)
                self.request_count += 1
            return None, display_name, error
        
        with self.lock:
            self.saham_ok.append(display_name)
            self.request_count += 1
        
        # Cek likuiditas
        is_liquid, avg_turnover = self.check_liquidity(df)
        if not is_liquid:
            return None, display_name, f"Likuiditas rendah"
        
        try:
            # Hitung indikator
            price = df['Close'].iloc[-1]
            ma50 = df['Close'].rolling(50).mean().iloc[-1]
            ma150 = df['Close'].rolling(150).mean().iloc[-1] if len(df) >= 150 else price
            ma200 = df['Close'].rolling(200).mean().iloc[-1] if len(df) >= 200 else price
            
            if len(df) >= 200:
                ma200_22 = df['Close'].rolling(200).mean().iloc[-22] if len(df) >= 222 else ma200
            else:
                ma200_22 = ma200
            
            low_52 = df['Low'].tail(200).min()
            high_52 = df['High'].tail(200).max()
            
            # RS Rating
            rs_ratio, rs_score = self.calculate_rs_rating(df)
            
            # VCP Score
            vcp_total, _, _ = self.calculate_vcp_score(df)
            
            # Evaluasi kriteria dengan toleransi
            c1 = price > ma150 and price > ma200 if not pd.isna(ma150) and not pd.isna(ma200) else False
            c2 = ma150 > ma200 if not pd.isna(ma150) and not pd.isna(ma200) else False
            c3 = ma200 > ma200_22 if not pd.isna(ma200) and not pd.isna(ma200_22) else False
            c4 = ma50 > ma150 and ma50 > ma200 if not pd.isna(ma50) and not pd.isna(ma150) and not pd.isna(ma200) else False
            c5 = price > ma50 if not pd.isna(ma50) else False
            c6 = price > (low_52 * 1.30) if low_52 > 0 else False
            c7 = price > (high_52 * 0.75) if high_52 > 0 else False
            c8 = rs_score > 70
            
            conditions = [c1, c2, c3, c4, c5, c6, c7, c8]
            score = sum(conditions)
            
            pct_from_low = ((price / low_52) - 1) * 100 if low_52 > 0 else 0
            pct_from_high = (1 - (price / high_52)) * 100 if high_52 > 0 else 0
            
            # Buat result
            result = {
                'Ticker': display_name,
                'Harga': f"Rp {int(price):,}".replace(',', '.'),
                'Skor': f"{score}/8",
                'Status': '8/8' if score == 8 else '7/8',
                'RS_Ratio': rs_ratio,
                'RS_Score': rs_score,
                'VCP': vcp_total,
                'Turnover_M': f"{avg_turnover/1e6:.1f}M",
                'Low': f"{pct_from_low:.1f}%",
                'High': f"{pct_from_high:.1f}%",
                'C1': '✓' if c1 else '✗',
                'C2': '✓' if c2 else '✗',
                'C3': '✓' if c3 else '✗',
                'C4': '✓' if c4 else '✗',
                'C5': '✓' if c5 else '✗',
                'C6': '✓' if c6 else '✗',
                'C7': '✓' if c7 else '✗',
                'C8': '✓' if c8 else '✗',
            }
            
            with self.lock:
                if score >= 7:
                    self.saham_lolos += 1
            
            return result, display_name, None
            
        except Exception as e:
            return None, display_name, f"Error proses: {str(e)[:50]}"

    # ============================================
    # FUNGSI UTAMA SCREENING
    # ============================================
    def screen(self, tickers):
        """
        Fungsi utama screening dengan multithreading
        """
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"MINERVINI PRO SCREENER - MULTITHREADING v5.1")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Total saham: {len(tickers)}")
        self.logger.info(f"Thread workers: {self.max_workers}")
        self.logger.info(f"{'='*80}\n")
        
        # Reset statistik
        self.total_saham = len(tickers)
        self.saham_lolos = 0
        self.saham_error = []
        self.saham_ok = []
        self.request_count = 0
        self.results = []
        self.start_time = time.time()
        
        # Ambil data IHSG
        self.fetch_ihsg_data()
        
        # Progress tracking
        processed = 0
        success = 0
        failed = 0
        
        print(f"🚀 Memulai screening dengan {self.max_workers} thread paralel...")
        print(f"{'='*80}")
        
        # Filter ticker yang valid dulu
        valid_tickers = [t for t in tickers if self.is_valid_ticker_format(t)]
        self.logger.info(f"📋 Valid ticker format: {len(valid_tickers)}/{len(tickers)}")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_ticker = {
                executor.submit(self.process_one_ticker, ticker, i, len(valid_tickers)): ticker 
                for i, ticker in enumerate(valid_tickers, 1)
            }
            
            for future in as_completed(future_to_ticker):
                processed += 1
                result, display_name, error = future.result()
                
                elapsed = time.time() - self.start_time
                avg_time = elapsed / processed if processed > 0 else 0
                remaining = (len(valid_tickers) - processed) * avg_time if processed > 0 else 0
                
                progress = (processed / len(valid_tickers)) * 100
                bar_length = 40
                filled = int(bar_length * processed // len(valid_tickers))
                bar = '█' * filled + '░' * (bar_length - filled)
                
                if result:
                    success += 1
                    self.results.append(result)
                    status = f"✅ {result['Skor']} {result['Ticker']}"
                else:
                    failed += 1
                    status = f"❌ {display_name}: {error if error else 'Gagal'}"
                
                print(f"\r[{bar}] {progress:.1f}% | "
                      f"✓:{success} ✗:{failed} | "
                      f"Sisa:{int(remaining//60)}m{int(remaining%60)}s | "
                      f"{status[:50]}", end="", flush=True)
        
        print("\n")
        
        # Buat DataFrame hasil
        if self.results:
            df_results = pd.DataFrame(self.results)
            output_cols = ['Ticker', 'Harga', 'Skor', 'Status', 'RS_Ratio', 'RS_Score', 'VCP', 
                          'Turnover_M', 'Low', 'High', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8']
            available_cols = [col for col in output_cols if col in df_results.columns]
            df_results = df_results[available_cols]
            df_results = df_results.sort_values(['Skor', 'RS_Score'], ascending=[False, False])
        else:
            df_results = pd.DataFrame()
        
        # Ringkasan
        total_time = time.time() - self.start_time
        self.logger.info(f"\n{'='*80}")
        self.logger.info("📊 RINGKASAN SCREENING")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Total saham: {self.total_saham}")
        self.logger.info(f"Valid format: {len(valid_tickers)}")
        self.logger.info(f"Berhasil: {success}")
        self.logger.info(f"Error: {failed}")
        self.logger.info(f"Lolos: {len(self.results)}")
        self.logger.info(f"Waktu: {int(total_time//60)}m {int(total_time%60)}s")
        
        return df_results

    def is_valid_ticker_format(self, ticker):
        """Cek format ticker valid"""
        if '#' in ticker:
            ticker = ticker.split('#')[0].strip()
        return len(ticker) > 0 and not ticker.startswith('#')
