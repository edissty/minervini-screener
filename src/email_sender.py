# ============================================
# EMAIL_SENDER.PY - MINERVINI SCREENER v6.0
# Dengan Chart Patterns & Timezone WIB
# ============================================

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, timezone, timedelta

def get_wib_time():
    """
    Mendapatkan waktu WIB (UTC+7) yang akurat
    """
    utc_now = datetime.now(timezone.utc)
    wib_now = utc_now + timedelta(hours=7)
    return wib_now

def format_currency(value):
    """
    Format angka ke format Rupiah
    """
    try:
        if isinstance(value, str):
            # Hapus 'Rp ' dan titik
            clean = value.replace('Rp ', '').replace('.', '')
            value = float(clean)
        return f"Rp {value:,.0f}".replace(',', '.')
    except:
        return str(value)

def parse_price(price_str):
    """
    Parse harga dari string ke numeric
    """
    try:
        if isinstance(price_str, str):
            clean = price_str.replace('Rp ', '').replace('.', '').replace('K', '000')
            return float(clean)
        return float(price_str)
    except:
        return 0

def send_email_report(df, email_to, email_from, password, criteria, smtp_server='smtp.gmail.com', port=587):
    """
    Mengirim laporan hasil screening ke email dengan panduan trading + chart patterns
    """
    print("\n" + "=" * 50)
    print("📧 PROSES KIRIM EMAIL")
    print("=" * 50)
    
    wib_time = get_wib_time()
    
    try:
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = f"📊 Minervini Screener + Patterns - {wib_time.strftime('%d/%m/%Y %H:%M')} WIB"
        
        if df is not None and not df.empty:
            total_8 = len(df[df['Status'] == '8/8']) if 'Status' in df.columns else 0
            total_7 = len(df[df['Status'] == '7/8']) if 'Status' in df.columns else 0
            
            # Buat tabel HTML dengan styling
            table_html = df.to_html(index=False, escape=False, classes='screening-table')
            
            # Tambahkan panduan trading untuk setiap saham
            trading_guide_html = ""
            for idx, row in df.iterrows():
                ticker = row['Ticker']
                harga = row['Harga']
                rs = row['RS'] if 'RS' in row else '70'
                vcp = row['VCP'] if 'VCP' in row else 'N/A'
                patterns = row['Patterns'] if 'Patterns' in row else 'Tidak ada pola'
                
                # Hitung level trading
                harga_numeric = parse_price(harga)
                if harga_numeric > 0:
                    entry_price = harga_numeric
                    stop_loss = entry_price * 0.93  # 7% stop loss
                    target1 = entry_price * 1.20    # 20% target
                    target2 = entry_price * 1.40    # 40% target
                    
                    risk = entry_price - stop_loss
                    reward = target1 - entry_price
                    risk_reward = reward / risk if risk > 0 else 0
                    
                    entry_str = format_currency(entry_price)
                    stop_str = format_currency(stop_loss)
                    target1_str = format_currency(target1)
                    target2_str = format_currency(target2)
                else:
                    entry_str = harga
                    stop_str = "-"
                    target1_str = "-"
                    target2_str = "-"
                    risk_reward = 0
                
                # Warna badge berdasarkan pola
                pattern_class = "pattern-badge"
                if "VCP Kuat" in patterns or "Perfect Order" in patterns:
                    pattern_class = "pattern-badge-strong"
                elif "Uptrend" in patterns:
                    pattern_class = "pattern-badge-good"
                
                trading_guide_html += f"""
                <div class="trading-card">
                    <h4>📈 {ticker} - Trading Plan</h4>
                    <table class="trading-table">
                        <tr>
                            <td><strong>Entry Point:</strong></td>
                            <td>{entry_str}</td>
                        </tr>
                        <tr>
                            <td><strong>Stop Loss:</strong></td>
                            <td>{stop_str} (7% di bawah entry) ⚠️</td>
                        </tr>
                        <tr>
                            <td><strong>Target 1 (20%):</strong></td>
                            <td>{target1_str} → Jual 30-50%</td>
                        </tr>
                        <tr>
                            <td><strong>Target 2 (40%):</strong></td>
                            <td>{target2_str} → Trailing stop</td>
                        </tr>
                        <tr>
                            <td><strong>Risk/Reward:</strong></td>
                            <td>1 : {risk_reward:.1f} (ideal ≥ 3)</td>
                        </tr>
                        <tr>
                            <td><strong>RS / VCP:</strong></td>
                            <td>RS: {rs} | VCP: {vcp}</td>
                        </tr>
                        <tr>
                            <td><strong>Chart Patterns:</strong></td>
                            <td><span class="{pattern_class}">{patterns}</span></td>
                        </tr>
                    </table>
                </div>
                """
            
            body = f"""
            <html>
            <head>
                <style>
                    body {{ 
                        font-family: 'Segoe UI', Arial, sans-serif; 
                        margin: 20px; 
                        color: #333;
                        background-color: #f5f5f5;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 25px;
                        border-radius: 15px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }}
                    h2 {{ 
                        color: #2c3e50; 
                        border-bottom: 3px solid #3498db; 
                        padding-bottom: 10px;
                        margin-top: 0;
                    }}
                    h3 {{
                        color: #34495e;
                        margin-top: 25px;
                    }}
                    .summary-box {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 20px 0;
                    }}
                    .summary-box ul {{
                        list-style: none;
                        padding: 0;
                    }}
                    .summary-box li {{
                        margin: 10px 0;
                        font-size: 16px;
                    }}
                    .criteria-box {{
                        background-color: #f8f9fa;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 20px 0;
                        border-left: 5px solid #3498db;
                    }}
                    .criteria-list {{
                        display: grid;
                        grid-template-columns: repeat(2, 1fr);
                        gap: 10px;
                        list-style: none;
                        padding: 0;
                    }}
                    .criteria-list li {{
                        padding: 8px;
                        background-color: white;
                        border-radius: 5px;
                        border-left: 3px solid #3498db;
                    }}
                    table {{ 
                        border-collapse: collapse; 
                        width: 100%;
                        margin: 20px 0;
                        font-size: 13px;
                        background-color: white;
                        border-radius: 10px;
                        overflow: hidden;
                        box-shadow: 0 2px 3px rgba(0,0,0,0.1);
                    }}
                    th {{ 
                        background-color: #3498db; 
                        color: white; 
                        padding: 12px;
                        text-align: left;
                    }}
                    td {{ 
                        border: 1px solid #ddd; 
                        padding: 8px; 
                    }}
                    tr:nth-child(even) {{ 
                        background-color: #f8f9fa; 
                    }}
                    .badge-8 {{
                        background-color: #27ae60;
                        color: white;
                        padding: 3px 10px;
                        border-radius: 15px;
                        font-weight: bold;
                        display: inline-block;
                    }}
                    .badge-7 {{
                        background-color: #f39c12;
                        color: white;
                        padding: 3px 10px;
                        border-radius: 15px;
                        font-weight: bold;
                        display: inline-block;
                    }}
                    .trading-card {{
                        background-color: #f0f7ff;
                        padding: 15px;
                        margin: 15px 0;
                        border-left: 5px solid #3498db;
                        border-radius: 10px;
                    }}
                    .trading-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 10px 0;
                        background-color: transparent;
                        box-shadow: none;
                    }}
                    .trading-table td {{
                        border: none;
                        padding: 5px;
                        background-color: transparent;
                    }}
                    .pattern-badge {{
                        display: inline-block;
                        background-color: #e1f5fe;
                        color: #0277bd;
                        padding: 5px 10px;
                        border-radius: 15px;
                        font-size: 12px;
                    }}
                    .pattern-badge-strong {{
                        display: inline-block;
                        background-color: #c8e6c9;
                        color: #2e7d32;
                        padding: 5px 10px;
                        border-radius: 15px;
                        font-size: 12px;
                        font-weight: bold;
                    }}
                    .pattern-badge-good {{
                        display: inline-block;
                        background-color: #fff3e0;
                        color: #e65100;
                        padding: 5px 10px;
                        border-radius: 15px;
                        font-size: 12px;
                    }}
                    .footer {{
                        margin-top: 30px;
                        padding-top: 15px;
                        border-top: 1px solid #eee;
                        text-align: center;
                        color: #7f8c8d;
                        font-size: 12px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>📈 MINERVINI SCREENER + CHART PATTERNS</h2>
                    <p><strong>Waktu Screening:</strong> {wib_time.strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                    
                    <div class="summary-box">
                        <h3 style="color: white; margin-top: 0;">📊 RINGKASAN HASIL</h3>
                        <ul>
                            <li>✅ Total Saham Lolos: <strong>{len(df)}</strong></li>
                            <li>🏆 Saham <span class="badge-8">8/8</span>: <strong>{total_8}</strong></li>
                            <li>📈 Saham <span class="badge-7">7/8</span>: <strong>{total_7}</strong></li>
                        </ul>
                    </div>
                    
                    <div class="criteria-box">
                        <h3>🎯 8 KRITERIA MINERVINI</h3>
                        <ul class="criteria-list">
                            <li><strong>C1:</strong> Harga > MA150 & MA200</li>
                            <li><strong>C2:</strong> MA150 > MA200</li>
                            <li><strong>C3:</strong> MA200 Menanjak (1 bulan)</li>
                            <li><strong>C4:</strong> MA50 > MA150 & MA200</li>
                            <li><strong>C5:</strong> Harga > MA50</li>
                            <li><strong>C6:</strong> Harga > 30% dari Low 52-W</li>
                            <li><strong>C7:</strong> Harga dalam 25% dari High 52-W</li>
                            <li><strong>C8:</strong> Relative Strength > 70</li>
                        </ul>
                    </div>
                    
                    <h3>📋 DETAIL SAHAM LOLOS SCREENING</h3>
                    <p><small>✓ = Memenuhi kriteria | ✗ = Tidak memenuhi</small></p>
                    {table_html}
                    
                    <h3>📊 TRADING PLAN + CHART PATTERNS</h3>
                    {trading_guide_html}
                    
                    <div class="footer">
                        <p><i>Disclaimer: Analisis pola chart otomatis mungkin tidak 100% akurat. 
                        Selalu lakukan verifikasi manual sebelum mengambil keputusan investasi.</i></p>
                        <p>Generated by Minervini Screener v6.0 • {wib_time.strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Lampirkan CSV
            csv_data = df.to_csv(index=False)
            attachment = MIMEApplication(csv_data.encode('utf-8'))
            attachment.add_header(
                'Content-Disposition', 'attachment', 
                filename=f"minervini_screening_{wib_time.strftime('%Y%m%d_%H%M')}.csv"
            )
            msg.attach(attachment)
            
        else:
            # Email ketika tidak ada hasil
            body = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: 'Segoe UI', Arial, sans-serif;
                        margin: 20px;
                        background-color: #f5f5f5;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 30px;
                        border-radius: 15px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }}
                    h2 {{ color: #2c3e50; border-bottom: 2px solid #e74c3c; padding-bottom: 10px; }}
                    .no-results {{
                        background-color: #f8d7da;
                        color: #721c24;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 20px 0;
                        text-align: center;
                    }}
                    .quote {{
                        font-style: italic;
                        color: #666;
                        margin-top: 20px;
                        padding: 15px;
                        background-color: #f8f9fa;
                        border-radius: 5px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>📈 MINERVINI STOCK SCREENER</h2>
                    <p><strong>Waktu Screening:</strong> {wib_time.strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                    
                    <div class="no-results">
                        <h3>📭 TIDAK ADA HASIL SCREENING</h3>
                        <p>Tidak ditemukan saham yang memenuhi kriteria 7/8 atau 8/8 pada screening kali ini.</p>
                    </div>
                    
                    <div class="quote">
                        <p>"Sit-out power - lebih baik tidak trading daripada memaksakan entry di saham yang tidak memenuhi kriteria."</p>
                        <p style="text-align: right;">- Mark Minervini</p>
                    </div>
                    
                    <p style="color: #7f8c8d; font-size: 12px; text-align: center; margin-top: 20px;">
                        Generated by Minervini Screener v6.0 • {wib_time.strftime('%d-%m-%Y %H:%M:%S')} WIB
                    </p>
                </div>
            </body>
            </html>
            """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Kirim email
        print(f"📤 Menghubungi server {smtp_server}:{port}...")
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        
        print(f"🔑 Login dengan {email_from}...")
        server.login(email_from, password)
        
        print(f"📧 Mengirim ke {email_to}...")
        server.send_message(msg)
        server.quit()
        
        print("✅ EMAIL BERHASIL DIKIRIM!")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ GAGAL LOGIN: {e}")
        print("   Penyebab: App Password salah atau 2FA belum diaktifkan")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP ERROR: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
