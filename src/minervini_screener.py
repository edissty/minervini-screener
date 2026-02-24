import yfinance as yf
import pandas as pd
import numpy as np
import time

class MinerviniScreener:
    def __init__(self):
        self.criteria = {
            'c1': 'Harga > MA150 dan MA200',
            'c2': 'MA150 > MA200',
            'c3': 'MA50 > MA150 dan MA200',
            'c4': 'Harga > MA50',
            'c5': 'Harga > MA20',
            'c6': 'MA20 > MA50',
            'c7': 'Trend naik (harga 25% > harga 50 hari lalu)',
            'c8': 'Volume lebih besar dari rata-rata'
        }
        
    def get_stock_data(self, ticker, period='6mo'):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if not ticker.endswith('.JK'):
                    ticker_jk = f"{ticker}.JK"
                else:
                    ticker_jk = ticker
                
                stock = yf.Ticker(ticker_jk)
                df = stock.history(period=period)
                
                if df.empty:
                    return None
                    
                return df
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  Retry {attempt + 1} untuk {ticker}...")
                    time.sleep(2)
                else:
                    print(f"  Error mengambil data {ticker}: {e}")
                    return None
    
    def calculate_ma(self, df, periods):
        for period in periods:
            df[f'MA{period}'] = df['Close'].rolling(window=period).mean()
        return df
    
    def check_criteria(self, df):
        if df is None or len(df) < 200:
            return {}
        
        df = self.calculate_ma(df, [20, 50, 150, 200])
        latest = df.iloc[-1]
        prev_50 = df.iloc[-50] if len(df) >= 50 else None
        
        results = {}
        
        try:
            results['c1'] = latest['Close'] > latest['MA150'] and latest['Close'] > latest['MA200']
            results['c2'] = latest['MA150'] > latest['MA200']
            results['c3'] = latest['MA50'] > latest['MA150'] and latest['MA50'] > latest['MA200']
            results['c4'] = latest['Close'] > latest['MA50']
            results['c5'] = latest['Close'] > latest['MA20']
            results['c6'] = latest['MA20'] > latest['MA50']
            
            if prev_50 is not None:
                results['c7'] = (latest['Close'] / prev_50['Close'] - 1) > 0.25
            else:
                results['c7'] = False
            
            avg_volume_50 = df['Volume'].tail(50).mean()
            results['c8'] = latest['Volume'] > avg_volume_50
            
        except Exception as e:
            print(f"  Error memeriksa kriteria: {e}")
            return {}
        
        return results
    
    def screen_stocks(self, tickers):
        results = []
        
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] Memeriksa {ticker}...")
            
            df = self.get_stock_data(ticker)
            criteria_results = self.check_criteria(df)
            
            if criteria_results:
                total_met = sum(criteria_results.values())
                if total_met >= 7:
                    if df is not None:
                        latest_price = df.iloc[-1]['Close']
                    else:
                        latest_price = 0
                    
                    results.append({
                        'Ticker': ticker,
                        'Kriteria Terpenuhi': total_met,
                        'Status': '8/8' if total_met == 8 else '7/8',
                        'C1': '✓' if criteria_results.get('c1', False) else '✗',
                        'C2': '✓' if criteria_results.get('c2', False) else '✗',
                        'C3': '✓' if criteria_results.get('c3', False) else '✗',
                        'C4': '✓' if criteria_results.get('c4', False) else '✗',
                        'C5': '✓' if criteria_results.get('c5', False) else '✗',
                        'C6': '✓' if criteria_results.get('c6', False) else '✗',
                        'C7': '✓' if criteria_results.get('c7', False) else '✗',
                        'C8': '✓' if criteria_results.get('c8', False) else '✗',
                        'Harga': f"Rp {latest_price:,.0f}"
                    })
            
            time.sleep(1)
        
        return pd.DataFrame(results)
