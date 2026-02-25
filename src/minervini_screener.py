import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime
from curl_cffi import requests  # GANTI DENGAN INI!

class MinerviniScreener:
    def __init__(self):
        self.criteria = {
            'C1': 'Harga > MA150 dan MA200',
            'C2': 'MA150 > MA200',
            'C3': 'MA50 > MA150 dan MA200',
            'C4': 'Harga > MA50',
            'C5': 'Harga > MA20',
            'C6': 'MA20 > MA50',
            'C7': 'Trend naik (harga 25% > harga 50 hari lalu)',
            'C8': 'Volume > rata-rata 50 hari'
        }
        self.total_saham = 0
        self.saham_lolos = 0
        self.saham_error = []
        self.saham_ok = []
        
    def get_stock_data(self, ticker, period='6mo'):
        """
        Mengambil data saham dengan curl_cffi (wajib untuk Yahoo Finance sekarang)
        """
        max_retries = 3
        
        # HAPUS KOMENTAR DARI TICKER! (ini penting)
        # Ambil hanya kode saham, buang komentar setelah #
        if '#' in ticker:
            ticker = ticker.split('#')[0].strip()
        
        original_ticker = ticker
        
        # Format yang akan dicoba
        ticker_formats = [
            f"{ticker}.JK",              # ADRO.JK
            f"JK:{ticker}",               # JK:ADRO
            ticker,                        # ADRO
            f"{ticker}.JKT",                # ADRO.JKT
            f"{ticker}.JK"                  # ADRO.JK (ulang)
        ]
        
        # Hapus duplikat
        ticker_formats = list(dict.fromkeys(ticker_formats))
        
        print(f"  Debug: Mencoba {len(ticker_formats)} format untuk {original_ticker}...")
        
        for attempt in range(max_retries):
            for ticker_format in ticker_formats:
                try:
                    # YANG PALING PENTING: Gunakan curl_cffi session!
                    # Buat session dengan impersonate browser
                    session = requests.Session()
                    session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    })
                    
                    # Impersonate Chrome (ini kunci utamanya!)
                    session.impersonate = "chrome120"
                    
                    # Panggil yfinance dengan session curl_cffi
                    stock = yf.Ticker(ticker_format, session=session)
                    
                    # Ambil data dengan timeout
                    df = stock.history(period=period, timeout=15)
                    
                    print(f"    Debug: Mencoba format '{ticker_format}'... ", end='')
                    
                    if df is not None and not df.empty:
                        print(f"✅ BERHASIL! ({len(df)} data points)")
                        self.saham_ok.append(original_ticker)
                        return df
                    else:
                        print(f"❌ Data kosong")
                        
                except Exception as e:
                    error_msg = str(e)
                    print(f"    Debug: Error '{ticker_format}': {error_msg[:50]}...")
                    
                    # Jika error SSL, coba dengan impersonate berbeda
                    if "SSL" in error_msg or "certificate" in error_msg:
                        try:
                            # Coba dengan impersonate Firefox
                            session.impersonate = "firefox120"
                            stock = yf.Ticker(ticker_format, session=session)
                            df = stock.history(period=period, timeout=15)
                            if df is not None and not df.empty:
                                print(f"    Debug: BERHASIL dengan Firefox! {len(df)} data")
                                self.saham_ok.append(original_ticker)
                                return df
                        except:
                            pass
                    continue
            
            if attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1)
                print(f"  Debug: Percobaan ke-{attempt+1} gagal, menunggu {wait_time} detik sebelum retry...")
                time.sleep(wait_time)
        
        print(f"  ⚠ {original_ticker}: SEMUA FORMAT GAGAL setelah {max_retries} percobaan")
        self.saham_error.append(original_ticker)
        return None
    
    def calculate_ma(self, df, periods):
        """Menghitung Moving Average"""
        for period in periods:
            df[f'MA{period}'] = df['Close'].rolling(window=period).mean()
        return df
    
    def check_criteria(self, df):
        """Memeriksa kriteria Minervini"""
        if df is None or len(df) < 200:
            print(f"  Debug: Data tidak cukup ({len(df) if df is not None else 0} hari)")
            return {}
        
        try:
            # Hitung MA
            df = self.calculate_ma(df, [20, 50, 150, 200])
            
            # Data terbaru
            latest = df.iloc[-1]
            
            # Data 50 hari lalu
            prev_50 = df.iloc[-50] if len(df) >= 50 else None
            
            results = {}
            
            # C1: Harga > MA150 dan MA200
            results['C1'] = (
                latest['Close'] > latest['MA150'] and 
                latest['Close'] > latest['MA200']
            )
            
            # C2: MA150 > MA200
            results['C2'] = latest['MA150'] > latest['MA200']
            
            # C3: MA50 > MA150 dan MA200
            results['C3'] = (
                latest['MA50'] > latest['MA150'] and 
                latest['MA50'] > latest['MA200']
            )
            
            # C4: Harga > MA50
            results['C4'] = latest['Close'] > latest['MA50']
            
            # C5: Harga > MA20
            results['C5'] = latest['Close'] > latest['MA20']
            
            # C6: MA20 > MA50
            results['C6'] = latest['MA20'] > latest['MA50']
            
            # C7: Trend naik (25% dalam 50 hari)
            if prev_50 is not None and prev_50['Close'] > 0:
                pct_change = (latest['Close'] / prev_50['Close'] - 1) * 100
                results['C7'] = pct_change > 25
            else:
                results['C7'] = False
            
            # C8: Volume > rata-rata 50 hari
            avg_volume = df['Volume'].tail(50).mean()
            if avg_volume > 0:
                results['C8'] = latest['Volume'] > avg_volume
            else:
                results['C8'] = False
            
            # Validasi harga wajar
            if latest['Close'] <= 0:
                return {}
                
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
        
        print(f"\n{'='*60}")
        print(f"📊 MINERVINI SCREENER - SAHAM SYARIAH")
        print(f"{'='*60}")
        print(f"Total saham: {self.total_saham}")
        print(f"Mulai: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}\n")
        
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
            print(f"[{i}/{self.total_saham}] ({progress:.1f}%) {ticker}")
            if remaining > 0:
                print(f"   ⏱️  Estimasi sisa: {int(remaining//60)}m {int(remaining%60)}s")
            
            # Ambil data
            df = self.get_stock_data(ticker)
            
            if df is not None:
                success_count += 1
                criteria_results = self.check_criteria(df)
                
                if criteria_results:
                    total_met = sum(criteria_results.values())
                    
                    # Hanya simpan yang 7/8 atau 8/8
                    if total_met >= 7:
                        latest_price = df.iloc[-1]['Close']
                        
                        # Format harga
                        if latest_price >= 1000:
                            price_str = f"Rp {latest_price/1000:.1f}K"
                        else:
                            price_str = f"Rp {latest_price:,.0f}"
                        
                        # Ambil kode bersih (tanpa komentar)
                        clean_ticker = ticker.split('#')[0].strip()
                        
                        result = {
                            'Ticker': clean_ticker,
                            'Skor': f"{total_met}/8",
                            'Status': '8/8' if total_met == 8 else '7/8',
                            'Harga': price_str,
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
                        print(f"  ✅ LOLOS! ({total_met}/8) - {price_str}")
                    else:
                        print(f"  ❌ Tidak lolos ({total_met}/8)")
                else:
                    print(f"  ❌ Gagal kriteria")
            else:
                print(f"  ❌ Gagal data")
            
            # Jeda antar request
            time.sleep(2)
        
        # Konversi ke DataFrame
        if results:
            df_results = pd.DataFrame(results)
            df_results = df_results.sort_values('Status', ascending=False)
            self.saham_lolos = len(df_results)
        else:
            df_results = pd.DataFrame()
            self.saham_lolos = 0
        
        # Tampilkan ringkasan
        total_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("📊 RINGKASAN FINAL")
        print("=" * 60)
        print(f"Total saham      : {self.total_saham}")
        print(f"Berhasil diambil : {success_count}")
        print(f"Error/Delisted   : {len(self.saham_error)}")
        print(f"Lolos screening  : {self.saham_lolos}")
        print(f"Waktu total      : {int(total_time//60)}m {int(total_time%60)}s")
        
        return df_results
