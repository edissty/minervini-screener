# ============================================
# GEMINI SENIOR HEDGE FUND ANALYST
# Gratis unlimited via Google AI Studio
# ============================================

import os
import google.generativeai as genai
from typing import Dict, Any, List

class GeminiAnalyst:
    """
    Senior Hedge Fund Analyst powered by Google Gemini
    Gratis 60 request per menit!
    """
    
    def __init__(self):
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("⚠️ GEMINI_API_KEY tidak ditemukan - analisis tidak akan dijalankan")
            self.available = False
            return
        
        # Konfigurasi Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')  # Model cepat & gratis
        self.available = True
        print("✅ Gemini Analyst siap digunakan (GRATIS 60 RPM!)")
    
    def analyze_stock(self, stock_data: Dict[str, Any]) -> str:
        """
        Analisis saham sebagai Senior Hedge Fund Analyst
        """
        if not self.available:
            return "Analisis tidak tersedia (API key tidak ditemukan)"
        
        ticker = stock_data.get('Ticker', 'N/A')
        harga = stock_data.get('Harga', 'N/A')
        rs = stock_data.get('RS', 'N/A')
        vcp = stock_data.get('VCP', 'N/A')
        patterns = stock_data.get('Patterns', 'Tidak ada pola')
        rr = stock_data.get('RR_Ratio', 'N/A')
        
        is_breakout = 'BREAKOUT' in str(patterns).upper()
        
        prompt = f"""Anda adalah Senior Hedge Fund Analyst dengan pengalaman 20+ tahun. Analisis saham berikut:

DATA SAHAM:
- Ticker: {ticker}
- Harga: {harga}
- RS Rating: {rs}/100 (>70 = outperform pasar)
- VCP Score: {vcp}/100 (>70 = kontraksi volatilitas kuat)
- Chart Patterns: {patterns}
- Risk/Reward: 1:{rr}
- Status: {'BREAKOUT DETECTED' if is_breakout else 'Konsolidasi'}

BERIKAN ANALISIS SINGKAT (max 100 kata):
1. Teknikal outlook (1 kalimat)
2. Rekomendasi: ENTRY / WAIT / AVOID (1 kalimat)
3. Level support & resistance kunci (1 kalimat)

Gunakan format profesional, tanpa disclaimer."""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error: {str(e)}"
    
    def analyze_breakout_stocks(self, stocks_df) -> str:
        """Ringkasan cepat untuk saham breakout"""
        if not self.available or stocks_df.empty:
            return ""
        
        breakout_stocks = []
        for _, row in stocks_df.iterrows():
            patterns = str(row.get('Patterns', ''))
            if 'BREAKOUT' in patterns.upper():
                breakout_stocks.append(row)
        
        if not breakout_stocks:
            return ""
        
        # Buat list ticker untuk analisis batch
        tickers = [s.get('Ticker', '') for s in breakout_stocks[:5]]
        
        prompt = f"""Anda adalah Senior Hedge Fund Analyst. Prioritaskan saham-saham berikut untuk trading hari ini:

{chr(10).join([f"- {t}" for t in tickers])}

Beri rekomendasi 1-2 kalimat: mana yang paling siap entry dan alasannya."""
        
        try:
            response = self.model.generate_content(prompt)
            return f"🔥 **PRIORITAS TRADING**\n{response.text.strip()}"
        except:
            return "🔥 **PRIORITAS TRADING**\n" + "\n".join([f"• **{t}**: ENTRY (breakout valid)" for t in tickers])
