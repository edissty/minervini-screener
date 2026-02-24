import os
import sys
from datetime import datetime
from src.minervini_screener import MinerviniScreener
from src.email_sender import send_email_report

def main():
    print("=" * 60)
    print("MINERVINI STOCK SCREENER")
    print(f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Baca daftar saham
    stocks_file = "config/stocks_list.txt"
    try:
        with open(stocks_file, 'r') as f:
            stocks = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"Total saham yang akan di-screening: {len(stocks)}")
    except FileNotFoundError:
        print(f"Error: File {stocks_file} tidak ditemukan!")
        sys.exit(1)
    
    # Inisialisasi screener
    screener = MinerviniScreener()
    
    # Lakukan screening
    print("\nMemulai screening...")
    results_df = screener.screen_stocks(stocks)
    
    if not results_df.empty:
        print("\n" + "=" * 60)
        print("HASIL SCREENING")
        print("=" * 60)
        print(f"Total saham memenuhi kriteria: {len(results_df)}")
        print(f"Saham 8/8: {len(results_df[results_df['Status'] == '8/8'])}")
        print(f"Saham 7/8: {len(results_df[results_df['Status'] == '7/8'])}")
        
        # Simpan hasil
        os.makedirs("results", exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"results/minervini_screening_{timestamp}.csv"
        results_df.to_csv(filename, index=False)
        print(f"\nHasil disimpan ke: {filename}")
        
        # Kirim email
        print("\nMengirim email...")
        email_from = os.environ.get('EMAIL_FROM')
        email_password = os.environ.get('EMAIL_PASSWORD')
        email_to = os.environ.get('EMAIL_TO', 'edissty@gmail.com')
        
        if email_from and email_password:
            success = send_email_report(
                results_df, 
                email_to, 
                email_from, 
                email_password,
                screener.criteria
            )
            if success:
                print("✓ Email berhasil dikirim")
            else:
                print("✗ Gagal mengirim email")
        else:
            print("⚠ Konfigurasi email tidak lengkap")
    else:
        print("\nTidak ada saham yang memenuhi kriteria 7/8 atau 8/8.")
        
        # Tetap kirim notifikasi
        if os.environ.get('EMAIL_FROM') and os.environ.get('EMAIL_PASSWORD'):
            empty_df = None
            send_email_report(
                empty_df, 
                os.environ.get('EMAIL_TO', 'edissty@gmail.com'), 
                os.environ.get('EMAIL_FROM'), 
                os.environ.get('EMAIL_PASSWORD'),
                screener.criteria
            )

if __name__ == "__main__":
    main()
