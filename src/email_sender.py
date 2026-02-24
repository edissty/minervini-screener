import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

def send_email_report(df, email_to, email_from, password, criteria, smtp_server='smtp.gmail.com', port=587):
    """
    Mengirim laporan hasil screening ke email
    """
    print("\n" + "=" * 50)
    print("PROSES KIRIM EMAIL")
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
        msg['Subject'] = f"📊 Minervini Screener - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        # Buat body email
        if df is not None and not df.empty:
            print(f"📊 Data: {len(df)} saham lolos screening")
            
            # Hitung statistik
            total_8 = len(df[df['Status'] == '8/8'])
            total_7 = len(df[df['Status'] == '7/8'])
            
            # Buat tabel HTML
            table_html = df.to_html(index=False, escape=False)
            
            # Body HTML
            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    h2 {{ color: #2c3e50; }}
                    h3 {{ color: #34495e; }}
                    .summary {{ 
                        background-color: #f8f9fa; 
                        padding: 15px; 
                        border-radius: 5px;
                        margin: 20px 0;
                    }}
                    table {{ 
                        border-collapse: collapse; 
                        width: 100%;
                        margin: 20px 0;
                    }}
                    th {{ 
                        background-color: #3498db; 
                        color: white; 
                        padding: 10px;
                        text-align: left;
                    }}
                    td {{ 
                        border: 1px solid #ddd; 
                        padding: 8px; 
                    }}
                    .badge-8 {{
                        background-color: #27ae60;
                        color: white;
                        padding: 3px 8px;
                        border-radius: 3px;
                    }}
                    .badge-7 {{
                        background-color: #f39c12;
                        color: white;
                        padding: 3px 8px;
                        border-radius: 3px;
                    }}
                </style>
            </head>
            <body>
                <h2>📈 Minervini Stock Screener Results</h2>
                <p><strong>Waktu Screening:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</p>
                
                <div class="summary">
                    <h3>Ringkasan:</h3>
                    <ul>
                        <li>Total saham di-screening: <strong>{len(df)}</strong></li>
                        <li>Saham <span class="badge-8">8/8</span>: <strong>{total_8}</strong></li>
                        <li>Saham <span class="badge-7">7/8</span>: <strong>{total_7}</strong></li>
                    </ul>
                </div>
                
                <h3>Kriteria Minervini:</h3>
                <ul>
            """
            
            for kode, desc in criteria.items():
                body += f"<li><strong>{kode}</strong>: {desc}</li>"
            
            body += f"""
                </ul>
                
                <h3>Detail Saham:</h3>
                {table_html}
                
                <p><small>Email ini dikirim otomatis oleh GitHub Actions</small></p>
            </body>
            </html>
            """
            
            # Lampirkan CSV
            csv_data = df.to_csv(index=False)
            attachment = MIMEApplication(csv_data.encode('utf-8'))
            attachment.add_header(
                'Content-Disposition', 
                'attachment', 
                filename=f"screening_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            )
            msg.attach(attachment)
            
        else:
            print("📭 Data: Tidak ada saham lolos screening")
            
            body = f"""
            <html>
            <body>
                <h2>📈 Minervini Stock Screener Results</h2>
                <p><strong>Waktu Screening:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</p>
                
                <div style="background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px;">
                    <h3>Tidak Ada Hasil Screening</h3>
                    <p>Tidak ditemukan saham yang memenuhi kriteria 7/8 atau 8/8.</p>
                </div>
                
                <p><small>Email ini dikirim otomatis oleh GitHub Actions</small></p>
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
