# ============================================
# MAIN.PY - MINERVINI SCREENER v6.0
# Dengan Deteksi Pola Chart & Timezone WIB
# ============================================

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from src.minervini_screener import MinerviniScreenerPro
from src.email_sender import send_email_report
from src.sheets_sender import send_to_google_sheets

def get_wib_time():
    """
    Mendapatkan waktu WIB (UTC+7) yang akurat
    """
    utc_now = datetime.now(timezone.utc)
    wib_now = utc_now + timedelta(hours=7)
    return wib_now

def load_tickers_from_file(filename="config/stocks_list.txt"):
    """
    Membaca daftar saham dari file
    """
    tickers = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
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

def validate_email_config(email_from, email_password, email_to):
    """
    Validasi konfigurasi email
    """
    if not email_from or not email_password:
        return False, "Email tidak dikonfigurasi (EMAIL_FROM atau EMAIL_PASSWORD kosong)"
    if not email_to:
        return False, "Email tujuan tidak dikonfigurasi (EMAIL_TO kosong)"
    return True, "OK"

def main():
    """
    Fungsi utama screening
    """
    # ===== HEADER DENGAN WIB =====
    wib_time = get_wib_time()
    print("=" * 80)
    print("📈 MINERVINI STOCK SCREENER v6.0")
    print(f"🕐 Waktu Screening: {wib_time.strftime('%Y-%m-%d %H:%M:%S')} WIB")
    print("=" * 80)
    
    # ===== CEK ENVIRONMENT VARIABLES =====
    print("\n📧 Konfigurasi Email:")
    email_from = os.environ.get('EMAIL_FROM', '')
    email_password = os.environ.get('EMAIL_PASSWORD', '')
    email_to = os.environ.get('EMAIL_TO', 'edissty@gmail.com')
    
    print(f"   Dari : {'✓' if email_from else '✗'} {email_from}")
    print(f"   Ke   : {'✓' if email_to else '✗'} {email_to}")
    print(f"   Pass : {'✓' if email_password else '✗'} ({len(email_password)} chars)")
    
    is_email_valid, email_msg = validate_email_config(email_from, email_password, email_to)
    if not is_email_valid:
        print(f"   ⚠️ {email_msg}")
    
    # ===== CEK GOOGLE SHEETS =====
    google_sheets_url = os.environ.get('GOOGLE_SHEETS_WEBHOOK', '')
    print(f"\n📊 Google Sheets: {'✓' if google_sheets_url else '✗'}")
    
    # ===== BACA DAFTAR SAHAM =====
    stocks = load_tickers_from_file()
    if not stocks:
        print("❌ Tidak ada saham untuk di-screening!")
        sys.exit(1)
    
    # ===== JALANKAN SCREENING =====
    print("\n" + "=" * 80)
    print("🔍 MEMULAI SCREENING DENGAN MULTITHREADING...")
    print("=" * 80)
    
    # Inisialisasi screener dengan optimasi
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    recommended_workers = min(15, cpu_count * 2)  # Turunkan sedikit untuk stabilitas
    
    screener = MinerviniScreenerPro(
        min_turnover=300_000_000,  # Turunkan threshold likuiditas
        max_workers=recommended_workers,
        log_level=logging.INFO
    )
    
    # Jalankan screening
    print(f"🚀 Thread workers: {recommended_workers}")
    print(f"📊 Total saham: {len(stocks)}")
    print()
    
    results_df = screener.screen(stocks)
    
    # ===== PROSES HASIL =====
    if results_df is not None and not results_df.empty:
        print("\n" + "=" * 80)
        print("✅ SCREENING SELESAI!")
        print(f"📊 Saham lolos: {len(results_df)}")
        
        # Hitung statistik
        count_8 = len(results_df[results_df['Status'] == '8/8']) if 'Status' in results_df.columns else 0
        count_7 = len(results_df[results_df['Status'] == '7/8']) if 'Status' in results_df.columns else 0
        
        print(f"   - 8/8: {count_8}")
        print(f"   - 7/8: {count_7}")
        
        # Tampilkan hasil singkat dengan pola chart
        print("\n📋 DAFTAR SAHAM LOLOS:")
        display_cols = ['Ticker', 'Status', 'Harga', 'RS', 'VCP', 'Patterns']
        if all(col in results_df.columns for col in display_cols):
            # Batasi tampilan untuk konsol
            display_df = results_df[display_cols].head(10).copy()
            # Persingkat kolom Patterns untuk tampilan
            if 'Patterns' in display_df.columns:
                display_df['Patterns'] = display_df['Patterns'].str.slice(0, 30)
            print(display_df.to_string(index=False))
        else:
            print(results_df.head(10).to_string(index=False))
        
        # ===== SIMPAN KE CSV DENGAN TIMESTAMP WIB =====
        os.makedirs("results", exist_ok=True)
        timestamp = wib_time.strftime('%Y%m%d_%H%M%S')
        filename = f"results/screening_{timestamp}.csv"
        results_df.to_csv(filename, index=False)
        print(f"\n💾 Hasil disimpan ke: {filename}")
        
        # ===== KIRIM KE GOOGLE SHEETS =====
        if google_sheets_url:
            print("\n📊 Mengirim ke Google Sheets...")
            try:
                send_to_google_sheets(results_df, google_sheets_url)
                print("   ✅ Google Sheets berhasil")
            except Exception as e:
                print(f"   ❌ Gagal: {e}")
        
        # ===== KIRIM EMAIL =====
        if email_from and email_password and email_to:
            print("\n📧 Mengirim email...")
            try:
                send_email_report(
                    results_df, 
                    email_to, 
                    email_from, 
                    email_password,
                    screener.criteria_desc
                )
                print("   ✅ Email berhasil")
            except Exception as e:
                print(f"   ❌ Gagal: {e}")
        else:
            print("\n⚠️ Email tidak dikirim (konfigurasi tidak lengkap)")
            
    else:
        print("\n📭 TIDAK ADA SAHAM LOLOS SCREENING")
        
        # Tetap kirim notifikasi email
        if email_from and email_password and email_to:
            print("\n📧 Mengirim notifikasi...")
            try:
                send_email_report(
                    None, 
                    email_to, 
                    email_from, 
                    email_password,
                    screener.criteria_desc
                )
                print("   ✅ Notifikasi email terkirim")
            except Exception as e:
                print(f"   ❌ Gagal: {e}")
    
    # ===== FOOTER =====
    wib_end = get_wib_time()
    duration = (wib_end - wib_time).total_seconds()
    
    print("\n" + "=" * 80)
    print("🎯 SCREENING SELESAI")
    print(f"🕐 Waktu selesai: {wib_end.strftime('%Y-%m-%d %H:%M:%S')} WIB")
    print(f"⏱️  Durasi: {int(duration//60)} menit {int(duration%60)} detik")
    print("=" * 80)

if __name__ == "__main__":
    main()
