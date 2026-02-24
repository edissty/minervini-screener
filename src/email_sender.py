import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

def send_email_report(df, email_to, email_from, password, criteria, smtp_server='smtp.gmail.com', port=587):
    msg = MIMEMultipart()
    msg['From'] = email_from
    msg['To'] = email_to
    msg['Subject'] = f"📊 Minervini Screener Report - {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    
    if df is not None and not df.empty:
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h2 {{ color: #2c3e50; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th {{ background-color: #3498db; color: white; padding: 10px; }}
                td {{ border: 1px solid #ddd; padding: 8px; }}
                .badge-8 {{ background-color: #27ae60; color: white; padding: 3px 8px; border-radius: 3px; }}
                .badge-7 {{ background-color: #f39c12; color: white; padding: 3px 8px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <h2>📈 Minervini Stock Screener Results</h2>
            <p><strong>Waktu:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</p>
            
            <h3>Ringkasan:</h3>
            <ul>
                <li>Total saham: <strong>{len(df)}</strong></li>
                <li>Saham 8/8: <strong>{len(df[df['Status'] == '8/8'])}</strong></li>
                <li>Saham 7/8: <strong>{len(df[df['Status'] == '7/8'])}</strong></li>
            </ul>
            
            <h3>Detail Saham:</h3>
            {df.to_html(index=False)}
        </body>
        </html>
        """
    else:
        body = f"""
        <html>
        <body>
            <h2>📈 Minervini Stock Screener Results</h2>
            <p><strong>Waktu:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</p>
            <p><strong>Tidak ada saham yang memenuhi kriteria 7/8 atau 8/8.</strong></p>
        </body>
        </html>
        """
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(email_from, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
