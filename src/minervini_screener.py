import yfinance as yf
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime
from curl_cffi import requests

class MinerviniScreener:
    def __init__(self):
        self.criteria = {
            'C1': 'Harga > MA150 dan MA200',
            'C2': 'MA150 > MA200',
            'C3': 'MA200 Menanjak (lebih tinggi dari 1 bulan lalu)',
            'C4': 'MA50 > MA150 dan MA200',
            'C5': 'Harga > MA50',
            'C6': 'Harga > 30% dari 52-Week Low',
            'C7': 'Harga dalam 25% dari 52-Week High',
            'C8': 'Relative Strength (RS) > 70'
        }
        self.total_saham = 0
        self.saham_lolos = 0
        self.saham_error = []
        self.saham_ok = []
        self.saham_kurang_data = []
        
        # Statistik
        self.request_count = 0
        self.last_request_time = None
        self.error_count = 0
        self.consecutive_errors = 0
        
    def smart_delay(self, is_error=False):
        """Delay 1-2 detik untuk 220 saham"""
        self.request_count += 1
        
        if is_error or self.consecutive_errors > 0:
            print(f"  ⚠ Error delay: 5s")
            time.sleep(5)
            self.consecutive_errors = max(0, self.consecutive_errors - 1)
            return
        
        base_delay = random.uniform(1.0, 2.0)
        
        if self.request_count % 20 == 0:
            long_delay = random.uniform(3.0, 5.0)
            print(f"  💤 Bulk delay: {long_delay:.1f}s (after {self.request_count} requests)")
            time.sleep(long_delay)
        else:
            print(f"  💤 Delay: {base_delay:.1f}s")
            time.sleep(base_delay)
        
        self.last_request_time = datetime.now()
    
    def get_stock_data(self, ticker, period='1y'):
        """Ambil data saham - TANPA nambah .JK jika sudah ada"""
        max_retries = 2
        
        # Bersihkan ticker dari komentar
        if '#' in ticker:
            ticker = ticker.split('#')[0].strip()
        
        original_ticker = ticker
        
        # Format yang akan dicoba - JANGAN nambah .JK jika sudah ada
        ticker_formats = []
        
        if ticker.endswith('.JK'):
            # Jika sudah pakai .JK, gunakan apa adanya
            ticker_formats = [
                ticker,                    # ADRO.JK
                ticker.replace('.JK', ''),  # ADRO (tanpa .JK)
                f"JK:{ticker.replace('.JK', '')}"  # JK:ADRO
            ]
        else:
            # Jika belum pakai .JK, tambahkan
            ticker_formats = [
                f"{ticker}.JK",  # ADRO.JK
                ticker,            # ADRO
                f"JK:{ticker}"     # JK:ADRO
            ]
        
        # Hapus duplikat
        ticker_formats = list(dict.fromkeys(ticker_formats))
        
        periods_to_try = ['2y', '1y']
        
        for attempt in range(max_retries):
            for ticker_format in ticker_formats:
                for period_try in periods_to_try:
                    try:
                        session = requests.Session()
                        session.impersonate = "chrome120"
                        
                        session.headers.update({
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        })
                        
                        stock = yf.Ticker(ticker_format, session=session)
                        df = stock.history(period=period_try, timeout=10)
                        
                        if df is not None and not df.empty:
                            print(f"    ✅ {ticker_format} = {len(df)} data points")
                            self.consecutive_errors = 0
                            
                            if len(df) >= 200:
                                self.saham_ok.append(original_ticker)
                                return df
                            else:
                                print(f"    ⚠ Data {len(df)}/200")
                                if len(df) > 150:
                                    self.saham_kurang_data.append(original_ticker)
                                    return df
                                return None
                                
                    except Exception as e:
                        print(f"    Debug: {ticker_format} error: {str(e)[:30]}...")
                        continue
                    
                    time.sleep(0.2)
            
            if attempt == 0:
                # Coba format alternatif di percobaan kedua
                if ticker.endswith('.JK'):
                    ticker_formats = [f"JK:{ticker.replace('.JK', '')}"]
                else:
                    ticker_formats = [f"JK:{ticker}"]
                time.sleep(2)
        
        self.saham_error.append(original_ticker)
        self.consecutive_errors += 1
        return None
    
    def calculate_relative_strength(self, df):
        """RS Rating sederhana (tanpa IHSG)"""
        try:
            if len(df) < 60:
                return 50
            
            # Hitung return 60 hari
            returns = df['Close'].pct_change(60).iloc[-1] * 100
            
            if pd.notna(returns):
                # Konversi ke skala 1-99
                rs = min(99, max(1, returns + 50))
                return rs
            return 50
        except:
            return 50

    # ==================== VCP SCORING ====================
    def calculate_vcp_score(self, df):
        """
        Menghitung VCP Score (0-100) berdasarkan kontraksi volatilitas dan volume dry-up.
        Skor semakin tinggi menandakan pola VCP semakin ketat.
        """
        if df is None or len(df) < 120:
            return 0.0, 0.0, 0.0

        # --- Tightness Score (bobot 70) ---
        windows = [20, 30, 40, 60]
        tight_scores = []
        for w in windows:
            if len(df) < w + 60:
                continue
            # Rentang harga (high-low) rata-rata periode terakhir
            recent_range = (df['High'].iloc[-w:] - df['Low'].iloc[-w:]).mean()
            # Rentang harga periode historis (sebelumnya, 60 hari)
            hist_range = (df['High'].iloc[-(w+60):-w] - df['Low'].iloc[-(w+60):-w]).mean()
            if hist_range > 0:
                ratio = recent_range / hist_range
                # Semakin kecil ratio (range menyempit) -> skor tinggi
                score = max(0, (1 - ratio) * 100)
                tight_scores.append(min(100, score))
        if tight_scores:
            tight_avg = sum(tight_scores) / len(tight_scores)
            tight_score = tight_avg * 0.7  # bobot 70%
        else:
            tight_score = 0

        # --- Volume Dry-Up Score (bobot 30) ---
        if len(df) >= 60:
            recent_vol = df['Volume'].iloc[-10:].mean()
            hist_vol = df['Volume'].iloc[-60:-10].mean()
            if hist_vol > 0:
                vol_ratio = recent_vol / hist_vol
                # Semakin kecil vol_ratio (volume mengering) -> skor tinggi
                vol_score = max(0, (1 - vol_ratio) * 100) * 0.3
                vol_score = min(30, vol_score)
            else:
                vol_score = 0
        else:
            vol_score = 0

        total = round(tight_score + vol_score, 1)
        return total, round(tight_score, 1), round(vol_score, 1)
    # ===================================================

    def check_criteria(self, df):
        """Cek 8 kriteria Minervini"""
        if df is None or len(df) < 150:
            return {}
        
        try:
            # Hitung MA
            for period in [20, 50, 150, 200]:
                if len(df) >= period:
                    df[f'MA{period}'] = df['Close'].rolling(window=period).mean()
            
            latest = df.iloc[-1]
            
            # 52-week range
            year_high = df['High'].tail(252).max()
            year_low = df['Low'].tail(252).min()
            
            current_price = latest['Close']
            
            # MA200 trend
            ma200_up = False
            if 'MA200' in df.columns and len(df) >= 222:
                ma200_up = df['MA200'].iloc[-1] > df['MA200'].iloc[-22]
            
            # RS Rating
            rs = self.calculate_relative_strength(df)
            
            # Hitung dari low dan high
            pct_from_low = (current_price / year_low - 1) * 100 if year_low > 0 else 0
            pct_from_high = (1 - current_price / year_high) * 100 if year_high > 0 else 0
            
            results = {
                'C1': ('MA150' in df.columns and 'MA200' in df.columns and 
                       current_price > latest['MA150'] and current_price > latest['MA200']),
                'C2': ('MA150' in df.columns and 'MA200' in df.columns and 
                       latest['MA150'] > latest['MA200']),
                'C3': ma200_up,
                'C4': ('MA50' in df.columns and 'MA150' in df.columns and 'MA200' in df.columns and
                       latest['MA50'] > latest['MA150'] and latest['MA50'] > latest['MA200']),
                'C5': ('MA50' in df.columns and current_price > latest['MA50']),
                'C6': pct_from_low > 30,
                'C7': pct_from_high <= 25,
                'C8': rs > 70,
                '_price': current_price,
                '_rs': rs,
                '_from_low': pct_from_low,
                '_from_high': pct_from_high
            }
            
            return results
            
        except Exception as e:
            return {}
    
    def screen_stocks(self, tickers):
        """Main screening function"""
        results = []
        self.total_saham = len(tickers)
        self.saham_error = []
        self.saham_ok = []
        self.saham_kurang_data = []
        self.request_count = 0
        
        print(f"\n{'='*70}")
        print(f"⚡ MINERVINI SCREENER - SAHAM SYARIAH + VCP SCORING")
        print(f"{'='*70}")
        print(f"Total saham: {self.total_saham}")
        print(f"Target waktu: {self.total_saham * 1.5 / 60:.1f} menit")
        print(f"{'='*70}\n")
        
        # Tampilkan kriteria
        print("📋 8 KRITERIA MINERVINI:")
        for k, v in self.criteria.items():
            print(f"   {k}: {v}")
        print()
        
        start_time = time.time()
        success_count = 0
        
        for i, ticker in enumerate(tickers, 1):
            elapsed = time.time() - start_time
            avg_time = elapsed / i if i > 0 else 0
            remaining = (self.total_saham - i) * avg_time
            
            progress = (i / self.total_saham) * 100
            print(f"\n[{i}/{self.total_saham}] ({progress:.1f}%) {ticker}")
            print(f"   ⏱️  Sisa: {int(remaining//60)}m {int(remaining%60)}s | Rata: {avg_time:.1f}s/saham")
            
            df = self.get_stock_data(ticker)
            
            if df is not None:
                success_count += 1
                criteria = self.check_criteria(df)
                
                if criteria:
                    total_met = sum([v for k, v in criteria.items() if k.startswith('C')])
                    
                    if total_met >= 7:
                        price = criteria.get('_price', 0)
                        # FORMAT HARGA DETAIL
                        price_str = f"Rp {price:,.0f}".replace(',', '.')
                        
                        rs = criteria.get('_rs', 0)
                        from_low = criteria.get('_from_low', 0)
                        from_high = criteria.get('_from_high', 0)
                        
                        # Hitung VCP Score
                        vcp_total, vcp_tight, vcp_vol = self.calculate_vcp_score(df)
                        
                        # Ticker tanpa .JK untuk tampilan
                        display_ticker = ticker.replace('.JK', '') if ticker.endswith('.JK') else ticker
                        
                        result = {
                            'Ticker': display_ticker,
                            'Data': f"{len(df)}hr",
                            'Skor': f"{total_met}/8",
                            'Status': '8/8' if total_met == 8 else '7/8',
                            'Harga': price_str,
                            'RS': f"{rs:.0f}",
                            'VCP': vcp_total,          # VCP Score
                            'Low': f"{from_low:.0f}%",
                            'High': f"{from_high:.0f}%",
                            'C1': '✓' if criteria.get('C1') else '✗',
                            'C2': '✓' if criteria.get('C2') else '✗',
                            'C3': '✓' if criteria.get('C3') else '✗',
                            'C4': '✓' if criteria.get('C4') else '✗',
                            'C5': '✓' if criteria.get('C5') else '✗',
                            'C6': '✓' if criteria.get('C6') else '✗',
                            'C7': '✓' if criteria.get('C7') else '✗',
                            'C8': '✓' if criteria.get('C8') else '✗',
                        }
                        results.append(result)
                        print(f"  ✅ LOLOS! ({total_met}/8) RS:{rs:.0f} VCP:{vcp_total} Harga:{price_str}")
                    else:
                        print(f"  ❌ {total_met}/8")
            
            self.smart_delay(is_error=(df is None))
        
        # Hasil
        total_time = time.time() - start_time
        print("\n" + "=" * 70)
        print("📊 HASIL SCREENING")
        print("=" * 70)
        print(f"Total saham    : {self.total_saham}")
        print(f"Berhasil       : {success_count}")
        print(f"Error          : {len(self.saham_error)}")
        print(f"Lolos          : {len(results)}")
        print(f"Waktu total    : {int(total_time//60)}m {int(total_time%60)}s")
        print(f"Rata-rata      : {total_time/self.total_saham:.1f}s/saham")
        
        if results:
            df_results = pd.DataFrame(results)
            # Urutkan berdasarkan Status (8/8 dulu), lalu VCP Score tertinggi
            df_results = df_results.sort_values(['Status', 'VCP'], ascending=[False, False])
            return df_results
        
        return pd.DataFrame()