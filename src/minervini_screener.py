# ============================================
# MINERVINI PRO SCREENER - VERSI FINAL
# Hanya mengirim SAHAM 8/8 ke Google Sheets
# Format Keterangan: Minervini 8/8 VCP:82 RS:85 | Entry: 11.250 | Patterns
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
import pytz

# Import untuk deteksi pola chart (library tambahan)
try:
    from patternpy.tradingpatterns import (
        head_and_shoulders,
        double_top_bottom,
        horizontal_support_resistance,
        ascending_triangle,
        descending_triangle,
        wedge_patterns,
        channel_patterns
    )
    PATTERN_LIB_AVAILABLE = True
except ImportError:
    PATTERN_LIB_AVAILABLE = False
    print("⚠️ PatternPy tidak terinstall. Install dengan: pip install patternpy")

class MinerviniScreenerPro:
    """
    Screener saham syariah Indonesia dengan 8 kriteria Minervini
    Output: Hanya mengirim SAHAM 8/8 ke Google Sheets
    """
    
    def __init__(self, min_turnover=300_000_000, max_workers=15, log_level=logging.INFO):
        """
        Inisialisasi screener dengan multithreading
        """
        self.criteria_desc = {
            'C1': 'Harga > MA150 & MA200',
            'C2': 'MA150 > MA200',
            'C3': 'MA200 Trending Up (1 bulan)',
            'C4': 'MA50 > MA150 & MA200',
            'C5': 'Harga > MA50',
            'C6': 'Harga > 30% dari Low 52-W',
            'C7': 'Harga dekat High 52-W (dlm 25%)',
            'C8': 'RS Rating > 70'
        }
        
        self.index_data = None
        self.index_fetched = False
        self.min_turnover = min_turnover
        self.max_workers = max_workers
        self.setup_logging(log_level)
        
        # Statistik (dengan thread-safe lock)
        self.lock = Lock()
        self.total_saham = 0
        self.saham_lolos = 0
        self.saham_error = []
        self.saham_ok = []
        self.saham_kurang_data = []
        self.request_count = 0
        self.results = []
        self.start_time = None
        
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

    def fix_timezone(self, df):
        """Memperbaiki masalah timezone pada dataframe"""
        if df is None or df.empty:
            return df
        try:
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            return df
        except:
            return df

    # ============================================
    # FUNGSI FETCH IHSG (UNTUK RS RATING)
    # ============================================
    def fetch_ihsg_data(self):
        """Mengambil data IHSG untuk benchmark RS Rating (opsional)"""
        try:
            self.logger.info("📊 Mencoba mengambil data IHSG...")
            session = requests.Session()
            session.impersonate = "chrome120"
            
            data = yf.download(
                "^JKSE", 
                period="1y", 
                interval="1d", 
                progress=False,
                session=session,
                timeout=15
            )
            
            if data is not None and not data.empty and len(data) >= 100:
                self.index_data = self.fix_timezone(data)
                self.index_fetched = True
                self.logger.info(f"✅ IHSG berhasil dimuat ({len(data)} data)")
                return True
            else:
                self.logger.warning("⚠️ Data IHSG kosong atau tidak cukup")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Gagal mengambil IHSG: {str(e)[:50]}")
            return False

    # ============================================
    # FUNGSI DETEKSI POLA CHART
    # ============================================
    def detect_chart_patterns(self, df):
        """
        Mendeteksi berbagai pola chart dari data OHLC
        Returns: string patterns yang siap digabung
        """
        patterns = []
        
        if df is None or len(df) < 100:
            return ""
        
        try:
            # Fix timezone
            df = self.fix_timezone(df)
            
            # ===== 1. VCP Score (sudah ada) =====
            vcp_total, vcp_tight, vcp_vol = self.calculate_vcp_score(df)
            
            # ===== 2. Support/Resistance Detection =====
            sr_levels = self.detect_support_resistance(df)
            if sr_levels:
                patterns.append(f"Support/Resistance: {sr_levels}")
            
            # ===== 3. Moving Average Alignment =====
            ma_alignment = self.detect_ma_alignment(df)
            if ma_alignment:
                patterns.append(ma_alignment)
            
            # ===== 4. Price Action Patterns =====
            if len(df) >= 50:
                # Deteksi higher highs / higher lows (uptrend)
                highs = df['High'].tail(20).values
                lows = df['Low'].tail(20).values
                
                if self.is_uptrend(highs, lows):
                    patterns.append("Uptrend (HH/HL)")
                elif self.is_downtrend(highs, lows):
                    patterns.append("Downtrend (LH/LL)")
                else:
                    patterns.append("Sideways")
                
                # Deteksi breakout
                if self.is_breakout(df):
                    patterns.append("Breakout Signal")
                
                # Deteksi pullback
                if self.is_pullback(df):
                    patterns.append("Pullback to MA")
            
            # ===== 5. Gunakan PatternPy jika tersedia =====
            if PATTERN_LIB_AVAILABLE:
                lib_patterns = self.detect_patternpy(df)
                patterns.extend(lib_patterns)
            
            # Gabungkan dengan koma
            if patterns:
                result = ", ".join(patterns)
                return result
            else:
                return ""
            
        except Exception as e:
            self.logger.debug(f"Error deteksi pola: {e}")
            return ""

    def detect_support_resistance(self, df, lookback=100, threshold=0.02):
        """
        Deteksi level support dan resistance horizontal
        Returns: string seperti "R12500 S11200"
        """
        try:
            if len(df) < lookback:
                return ""
            
            # Ambil data lookback terakhir
            recent_df = df.tail(lookback)
            highs = recent_df['High'].values
            lows = recent_df['Low'].values
            closes = recent_df['Close'].values
            
            # Cari level yang sering disentuh
            levels = []
            
            # Resistance: level tinggi yang diuji minimal 2 kali
            for i in range(len(highs)-10, len(highs)):
                current_high = highs[i]
                touch_count = 0
                for j in range(len(highs)):
                    if abs(highs[j] - current_high) / current_high < threshold:
                        touch_count += 1
                if touch_count >= 3 and current_high > closes[-1] * 0.95:
                    levels.append(f"R{current_high:.0f}")
                    break
            
            # Support: level rendah yang diuji minimal 2 kali
            for i in range(len(lows)-10, len(lows)):
                current_low = lows[i]
                touch_count = 0
                for j in range(len(lows)):
                    if abs(lows[j] - current_low) / current_low < threshold:
                        touch_count += 1
                if touch_count >= 3 and current_low < closes[-1] * 1.05:
                    levels.append(f"S{current_low:.0f}")
                    break
            
            return " ".join(levels)
            
        except:
            return ""

    def detect_ma_alignment(self, df):
        """Deteksi alignment moving average"""
        try:
            if len(df) < 200:
                return ""
            
            # Hitung MA
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            ma50 = df['Close'].rolling(50).mean().iloc[-1]
            ma150 = df['Close'].rolling(150).mean().iloc[-1]
            ma200 = df['Close'].rolling(200).mean().iloc[-1]
            price = df['Close'].iloc[-1]
            
            # Golden Cross (MA20 > MA50)
            golden_cross = ma20 > ma50
            
            # Perfect Order (MA20 > MA50 > MA150 > MA200)
            perfect_order = (ma20 > ma50 > ma150 > ma200)
            
            # Price above all MAs
            above_all = price > ma20 and price > ma50 and price > ma150 and price > ma200
            
            if perfect_order and above_all:
                return "Perfect Order (MA20>50>150>200)"
            elif golden_cross and above_all:
                return "Golden Cross + Above MAs"
            elif above_all:
                return "Above All MAs"
            else:
                return ""
                
        except:
            return ""

    def is_uptrend(self, highs, lows):
        """Cek apakah dalam uptrend (higher highs, higher lows)"""
        try:
            if len(highs) < 5:
                return False
            
            # Cek higher highs
            hh = highs[-1] > highs[-3] > highs[-5]
            # Cek higher lows
            hl = lows[-1] > lows[-3] > lows[-5]
            
            return hh and hl
        except:
            return False

    def is_downtrend(self, highs, lows):
        """Cek apakah dalam downtrend (lower highs, lower lows)"""
        try:
            if len(highs) < 5:
                return False
            
            # Cek lower highs
            lh = highs[-1] < highs[-3] < highs[-5]
            # Cek lower lows
            ll = lows[-1] < lows[-3] < lows[-5]
            
            return lh and ll
        except:
            return False

    def is_breakout(self, df, lookback=20, volume_threshold=1.5):
        """Deteksi breakout dengan volume tinggi"""
        try:
            # Harga tertinggi dalam lookback
            recent_high = df['High'].tail(lookback).max()
            current_price = df['Close'].iloc[-1]
            current_vol = df['Volume'].iloc[-1]
            avg_vol = df['Volume'].tail(20).mean()
            
            # Breakout jika harga > 98% dari recent high dan volume > rata2
            if current_price >= recent_high * 0.98 and current_vol > avg_vol * volume_threshold:
                return True
            return False
        except:
            return False

    def is_pullback(self, df, lookback=20, ma_period=20):
        """Deteksi pullback ke moving average"""
        try:
            if len(df) < ma_period + 10:
                return False
            
            ma = df['Close'].rolling(ma_period).mean()
            current_price = df['Close'].iloc[-1]
            
            # Harga tertinggi dalam lookback
            recent_high = df['High'].tail(lookback).max()
            
            # Pullback jika harga di atas MA tapi turun dari high
            if (current_price > ma.iloc[-1] and 
                current_price < recent_high * 0.97 and
                current_price > ma.iloc[-1] * 1.01):
                return True
            return False
        except:
            return False

    def detect_patternpy(self, df):
        """Gunakan PatternPy untuk deteksi pola klasik"""
        patterns = []
        
        try:
            if not PATTERN_LIB_AVAILABLE:
                return patterns
            
            # Head & Shoulders
            df_hs = head_and_shoulders(df.copy())
            if 'head_shoulder_pattern' in df_hs.columns:
                last_pattern = df_hs['head_shoulder_pattern'].iloc[-1]
                if pd.notna(last_pattern):
                    patterns.append(str(last_pattern))
            
            # Double Top/Bottom
            df_dt = double_top_bottom(df.copy())
            if 'double_pattern' in df_dt.columns:
                last_pattern = df_dt['double_pattern'].iloc[-1]
                if pd.notna(last_pattern):
                    patterns.append(str(last_pattern))
            
            # Triangle Patterns
            df_at = ascending_triangle(df.copy())
            if 'ascending_triangle' in df_at.columns:
                last_pattern = df_at['ascending_triangle'].iloc[-1]
                if pd.notna(last_pattern):
                    patterns.append("Ascending Triangle")
            
            df_dt = descending_triangle(df.copy())
            if 'descending_triangle' in df_dt.columns:
                last_pattern = df_dt['descending_triangle'].iloc[-1]
                if pd.notna(last_pattern):
                    patterns.append("Descending Triangle")
            
        except Exception as e:
            self.logger.debug(f"PatternPy error: {e}")
        
        return patterns

    # ============================================
    # FUNGSI RS RATING (2 DIGIT)
    # ============================================
    def calculate_relative_strength(self, df):
        """
        RS Rating dengan hybrid method
        Output: integer 0-99 (tanpa desimal)
        """
        if self.index_fetched and self.index_data is not None and len(df) >= 60:
            try:
                common_dates = df.index.intersection(self.index_data.index)
                if len(common_dates) >= 50:
                    stock_ret_3m = (df['Close'].iloc[-1] / df['Close'].iloc[-63] - 1) * 100
                    ihsg_ret_3m = (self.index_data['Close'].iloc[-1] / self.index_data['Close'].iloc[-63] - 1) * 100
                    
                    stock_ret_1m = (df['Close'].iloc[-1] / df['Close'].iloc[-21] - 1) * 100
                    ihsg_ret_1m = (self.index_data['Close'].iloc[-1] / self.index_data['Close'].iloc[-21] - 1) * 100
                    
                    outperf = (stock_ret_3m - ihsg_ret_3m) * 0.6 + (stock_ret_1m - ihsg_ret_1m) * 0.4
                    rs_score = 50 + outperf
                    rs_score = max(1, min(99, rs_score))
                    
                    return int(round(rs_score))
            except:
                pass
        
        try:
            if len(df) < 60:
                return 50
            
            returns = df['Close'].pct_change(60).iloc[-1] * 100
            if pd.notna(returns):
                rs = min(99, max(1, returns + 50))
                return int(round(rs))
            return 50
        except:
            return 50

    # ============================================
    # FUNGSI VCP SCORE (TETAP)
    # ============================================
    def calculate_vcp_score(self, df):
        """Menghitung VCP Score (0-100)"""
        if df is None or len(df) < 120:
            return 0.0, 0.0, 0.0

        try:
            windows = [20, 30, 40, 60]
            tight_scores = []
            for w in windows:
                if len(df) < w + 60:
                    continue
                recent_range = (df['High'].iloc[-w:] - df['Low'].iloc[-w:]).mean()
                hist_range = (df['High'].iloc[-(w+60):-w] - df['Low'].iloc[-(w+60):-w]).mean()
                if hist_range > 0:
                    ratio = recent_range / hist_range
                    score = max(0, (1 - ratio) * 100)
                    tight_scores.append(min(100, score))
            
            if tight_scores:
                tight_avg = sum(tight_scores) / len(tight_scores)
                tight_score = tight_avg * 0.7
            else:
                tight_score = 0

            if len(df) >= 60:
                recent_vol = df['Volume'].iloc[-10:].mean()
                hist_vol = df['Volume'].iloc[-60:-10].mean()
                if hist_vol > 0:
                    vol_ratio = recent_vol / hist_vol
                    vol_score = max(0, (1 - vol_ratio) * 100) * 0.3
                    vol_score = min(30, vol_score)
                else:
                    vol_score = 0
            else:
                vol_score = 0

            total = round(tight_score + vol_score, 1)
            return total, round(tight_score, 1), round(vol_score, 1)
        except:
            return 0, 0, 0

    # ============================================
    # FUNGSI AMBIL DATA SAHAM
    # ============================================
    def get_stock_data(self, ticker):
        """Ambil data saham dengan retry"""
        max_retries = 2
        
        if '#' in ticker:
            ticker = ticker.split('#')[0].strip()
        
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
                df = stock.history(period="1y", timeout=10)
                
                if df is not None and not df.empty:
                    df = self.fix_timezone(df)
                    if len(df) >= 150:
                        return df, display_name, None
                    else:
                        return None, display_name, f"Data {len(df)}/150 hari"
                else:
                    return None, display_name, "Data kosong"
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    return None, display_name, str(e)[:50]
        
        return None, display_name, "Gagal"

    def check_liquidity(self, df):
        """Cek likuiditas"""
        try:
            avg_turnover = (df['Close'] * df['Volume']).tail(20).mean()
            is_liquid = avg_turnover >= self.min_turnover
            return is_liquid, avg_turnover
        except:
            return False, 0

    def calculate_risk_reward(self, price, stop_loss_pct=7, target_pct=20):
        """Menghitung risk/reward ratio"""
        try:
            risk = price * (stop_loss_pct / 100)
            reward = price * (target_pct / 100)
            rr_ratio = reward / risk
            return round(rr_ratio, 2)
        except:
            return 0

    # ============================================
    # FUNGSI PROCESS ONE TICKER (HANYA 8/8 YANG DISIMPAN)
    # ============================================
    def process_one_ticker(self, ticker, index, total):
        """Fungsi yang akan dijalankan oleh masing-masing thread"""
        result = None
        error_msg = None
        
        df, display_name, error = self.get_stock_data(ticker)
        
        if df is None:
            with self.lock:
                self.saham_error.append(display_name)
                self.request_count += 1
            return None, display_name, error
        
        with self.lock:
            self.saham_ok.append(display_name)
            self.request_count += 1
        
        is_liquid, avg_turnover = self.check_liquidity(df)
        if not is_liquid:
            return None, display_name, f"Likuiditas rendah"
        
        try:
            # Hitung indikator teknikal
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
            
            # RS Rating (2 digit)
            rs_score = self.calculate_relative_strength(df)
            
            # VCP Score
            vcp_total, vcp_tight, vcp_vol = self.calculate_vcp_score(df)
            
            # ===== DETEKSI POLA CHART =====
            patterns_str = self.detect_chart_patterns(df)
            
            # Evaluasi kriteria
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
            
            # Hitung Risk/Reward Ratio
            rr_ratio = self.calculate_risk_reward(price)
            
            # Hanya simpan jika score == 8 (8/8)
            if score == 8:
                # Buat entry price untuk keterangan
                entry_price = int(price)
                
                # Format harga untuk keterangan (tanpa Rp, angka saja)
                entry_str = f"{entry_price:,}".replace(',', '.')
                
                # ===== BUAT KETERANGAN UNTUK GOOGLE SHEETS =====
                # Format dasar
                keterangan = f"Minervini 8/8 VCP:{vcp_total} RS:{rs_score} | Entry: {entry_str}"
                
                # TAMBAHKAN PATTERN JIKA ADA
                if patterns_str and patterns_str.strip() and patterns_str != "":
                    keterangan += f" | {patterns_str}"
                
                # Buat result - HANYA UNTUK 8/8
                result = {
                    'Ticker': display_name,
                    'Harga': f"Rp {entry_price:,}".replace(',', '.'),
                    'Status': '8/8',
                    'RS': rs_score,
                    'VCP': vcp_total,
                    'Patterns': patterns_str,  # Untuk email
                    'RR_Ratio': rr_ratio,
                    'Turnover_M': f"{avg_turnover/1e6:.1f}M",
                    'Low': f"{pct_from_low:.1f}%",
                    'High': f"{pct_from_high:.1f}%",
                    'Keterangan': keterangan,  # Untuk Google Sheets (SUDAH include pattern)
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
                    self.saham_lolos += 1
                
                return result, display_name, None
            else:
                # Tidak simpan untuk 7/8 atau di bawahnya
                return None, display_name, f"Tidak lolos ({score}/8)"
            
        except Exception as e:
            return None, display_name, f"Error: {str(e)[:50]}"

    # ============================================
    # FUNGSI UTAMA SCREENING
    # ============================================
    def screen(self, tickers):
        """
        Fungsi utama screening dengan multithreading
        """
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"MINERVINI PRO SCREENER v6.3 - HANYA 8/8")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Total saham: {len(tickers)}")
        self.logger.info(f"Thread workers: {self.max_workers}")
        if PATTERN_LIB_AVAILABLE:
            self.logger.info(f"Pattern Library: ✅ PatternPy tersedia")
        else:
            self.logger.info(f"Pattern Library: ⚠️ PatternPy tidak ada (fallback manual)")
        self.logger.info(f"{'='*80}\n")
        
        # Reset statistik
        self.total_saham = len(tickers)
        self.saham_lolos = 0
        self.saham_error = []
        self.saham_ok = []
        self.saham_kurang_data = []
        self.request_count = 0
        self.results = []
        self.start_time = time.time()
        
        # Ambil data IHSG untuk benchmark (opsional)
        self.fetch_ihsg_data()
        
        # Filter ticker valid
        valid_tickers = [t for t in tickers if t and not t.startswith('#')]
        
        processed = 0
        success = 0
        failed = 0
        
        print(f"🚀 Memulai screening dengan {self.max_workers} thread paralel...")
        print(f"{'='*80}")
        
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
                    status = f"✅ 8/8 {result['Ticker']}"
                else:
                    failed += 1
                    status = f"❌ {display_name}: {error if error else 'Gagal'}"
                
                print(f"\r[{bar}] {progress:.1f}% | "
                      f"✓:8/8:{success} ✗:{failed} | "
                      f"Sisa:{int(remaining//60)}m{int(remaining%60)}s | "
                      f"{status[:50]}", end="", flush=True)
        
        print("\n")
        
        # Buat DataFrame hasil
        if self.results:
            df_results = pd.DataFrame(self.results)
            # Urutkan berdasarkan RS
            df_results = df_results.sort_values(['RS'], ascending=[False])
        else:
            df_results = pd.DataFrame()
        
        # Ringkasan
        total_time = time.time() - self.start_time
        self.logger.info(f"\n{'='*80}")
        self.logger.info("📊 RINGKASAN SCREENING")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Total saham: {self.total_saham}")
        self.logger.info(f"Valid format: {len(valid_tickers)}")
        self.logger.info(f"Berhasil: {success + failed}")
        self.logger.info(f"Lolos 8/8: {len(self.results)}")
        self.logger.info(f"Waktu: {int(total_time//60)}m {int(total_time%60)}s")
        
        return df_results


# ============================================
# FUNGSI UNTUK TESTING
# ============================================
if __name__ == "__main__":
    # Contoh penggunaan
    tickers = ["BBCA.JK", "BBRI.JK", "BMRI.JK"]
    screener = MinerviniScreenerPro()
    results = screener.screen(tickers)
    print(results)
