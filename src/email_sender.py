import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

def send_email_report(df, email_to, email_from, password, criteria, smtp_server='smtp.gmail.com', port=587):
    """
    Mengirim laporan hasil screening ke email dengan kriteria Minervini yang sesungguhnya
    """
    print("\n" + "=" * 50)
    print("📧 PROSES KIRIM EMAIL")
    print("=" * 50)
    
    print(f"📧 Konfigurasi Email:")
    print(f"   Dari   : {email_from}")
    print(f"   Ke     : {email_to}")
    print(f"   Server : {smtp_server}:{port}")
    
    try:
        # Buat pesan email
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = f"📊 Minervini Screener Report - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        # Buat body email
        if df is not None and not df.empty:
            print(f"📊 Data: {len(df)} saham lolos screening")
            
            # Hitung statistik
            total_8 = len(df[df['Status'] == '8/8']) if 'Status' in df.columns else 0
            total_7 = len(df[df['Status'] == '7/8']) if 'Status' in df.columns else 0
            
            # Buat tabel HTML
            table_html = df.to_html(index=False, escape=False, classes='screening-table')
            
            # Body HTML dengan kriteria yang benar
            body = f"""
            <html>
            <head>
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        margin: 20px;
                        color: #333;
                    }}
                    h2 {{ 
                        color: #2c3e50;
                        border-bottom: 2px solid #3498db;
                        padding-bottom: 10px;
                    }}
                    h3 {{ 
                        color: #34495e;
                        margin-top: 25px;
                    }}
                    .summary {{ 
                        background-color: #f8f9fa; 
                        padding: 20px; 
                        border-radius: 10px;
                        margin: 20px 0;
                        border-left: 5px solid #3498db;
                    }}
                    .criteria-box {{
                        background-color: #f0f7ff;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 20px 0;
                        border: 1px solid #bde0fe;
                    }}
                    .criteria-list {{
                        columns: 2;
                        list-style-type: none;
                        padding: 0;
                    }}
                    .criteria-list li {{
                        margin: 10px 0;
                        padding: 8px;
                        background-color: white;
                        border-radius: 5px;
                        border-left: 3px solid #3498db;
                    }}
                    table {{ 
                        border-collapse: collapse; 
                        width: 100%;
                        margin: 20px 0;
                        font-size: 14px;
                        box-shadow: 0 2px 3px rgba(0,0,0,0.1);
                    }}
                    th {{ 
                        background-color: #3498db; 
                        color: white; 
                        padding: 12px;
                        text-align: left;
                        font-weight: bold;
                    }}
                    td {{ 
                        border: 1px solid #ddd; 
                        padding: 10px; 
                        text-align: left;
                    }}
                    tr:nth-child(even) {{ 
                        background-color: #f8f9fa; 
                    }}
                    tr:hover {{ 
                        background-color: #f1f1f1; 
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
                    .check-mark {{
                        color: #27ae60;
                        font-weight: bold;
                    }}
                    .x-mark {{
                        color: #e74c3c;
                        font-weight: bold;
                    }}
                    .footer {{ 
                        margin-top: 30px; 
                        font-size: 12px; 
                        color: #7f8c8d;
                        border-top: 1px solid #eee;
                        padding-top: 15px;
                        text-align: center;
                    }}
                    .timestamp {{
                        color: #7f8c8d;
                        font-size: 14px;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <h2>📈 MINERVINI STOCK SCREENER RESULTS</h2>
                <div class="timestamp">
                    <strong>Waktu Screening:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} WIB
                </div>
                
                <div class="summary">
                    <h3>📊 RINGKASAN HASIL</h3>
                    <table style="width: 100%; background: white; margin: 0;">
                        <tr>
                            <td style="border: none; padding: 10px;"><strong>Total Saham Lolos:</strong></td>
                            <td style="border: none; padding: 10px;">{len(df)}</td>
                        </tr>
                        <tr>
                            <td style="border: none; padding: 10px;"><strong>Saham 8/8:</strong></td>
                            <td style="border: none; padding: 10px;"><span class="badge-8">{total_8}</span></td>
                        </tr>
                        <tr>
                            <td style="border: none; padding: 10px;"><strong>Saham 7/8:</strong></td>
                            <td style="border: none; padding: 10px;"><span class="badge-7">{total_7}</span></td>
                        </tr>
                    </table>
                </div>
                
                <div class="criteria-box">
                    <h3>🎯 8 KRITERIA MINERVINI</h3>
                    <ul class="criteria-list">
                        <li><strong>C1:</strong> Harga > MA150 & MA200</li>
                        <li><strong>C2:</strong> MA150 > MA200</li>
                        <li><strong>C3:</strong> MA200 Menanjak (1 bulan terakhir)</li>
                        <li><strong>C4:</strong> MA50 > MA150 & MA200</li>
                        <li><strong>C5:</strong> Harga > MA50</li>
                        <li><strong>C6:</strong> Harga > 30% dari 52-Week Low</li>
                        <li><strong>C7:</strong> Harga dalam 25% dari 52-Week High</li>
                        <li><strong>C8:</strong> Relative Strength > 70</li>
                    </ul>
                </div>
                
                <h3>📋 DETAIL SAHAM LOLOS SCREENING</h3>
                <p><small>✓ = Memenuhi kriteria | ✗ = Tidak memenuhi kriteria</small></p>
                {table_html}
                
                <div class="footer">
                    <p><i>Disclaimer: Screening ini menggunakan data dari Yahoo Finance dan kriteria Minervini.</i></p>
                    <p><i>Hasil screening bukan rekomendasi beli/jual. Lakukan analisis lebih lanjut sebelum investasi.</i></p>
                    <p>Generated by Minervini Screener GitHub Actions • {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</p>
                </div>
            </body>
            </html>
            """
            
            # Lampirkan CSV
            csv_data = df.to_csv(index=False)
            attachment = MIMEApplication(csv_data.encode('utf-8'))
            attachment.add_header(
                'Content-Disposition', 
                'attachment', 
                filename=f"minervini_screening_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            )
            msg.attach(attachment)
            
        else:
            print("📭 Data: Tidak ada saham lolos screening")
            
            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h2 {{ color: #2c3e50; }}
                    .no-results {{
                        background-color: #f8d7da;
                        color: #721c24;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 20px 0;
                        border: 1px solid #f5c6cb;
                    }}
                    .criteria-box {{
                        background-color: #f0f7ff;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 20px 0;
                    }}
                </style>
            </head>
            <body>
                <h2>📈 MINERVINI STOCK SCREENER RESULTS</h2>
                <p><strong>Waktu Screening:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                
                <div class="no-results">
                    <h3>📭 TIDAK ADA HASIL SCREENING</h3>
                    <p>Tidak ditemukan saham yang memenuhi kriteria 7/8 atau 8/8 pada screening kali ini.</p>
                </div>
                
                <div class="criteria-box">
                    <h3>🎯 8 KRITERIA MINERVINI</h3>
                    <ul>
                        <li><strong>C1:</strong> Harga > MA150 & MA200</li>
                        <li><strong>C2:</strong> MA150 > MA200</li>
                        <li><strong>C3:</strong> MA200 Menanjak (1 bulan terakhir)</li>
                        <li><strong>C4:</strong> MA50 > MA150 & MA200</li>
                        <li><strong>C5:</strong> Harga > MA50</li>
                        <li><strong>C6:</strong> Harga > 30% dari 52-Week Low</li>
                        <li><strong>C7:</strong> Harga dalam 25% dari 52-Week High</li>
                        <li><strong>C8:</strong> Relative Strength > 70</li>
                    </ul>
                </div>
                
                <p><small>Email ini dikirim otomatis oleh GitHub Actions • {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</small></p>
            </body>
            </html>
            """
        
        # Attach body
        msg.attach(MIMEText(body, 'html'))
        
        # Kirim email
        print("\n🔄 Menghubungi server email...")
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        
        print(f"🔑 Login dengan {email_from}...")
        server.login(email_from, password)
        
        print(f"📤 Mengirim pesan ke {email_to}...")
        server.send_message(msg)
        
        print(f"👋 Menutup koneksi...")
        server.quit()
        
        print("✅ EMAIL BERHASIL DIKIRIM!")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ GAGAL LOGIN: {e}")
        print("   Penyebab: Password salah atau App Password tidak valid")
        print("   Solusi: Buat ulang App Password di https://myaccount.google.com/apppasswords")
        return False
        
    except smtplib.SMTPException as e:
        print(f"❌ SMTP ERROR: {e}")
        return False
        
    except Exception as e:
        print(f"❌ ERROR LAIN: {e}")
        return False
