# ============================================
# MINERVINI PRO SCREENER - MULTITHREADING VERSION
# Versi 5.0 - Dengan Concurrent Processing
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
            'C8': 'RS Rating > 1.0 (Outperform IHSG)'
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
    # FUNGSI FETCH DATA IHSG (DENGAN CACHING)
    # ============================================
    def fetch_ihsg_data(self, force_refresh=False):
        """Mengambil data IHSG sebagai benchmark RS Rating"""
        if self.index_data is not None and not force_refresh:
            self.logger.info("📊 Menggunakan data IHSG dari cache")
            return self.index_data
        
        self.logger.info("📊 Mengambil data benchmark IHSG (^JKSE)...")
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                session = requests.Session()
                session.impersonate = "chrome120"
                
                self.index_data = yf.download(
                    "^JKSE", 
                    period="2y", 
                    interval="1d", 
                    progress=False,
                    session=session
                )
                
                if self.index_data.empty:
                    raise ValueError("Data IHSG kosong")
                    
                self.logger.info(f"✅ Data IHSG berhasil dimuat ({len(self.index_data)} data points)")
                return self.index_data
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 5 * (attempt + 1)
                    self.logger.warning(f"⚠️ Gagal, coba lagi dalam {wait} detik...")
                    time.sleep(wait)
                else:
                    self.logger.error(f"❌ Gagal mengambil data IHSG: {e}")
                    return None
        return None

    # ============================================
    # FUNGSI RS RATING (AKURAT vs IHSG)
    # ============================================
    def calculate_rs_rating(self, stock_df):
        """RS Rating dengan multiple timeframe (12m, 6m, 3m, 1m)"""
        if self.index_data is None or stock_df is None or len(stock_df) < 252:
            return 0, 0
        
        try:
            common_dates = stock_df.index.intersection(self.index_data.index)
            if len(common_dates) < 200:
                return 0, 0
            
            s_price = stock_df.loc[common_dates, 'Close']
            i_price = self.index_data.loc[common_dates, 'Close']
            
            periods = [21, 63, 126, 252]
            weights = [0.1, 0.2, 0.3, 0.4]
            
            stock_perf = 0
            index_perf = 0
            
            for period, weight in zip(periods, weights):
                if len(s_price) > period:
                    s_ret = (s_price.iloc[-1] / s_price.iloc[-period] - 1)
                    i_ret = (i_price.iloc[-1] / i_price.iloc[-period] - 1)
                    
                    stock_perf += (1 + s_ret) * weight
                    index_perf += (1 + i_ret) * weight
            
            rs_ratio = stock_perf / index_perf if index_perf > 0 else 1
            rs_score = min(99, max(1, (rs_ratio - 0.5) * 100))
            
            return round(rs_ratio, 3), round(rs_score, 1)
            
        except Exception as e:
            self.logger.debug(f"Error RS Rating: {e}")
            return 0, 0

    # ============================================
    # FUNGSI VCP SCORE (KOMPREHENSIF)
    # ============================================
    def calculate_vcp_score(self, df):
        """VCP Score (0-100)"""
        if len(df) < 150:
            return 0, 0, 0
        
        try:
            windows = [10, 20, 30, 40]
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
                tightness = (sum(tight_scores) / len(tight_scores)) * 0.6
            else:
                tightness = 0
            
            recent_vol = df['Volume'].iloc[-10:].mean()
            hist_vol = df['Volume'].iloc[-60:-10].mean()
            
            vol_dryup = 0
            if hist_vol > 0:
                vol_ratio = recent_vol / hist_vol
                vol_dryup = max(0, (1 - vol_ratio) * 100) * 0.3
                vol_dryup = min(30, vol_dryup)
            
            price = df['Close'].iloc[-1]
            high_52 = df['High'].tail(252).max()
            if high_52 > 0:
                price_position = (price / high_52) * 10
                price_position = min(10, price_position)
            else:
                price_position = 0
            
            total = tightness + vol_dryup + price_position
            return round(total, 1), round(tightness, 1), round(vol_dryup, 1)
            
        except Exception as e:
            self.logger.debug(f"Error VCP Score: {e}")
            return 0, 0, 0

    # ============================================
    # FUNGSI CEK LIKUIDITAS
    # ============================================
    def check_liquidity(self, df):
        """Cek apakah saham cukup likuid"""
        try:
            avg_turnover = (df['Close'] * df['Volume']).tail(20).mean()
            is_liquid = avg_turnover >= self.min_turnover
            return is_liquid, avg_turnover
        except Exception as e:
            self.logger.debug(f"Error cek likuiditas: {e}")
            return False, 0

    # ============================================
    # FUNGSI AMBIL DATA SAHAM (UNTUK THREAD)
    # ============================================
    def get_stock_data(self, ticker):
        """Ambil data saham dengan retry mechanism (versi thread-safe)"""
        max_retries = 2
        
        # Bersihkan ticker
        if '#' in ticker:
            ticker = ticker.split('#')[0].strip()
        
        original_ticker = ticker
        
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
                df = stock.history(period="2y", timeout=15)
                
                if df is not None and not df.empty:
                    if len(df) >= 200:
                        return df, display_name, None
                    else:
                        return None, display_name, f"Data {len(df)}/200 hari"
                else:
                    return None, display_name, "Data kosong"
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    return None, display_name, str(e)[:50]
        
        return None, display_name, "Gagal setelah retry"

    # ============================================
    # FUNGSI PROCESS SATU TICKER (UNTUK THREAD)
    # ============================================
    def process_one_ticker(self, ticker, index, total):
        """
        Fungsi yang akan dijalankan oleh masing-masing thread
        Memproses satu ticker dan mengembalikan hasil
        """
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
            return None, display_name, f"Likuiditas rendah: Rp {avg_turnover/1e6:.1f}M"
        
        # Hitung indikator
        price = df['Close'].iloc[-1]
        ma50 = df['Close'].rolling(50).mean().iloc[-1]
        ma150 = df['Close'].rolling(150).mean().iloc[-1]
        ma200 = df['Close'].rolling(200).mean().iloc[-1]
        
        if len(df) >= 222:
            ma200_22 = df['Close'].rolling(200).mean().iloc[-22]
        else:
            ma200_22 = ma200
        
        low_52 = df['Low'].tail(252).min()
        high_52 = df['High'].tail(252).max()
        
        # RS dan VCP
        rs_ratio, rs_score = self.calculate_rs_rating(df)
        vcp_total, vcp_tight, vcp_vol = self.calculate_vcp_score(df)
        
        # Evaluasi kriteria
        c1 = price > ma150 and price > ma200
        c2 = ma150 > ma200
        c3 = ma200 > ma200_22 if len(df) >= 222 else False
        c4 = ma50 > ma150 and ma50 > ma200
        c5 = price > ma50
        c6 = price > (low_52 * 1.30) if low_52 > 0 else False
        c7 = price > (high_52 * 0.75) if high_52 > 0 else False
        c8 = rs_ratio > 1.0
        
        conditions = [c1, c2, c3, c4, c5, c6, c7, c8]
        score = sum(conditions)
        
        pct_from_low = ((price / low_52) - 1) * 100 if low_52 > 0 else 0
        pct_from_high = (1 - (price / high_52)) * 100 if high_52 > 0 else 0
        
        # Buat result
        result = {
            'Ticker': display_name,
            'Harga': int(price),
            'Harga_Str': f"Rp {int(price):,}".replace(',', '.'),
            'Skor': f"{score}/8",
            'Status': '8/8' if score == 8 else '7/8',
            'RS_Ratio': rs_ratio,
            'RS_Score': rs_score,
            'VCP': vcp_total,
            'Turnover': avg_turnover,
            'Turnover_M': f"{avg_turnover/1e6:.1f}M",
            'Low': f"{pct_from_low:.1f}%",
            'High': f"{pct_from_high:.1f}%",
            'C1': c1, 'C2': c2, 'C3': c3, 'C4': c4,
            'C5': c5, 'C6': c6, 'C7': c7, 'C8': c8,
        }
        
        with self.lock:
            if score >= 7:
                self.saham_lolos += 1
        
        return result, display_name, None

    # ============================================
    # FUNGSI UTAMA SCREENING (MULTITHREADING)
    # ============================================
    def screen(self, tickers):
        """
        Fungsi utama screening dengan multithreading
        
        Args:
            tickers: List kode saham (bisa dengan atau tanpa .JK)
            
        Returns:
            DataFrame dengan hasil screening
        """
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"MINERVINI PRO SCREENER - MULTITHREADING v5.0")
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
        
        # Ambil data IHSG untuk benchmark
        self.fetch_ihsg_data()
        
        # Progress tracking
        processed = 0
        success = 0
        failed = 0
        
        print(f"🚀 Memulai screening dengan {self.max_workers} thread paralel...")
        print(f"{'='*80}")
        
        # Gunakan ThreadPoolExecutor untuk multithreading
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit semua task
            future_to_ticker = {
                executor.submit(self.process_one_ticker, ticker, i, len(tickers)): ticker 
                for i, ticker in enumerate(tickers, 1)
            }
            
            # Proses hasil secara real-time
            for future in as_completed(future_to_ticker):
                processed += 1
                result, display_name, error = future.result()
                
                elapsed = time.time() - self.start_time
                avg_time = elapsed / processed
                remaining = (len(tickers) - processed) * avg_time
                
                # Progress bar
                progress = (processed / len(tickers)) * 100
                bar_length = 40
                filled = int(bar_length * processed // len(tickers))
                bar = '█' * filled + '░' * (bar_length - filled)
                
                if result:
                    success += 1
                    self.results.append(result)
                    status = f"✅ LOLOS! ({result['Skor']}) {result['Ticker']} RS:{result['RS_Ratio']:.2f} VCP:{result['VCP']}"
                else:
                    failed += 1
                    status = f"❌ {display_name}: {error if error else 'Gagal'}"
                
                # Print progress (update baris yang sama)
                print(f"\r[{bar}] {progress:.1f}% | "
                      f"Sukses:{success} Gagal:{failed} | "
                      f"Sisa:{int(remaining//60)}m{int(remaining%60)}s | "
                      f"{status[:60]}", end="", flush=True)
        
        print("\n")  # New line setelah selesai
        
        # Buat DataFrame hasil
        if self.results:
            df_results = pd.DataFrame(self.results)
            # Pilih kolom untuk output
            output_cols = ['Ticker', 'Harga_Str', 'Skor', 'Status', 'RS_Ratio', 'VCP', 
                          'Turnover_M', 'Low', 'High', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8']
            df_results = df_results[output_cols]
            # Rename untuk konsistensi
            df_results = df_results.rename(columns={'Harga_Str': 'Harga'})
            # Urutkan
            df_results = df_results.sort_values(
                ['Skor', 'RS_Ratio', 'VCP'], 
                ascending=[False, False, False]
            )
        else:
            df_results = pd.DataFrame()
        
        # Tampilkan ringkasan akhir
        total_time = time.time() - self.start_time
        self.logger.info(f"\n{'='*80}")
        self.logger.info("📊 RINGKASAN SCREENING")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Total saham: {self.total_saham}")
        self.logger.info(f"Berhasil diambil: {success}")
        self.logger.info(f"Error/Delisted: {failed}")
        self.logger.info(f"Lolos screening: {len(self.results)}")
        self.logger.info(f"Waktu total: {int(total_time//60)}m {int(total_time%60)}s")
        self.logger.info(f"Kecepatan: {self.total_saham/total_time:.1f} saham/detik")
        
        if len(self.results) > 0:
            count_8 = sum(1 for r in self.results if r['Status'] == '8/8')
            count_7 = sum(1 for r in self.results if r['Status'] == '7/8')
            self.logger.info(f"   - 8/8: {count_8}")
            self.logger.info(f"   - 7/8: {count_7}")
            
            print("\n📋 TOP 10 SAHAM:")
            top10 = df_results[['Ticker', 'Status', 'Harga', 'RS_Ratio', 'VCP']].head(10)
            print(top10.to_string(index=False))
        
        return df_results

    # ============================================
    # FUNGSI KONVERSI KE FORMAT GOOGLE SHEETS
    # ============================================
    def to_sheets_format(self, results_df):
        """Konversi hasil screening ke format yang siap dikirim ke Google Sheets"""
        if results_df is None or results_df.empty:
            return []
        
        formatted = []
        for _, row in results_df.iterrows():
            formatted.append({
                'Ticker': row['Ticker'],
                'Status': row['Status'],
                'Harga': row['Harga'],
                'VCP': row['VCP'],
                'RS': row['RS_Ratio']
            })
        return formatted


# ============================================
# FUNGSI UNTUK MEMBACA DAFTAR SAHAM DARI FILE
# ============================================
def load_tickers_from_file(filename="config/stocks_list.txt"):
    """Membaca daftar saham dari file"""
    tickers = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '#' in line:
                        ticker = line.split('#')[0].strip()
                    else:
                        ticker = line.strip()
                    if ticker:
                        tickers.append(ticker)
        print(f"📋 Loaded {len(tickers)} tickers from {filename}")
    except FileNotFoundError:
        print(f"⚠️ File {filename} tidak ditemukan, menggunakan daftar default")
        # Default tickers jika file tidak ada
        tickers = ["ADRO", "ANTM", "ASII", "BBCA", "BBNI", "BBRI", "BMRI", "BRIS"]
    return tickers


# ============================================
# FUNGSI MAIN UNTUK TESTING
# ============================================
def main():
    """Fungsi utama untuk testing dengan multithreading"""
    
    # Load tickers dari file
    tickers = load_tickers_from_file()
    
    print(f"\n{'='*80}")
    print(f"MINERVINI PRO SCREENER - MULTITHREADING v5.0")
    print(f"{'='*80}")
    print(f"Total saham: {len(tickers)}")
    
    # Pilih jumlah thread berdasarkan jumlah CPU
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    recommended_workers = min(20, cpu_count * 2)
    
    print(f"CPU Cores: {cpu_count}")
    print(f"Recommended workers: {recommended_workers}")
    print()
    
    # Inisialisasi screener dengan multithreading
    screener = MinerviniScreenerPro(
        min_turnover=500_000_000,
        max_workers=recommended_workers
    )
    
    # Jalankan screening
    results = screener.screen(tickers)
    
    # Simpan ke CSV
    if not results.empty:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"minervini_results_{timestamp}.csv"
        results.to_csv(filename, index=False)
        print(f"\n💾 Hasil disimpan ke: {filename}")
        
        # Konversi ke format sheets
        sheets_format = screener.to_sheets_format(results)
        print(f"\n📊 Siap dikirim ke Google Sheets: {len(sheets_format)} data")
    
    print("\n✨ Selesai!")


# ============================================
# ENTRY POINT
# ============================================
if __name__ == "__main__":
    main()
