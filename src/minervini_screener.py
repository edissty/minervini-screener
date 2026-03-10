# ============================================
# MINERVINI PRO SCREENER - SAHAM SYARIAH INDONESIA
# Versi 4.0 - Dengan RS vs IHSG & VCP Scoring
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

class MinerviniScreenerPro:
    """
    Screener saham syariah Indonesia dengan 8 kriteria Minervini + VCP Scoring
    dan Relative Strength vs IHSG yang akurat.
    """
    
    def __init__(self, min_turnover=500_000_000, log_level=logging.INFO):
        """
        Inisialisasi screener
        
        Args:
            min_turnover: Minimal turnover (harga * volume) untuk filter likuiditas
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
        self.setup_logging(log_level)
        
        # Statistik
        self.total_saham = 0
        self.saham_lolos = 0
        self.saham_error = []
        self.saham_ok = []
        self.request_count = 0
        
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
        self.logger.info("="*80)
        self.logger.info("MINERVINI PRO SCREENER INITIALIZED")
        self.logger.info("="*80)
        
    # ============================================
    # FUNGSI FETCH DATA IHSG (DENGAN CACHING)
    # ============================================
    def fetch_ihsg_data(self, force_refresh=False):
        """
        Mengambil data IHSG sebagai benchmark RS Rating
        Dengan caching untuk menghindari fetch berulang
        """
        if self.index_data is not None and not force_refresh:
            self.logger.info("📊 Menggunakan data IHSG dari cache")
            return self.index_data
        
        self.logger.info("📊 Mengambil data benchmark IHSG (^JKSE)...")
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Gunakan session dengan impersonate
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
        """
        RS Rating dengan multiple timeframe (12m, 6m, 3m, 1m)
        Return: (rs_ratio, rs_score_0_100)
        """
        if self.index_data is None or stock_df is None or len(stock_df) < 252:
            return 0, 0
        
        try:
            # Sinkronisasi tanggal (ambil data yang sama)
            common_dates = stock_df.index.intersection(self.index_data.index)
            if len(common_dates) < 200:
                self.logger.debug(f"Data tidak sinkron: hanya {len(common_dates)} tanggal")
                return 0, 0
            
            s_price = stock_df.loc[common_dates, 'Close']
            i_price = self.index_data.loc[common_dates, 'Close']
            
            # Periode: 1, 3, 6, 12 bulan (dalam hari trading)
            periods = [21, 63, 126, 252]
            weights = [0.1, 0.2, 0.3, 0.4]  # Bobot lebih besar untuk jangka panjang
            
            stock_perf = 0
            index_perf = 0
            
            for period, weight in zip(periods, weights):
                if len(s_price) > period:
                    s_ret = (s_price.iloc[-1] / s_price.iloc[-period] - 1)
                    i_ret = (i_price.iloc[-1] / i_price.iloc[-period] - 1)
                    
                    stock_perf += (1 + s_ret) * weight
                    index_perf += (1 + i_ret) * weight
            
            rs_ratio = stock_perf / index_perf if index_perf > 0 else 1
            
            # Konversi ke skala 0-100 (opsional, untuk sorting)
            # Asumsi rs_ratio normal antara 0.5 - 2.0
            rs_score = min(99, max(1, (rs_ratio - 0.5) * 100))
            
            return round(rs_ratio, 3), round(rs_score, 1)
            
        except Exception as e:
            self.logger.debug(f"Error RS Rating: {e}")
            return 0, 0

    # ============================================
    # FUNGSI VCP SCORE (KOMPREHENSIF)
    # ============================================
    def calculate_vcp_score(self, df):
        """
        VCP Score (0-100) berdasarkan:
        - Volatility contraction (bobot 60)
        - Volume dry-up (bobot 30)
        - Price position (bobot 10)
        """
        if len(df) < 150:
            return 0, 0, 0
        
        try:
            # 1. Volatility Tightness (bobot 60)
            # Gunakan multiple windows untuk deteksi lebih akurat
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
            
            # 2. Volume Dry-up (bobot 30)
            recent_vol = df['Volume'].iloc[-10:].mean()
            hist_vol = df['Volume'].iloc[-60:-10].mean()
            
            vol_dryup = 0
            if hist_vol > 0:
                vol_ratio = recent_vol / hist_vol
                vol_dryup = max(0, (1 - vol_ratio) * 100) * 0.3
                vol_dryup = min(30, vol_dryup)
            
            # 3. Price Position (bobot 10) - Harga di dekat 52-week high
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
        """Cek apakah saham cukup likuid (minimal turnover tertentu)"""
        try:
            avg_turnover = (df['Close'] * df['Volume']).tail(20).mean()
            is_liquid = avg_turnover >= self.min_turnover
            return is_liquid, avg_turnover
        except Exception as e:
            self.logger.debug(f"Error cek likuiditas: {e}")
            return False, 0

    # ============================================
    # FUNGSI AMBIL DATA SAHAM (DENGAN RETRY)
    # ============================================
    def get_stock_data(self, ticker, period='2y'):
        """Ambil data saham dengan retry mechanism"""
        max_retries = 3
        
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
                # Gunakan session dengan impersonate
                session = requests.Session()
                session.impersonate = "chrome120"
                
                stock = yf.Ticker(symbol, session=session)
                df = stock.history(period=period, timeout=15)
                
                if df is not None and not df.empty:
                    if len(df) >= 200:
                        return df, display_name
                    else:
                        self.logger.debug(f"⚠️ {display_name}: Data {len(df)}/200 hari")
                        return None, display_name
                else:
                    return None, display_name
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 3 * (attempt + 1)
                    self.logger.debug(f"⏳ {display_name}: Retry {attempt+1} dalam {wait}s")
                    time.sleep(wait)
                else:
                    self.logger.debug(f"❌ {display_name}: Gagal total - {str(e)[:50]}")
                    return None, display_name
        
        return None, display_name

    # ============================================
    # FUNGSI UTAMA SCREENING
    # ============================================
    def screen(self, tickers):
        """
        Fungsi utama untuk screening saham
        
        Args:
            tickers: List kode saham (bisa dengan atau tanpa .JK)
            
        Returns:
            DataFrame dengan hasil screening
        """
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"MINERVINI PRO SCREENER - {len(tickers)} SAHAM SYARIAH")
        self.logger.info(f"{'='*80}")
        
        # Reset statistik
        self.total_saham = len(tickers)
        self.saham_lolos = 0
        self.saham_error = []
        self.saham_ok = []
        self.request_count = 0
        results = []
        
        # Ambil data IHSG untuk benchmark
        self.fetch_ihsg_data()
        
        start_time = time.time()
        success_count = 0
        
        for i, ticker in enumerate(tickers, 1):
            # Hitung progress
            elapsed = time.time() - start_time
            if success_count > 0:
                avg_time = elapsed / success_count
                remaining = (len(tickers) - i) * avg_time
            else:
                remaining = 0
            
            progress = (i / len(tickers)) * 100
            print(f"[{i}/{len(tickers)}] ({progress:.1f}%) {ticker} | "
                  f"Sisa: {int(remaining//60)}m {int(remaining%60)}s")
            
            # Ambil data saham
            df, display_name = self.get_stock_data(ticker)
            
            if df is not None:
                success_count += 1
                self.saham_ok.append(display_name)
                
                # Cek likuiditas
                is_liquid, avg_turnover = self.check_liquidity(df)
                if not is_liquid:
                    print(f"   ⚠ Likuiditas rendah: Rp {avg_turnover/1e6:.1f}M < target")
                    continue
                
                # Hitung indikator teknikal
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
                
                # Hitung RS Rating dan VCP Score
                rs_ratio, rs_score = self.calculate_rs_rating(df)
                vcp_total, vcp_tight, vcp_vol = self.calculate_vcp_score(df)
                
                # Evaluasi 8 kriteria
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
                
                # Hitung jarak dari low dan high
                pct_from_low = ((price / low_52) - 1) * 100 if low_52 > 0 else 0
                pct_from_high = (1 - (price / high_52)) * 100 if high_52 > 0 else 0
                
                # Simpan jika minimal 7 kriteria terpenuhi
                if score >= 7:
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
                    results.append(result)
                    print(f"   ✅ LOLOS! ({score}/8) RS:{rs_ratio:.2f} VCP:{vcp_total}")
                else:
                    print(f"   ❌ Tidak lolos ({score}/8)")
            
            else:
                self.saham_error.append(display_name)
                print(f"   ❌ Gagal mengambil data")
            
            # Delay dinamis untuk menghindari rate limit
            delay = random.uniform(0.8, 1.2)
            if success_count > 0 and success_count % 10 == 0:
                print(f"   💤 Istirahat 3 detik...")
                delay += 3
            time.sleep(delay)
        
        # Buat DataFrame hasil
        if results:
            df_results = pd.DataFrame(results)
            # Urutkan berdasarkan skor, lalu RS, lalu VCP
            df_results = df_results.sort_values(
                ['Skor', 'RS_Score', 'VCP'], 
                ascending=[False, False, False]
            )
            self.saham_lolos = len(df_results)
        else:
            df_results = pd.DataFrame()
            self.saham_lolos = 0
        
        # Tampilkan ringkasan akhir
        total_time = time.time() - start_time
        self.logger.info(f"\n{'='*80}")
        self.logger.info("📊 RINGKASAN SCREENING")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Total saham: {self.total_saham}")
        self.logger.info(f"Berhasil diambil: {success_count}")
        self.logger.info(f"Error/Delisted: {len(self.saham_error)}")
        self.logger.info(f"Lolos screening: {self.saham_lolos}")
        self.logger.info(f"Waktu total: {int(total_time//60)}m {int(total_time%60)}s")
        
        if self.saham_lolos > 0:
            count_8 = len(df_results[df_results['Status'] == '8/8'])
            count_7 = len(df_results[df_results['Status'] == '7/8'])
            self.logger.info(f"   - 8/8: {count_8}")
            self.logger.info(f"   - 7/8: {count_7}")
            
            print("\n📋 TOP SAHAM:")
            print(df_results[['Ticker', 'Status', 'Harga', 'RS_Ratio', 'VCP']].head(10).to_string(index=False))
        
        return df_results

    # ============================================
    # FUNGSI KONVERSI KE FORMAT GOOGLE SHEETS
    # ============================================
    def to_sheets_format(self, results_df):
        """
        Konversi hasil screening ke format yang siap dikirim ke Google Sheets
        """
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
# FUNGSI MAIN UNTUK TESTING
# ============================================
def main():
    """Fungsi utama untuk testing"""
    
    # Daftar saham syariah untuk testing
    tickers = [
        "ADRO", "ANTM", "ASII", "BBCA", "BBNI", "BBRI", "BMRI", "BRIS",
        "CPIN", "ERAA", "EXCL", "GOTO", "HMSP", "ICBP", "INCO", "INDF",
        "INKP", "INTP", "ISAT", "ITMG", "JPFA", "JSMR", "KLBF", "MAPI",
        "MDKA", "MIKA", "MTDL", "MYOR", "PGAS", "PTBA", "PTPP", "PWON",
        "SIDO", "SILO", "SMGR", "TBIG", "TKIM", "TLKM", "TOWR", "UNTR",
        "UNVR", "WIKA", "WSKT"
    ]
    
    # Inisialisasi screener
    screener = MinerviniScreenerPro(min_turnover=500_000_000)
    
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


# ============================================
# ENTRY POINT
# ============================================
if __name__ == "__main__":
    main()
