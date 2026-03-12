# ============================================
# EMAIL_SENDER.PY - MINERVINI SCREENER v6.5
# Hanya mengirim SAHAM 8/8 ke email
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
    Mengirim laporan hasil screening ke email - HANYA SAHAM 8/8
    """
    print("\n" + "=" * 50)
    print("📧 PROSES KIRIM EMAIL")
    print("=" * 50)
    
    wib_time = get_wib_time()
    
    try:
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = f"📊 MINERVINI SCREENER 8/8 + CHART PATTERNS - {wib_time.strftime('%d-%m-%Y %H:%M')} WIB"
        
        if df is not None and not df.empty:
            # Filter hanya 8/8
            df_88 = df[df['Status'] == '8/8'] if 'Status' in df.columns else df
            
            if df_88.empty:
                # Jika tidak ada 8/8, tetap kirim notifikasi
                body = f"""
                <html>
                <body>
                    <div style="font-family: Arial; max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2>📈 MINERVINI SCREENER</h2>
                        <p><strong>Waktu Screening:</strong> {wib_time.strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                        <div style="background-color: #f8d7da; padding: 20px; border-radius: 10px;">
                            <h3>📭 TIDAK ADA SAHAM 8/8</h3>
                            <p>Tidak ditemukan saham yang memenuhi semua 8 kriteria Minervini pada screening kali ini.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                msg.attach(MIMEText(body, 'html'))
            else:
                total_8 = len(df_88)
                
                # Buat tabel HTML
                table_html = df_88.to_html(index=False, escape=False, classes='screening-table')
                
                # Buat trading plan untuk setiap saham 8/8
                trading_plans_html = ""
                for idx, row in df_88.iterrows():
                    ticker = row['Ticker']
                    harga = row['Harga']
                    rs = row['RS'] if 'RS' in row else '70'
                    vcp = row['VCP'] if 'VCP' in row else 'N/A'
                    patterns = row['Patterns'] if 'Patterns' in row else 'Tidak ada pola'
                    rr = row['RR_Ratio'] if 'RR_Ratio' in row else '2.9'
                    
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
                    
                    # Buat trading plan card
                    trading_plans_html += f"""
                    <div style="background-color: #f0f7ff; padding: 15px; margin: 15px 0; border-left: 5px solid #27ae60; border-radius: 10px;">
                        <h4 style="margin-top: 0; color: #2c3e50;">📈 {ticker} - Trading Plan (8/8)</h4>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px; width: 30%;"><strong>Entry Point:</strong></td>
                                <td style="padding: 8px;">{entry_str}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px;"><strong>Stop Loss:</strong></td>
                                <td style="padding: 8px;">{stop_str} (7% di bawah entry) ⚠️</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px;"><strong>Target 1 (20%):</strong></td>
                                <td style="padding: 8px;">{target1_str} → Jual 30-50%</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px;"><strong>Target 2 (40%):</strong></td>
                                <td style="padding: 8px;">{target2_str} → Trailing stop</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px;"><strong>Risk/Reward:</strong></td>
                                <td style="padding: 8px;">1 : {risk_reward:.1f} (ideal ≥ 3)</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px;"><strong>RS / VCP:</strong></td>
                                <td style="padding: 8px;">RS: {rs} | VCP: {vcp}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px;"><strong>Chart Patterns:</strong></td>
                                <td style="padding: 8px; color: {'#27ae60' if patterns != 'Tidak ada pola' else '#7f8c8d'};">
                                    {patterns}
                                </td>
                            </tr>
                        </table>
                    </div>
                    """
                
                # Body email
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
                            border-bottom: 3px solid #27ae60; 
                            padding-bottom: 10px;
                            margin-top: 0;
                        }}
                        h3 {{
                            color: #34495e;
                            margin-top: 25px;
                        }}
                        .summary-box {{
                            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
                            color: white;
                            padding: 20px;
                            border-radius: 10px;
                            margin: 20px 0;
                        }}
                        .summary-box p {{
                            font-size: 24px;
                            margin: 10px 0;
                        }}
                        .criteria-box {{
                            background-color: #f8f9fa;
                            padding: 20px;
                            border-radius: 10px;
                            margin: 20px 0;
                            border-left: 5px solid #27ae60;
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
                            border-left: 3px solid #27ae60;
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
                            background-color: #27ae60; 
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
                        <h2>📈 MINERVINI SCREENER + CHART PATTERNS - 8/8 ONLY</h2>
                        <p><strong>Waktu Screening:</strong> {wib_time.strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                        
                        <div class="summary-box">
                            <h3 style="color: white; margin-top: 0;">📊 RINGKASAN</h3>
                            <p>Total Saham 8/8: <strong>{total_8}</strong></p>
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
                        
                        <h3>📋 DETAIL SAHAM 8/8</h3>
                        <p><small>✓ = Memenuhi kriteria | ✗ = Tidak memenuhi</small></p>
                        {table_html}
                        
                        <h3>📊 TRADING PLAN (8/8)</h3>
                        {trading_plans_html}
                        
                        <div class="footer">
                            <p><i>Hanya saham dengan 8/8 kriteria Minervini yang ditampilkan.</i></p>
                            <p><i>Stop Loss 7%, Target 1: 20%, Target 2: 40% (sesuai standar Minervini).</i></p>
                            <p>Generated by Minervini Screener v6.5 • {wib_time.strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                msg.attach(MIMEText(body, 'html'))
                
                # Lampirkan CSV (hanya 8/8)
                csv_data = df_88.to_csv(index=False)
                attachment = MIMEApplication(csv_data.encode('utf-8'))
                attachment.add_header(
                    'Content-Disposition', 'attachment', 
                    filename=f"minervini_88_{wib_time.strftime('%Y%m%d_%H%M')}.csv"
                )
                msg.attach(attachment)
            
        else:
            # Email ketika tidak ada data sama sekali
            body = f"""
            <html>
            <body>
                <div style="font-family: Arial; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2>📈 MINERVINI SCREENER</h2>
                    <p><strong>Waktu:</strong> {wib_time.strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                    <div style="background-color: #f8d7da; padding: 20px; border-radius: 10px;">
                        <h3>📭 TIDAK ADA HASIL SCREENING</h3>
                        <p>Tidak ditemukan saham yang memenuhi kriteria 8/8.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))
        
        # Kirim email
        print(f"📤 Menghubungi server {smtp_server}:{port}...")
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(email_from, password)
        server.send_message(msg)
        server.quit()
        
        print("✅ EMAIL BERHASIL DIKIRIM!")
        return True
        
    except Exception as e:
        print(f"❌ GAGAL KIRIM EMAIL: {e}")
        return False
