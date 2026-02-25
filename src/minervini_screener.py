import yfinance as yf
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime, timedelta
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
        
        # Statistik untuk delay management
        self.request_count = 0
        self.last_request_time = None
        self.error_count = 0
        self.consecutive_errors = 0
        
    def smart_delay(self):
        """
        Delay yang cerdas untuk menghindari rate limiting Yahoo Finance
        - Delay dasar: 2-4 detik (random)
        - Delay lebih panjang setiap 10 request
        - Delay eksponensial jika banyak error
        """
        self.request_count += 1
        
        # Delay dasar (random antara 2-4 detik)
        base_delay = random.uniform(2.0, 4.0)
        
        # Delay lebih panjang setiap 10 request
        if self.request_count % 10 == 0:
            long_delay = random.uniform(8.0, 12.0)
            print(f"  💤 Istirahat panjang {long_delay:.1f} detik (setelah {self.request_count} request)...")
            time.sleep(long_delay)
        
        # Jika ada error beruntun, delay eksponensial
        if self.consecutive_errors > 0:
            error_delay = min(30, 5 * (2 ** (self.consecutive_errors - 1)))
            print(f"  ⚠ Delay karena error ({self.consecutive_errors}x): {error_delay} detik")
            time.sleep(error_delay)
            self.consecutive_errors = 0  # Reset setelah delay
        
        # Delay normal
        print(f"  💤 Delay {base_delay:.1f} detik...")
        time.sleep(base_delay)
        
        # Update waktu request terakhir
        self.last_request_time = datetime.now()
    
    def get_stock_data(self, ticker, period='1y'):
        """
        Mengambil data saham dengan delay management dan multiple retry
        """
        max_retries = 4
        retry_delays = [5, 10, 20, 30]  # Exponential backoff
        
        # Bersihkan ticker dari komentar
        if '#' in ticker:
            ticker = ticker.split('#')[0].strip()
        
        original_ticker = ticker
        
        # Format yang akan dicoba (prioritas)
        ticker_formats = [
            f"{ticker}.JK",              # ADRO.JK (prioritas utama)
            ticker,                        # ADRO
            f"JK:{ticker}",               # JK:ADRO
            f"{ticker}.JKT",                # ADRO.JKT
            f"{ticker}.JK"                  # ADRO.JK (ulang)
        ]
        
        # Hapus duplikat
        ticker_formats = list(dict.fromkeys(ticker_formats))
        
        print(f"  Debug: Mencoba {len(ticker_formats)} format untuk {original_ticker}...")
        
        # Coba dengan periode berbeda
        periods_to_try = ['2y', '1y', 'max', '18mo']
        
        for attempt in range(max_retries):
            for ticker_format in ticker_formats:
                for period_try in periods_to_try:
                    try:
                        # Gunakan curl_cffi session
                        session = requests.Session()
                        
                        # Rotate User-Agent untuk menghindari deteksi bot
                        user_agents = [
                            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
                            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        ]
                        
                        session.headers.update({
                            'User-Agent': random.choice(user_agents),
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
                            'Accept-Encoding': 'gzip, deflate, br',
                            'Connection': 'keep-alive',
                            'Upgrade-Insecure-Requests': '1',
                            'Cache-Control': 'no-cache',
                            'Pragma': 'no-cache'
                        })
                        
                        # Rotate impersonate
                        if random.choice([True, False]):
                            session.impersonate = "chrome120"
                        else:
                            session.impersonate = "firefox120"
                        
                        # Tambahkan cookies random
                        session.cookies.set('consent', 'yes', domain='.yahoo.com')
                        session.cookies.set('A3', f'dummy{random.randint(1000,9999)}', domain='.yahoo.com')
                        
                        # Panggil yfinance dengan session
                        stock = yf.Ticker(ticker_format, session=session)
                        
                        # Ambil data dengan timeout lebih panjang
                        df = stock.history(period=period_try, timeout=20)
                        
                        print(f"    Debug: {ticker_format} period={period_try}... ", end='')
                        
                        if df is not None and not df.empty:
                            print(f"✅ {len(df)} data points")
                            self.consecutive_errors = 0  # Reset error counter
                            
                            # Minimal butuh 250 hari untuk analysis 52-week
                            if len(df) >= 250:
                                print(f"      ✓ Data cukup! ({len(df)} >= 250)")
                                self.saham_ok.append(original_ticker)
                                return df
                            else:
                                print(f"      ⚠ Data kurang: {len(df)}/250 hari")
                                if len(df) > 200:
                                    self.saham_kurang_data.append(original_ticker)
                                    return df
                                return None
                        else:
                            print(f"❌ Kosong")
                            
                    except Exception as e:
                        error_msg = str(e).lower()
                        print(f"    Debug: Error: {str(e)[:70]}...")
                        
                        # Deteksi rate limiting / block
                        if "rate" in error_msg or "limit" in error_msg or "429" in error_msg:
                            self.consecutive_errors += 1
                            print(f"    ⚠ Rate limited detected! Consecutive errors: {self.consecutive_errors}")
                            # Langsung delay panjang
                            time.sleep(retry_delays[min(self.consecutive_errors, len(retry_delays)-1)])
                        elif "ssl" in error_msg or "certificate" in error_msg:
                            # SSL error, coba dengan impersonate berbeda
                            pass
                        
                        continue
                    
                    # Delay antar format dalam satu saham
                    time.sleep(random.uniform(0.5, 1.5))
            
            # Jika gagal semua format di attempt ini, delay sebelum retry
            if attempt < max_retries - 1:
                wait_time = retry_delays[attempt]
                print(f"  Debug: Percobaan ke-{attempt+1} gagal, menunggu {wait_time} detik sebelum retry...")
                time.sleep(wait_time)
                
                # Reset format untuk next attempt
                random.shuffle(ticker_formats)  # Acak ulang format
        
        print(f"  ⚠ {original_ticker}: GAGAL TOTAL setelah {max_retries} percobaan")
        self.saham_error.append(original_ticker)
        self.consecutive_errors += 1
        return None
    
    def calculate_ma(self, df, periods):
        """Menghitung Moving Average"""
        for period in periods:
            df[f'MA{period}'] = df['Close'].rolling(window=period).mean()
        return df
    
    def calculate_relative_strength(self, df, benchmark='^JKSE'):
        """
        Menghitung Relative Strength Rating (0-100)
        """
        try:
            if len(df) < 60:
                return 50
            
            # Ambil data IHSG dengan delay management
            session = requests.Session()
            session.impersonate = random.choice(["chrome120", "firefox120"])
            idx = yf.Ticker(benchmark, session=session)
            idx_df = idx.history(period='3mo')
            
            if idx_df.empty or len(idx_df) < 60:
                # Fallback: gunakan return saham saja
                returns = df['Close'].pct_change().dropna()
                if len(returns) > 0:
                    rs = min(99, max(1, (returns.mean() * 100) + 50))
                    return rs
                return 50
            
            # Hitung return 3 bulan
            stock_return = (df['Close'].iloc[-1] / df['Close'].iloc[-60] - 1) * 100
            market_return = (idx_df['Close'].iloc[-1] / idx_df['Close'].iloc[-60] - 1) * 100
            
            # Relative Strength = stock_return - market_return + 50
            rs = min(99, max(1, stock_return - market_return + 50))
            
            return rs
            
        except Exception as e:
            print(f"    Debug: Error RS: {e}")
            return 50
    
    def check_criteria(self, df):
        """Memeriksa 8 kriteria Minervini"""
        if df is None:
            return {}
        
        data_points = len(df)
        print(f"  Debug: Memeriksa {data_points} data points")
        
        # Hitung MA
        available_periods = []
        if data_points >= 20:
            available_periods.append(20)
        if data_points >= 50:
            available_periods.append(50)
        if data_points >= 150:
            available_periods.append(150)
        if data_points >= 200:
            available_periods.append(200)
        
        df = self.calculate_ma(df, available_periods)
        
        try:
            latest = df.iloc[-1]
            
            # MA200 trend (1 bulan lalu)
            ma200_1month_ago = None
            if 'MA200' in df.columns and len(df) >= 222:
                ma200_1month_ago = df['MA200'].iloc[-22]
            
            # 52-week high/low
            if len(df) >= 252:
                year_data = df.tail(252)
                year_high = year_data['High'].max()
                year_low = year_data['Low'].min()
            else:
                year_high = df['High'].max()
                year_low = df['Low'].min()
            
            current_price = latest['Close']
            
            # Hitung Relative Strength
            rs_rating = self.calculate_relative_strength(df)
            
            results = {}
            
            # C1: Harga > MA150 dan MA200
            if 'MA150' in df.columns and 'MA200' in df.columns:
                results['C1'] = current_price > latest['MA150'] and current_price > latest['MA200']
            else:
                results['C1'] = False
            
            # C2: MA150 > MA200
            if 'MA150' in df.columns and 'MA200' in df.columns:
                results['C2'] = latest['MA150'] > latest['MA200']
            else:
                results['C2'] = False
            
            # C3: MA200 Menanjak
            if 'MA200' in df.columns and ma200_1month_ago is not None:
                results['C3'] = latest['MA200'] > ma200_1month_ago
            else:
                results['C3'] = False
            
            # C4: MA50 > MA150 dan MA200
            if 'MA50' in df.columns and 'MA150' in df.columns and 'MA200' in df.columns:
                results['C4'] = latest['MA50'] > latest['MA150'] and latest['MA50'] > latest['MA200']
            else:
                results['C4'] = False
            
            # C5: Harga > MA50
            if 'MA50' in df.columns:
                results['C5'] = current_price > latest['MA50']
            else:
                results['C5'] = False
            
            # C6: Harga > 30% dari 52-Week Low
            if year_low > 0:
                pct_from_low = (current_price / year_low - 1) * 100
                results['C6'] = pct_from_low > 30
                print(f"    Debug: Jarak dari low: {pct_from_low:.1f}%")
            else:
                results['C6'] = False
            
            # C7: Harga dalam 25% dari 52-Week High
            if year_high > 0:
                pct_from_high = (1 - current_price / year_high) * 100
                results['C7'] = pct_from_high <= 25
                print(f"    Debug: Jarak dari high: {pct_from_high:.1f}%")
            else:
                results['C7'] = False
            
            # C8: Relative Strength > 70
            results['C8'] = rs_rating > 70
            print(f"    Debug: RS Rating: {rs_rating:.1f}")
            
            if current_price <= 0:
                return {}
            
            # Simpan data tambahan
            results['_price'] = current_price
            results['_rs'] = rs_rating
            results['_from_low'] = pct_from_low if year_low > 0 else 0
            results['_from_high'] = pct_from_high if year_high > 0 else 0
            
            total_met = sum([v for k, v in results.items() if k.startswith('C')])
            print(f"  Debug: Kriteria terpenuhi: {total_met}/8")
            
            return results
            
        except Exception as e:
            print(f"  Debug: Error kriteria: {e}")
            return {}
    
    def screen_stocks(self, tickers):
        """Melakukan screening dengan delay management global"""
        results = []
        self.total_saham = len(tickers)
        self.saham_error = []
        self.saham_ok = []
        self.saham_kurang_data = []
        self.request_count = 0
        self.consecutive_errors = 0
        
        print(f"\n{'='*80}")
        print(f"📊 MINERVINI SCREENER - 220+ SAHAM SYARIAH")
        print(f"{'='*80}")
        print(f"Total saham: {self.total_saham}")
        print(f"Mulai: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*80}\n")
        
        # Tampilkan kriteria
        print("📋 8 KRITERIA MINERVINI:")
        for k, v in self.criteria.items():
            print(f"   {k}: {v}")
        print()
        
        start_time = time.time()
        success_count = 0
        
        for i, ticker in enumerate(tickers, 1):
            # Hitung progress
            elapsed = time.time() - start_time
            if success_count > 0:
                avg_time = elapsed / success_count
                remaining = (self.total_saham - i) * avg_time
            else:
                remaining = 0
            
            progress = (i / self.total_saham) * 100
            print(f"\n[{i}/{self.total_saham}] ({progress:.1f}%) {ticker}")
            if remaining > 0:
                print(f"   ⏱️  Estimasi sisa: {int(remaining//60)}m {int(remaining%60)}s")
                print(f"   📊 Progress: {success_count} berhasil, {len(self.saham_error)} error")
            
            # Ambil data
            df = self.get_stock_data(ticker)
            
            if df is not None:
                success_count += 1
                data_points = len(df)
                
                if data_points < 250:
                    print(f"   ⚠ Data: {data_points} hari (< 250)")
                
                criteria_results = self.check_criteria(df)
                
                if criteria_results:
                    total_met = sum([v for k, v in criteria_results.items() if k.startswith('C')])
                    
                    # Format harga
                    price = criteria_results.get('_price', 0)
                    if price >= 1000:
                        price_str = f"Rp {price/1000:.1f}K"
                    else:
                        price_str = f"Rp {price:,.0f}"
                    
                    rs = criteria_results.get('_rs', 0)
                    
                    if total_met >= 7:
                        clean_ticker = ticker.split('#')[0].strip()
                        
                        result = {
                            'Ticker': clean_ticker,
                            'Data': f"{data_points}hr",
                            'Skor': f"{total_met}/8",
                            'Status': '8/8' if total_met == 8 else '7/8',
                            'Harga': price_str,
                            'RS': f"{rs:.0f}",
                            'C1': '✓' if criteria_results.get('C1', False) else '✗',
                            'C2': '✓' if criteria_results.get('C2', False) else '✗',
                            'C3': '✓' if criteria_results.get('C3', False) else '✗',
                            'C4': '✓' if criteria_results.get('C4', False) else '✗',
                            'C5': '✓' if criteria_results.get('C5', False) else '✗',
                            'C6': '✓' if criteria_results.get('C6', False) else '✗',
                            'C7': '✓' if criteria_results.get('C7', False) else '✗',
                            'C8': '✓' if criteria_results.get('C8', False) else '✗',
                        }
                        results.append(result)
                        print(f"  ✅ LOLOS! ({total_met}/8) - {price_str} (RS: {rs:.0f})")
                    else:
                        print(f"  ❌ Tidak lolos ({total_met}/8) - RS: {rs:.0f}")
                else:
                    print(f"  ❌ Gagal kriteria")
            
            # Delay antar saham (WAJIB!)
            self.smart_delay()
        
        # Konversi ke DataFrame
        if results:
            df_results = pd.DataFrame(results)
            df_results = df_results.sort_values(['Status', 'RS'], ascending=[False, False])
            self.saham_lolos = len(df_results)
        else:
            df_results = pd.DataFrame()
            self.saham_lolos = 0
        
        # Tampilkan ringkasan
        total_time = time.time() - start_time
        print("\n" + "=" * 80)
        print("📊 RINGKASAN FINAL")
        print("=" * 80)
        print(f"Total saham         : {self.total_saham}")
        print(f"Berhasil diambil    : {success_count}")
        print(f"  - Data cukup      : {success_count - len(self.saham_kurang_data)}")
        print(f"  - Data kurang     : {len(self.saham_kurang_data)}")
        print(f"Error/Delisted      : {len(self.saham_error)}")
        print(f"Lolos screening     : {self.saham_lolos}")
        print(f"Total request       : {self.request_count}")
        print(f"Waktu total         : {int(total_time//60)}m {int(total_time%60)}s")
        print(f"Rata-rata per saham : {total_time/self.total_saham:.1f} detik")
        
        if self.saham_lolos > 0:
            count_8 = len(df_results[df_results['Status'] == '8/8'])
            count_7 = len(df_results[df_results['Status'] == '7/8'])
            print(f"\n✅ RINCIAN KELULUSAN:")
            print(f"   - 8/8: {count_8}")
            print(f"   - 7/8: {count_7}")
            
            print(f"\n📋 TOP 10 SAHAM:")
            top10 = df_results.head(10)
            for idx, row in top10.iterrows():
                print(f"   {row['Ticker']}: {row['Status']} (RS: {row['RS']}) - {row['Harga']}")
        
        return df_results
