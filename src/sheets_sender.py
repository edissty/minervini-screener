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
    print("\n📊 MENGIRIM KE GOOGLE SHEETS...")
    
    try:
        if df is None or df.empty:
            print("  ⚠ Tidak ada data untuk dikirim")
            return False
        
        # Filter hanya 8/8
        df_88 = df[df['Status'] == '8/8'] if 'Status' in df.columns else df
        
        if df_88.empty:
            print("  ⚠ Tidak ada saham 8/8 dalam data")
            return False
        
        # Konversi DataFrame ke list of dicts
        results = []
        for _, row in df_88.iterrows():
            result = {
                'Ticker': row.get('Ticker', ''),
                'Status': '8/8',
                'Harga': row.get('Harga', '0'),
                'VCP': row.get('VCP', '0'),
                'RS': row.get('RS', '0'),
                'Keterangan': row.get('Keterangan', '')  # PASTIKAN INI ADA
            }
            results.append(result)
        
        # Buat payload
        payload = {
            'timestamp': datetime.now().isoformat(),
            'total': len(results),
            'results': results,
            'type': '88_only'
        }
        
        print(f"  📤 Mengirim {len(results)} data 8/8 ke Google Sheets...")
        if results:
            print(f"  📝 Contoh keterangan: {results[0]['Keterangan'][:100]}...")
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            webhook_url,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"  ✅ Berhasil dikirim ke Google Sheets!")
            return True
        else:
            print(f"  ❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
