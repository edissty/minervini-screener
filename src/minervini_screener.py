import yfinance as yf
import pandas as pd
import numpy as np
import time
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
        
    def get_stock_data(self, ticker, period='1y'):
        """
        Mengambil data saham dengan periode cukup untuk 52-week analysis
        """
        max_retries = 3
        
        # Bersihkan ticker dari komentar
        if '#' in ticker:
            ticker = ticker.split('#')[0].strip()
        
        original_ticker = ticker
        
        # Format yang akan dicoba
        ticker_formats = [
            f"{ticker}.JK",              # ADRO.JK
            f"JK:{ticker}",               # JK:ADRO
            ticker,                        # ADRO
            f"{ticker}.JKT",                # ADRO.JKT
        ]
        
        # Hapus duplikat
        ticker_formats = list(dict.fromkeys(ticker_formats))
        
        print(f"  Debug: Mencoba {len(ticker_formats)} format untuk {original_ticker}...")
        
        # Coba dengan periode berbeda
        periods_to_try = ['2y', '1y', 'max']
        
        for attempt in range(max_retries):
            for ticker_format in ticker_formats:
                for period_try in periods_to_try:
                    try:
                        # Gunakan curl_cffi session
                        session = requests.Session()
                        session.headers.update({
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        })
                        
                        # Impersonate Chrome
                        session.impersonate = "chrome120"
                        
                        # Panggil yfinance
                        stock = yf.Ticker(ticker_format, session=session)
                        
                        # Ambil data
                        df = stock.history(period=period_try, timeout=15)
                        
                        print(f"    Debug: {ticker_format} period={period_try}... ", end='')
                        
                        if df is not None and not df.empty:
                            print(f"✅ {len(df)} data points")
                            
                            # Minimal butuh 250 hari untuk analysis 52-week (252 hari trading)
                            if len(df) >= 250:
                                print(f"      ✓ Data cukup! ({len(df)} >= 250)")
                                self.saham_ok.append(original_ticker)
                                return df
                            else:
                                print(f"      ⚠ Data kurang: {len(df)}/250 hari")
                                if len(df) > 200:
                                    self.saham_kurang_data.append(original_ticker)
                                    return df
                        else:
                            print(f"❌ Kosong")
                            
                    except Exception as e:
                        print(f"    Debug: Error: {str(e)[:50]}...")
                        continue
                    
                    time.sleep(0.5)
            
            if attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1)
                print(f"  Debug: Percobaan ke-{attempt+1} gagal, menunggu {wait_time} detik...")
                time.sleep(wait_time)
        
        print(f"  ⚠ {original_ticker}: GAGAL TOTAL")
        self.saham_error.append(original_ticker)
        return None
    
    def calculate_ma(self, df, periods):
        """Menghitung Moving Average"""
        for period in periods:
            df[f'MA{period}'] = df['Close'].rolling(window=period).mean()
        return df
    
    def calculate_relative_strength(self, df, benchmark='^JKSE'):
        """
        Menghitung Relative Strength Rating (0-100)
        Membandingkan kinerja saham dengan IHSG (JKSE)
        """
        try:
            if len(df) < 60:  # Butuh minimal 60 hari untuk perhitungan
                return 0
            
            # Ambil data IHSG sebagai benchmark
            session = requests.Session()
            session.impersonate = "chrome120"
            idx = yf.Ticker(benchmark, session=session)
            idx_df = idx.history(period='3mo')
            
            if idx_df.empty or len(idx_df) < 60:
                # Fallback: gunakan return saham saja
                returns = df['Close'].pct_change().dropna()
                if len(returns) > 0:
                    # Hitung percentile dari return harian
                    rs = min(99, max(1, (returns.mean() * 100) + 50))
                    return rs
                return 50
            
            # Hitung return 3 bulan
            stock_return = (df['Close'].iloc[-1] / df['Close'].iloc[-60] - 1) * 100
            market_return = (idx_df['Close'].iloc[-1] / idx_df['Close'].iloc[-60] - 1) * 100
            
            # Relative Strength = stock_return - market_return + 50
            # Dibatasi antara 1-99
            rs = min(99, max(1, stock_return - market_return + 50))
            
            return rs
            
        except Exception as e:
            print(f"    Debug: Error RS: {e}")
            return 50
    
    def check_criteria(self, df):
        """Memeriksa 8 kriteria Minervini yang sesungguhnya"""
        if df is None:
            return {}
        
        data_points = len(df)
        print(f"  Debug: Memeriksa {data_points} data points")
        
        # Hitung semua MA
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
            # Data terbaru
            latest = df.iloc[-1]
            
            # Data untuk MA200 trend (1 bulan yang lalu = 22 hari trading)
            ma200_1month_ago = None
            if 'MA200' in df.columns and len(df) >= 222:  # 200 + 22
                ma200_1month_ago = df['MA200'].iloc[-22]
            
            # 52-week high/low
            if len(df) >= 252:
                year_data = df.tail(252)
                year_high = year_data['High'].max()
                year_low = year_data['Low'].min()
            else:
                # Pakai data yang ada
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
            
            # C3: MA200 Menanjak (lebih tinggi dari 1 bulan lalu)
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
            
            # Validasi
            if current_price <= 0:
                return {}
            
            total_met = sum(results.values())
            print(f"  Debug: Kriteria terpenuhi: {total_met}/8")
            
            # Tambahkan data tambahan untuk output
            results['_price'] = current_price
            results['_rs'] = rs_rating
            results['_from_low'] = pct_from_low if year_low > 0 else 0
            results['_from_high'] = pct_from_high if year_high > 0 else 0
            
            return results
            
        except Exception as e:
            print(f"  Debug: Error kriteria: {e}")
            return {}
    
    def screen_stocks(self, tickers):
        """Melakukan screening untuk daftar saham"""
        results = []
        self.total_saham = len(tickers)
        self.saham_error = []
        self.saham_ok = []
        self.saham_kurang_data = []
        
        print(f"\n{'='*80}")
        print(f"📊 MINERVINI SCREENER - 8 KRITERIA LENGKAP")
        print(f"{'='*80}")
        print(f"Total saham: {self.total_saham}")
        print(f"Mulai: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*80}\n")
        
        # Tampilkan kriteria
        print("📋 KRITERIA MINERVINI:")
        for k, v in self.criteria.items():
            print(f"   {k}: {v}")
        print()
        
        start_time = time.time()
        success_count = 0
        kurang_data_count = 0
        
        for i, ticker in enumerate(tickers, 1):
            # Hitung progress
            elapsed = time.time() - start_time
            if success_count > 0:
                avg_time = elapsed / success_count
                remaining = (self.total_saham - i) * avg_time
            else:
                remaining = 0
            
            progress = (i / self.total_saham) * 100
            print(f"[{i}/{self.total_saham}] ({progress:.1f}%) {ticker}")
            if remaining > 0:
                print(f"   ⏱️  Estimasi sisa: {int(remaining//60)}m {int(remaining%60)}s")
            
            # Ambil data
            df = self.get_stock_data(ticker)
            
            if df is not None:
                data_points = len(df)
                success_count += 1
                
                if data_points < 250:
                    kurang_data_count += 1
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
                    
                    # Ambil data tambahan
                    rs = criteria_results.get('_rs', 0)
                    from_low = criteria_results.get('_from_low', 0)
                    from_high = criteria_results.get('_from_high', 0)
                    
                    # Hanya simpan yang 7/8 atau 8/8
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
                        print(f"     Low: {from_low:.1f}% | High: {from_high:.1f}%")
                    else:
                        print(f"  ❌ Tidak lolos ({total_met}/8) - RS: {rs:.0f}")
                else:
                    print(f"  ❌ Gagal kriteria")
            else:
                print(f"  ❌ Gagal data")
            
            # Jeda antar request
            time.sleep(2)
        
        # Konversi ke DataFrame
        if results:
            df_results = pd.DataFrame(results)
            # Urutkan berdasarkan skor
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
        print(f"  - Data cukup      : {success_count - kurang_data_count}")
        print(f"  - Data kurang     : {kurang_data_count}")
        print(f"Error/Delisted      : {len(self.saham_error)}")
        print(f"Lolos screening     : {self.saham_lolos}")
        print(f"Waktu total         : {int(total_time//60)}m {int(total_time%60)}s")
        
        if self.saham_lolos > 0:
            count_8 = len(df_results[df_results['Status'] == '8/8'])
            count_7 = len(df_results[df_results['Status'] == '7/8'])
            print(f"\n✅ RINCIAN KELULUSAN:")
            print(f"   - 8/8: {count_8}")
            print(f"   - 7/8: {count_7}")
            
            print(f"\n📋 TOP SAHAM:")
            top5 = df_results.head(5)
            for idx, row in top5.iterrows():
                print(f"   {row['Ticker']}: {row['Status']} (RS: {row['RS']}) - {row['Harga']}")
        
        return df_results
