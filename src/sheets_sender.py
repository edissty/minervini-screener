# ============================================
# SHEETS_SENDER.PY - MINERVINI SCREENER v6.5
# Hanya mengirim SAHAM 8/8 ke Google Sheets
# ============================================

import requests
import json
from datetime import datetime

def send_to_google_sheets(df, webhook_url):
    """
    Mengirim hasil screening ke Google Sheets - HANYA 8/8
    """
    print("\n" + "=" * 50)
    print("📊 MENGIRIM KE GOOGLE SHEETS")
    print("=" * 50)
    
    try:
        if df is None or df.empty:
            print("  ⚠ Tidak ada data untuk dikirim")
            return False
        
        print(f"  📊 DataFrame shape: {df.shape}")
        print(f"  📋 Kolom yang tersedia: {list(df.columns)}")
        
        # Filter hanya 8/8
        df_88 = df[df['Status'] == '8/8'] if 'Status' in df.columns else df
        
        if df_88.empty:
            print("  ⚠ Tidak ada saham 8/8 dalam data")
            return False
        
        print(f"  ✅ Ditemukan {len(df_88)} saham 8/8")
        
        # Konversi DataFrame ke list of dicts
        results = []
        for idx, row in df_88.iterrows():
            # Ambil nilai dengan default
            ticker = row.get('Ticker', '')
            status = row.get('Status', '8/8')
            harga = row.get('Harga', '0')
            vcp = row.get('VCP', 0)
            rs = row.get('RS', 0)
            keterangan = row.get('Keterangan', '')
            
            # Debug untuk melihat keterangan
            print(f"    📝 {ticker}: Keterangan = '{keterangan[:50]}...'")
            
            result = {
                'Ticker': ticker,
                'Status': status,
                'Harga': harga,
                'VCP': vcp,
                'RS': rs,
                'Keterangan': keterangan  # PASTIKAN INI TERKIRIM
            }
            results.append(result)
        
        # Buat payload
        payload = {
            'timestamp': datetime.now().isoformat(),
            'total': len(results),
            'results': results,
            'type': '88_only'
        }
        
        print(f"\n  📤 Mengirim {len(results)} data 8/8 ke Google Sheets...")
        print(f"  📝 Contoh data pertama:")
        print(f"      Ticker: {results[0]['Ticker']}")
        print(f"      Keterangan: {results[0]['Keterangan'][:100]}...")
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            webhook_url,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"\n  ✅ Berhasil dikirim ke Google Sheets!")
            return True
        else:
            print(f"\n  ❌ HTTP Error: {response.status_code}")
            print(f"     Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        return False
