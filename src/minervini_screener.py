import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime

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
        
    def get_stock_data(self, ticker, period='6mo'):
        """Mengambil data saham dengan retry mechanism"""
        max_retries = 2
        
        # PASTIKAN TICKER SUDAH PUNYA .JK
        if not ticker.endswith('.JK'):
            ticker = f"{ticker}.JK"
        
        for attempt in range(max_retries):
            try:
                # Ambil data
                stock = yf.Ticker(ticker)
                df = stock.history(period=period)
                
                # Cek apakah data kosong
                if df.empty:
                    print(f"  ⚠ {ticker}: Data kosong (mungkin delisted)")
                    self.saham_error.append(ticker)
                    return None
                
                # Cek apakah data cukup
                if len(df) < 200:
                    print(f"  ⚠ {ticker}: Data tidak cukup ({len(df)} hari, butuh 200 hari)")
                    return None
                    
                return df
                
            except Exception as e:
                if "No data found" in str(e):
                    print(f"  ⚠ {ticker}: Tidak ditemukan di Yahoo Finance (mungkin delisted)")
                    self.saham_error.append(ticker)
                    return None
                elif attempt < max_retries - 1:
                    print(f"  ⚠ {ticker}: Retry {attempt + 1}...")
                    time.sleep(2)
                else:
                    print(f"  ⚠ {ticker}: Error: {str(e)[:50]}")
                    self.saham_error.append(ticker)
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
        
        results = {}
        
        try:
            # C1: Harga > MA150 dan MA200
            results['C1'] = latest['Close'] > latest['MA150'] and latest['Close'] > latest['MA200']
            
            # C2: MA150 > MA200
            results['C2'] = latest['MA150'] > latest['MA200']
            
            # C3: MA50 > MA150 dan MA200
            results['C3'] = latest['MA50'] > latest['MA150'] and latest['MA50'] > latest['MA200']
            
            # C4: Harga > MA50
            results['C4'] = latest['Close'] > latest['MA50']
            
            # C5: Harga > MA20
            results['C5'] = latest['Close'] > latest['MA20']
            
            # C6: MA20 > MA50
            results['C6'] = latest['MA20'] > latest['MA50']
            
            # C7: Trend naik (harga sekarang > 25% dari 50 hari lalu)
            if prev_50 is not None:
                pct_change = (latest['Close'] / prev_50['Close'] - 1) * 100
                results['C7'] = pct_change > 25
            else:
                results['C7'] = False
            
            # C8: Volume > rata-rata 50 hari
            avg_volume_50 = df['Volume'].tail(50).mean()
            results['C8'] = latest['Volume'] > avg_volume_50
            
        except Exception as e:
            return {}
        
        return results
    
    def screen_stocks(self, tickers):
        """Melakukan screening untuk daftar saham"""
        results = []
        self.total_saham = len(tickers)
        self.saham_error = []
        
        print(f"\n📊 Memeriksa {self.total_saham} saham...")
        print("-" * 60)
        
        for i, ticker in enumerate(tickers, 1):
            # Progress bar
            progress = (i / self.total_saham) * 100
            print(f"[{i}/{self.total_saham}] ({progress:.1f}%) {ticker}...")
            
            # Ambil data
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
                        
                        # Buat entry hasil
                        result = {
                            'Ticker': ticker.replace('.JK', ''),
                            'Kriteria': f"{total_met}/8",
                            'Status': '8/8' if total_met == 8 else '7/8',
                            'Harga': f"Rp {latest_price:,.0f}",
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
                        print(f"  ✅ Lolos! ({total_met}/8)")
            
            # Jeda biar tidak kena rate limit
            time.sleep(1)
        
        # Konversi ke DataFrame
        if results:
            df_results = pd.DataFrame(results)
            # Urutkan berdasarkan yang 8/8 dulu
            df_results = df_results.sort_values(['Status', 'Ticker'], ascending=[False, True])
            self.saham_lolos = len(df_results)
        else:
            df_results = pd.DataFrame()
            self.saham_lolos = 0
        
        # Tampilkan ringkasan
        print("\n" + "=" * 60)
        print("RINGKASAN SCREENING")
        print("=" * 60)
        print(f"Total saham di-screening : {self.total_saham}")
        print(f"Saham yang error/delisted : {len(self.saham_error)}")
        print(f"Saham lolos screening     : {self.saham_lolos}")
        
        if self.saham_error:
            print(f"\n⚠ Saham bermasalah (error/delisted):")
            for ticker in self.saham_error[:10]:  # Tampilkan max 10
                print(f"   - {ticker}")
            if len(self.saham_error) > 10:
                print(f"   ... dan {len(self.saham_error) - 10} lainnya")
        
        return df_results
