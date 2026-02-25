import os
import sys
from datetime import datetime
from src.minervini_screener import MinerviniScreener
from src.email_sender import send_email_report

def main():
    print("=" * 70)
    print("MINERVINI STOCK SCREENER - SAHAM SYARIAH")
    print(f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # CEK EMAIL
    email_from = os.environ.get('EMAIL_FROM', '')
    email_password = os.environ.get('EMAIL_PASSWORD', '')
    email_to = os.environ.get('EMAIL_TO', 'edissty@gmail.com')
    
    print("\n📧 Konfigurasi Email:")
    print(f"   Dari : {'✓' if email_from else '✗'} {email_from}")
    print(f"   Ke   : {'✓' if email_to else '✗'} {email_to}")
    print(f"   Pass : {'✓' if email_password else '✗'} ({len(email_password)} chars)")
    
    # BACA DAFTAR SAHAM
    stocks_file = "config/stocks_list.txt"
    print(f"\n📁 Membaca daftar saham dari: {stocks_file}")
    
    try:
        with open(stocks_file, 'r') as f:
            stocks = []
            for line in f:
                line = line.strip()
                # Skip baris kosong dan komentar
                if line and not line.startswith('#'):
                    # Ambil hanya kode saham (sebelum # atau spasi)
                    if '#' in line:
                        ticker = line.split('#')[0].strip()
                    else:
                        ticker = line.strip()
                    
                    # Pastikan tidak kosong
                    if ticker:
                        stocks.append(ticker)
        
        print(f"✓ Total saham ditemukan: {len(stocks)}")
        if stocks:
            print(f"  Contoh 5 pertama: {', '.join(stocks[:5])}")
    except FileNotFoundError:
        print(f"✗ ERROR: File {stocks_file} tidak ditemukan!")
        sys.exit(1)
    
    # JALANKAN SCREENING
    print("\n" + "=" * 70)
    print("🔍 MEMULAI SCREENING...")
    print("=" * 70)
    
    screener = MinerviniScreener()
    results_df = screener.screen_stocks(stocks)
    
    # PROSES HASIL
    if results_df is not None and not results_df.empty:
        print("\n✅ SCREENING SELESAI!")
        print(f"📊 Saham lolos: {len(results_df)}")
        
        # Hitung statistik
        count_8 = len(results_df[results_df['Status'] == '8/8'])
        count_7 = len(results_df[results_df['Status'] == '7/8'])
        
        print(f"   - 8/8: {count_8}")
        print(f"   - 7/8: {count_7}")
        
        # Tampilkan hasil
        print("\n📋 DAFTAR SAHAM LOLOS:")
        for idx, row in results_df.iterrows():
            print(f"   {row['Ticker']}: {row['Status']} - {row['Harga']}")
        
        # SIMPAN CSV
        os.makedirs("results", exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"results/screening_{timestamp}.csv"
        results_df.to_csv(filename, index=False)
        print(f"\n💾 Hasil disimpan ke: {filename}")
        
        # KIRIM EMAIL
        if email_from and email_password:
            print("\n📧 Mengirim email...")
            send_email_report(
                results_df, 
                email_to, 
                email_from, 
                email_password,
                screener.criteria
            )
    else:
        print("\n📭 TIDAK ADA SAHAM LOLOS SCREENING")
        
        # Kirim notifikasi
        if email_from and email_password:
            send_email_report(
                None, 
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
