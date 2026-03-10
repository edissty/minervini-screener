import os
import sys
from datetime import datetime
from src.minervini_screener import MinerviniScreenerPro  # UBAH INI!
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
    print("MINERVINI STOCK SCREENER - MULTITHREADING v5.0")
    print(f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # CEK ENVIRONMENT VARIABLES
    print("\n📧 Konfigurasi Email:")
    email_from = os.environ.get('EMAIL_FROM', '')
    email_password = os.environ.get('EMAIL_PASSWORD', '')
    email_to = os.environ.get('EMAIL_TO', 'edissty@gmail.com')
    
    print(f"   Dari : {'✓' if email_from else '✗'} {email_from}")
    print(f"   Ke   : {'✓' if email_to else '✗'} {email_to}")
    print(f"   Pass : {'✓' if email_password else '✗'} ({len(email_password)} chars)")
    
    # CEK GOOGLE SHEETS WEBHOOK
    google_sheets_url = os.environ.get('GOOGLE_SHEETS_WEBHOOK', '')
    print(f"\n📊 Google Sheets: {'✓' if google_sheets_url else '✗'}")
    
    # BACA DAFTAR SAHAM
    stocks = load_tickers_from_file()
    if not stocks:
        print("❌ Tidak ada saham untuk di-screening!")
        sys.exit(1)
    
    # JALANKAN SCREENING
    print("\n" + "=" * 80)
    print("🔍 MEMULAI SCREENING DENGAN MULTITHREADING...")
    print("=" * 80)
    
    # Inisialisasi screener dengan class baru
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    recommended_workers = min(20, cpu_count * 2)
    
    screener = MinerviniScreenerPro(
        min_turnover=500_000_000,  # Minimal Rp 500 juta/hari
        max_workers=recommended_workers
    )
    
    # Jalankan screening
    results_df = screener.screen(stocks)
    
    # PROSES HASIL
    if results_df is not None and not results_df.empty:
        print("\n" + "=" * 80)
        print("✅ SCREENING SELESAI!")
        print(f"📊 Saham lolos: {len(results_df)}")
        
        # Hitung statistik
        count_8 = len(results_df[results_df['Status'] == '8/8']) if 'Status' in results_df.columns else 0
        count_7 = len(results_df[results_df['Status'] == '7/8']) if 'Status' in results_df.columns else 0
        
        print(f"   - 8/8: {count_8}")
        print(f"   - 7/8: {count_7}")
        
        # Tampilkan hasil singkat
        print("\n📋 DAFTAR SAHAM LOLOS:")
        display_cols = ['Ticker', 'Status', 'Harga', 'RS_Ratio', 'VCP']
        if all(col in results_df.columns for col in display_cols):
            print(results_df[display_cols].head(10).to_string(index=False))
        else:
            print(results_df.head(10).to_string(index=False))
        
        # SIMPAN KE CSV
        os.makedirs("results", exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"results/screening_{timestamp}.csv"
        results_df.to_csv(filename, index=False)
        print(f"\n💾 Hasil disimpan ke: {filename}")
        
        # KIRIM KE GOOGLE SHEETS
        if google_sheets_url:
            print("\n📊 Mengirim ke Google Sheets...")
            from src.sheets_sender import send_to_google_sheets
            send_to_google_sheets(results_df, google_sheets_url)
        
        # KIRIM EMAIL
        if email_from and email_password:
            print("\n📧 Mengirim email...")
            send_email_report(
                results_df, 
                email_to, 
                email_from, 
                email_password,
                screener.criteria_desc  # Gunakan criteria_desc, bukan criteria
            )
    else:
        print("\n📭 TIDAK ADA SAHAM LOLOS SCREENING")
        
        # Tetap kirim notifikasi email
        if email_from and email_password:
            print("\n📧 Mengirim notifikasi...")
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
