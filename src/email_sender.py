import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

def send_email_report(df, email_to, email_from, password, criteria, smtp_server='smtp.gmail.com', port=587):
    print("\n" + "=" * 50)
    print("📧 PROSES KIRIM EMAIL")
    print("=" * 50)
    
    try:
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = f"📊 Minervini Screener - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        if df is not None and not df.empty:
            total_8 = len(df[df['Status'] == '8/8']) if 'Status' in df.columns else 0
            total_7 = len(df[df['Status'] == '7/8']) if 'Status' in df.columns else 0
            
            table_html = df.to_html(index=False, escape=False)
            
            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    h2 {{ color: #2c3e50; }}
                    .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th {{ background-color: #3498db; color: white; padding: 10px; }}
                    td {{ border: 1px solid #ddd; padding: 8px; }}
                    .badge-8 {{ background-color: #27ae60; color: white; padding: 3px 8px; border-radius: 3px; }}
                    .badge-7 {{ background-color: #f39c12; color: white; padding: 3px 8px; border-radius: 3px; }}
                </style>
            </head>
            <body>
                <h2>📈 MINERVINI STOCK SCREENER RESULTS</h2>
                <p><strong>Waktu:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                
                <div class="summary">
                    <h3>📊 RINGKASAN</h3>
                    <ul>
                        <li>Total Saham Lolos: <strong>{len(df)}</strong></li>
                        <li>Saham <span class="badge-8">8/8</span>: <strong>{total_8}</strong></li>
                        <li>Saham <span class="badge-7">7/8</span>: <strong>{total_7}</strong></li>
                    </ul>
                </div>
                
                <h3>🎯 8 KRITERIA MINERVINI</h3>
                <ul>
            """
            
            for k, v in criteria.items():
                body += f"<li><strong>{k}:</strong> {v}</li>"
            
            body += f"""
                </ul>
                
                <h3>📋 DETAIL SAHAM LOLOS</h3>
                {table_html}
                
                <p><small>Email ini dikirim otomatis oleh GitHub Actions</small></p>
            </body>
            </html>
            """
            
            # Lampiran CSV
            csv_data = df.to_csv(index=False)
            attachment = MIMEApplication(csv_data.encode('utf-8'))
            attachment.add_header('Content-Disposition', 'attachment', 
                                filename=f"screening_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
            msg.attach(attachment)
            
        else:
            body = f"""
            <html>
            <body>
                <h2>📈 MINERVINI STOCK SCREENER RESULTS</h2>
                <p><strong>Waktu:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px;">
                    <h3>📭 TIDAK ADA HASIL</h3>
                    <p>Tidak ditemukan saham yang memenuhi kriteria 7/8 atau 8/8.</p>
                </div>
            </body>
            </html>
            """
        
        msg.attach(MIMEText(body, 'html'))
        
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
