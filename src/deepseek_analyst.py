# ============================================
# DEEPSEEK SENIOR HEDGE FUND ANALYST
# ============================================
# File baru - Tambahkan ini di folder src/

import os
import json
import time
from typing import Dict, Any, List, Optional
import requests

class DeepSeekAnalyst:
    """
    Senior Hedge Fund Analyst powered by DeepSeek
    Memberikan analisis profesional untuk saham-saham hasil screening
    """
    
    def __init__(self):
        self.api_key = os.environ.get('DEEPSEEK_API_KEY')
        if not self.api_key:
            print("⚠️ DEEPSEEK_API_KEY tidak ditemukan - analisis tidak akan dijalankan")
            self.available = False
        else:
            self.available = True
            self.api_url = "https://api.deepseek.com/v1/chat/completions"
            self.model = "deepseek-chat"
            print("✅ DeepSeek Analyst siap digunakan")
    
    def analyze_stock(self, stock_data: Dict[str, Any], detailed: bool = True) -> str:
        """
        Menganalisis saham sebagai Senior Hedge Fund Analyst
        
        Args:
            stock_data: Dictionary berisi data saham (Ticker, Harga, RS, VCP, Patterns, dll)
            detailed: True untuk analisis lengkap, False untuk rekomendasi singkat
            
        Returns:
            String berisi analisis
        """
        if not self.available:
            return ""
        
        # Format data saham
        ticker = stock_data.get('Ticker', 'N/A')
        harga = stock_data.get('Harga', 'N/A')
        status = stock_data.get('Status', 'N/A')
        rs = stock_data.get('RS', 'N/A')
        vcp = stock_data.get('VCP', 'N/A')
        patterns = stock_data.get('Patterns', 'Tidak ada pola')
        rr = stock_data.get('RR_Ratio', 'N/A')
        low = stock_data.get('Low', 'N/A')
        high = stock_data.get('High', 'N/A')
        
        # Cek apakah ini saham breakout
        is_breakout = 'BREAKOUT' in str(patterns).upper()
        priority = "🔥 PRIORITAS TINGGI" if is_breakout else "📊 PERLU DIPANTAU"
        
        if detailed:
            # Prompt untuk analisis lengkap
            prompt = f"""Bertindaklah sebagai **Senior Hedge Fund Analyst** dengan pengalaman 20+ tahun di Wall Street.
Berikan analisis mendalam untuk saham berikut:

📊 **DATA SAHAM:**
- Ticker: {ticker}
- Harga Saat Ini: {harga}
- Status: {status} (8/8 Minervini)
- RS Rating: {rs} (0-99, >70 = outperform)
- VCP Score: {vcp} (0-100, >70 = kontraksi kuat)
- Jarak dari Low: {low}
- Jarak dari High: {high}
- Chart Patterns: {patterns}
- Risk/Reward: {rr} (ideal >3)

📈 **ANALISIS YANG DIINGINKAN:**
1. **Teknikal Outlook** (3-4 kalimat): Analisis chart patterns, support/resistance, dan breakout validity
2. **Fundamental Snapshot** (2-3 kalimat): Berdasarkan data publik, apa katalis potensial?
3. **Rekomendasi Entry Strategy** (2-3 kalimat): Scaling in plan dengan level spesifik
4. **Risk Management** (2-3 kalimat): Stop loss, target harga, dan trailing stop
5. **Market Context** (2-3 kalimat): Bagaimana posisi saham ini relatif terhadap sektor?
6. **Kesimpulan** (1 kalimat): ENTRY / WAIT / AVOID

Gunakan format profesional dengan data konkret, tanpa disclaimer berlebihan.
Total maksimal 250 kata."""
        else:
            # Prompt untuk rekomendasi singkat (1 kalimat)
            prompt = f"""Sebagai Senior Hedge Fund Analyst, beri rekomendasi 1 kalimat untuk saham {ticker}:
- Harga: {harga}
- RS: {rs}
- Patterns: {patterns}
- Status: {priority}

Format: "[Ticker]: [ENTRY/WAIT/AVOID] - [alasan singkat]"
"""
        
        try:
            # Panggil DeepSeek API dengan retry mechanism
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are a Senior Hedge Fund Analyst with 20+ years experience. Provide concise, professional analysis."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 600 if detailed else 100
                    }
                    
                    response = requests.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        analysis = result["choices"][0]["message"]["content"].strip()
                        return analysis
                    elif response.status_code == 429 and attempt < max_retries - 1:
                        # Rate limited, tunggu dan coba lagi
                        wait_time = 2 ** attempt
                        time.sleep(wait_time)
                    else:
                        return f"[Analisis tidak tersedia: Error {response.status_code}]"
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                    else:
                        return f"[Error analisis: {str(e)[:50]}]"
            
            return "[Analisis gagal setelah beberapa percobaan]"
            
        except Exception as e:
            return f"[Error: {str(e)[:50]}]"
    
    def analyze_breakout_stocks(self, stocks_df) -> str:
        """
        Menganalisis semua saham breakout sekaligus untuk ringkasan prioritas
        
        Args:
            stocks_df: DataFrame dengan semua saham 8/8
            
        Returns:
            String berisi ringkasan prioritas
        """
        if not self.available or stocks_df.empty:
            return ""
        
        # Filter saham dengan breakout
        breakout_stocks = []
        other_stocks = []
        
        for _, row in stocks_df.iterrows():
            patterns = str(row.get('Patterns', ''))
            if 'BREAKOUT' in patterns.upper():
                breakout_stocks.append(row)
            else:
                other_stocks.append(row)
        
        if not breakout_stocks:
            return ""
        
        # Buat ringkasan breakout
        summary = "🔥 **PRIORITAS TRADING - SAHAM BREAKOUT**\n\n"
        summary += "| Ticker | Harga | RS | Rekomendasi |\n"
        summary += "|--------|-------|----|-------------|\n"
        
        for stock in breakout_stocks[:5]:  # Maksimal 5 saham
            ticker = stock.get('Ticker', 'N/A')
            harga = stock.get('Harga', 'N/A')
            rs = stock.get('RS', 'N/A')
            
            # Dapatkan rekomendasi singkat
            rec = self.analyze_stock(stock.to_dict(), detailed=False)
            summary += f"| {ticker} | {harga} | {rs} | {rec} |\n"
        
        return summary
    
    def get_market_outlook(self) -> str:
        """
        Mendapatkan outlook pasar secara umum
        """
        if not self.available:
            return ""
        
        prompt = """Sebagai Senior Hedge Fund Analyst, berikan outlook pasar IHSG untuk hari ini:
- Kondisi global (AS, China, komoditas)
- Sektor yang sedang kuat
- Sektor yang harus dihindari
- Sentimen investor (risk on/risk off)

Maksimal 100 kata, format profesional."""
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a Senior Hedge Fund Analyst."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 300
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=20)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                return ""
                
        except:
            return ""
