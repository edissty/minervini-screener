import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime
import requests

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
        Mengambil data saham dengan User-Agent header dan multiple format attempts
        """
        max_retries = 2
        
        # Simpan ticker asli untuk logging
        original_ticker = ticker
        
        # Format yang akan dicoba (urutan prioritas)
        ticker_formats = []
        
        if ticker.endswith('.JK'):
            # Jika sudah pakai .JK, coba 3 format
            base = ticker.replace('.JK', '')
            ticker_formats = [
                ticker,                    # ADRO.JK
                f"JK:{base}",               # JK:ADRO
                base,                       # ADRO (tanpa .JK)
                f"{base}.JK",               # ADRO.JK (ulang)
                f"{base}.JAKARTA"           # ADRO.JAKARTA (kadang bekerja)
            ]
        else:
            # Jika belum pakai .JK
            ticker_formats = [
                f"{ticker}.JK",              # ADRO.JK
                f"JK:{ticker}",               # JK:ADRO
                ticker,                        # ADRO
                f"{ticker}.JAKARTA"            # ADRO.JAKARTA
            ]
        
        # Hapus duplikat
        ticker_formats = list(dict.fromkeys(ticker_formats))
        
        print(f"  Debug: Mencoba {len(ticker_formats)} format untuk {original_ticker}...")
        
        for attempt in range(max_retries):
            for ticker_format in ticker_formats:
                try:
                    # Buat session dengan User-Agent seperti browser
                    session = requests.Session()
                    session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    })
                    
                    # Tambahkan cookie consent
                    session.cookies.set('consent', 'yes', domain='.yahoo.com')
                    
                    # Panggil yfinance dengan session
                    stock = yf.Ticker(ticker_format, session=session)
                    
                    # Ambil data dengan timeout
                    df = stock.history(period=period, timeout=10)
                    
                    # Debug info
                    print(f"    Debug: Mencoba format '{ticker_format}'... ", end='')
                    
                    if df is not None and not df.empty:
                        print(f"✅ BERHASIL! ({len(df)} data points)")
                        self.saham_ok.append(original_ticker)
                        return df
                    else:
                        print(f"❌ Data kosong")
                        
                except Exception as e:
                    print(f"    Debug: Error '{ticker_format}': {str(e)[:50]}")
                    continue
            
            if attempt < max_retries - 1:
                print(f"  Debug: Percobaan ke-{attempt+1} gagal, menunggu 3 detik sebelum retry...")
                time.sleep(3)
        
        print(f"  ⚠ {original_ticker}: SEMUA FORMAT GAGAL - mungkin delisted atau masalah koneksi")
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
            return {}
        
        # Hitung MA
        df = self.calculate_ma(df, [20, 50, 150, 200])
        
        # Data terbaru
        latest = df.iloc[-1]
        
        # Data 50 hari lalu
        prev_50 = df.iloc[-50] if len(df) >= 50 else None
        
        # Data 20 hari lalu untuk validasi trend
        prev_20 = df.iloc[-20] if len(df) >= 20 else None
        
        results = {}
        
        try:
            # Cek apakah semua MA tersedia
            required_ma = ['MA20', 'MA50', 'MA150', 'MA200']
            if not all(ma in df.columns for ma in required_ma):
                return {}
            
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
            
            # C7: Trend naik (harga sekarang > 25% dari 50 hari lalu)
            if prev_50 is not None:
                pct_change_50 = (latest['Close'] / prev_50['Close'] - 1) * 100
                results['C7'] = pct_change_50 > 25
            else:
                results['C7'] = False
            
            # C8: Volume > rata-rata 50 hari
            avg_volume_50 = df['Volume'].tail(50).mean()
            if avg_volume_50 > 0:
                results['C8'] = latest['Volume'] > avg_volume_50
            else:
                results['C8'] = False
            
            # Validasi tambahan: pastikan harga wajar (tidak 0 atau negatif)
            if latest['Close'] <= 0:
                return {}
                
        except Exception as e:
            print(f"  Debug: Error memeriksa kriteria: {e}")
            return {}
        
        return results
    
    def screen_stocks(self, tickers):
        """Melakukan screening untuk daftar saham"""
        results = []
        self.total_saham = len(tickers)
        self.saham_error = []
        self.saham_ok = []
        
        print(f"\n{'='*60}")
        print(f"📊 MEMERIKSA {self.total_saham} SAHAM SYARIAH")
        print(f"{'='*60}")
        print(f"Waktu mulai: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        for i, ticker in enumerate(tickers, 1):
            # Progress bar
            elapsed = time.time() - start_time
            est_total = (elapsed / i) * self.total_saham if i > 0 else 0
            remaining = est_total - elapsed
            
            progress = (i / self.total_saham) * 100
            print(f"[{i}/{self.total_saham}] ({progress:.1f}%) {ticker}...")
            print(f"   ⏱️  Estimasi sisa: {int(remaining//60)}m {int(remaining%60)}s")
            
            # Ambil data dengan multiple format
            df = self.get_stock_data(ticker)
            
            # Cek kriteria
            if df is not None:
                criteria_results = self.check_criteria(df)
                
                if criteria_results:
                    total_met = sum(criteria_results.values())
                    
                    # Hanya simpan yang 7/8 atau 8/8
                    if total_met >= 7:
                        # Ambil harga terbaru
                        latest_price = df.iloc[-1]['Close']
                        
                        # Ambil volume
                        latest_volume = df.iloc[-1]['Volume']
                        
                        # Format harga
                        if latest_price >= 1000:
                            price_str = f"Rp {latest_price/1000:.1f}K"
                        else:
                            price_str = f"Rp {latest_price:,.0f}"
                        
                        # Buat entry hasil
                        result = {
                            'Ticker': ticker.replace('.JK', '').replace('JK:', ''),
                            'Kriteria': f"{total_met}/8",
                            'Status': '8/8' if total_met == 8 else '7/8',
                            'Harga': price_str,
                            'Volume': f"{latest_volume/1000000:.1f}M" if latest_volume >= 1000000 else f"{latest_volume/1000:.0f}K",
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
                        print(f"  ✅ LOLOS! ({total_met}/8) - Harga: {price_str}")
                    else:
                        print(f"  ❌ Tidak lolos ({total_met}/8)")
                else:
                    print(f"  ❌ Gagal memeriksa kriteria")
            else:
                print(f"  ❌ Gagal mengambil data")
            
            # Jeda antar request (hindari rate limiting)
            time.sleep(1.5)
            
            # Setiap 10 saham, jeda lebih panjang
            if i % 10 == 0 and i < self.total_saham:
                print(f"  💤 Istirahat 3 detik...")
                time.sleep(3)
        
        # Konversi ke DataFrame
        if results:
            df_results = pd.DataFrame(results)
            # Urutkan berdasarkan yang 8/8 dulu, lalu 7/8
            df_results = df_results.sort_values(
                ['Status', 'Ticker'], 
                ascending=[False, True]
            )
            self.saham_lolos = len(df_results)
        else:
            df_results = pd.DataFrame()
            self.saham_lolos = 0
        
        # Hitung waktu total
        total_time = time.time() - start_time
        
        # Tampilkan ringkasan
        print("\n" + "=" * 60)
        print("📊 RINGKASAN SCREENING")
        print("=" * 60)
        print(f"Total saham di-screening : {self.total_saham}")
        print(f"Saham berhasil diambil    : {len(self.saham_ok)}")
        print(f"Saham error/delisted      : {len(self.saham_error)}")
        print(f"Saham lolos screening     : {self.saham_lolos}")
        print(f"Waktu total               : {int(total_time//60)}m {int(total_time%60)}s")
        
        if self.saham_lolos > 0:
            print(f"\n✅ RINCIAN KELULUSAN:")
            count_8 = len(df_results[df_results['Status'] == '8/8'])
            count_7 = len(df_results[df_results['Status'] == '7/8'])
            print(f"   - Saham 8/8: {count_8}")
            print(f"   - Saham 7/8: {count_7}")
        
        if self.saham_error:
            print(f"\n⚠️  SAHAM BERMASALAH ({len(self.saham_error)}):")
            # Tampilkan 10 pertama
            for ticker in self.saham_error[:10]:
                print(f"   - {ticker}")
            if len(self.saham_error) > 10:
                print(f"   ... dan {len(self.saham_error) - 10} lainnya")
        
        # Simpan daftar error ke file
        if self.saham_error:
            error_file = f"results/error_stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            try:
                with open(error_file, 'w') as f:
                    f.write('\n'.join(self.saham_error))
                print(f"\n📄 Daftar saham error disimpan di: {error_file}")
            except:
                pass
        
        return df_results
    
    def get_summary(self):
        """Mendapatkan ringkasan hasil screening"""
        return {
            'total': self.total_saham,
            'ok': len(self.saham_ok),
            'error': len(self.saham_error),
            'lolos': self.saham_lolos,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
