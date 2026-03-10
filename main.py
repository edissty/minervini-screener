import os
import sys
import logging
from datetime import datetime
from src.minervini_screener import MinerviniScreenerPro  # ← NAMA INI HARUS SAMA
from src.email_sender import send_email_report
from src.sheets_sender import send_to_google_sheets

def load_tickers_from_file(filename="config/stocks_list.txt"):
    """Membaca daftar saham dari file"""
    tickers = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '#' in line:
                        ticker = line.split('#')[0].strip()
                    else:
                        ticker = line.strip()
                    if ticker:
                        tickers.append(ticker)
        print(f"📋 Loaded {len(tickers)} tickers from {filename}")
        return tickers
    except FileNotFoundError:
        print(f"❌ ERROR: File {filename} tidak ditemukan!")
        return []

def main():
    print("=" * 80)
    print("MINERVINI STOCK SCREENER v5.3")
    print(f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # CEK ENVIRONMENT VARIABLES
    email_from = os.environ.get('EMAIL_FROM', '')
    email_password = os.environ.get('EMAIL_PASSWORD', '')
    email_to = os.environ.get('EMAIL_TO', 'edissty@gmail.com')
    google_sheets_url = os.environ.get('GOOGLE_SHEETS_WEBHOOK', '')
    
    # BACA DAFTAR SAHAM
    stocks = load_tickers_from_file()
    if not stocks:
        print("❌ Tidak ada saham untuk di-screening!")
        sys.exit(1)
    
    # JALANKAN SCREENING
    print(f"\n📊 Total saham: {len(stocks)}")
    print("=" * 80)
    
    # Inisialisasi screener
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    recommended_workers = min(20, cpu_count * 2)
    
    screener = MinerviniScreenerPro(
        min_turnover=500_000_000,
        max_workers=recommended_workers,
        log_level=logging.INFO
    )
    
    # Jalankan screening
    results_df = screener.screen(stocks)
    
    # PROSES HASIL
    if results_df is not None and not results_df.empty:
        print(f"\n✅ SCREENING SELESAI! {len(results_df)} saham lolos")
        
        # SIMPAN KE CSV
        os.makedirs("results", exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"results/screening_{timestamp}.csv"
        results_df.to_csv(filename, index=False)
        print(f"💾 Hasil disimpan ke: {filename}")
        
        # KIRIM KE GOOGLE SHEETS
        if google_sheets_url:
            print("\n📊 Mengirim ke Google Sheets...")
            send_to_google_sheets(results_df, google_sheets_url)
        
        # KIRIM EMAIL
        if email_from and email_password:
            print("\n📧 Mengirim email...")
            send_email_report(
                results_df, 
                email_to, 
                email_from, 
                email_password,
                screener.criteria_desc
            )
    else:
        print("\n📭 TIDAK ADA SAHAM LOLOS SCREENING")
        
        if email_from and email_password:
            send_email_report(
                None, 
                email_to, 
                email_from, 
                email_password,
                screener.criteria_desc
            )
    
    print("\n" + "=" * 80)
    print("SCREENING SELESAI")
    print("=" * 80)

if __name__ == "__main__":
    main()
