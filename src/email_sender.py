# ============================================
# EMAIL_SENDER.PY - MINERVINI SCREENER v11.0
# Dengan DeepSeek Senior Hedge Fund Analyst
# ============================================

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, timezone, timedelta
from src.deepseek_analyst import DeepSeekAnalyst  # TAMBAHKAN IMPORT

def get_wib_time():
    utc_now = datetime.now(timezone.utc)
    wib_now = utc_now + timedelta(hours=7)
    return wib_now

def format_currency(value):
    try:
        if isinstance(value, str):
            clean = value.replace('Rp ', '').replace('.', '')
            value = float(clean)
        return f"Rp {value:,.0f}".replace(',', '.')
    except:
        return str(value)

def parse_price(price_str):
    try:
        if isinstance(price_str, str):
            clean = price_str.replace('Rp ', '').replace('.', '').replace('K', '000')
            return float(clean)
        return float(price_str)
    except:
        return 0

def send_email_report(df, email_to, email_from, password, criteria, smtp_server='smtp.gmail.com', port=587):
    """
    Mengirim laporan hasil screening ke email dengan analisis DeepSeek
    """
    print("\n" + "=" * 50)
    print("📧 PROSES KIRIM EMAIL")
    print("=" * 50)
    
    wib_time = get_wib_time()
    
    # Inisialisasi DeepSeek Analyst
    analyst = DeepSeekAnalyst()
    deepseek_section = ""
    
    try:
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = f"📊 MINERVINI SCREENER 8/8 + DEEPSEEK ANALYSIS - {wib_time.strftime('%d-%m-%Y %H:%M')} WIB"
        
        if df is not None and not df.empty:
            # Filter hanya 8/8
            df_88 = df[df['Status'] == '8/8'] if 'Status' in df.columns else df
            
            if df_88.empty:
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
                breakout_count = df_88['Patterns'].str.contains('BREAKOUT', na=False).sum() if 'Patterns' in df_88.columns else 0
                
                # ===== DEEPSEEK ANALYSIS =====
                if analyst.available:
                    print("\n🤖 Memanggil Senior Hedge Fund Analyst...")
                    
                    # Analisis breakout stocks
                    breakout_analysis = analyst.analyze_breakout_stocks(df_88)
                    
                    # Analisis detail untuk top 3 saham (prioritas breakout dulu)
                    detailed_analysis = ""
                    top_stocks = df_88.sort_values(
                        by=['Patterns'], 
                        key=lambda x: x.str.contains('BREAKOUT', na=False).astype(int),
                        ascending=False
                    ).head(3)
                    
                    for _, row in top_stocks.iterrows():
                        analysis = analyst.analyze_stock(row.to_dict(), detailed=True)
                        if analysis and not analysis.startswith('[Error'):
                            detailed_analysis += f"""
                            <div style="background: #1e1e2f; color: #f0f0f0; padding: 15px; margin: 10px 0; border-radius: 8px;">
                                <h4 style="color: #ffd700; margin-top: 0;">📊 {row['Ticker']} - Senior Hedge Fund Analysis</h4>
                                <div style="font-family: 'Courier New', monospace; font-size: 13px; line-height: 1.6;">
                                    {analysis.replace(chr(10), '<br>')}
                                </div>
                            </div>
                            """
                    
                    # Gabungkan semua analisis
                    if breakout_analysis or detailed_analysis:
                        deepseek_section = f"""
                        <div style="background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%); 
                                    color: white; padding: 20px; border-radius: 15px; margin: 25px 0;">
                            <h3 style="color: #ffd700; margin-top: 0; display: flex; align-items: center;">
                                <span style="font-size: 28px; margin-right: 10px;">🤖</span> 
                                SENIOR HEDGE FUND ANALYST INSIGHTS
                            </h3>
                            
                            {breakout_analysis.replace(chr(10), '<br>') if breakout_analysis else ''}
                            
                            {detailed_analysis}
                            
                            <p style="font-size: 11px; color: #aaa; margin-top: 15px; border-top: 1px solid #333; padding-top: 10px;">
                                <i>Analisis AI oleh DeepSeek • Bukan rekomendasi investasi • Selalu lakukan verifikasi manual</i>
                            </p>
                        </div>
                        """
                
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
                    
                    is_breakout = 'BREAKOUT' in str(patterns).upper()
                    
                    harga_numeric = parse_price(harga)
                    if harga_numeric > 0:
                        entry_price = harga_numeric
                        stop_loss = entry_price * 0.93
                        target1 = entry_price * 1.20
                        target2 = entry_price * 1.40
                        
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
                    
                    card_color = "#fff3cd" if is_breakout else "#f0f7ff"
                    border_color = "#ffc107" if is_breakout else "#27ae60"
                    
                    trading_plans_html += f"""
                    <div style="background-color: {card_color}; padding: 15px; margin: 15px 0; border-left: 5px solid {border_color}; border-radius: 10px;">
                        <h4 style="margin-top: 0; color: #2c3e50;">
                            📈 {ticker} - Trading Plan
                            {f'<span style="background-color: #ffc107; color: #000; padding: 3px 10px; border-radius: 15px; font-size: 12px; margin-left: 10px;">🚀 BREAKOUT</span>' if is_breakout else ''}
                        </h4>
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
                                <td style="padding: 8px; color: {'#d32f2f' if 'BREAKOUT' in patterns else '#27ae60'};">
                                    {patterns}
                                </td>
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
                            border-bottom: 3px solid #27ae60; 
                            padding-bottom: 10px;
                            margin-top: 0;
                        }}
                        .summary-box {{
                            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
                            color: white;
                            padding: 20px;
                            border-radius: 10px;
                            margin: 20px 0;
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
                        <h2>📈 MINERVINI SCREENER + DEEPSEEK ANALYST</h2>
                        <p><strong>Waktu Screening:</strong> {wib_time.strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                        
                        <div class="summary-box">
                            <h3 style="color: white; margin-top: 0;">📊 RINGKASAN</h3>
                            <p>Total Saham 8/8: <strong>{total_8}</strong></p>
                            <p>Saham dengan Breakout: <strong>{breakout_count}</strong></p>
                        </div>
                        
                        {deepseek_section}
                        
                        <h3>📋 DETAIL SAHAM 8/8</h3>
                        <p><small>✓ = Memenuhi kriteria | ✗ = Tidak memenuhi</small></p>
                        {table_html}
                        
                        <h3>📊 TRADING PLAN (8/8)</h3>
                        {trading_plans_html}
                        
                        <div class="footer">
                            <p><i>🚀 BREAKOUT = Harga mendekati resistance + Volume tinggi + Candle kuat</i></p>
                            <p><i>🤖 Analisis DeepSeek untuk prioritas entry</i></p>
                            <p>Generated by Minervini Screener v11.0 • {wib_time.strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                msg.attach(MIMEText(body, 'html'))
                
                csv_data = df_88.to_csv(index=False)
                attachment = MIMEApplication(csv_data.encode('utf-8'))
                attachment.add_header(
                    'Content-Disposition', 'attachment', 
                    filename=f"minervini_88_{wib_time.strftime('%Y%m%d_%H%M')}.csv"
                )
                msg.attach(attachment)
            
        else:
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
        
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(email_from, password)
        server.send_message(msg)
        server.quit()
        
        print("✅ EMAIL DENGAN DEEPSEEK ANALISIS BERHASIL DIKIRIM!")
        return True
        
    except Exception as e:
        print(f"❌ GAGAL KIRIM EMAIL: {e}")
        return False
