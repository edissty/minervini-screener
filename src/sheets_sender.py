import requests
import json
from datetime import datetime

def send_to_google_sheets(df, webhook_url):
    """
    Mengirim hasil screening ke Google Sheets via Apps Script
    
    Args:
        df: DataFrame hasil screening
        webhook_url: URL dari Google Apps Script yang sudah dideploy
    """
    print("\n📊 MENGIRIM KE GOOGLE SHEETS...")
    
    try:
        if df is None or df.empty:
            print("  ⚠ Tidak ada data untuk dikirim")
            return False
        
        # Konversi DataFrame ke list of dicts
        results = []
        for _, row in df.iterrows():
            result = {
                'Ticker': row.get('Ticker', ''),
                'Status': row.get('Status', ''),
                'Harga': row.get('Harga', '0'),
                'VCP': row.get('VCP', '0'),
                'RS': row.get('RS', '0'),
                'C1': row.get('C1', ''),
                'C2': row.get('C2', ''),
                'C3': row.get('C3', ''),
                'C4': row.get('C4', ''),
                'C5': row.get('C5', ''),
                'C6': row.get('C6', ''),
                'C7': row.get('C7', ''),
                'C8': row.get('C8', '')
            }
            results.append(result)
        
        # Buat payload
        payload = {
            'timestamp': datetime.now().isoformat(),
            'total': len(results),
            'results': results
        }
        
        print(f"  📤 Mengirim {len(results)} data ke Google Sheets...")
        
        # Kirim ke webhook
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            webhook_url,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"  ✅ Berhasil dikirim ke Google Sheets!")
                details = result.get('details', {})
                
                monthly = details.get('monthly', {})
                if monthly:
                    if monthly.get('saved'):
                        print(f"     • Baru di sheet bulanan: {monthly['saved']} saham")
                    if monthly.get('updated'):
                        print(f"     • Update harga: {monthly['updated']} saham")
                
                alert = details.get('alertLog', {})
                if alert.get('saved'):
                    print(f"     • Tersimpan di Alert_Log: {alert['saved']} data")
                
                return True
            else:
                print(f"  ❌ Gagal: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"  ❌ HTTP Error: {response.status_code}")
            print(f"     Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_connection(webhook_url):
    """Test koneksi ke Google Sheets endpoint"""
    try:
        print("\n🔍 Testing koneksi ke Google Sheets...")
        response = requests.get(webhook_url, timeout=10)
        if response.status_code == 200:
            print("  ✅ Koneksi OK!")
            return True
        else:
            print(f"  ❌ Gagal: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
