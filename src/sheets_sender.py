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
            print("  ⚠ Tidak ada data 8/8 untuk dikirim")
            return False
        
        # Konversi DataFrame ke list of dicts - HANYA 8/8
        results = []
        for _, row in df.iterrows():
            # Ambil hanya saham dengan Status 8/8
            if row.get('Status') == '8/8':
                result = {
                    'Ticker': row.get('Ticker', ''),
                    'Status': '8/8',  # Pastikan 8/8
                    'Harga': row.get('Harga', '0'),
                    'VCP': row.get('VCP', '0'),
                    'RS': row.get('RS', '0'),
                    'Keterangan': row.get('Keterangan', '')  # Keterangan dengan pola
                }
                results.append(result)
        
        if not results:
            print("  ⚠ Tidak ada saham 8/8 dalam data")
            return False
        
        # Buat payload
        payload = {
            'timestamp': datetime.now().isoformat(),
            'total': len(results),
            'results': results,
            'type': '88_only'  # Tandai khusus 8/8
        }
        
        print(f"  📤 Mengirim {len(results)} data 8/8 ke Google Sheets...")
        
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
