import os
import sys
from datetime import datetime
from src.minervini_screener import MinerviniScreener
from src.email_sender import send_email_report

def main():
    print("=" * 70)
    print("MINERVINI STOCK SCREENER")
    print(f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # CEK ENVIRONMENT VARIABLES
    print("\n🔍 CEK KONFIGURASI EMAIL:")
    email_from = os.environ.get('EMAIL_FROM', '')
    email_password = os.environ.get('EMAIL_PASSWORD', '')
    email_to = os.environ.get('EMAIL_TO', 'edissty@gmail.com')
    
    if email_from:
        print(f"✓ EMAIL_FROM: {email_from}")
    else:
        print("✗ EMAIL_FROM: TIDAK ADA")
        
    if email_password:
        print(f"✓ EMAIL_PASSWORD: [TERISI {len(email_password)} karakter]")
    else:
        print("✗ EMAIL_PASSWORD: TIDAK ADA")
        
    if email_to:
        print(f"✓ EMAIL_TO: {email_to}")
    else:
        print("✗ EMAIL_TO: TIDAK ADA")
    
    # BACA DAFTAR SAHAM
    stocks_file = "config/stocks_list.txt"
    print(f"\n📁 Membaca daftar saham dari: {stocks_file}")
    
    try:
        with open(stocks_file, 'r') as f:
            stocks = []
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    stocks.append(line)
        
        print(f"✓ Total saham ditemukan: {len(stocks)}")
        if stocks:
            print(f"  Contoh: {', '.join(stocks[:5])}")
    except FileNotFoundError:
        print(f"✗ ERROR: File {stocks_file} tidak ditemukan!")
        sys.exit(1)
    
    # INISIALISASI SCREENER
    print("\n🔄 Menginisialisasi screener...")
    screener = MinerviniScreener()
    
    # JALANKAN SCREENING
    print("\n🔍 Memulai screening saham...")
    print("-" * 70)
    
    results_df = screener.screen_stocks(stocks)
    
    print("-" * 70)
    
    # PROSES HASIL
    if results_df is not None and not results_df.empty:
        print(f"\n✅ SCREENING SELESAI!")
        print(f"📊 Total saham memenuhi kriteria: {len(results_df)}")
        
        # Hitung statistik
        count_8 = len(results_df[results_df['Status'] == '8/8'])
        count_7 = len(results_df[results_df['Status'] == '7/8'])
        
        print(f"   - Saham 8/8: {count_8}")
        print(f"   - Saham 7/8: {count_7}")
        
        # Tampilkan hasil singkat
        if len(results_df) > 0:
            print("\n📋 DAFTAR SAHAM LOLOS:")
            for idx, row in results_df.iterrows():
                print(f"   {row['Ticker']}: {row['Status']} - {row['Harga']}")
        
        # SIMPAN KE CSV
        os.makedirs("results", exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"results/screening_{timestamp}.csv"
        results_df.to_csv(filename, index=False)
        print(f"\n💾 Hasil disimpan ke: {filename}")
        
        # KIRIM EMAIL
        print("\n📧 MENGIRIM EMAIL...")
        if email_from and email_password:
            success = send_email_report(
                results_df, 
                email_to, 
                email_from, 
                email_password,
                screener.criteria
            )
            if success:
                print("✓ EMAIL BERHASIL DIKIRIM!")
            else:
                print("✗ GAGAL MENGIRIM EMAIL - Lihat log di atas")
        else:
            print("⚠ EMAIL TIDAK DIKIRIM - Konfigurasi email tidak lengkap")
            
    else:
        print("\n📭 TIDAK ADA SAHAM yang memenuhi kriteria 7/8 atau 8/8.")
        
        # TETAP KIRIM NOTIFIKASI
        if email_from and email_password:
            print("\n📧 MENGIRIM NOTIFIKASI (tidak ada hasil)...")
            empty_df = None
            send_email_report(
                empty_df, 
                email_to, 
                email_from, 
                email_password,
                screener.criteria
            )
    
    print("\n" + "=" * 70)
    print("SCREENING SELESAI")
    print("=" * 70)

if __name__ == "__main__":
    main()
