# ============================================
# GEMINI SENIOR HEDGE FUND ANALYST
# Versi Lengkap dengan Analisis Independen
# ============================================

import os
import google.generativeai as genai
from typing import Dict, Any, List
import time

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
        Analisis saham berdasarkan data screener
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

DATA SAHAM (dari screener):
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
        """
        Ringkasan cepat untuk saham breakout
        """
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
    
    # ========== METHOD BARU: ANALISIS INDEPENDEN ==========
    
    def analyze_stock_independent(self, ticker: str) -> str:
        """
        Menganalisis saham secara independen tanpa data screener.
        Gemini akan menerapkan 8 kriteria Minervini versinya sendiri.
        """
        if not self.available:
            return ""
        
        prompt = f"""Anda adalah Senior Hedge Fund Analyst yang menguasai metode Mark Minervini.
Analisis saham **{ticker}** secara mendalam dengan framework Anda sendiri:

🔍 **TUGAS ANALISIS:**

1. **Evaluasi 8 Kriteria Minervini versi Anda** (berdasarkan pemahaman Anda tentang metode Minervini):
   - C1: Harga di atas MA penting (MA50, MA150, MA200)
   - C2: Alignment moving average (MA50 > MA150 > MA200)
   - C3: Tren jangka panjang (MA200 menanjak)
   - C4: Relative Strength vs pasar
   - C5: Volume dan momentum (volume > rata-rata)
   - C6: Jarak dari 52-week low (>30%)
   - C7: Jarak dari 52-week high (<25%)
   - C8: Faktor fundamental/katalis

   Berikan penilaian untuk setiap kriteria (✓ = terpenuhi, ✗ = tidak terpenuhi)

2. **Gambaran Teknikal**:
   - Trend saat ini (uptrend/downtrend/sideways)
   - Support & resistance kunci (level spesifik)
   - Volume dan momentum (meningkat/menurun)
   - Pola chart yang terlihat (Head & Shoulders, Triangle, Wedge, dll)

3. **Gambaran Fundamental** (berdasarkan pengetahuan umum):
   - Sektor industri
   - Katalis potensial (berita, kinerja, dll)
   - Risiko fundamental

4. **Rekomendasi Trading Plan versi Anda**:
   - Entry point (harga spesifik atau kondisi)
   - Stop loss (level)
   - Target 1 (profit taking pertama)
   - Target 2 (trailing stop)
   - Risk/Reward ratio (estimasi)
   - Timeframe yang sesuai (harian/mingguan)

5. **Kesimpulan**: ENTRY / WAIT / AVOID beserta alasan kuat.

Gunakan format output yang profesional, padat, dan informatif. Tampilkan 8 kriteria Minervini dalam format checklist yang jelas.
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error analisis {ticker}: {str(e)}"
    
    def analyze_multiple_independent(self, tickers: List[str]) -> str:
        """
        Menganalisis beberapa saham sekaligus secara independen dan membandingkannya.
        tickers: list of strings (kode saham)
        """
        if not self.available or not tickers:
            return ""
        
        ticker_list = "\n".join([f"- {t}" for t in tickers])
        
        prompt = f"""Anda adalah Senior Hedge Fund Analyst. Bandingkan dan analisis saham-saham berikut secara mendalam:

{chr(10).join([f'{i+1}. {t}' for i, t in enumerate(tickers)])}

Untuk SETIAP saham, berikan analisis singkat yang mencakup:

1. **Evaluasi 8 Kriteria Minervini** (versi Anda) - berapa dari 8 yang terpenuhi
2. **Gambaran Teknikal** singkat (1 kalimat)
3. **Gambaran Fundamental** singkat (1 kalimat)
4. **Rekomendasi**: ENTRY/WAIT/AVOID
5. **Target harga** (estimasi)

Setelah menganalisis semua saham, berikan:
- **Urutan prioritas** dari yang paling prospektif (1 = terbaik)
- **Saran alokasi** (saham mana yang paling siap di-entry hari ini)

Gunakan format output seperti contoh berikut:

🔥 **PERBANDINGAN & PRIORITAS**

1. **ALKA** – ENTRY – [alasan singkat]
   - Kriteria Minervini: 7/8
   - Teknikal: Breakout ascending triangle
   - Fundamental: Sektor consumer goods
   - Target: Rp 1.308

2. **AGII** – WAIT – [alasan singkat]
   - Kriteria Minervini: 5/8
   - Teknikal: Konsolidasi
   - Fundamental: Valuasi tinggi
   - Target: Rp 2.500

...

📊 **RINGKASAN**
[Saham paling prioritas dan strategi trading]

Format profesional, padat, mudah dibaca.
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error analisis komparatif: {str(e)}"
