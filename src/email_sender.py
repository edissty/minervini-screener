# ============================================
# EMAIL_SENDER.PY - MINERVINI SCREENER v12.0
# Dengan Google Gemini Senior Hedge Fund Analyst (GRATIS!)
# ============================================

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, timezone, timedelta
from src.gemini_analyst import GeminiAnalyst  # Import Gemini Analyst

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
    Mengirim laporan hasil screening ke email dengan analisis Gemini
    """
    print("\n" + "=" * 50)
    print("📧 PROSES KIRIM EMAIL")
    print("=" * 50)
    
    wib_time = get_wib_time()
    
    # Inisialisasi Gemini Analyst
    analyst = GeminiAnalyst()
    gemini_section = ""
    
    try:
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = f"📊 MINERVINI SCREENER 8/8 + GEMINI ANALYSIS - {wib_time.strftime('%d-%m-%Y %H:%M')} WIB"
        
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
                
                # ===== GEMINI ANALYSIS =====
                if analyst.available:
                    print("\n🤖 Memanggil Gemini Senior Hedge Fund Analyst...")
                    
                    # Analisis breakout stocks (ringkasan)
                    breakout_analysis = analyst.analyze_breakout_stocks(df_88)
                    
                    # Analisis detail untuk top 5 saham (prioritas breakout dulu)
                    detailed_analysis = ""
                    
                    # Urutkan: breakout dulu, lalu RS tertinggi
                    df_sorted = df_88.copy()
                    if 'Patterns' in df_sorted.columns:
                        df_sorted['HasBreakout'] = df_sorted['Patterns'].str.contains('BREAKOUT', na=False).astype(int)
                        df_sorted = df_sorted.sort_values(['HasBreakout', 'RS'], ascending=[False, False])
                    else:
                        df_sorted = df_sorted.sort_values(['RS'], ascending=[False])
                    
                    top_stocks = df_sorted.head(5)
                    
                    for _, row in top_stocks.iterrows():
                        analysis = analyst.analyze_stock(row.to_dict())
                        if analysis and not analysis.startswith('Error'):
                            detailed_analysis += f"""
                            <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                                        color: #f0f0f0; padding: 18px; margin: 15px 0; border-radius: 12px; 
                                        border-left: 5px solid #ffd700;">
                                <h4 style="color: #ffd700; margin-top: 0; margin-bottom: 10px; font-size: 18px;">
                                    📊 {row['Ticker']} - Senior Hedge Fund Analysis
                                </h4>
                                <div style="font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.7; color: #e0e0e0;">
                                    {analysis.replace(chr(10), '<br>')}
                                </div>
                                <div style="margin-top: 10px; font-size: 12px; color: #888; border-top: 1px solid #333; padding-top: 8px;">
                                    <span style="background-color: {'#ffc107' if 'BREAKOUT' in str(row.get('Patterns','')).upper() else '#27ae60'}; 
                                          color: {'#000' if 'BREAKOUT' in str(row.get('Patterns','')).upper() else '#fff'}; 
                                          padding: 2px 8px; border-radius: 12px; font-weight: bold;">
                                        RS: {row.get('RS', 'N/A')} | VCP: {row.get('VCP', 'N/A')}
                                    </span>
                                </div>
                            </div>
                            """
                    
                    # Gabungkan semua analisis
                    if breakout_analysis or detailed_analysis:
                        gemini_section = f"""
                        <div style="background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%); 
                                    color: white; padding: 25px; border-radius: 15px; margin: 25px 0;
                                    border: 2px solid #ffd700; box-shadow: 0 10px 20px rgba(0,0,0,0.3);">
                            <h3 style="color: #ffd700; margin-top: 0; margin-bottom: 20px; display: flex; align-items: center; font-size: 24px;">
                                <span style="font-size: 32px; margin-right: 15px;">🤖</span> 
                                GEMINI SENIOR HEDGE FUND ANALYST
                            </h3>
                            
                            {f'<div style="background: rgba(255,215,0,0.1); padding: 15px; border-radius: 10px; margin-bottom: 20px;">{breakout_analysis.replace(chr(10), "<br>")}</div>' if breakout_analysis else ''}
                            
                            {detailed_analysis}
                            
                            <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; margin-top: 20px;">
                                <p style="font-size: 12px; color: #aaa; margin: 0; font-style: italic;">
                                    ⚡ Analisis oleh Google Gemini 2.5 Flash • Gratis 60 RPM • Data real-time dari screener Minervini
                                </p>
                                <p style="font-size: 11px; color: #666; margin: 5px 0 0 0;">
                                    Disclaimer: Analisis AI bukan rekomendasi investasi. Selalu lakukan verifikasi manual.
                                </p>
                            </div>
                        </div>
                        """
                
                # Buat tabel HTML untuk ringkasan
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
                    
                    card_color = "#fff3cd" if is_breakout else "#f0f7ff"
                    border_color = "#ffc107" if is_breakout else "#27ae60"
                    badge = '<span style="background-color: #ffc107; color: #000; padding: 3px 10px; border-radius: 15px; font-size: 12px; margin-left: 10px;">🚀 BREAKOUT</span>' if is_breakout else ''
                    
                    trading_plans_html += f"""
                    <div style="background-color: {card_color}; padding: 20px; margin: 20px 0; border-left: 6px solid {border_color}; border-radius: 12px; box-shadow: 0 4px 8px rgba(0,0,0,0.05);">
                        <h4 style="margin-top: 0; color: #2c3e50; font-size: 20px; display: flex; align-items: center;">
                            📈 {ticker} - Trading Plan {badge}
                        </h4>
                        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                            <tr>
                                <td style="padding: 10px; width: 35%; background-color: rgba(0,0,0,0.02);"><strong>Entry Point:</strong></td>
                                <td style="padding: 10px; font-weight: bold;">{entry_str}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; background-color: rgba(0,0,0,0.02);"><strong>Stop Loss:</strong></td>
                                <td style="padding: 10px; color: #d32f2f; font-weight: bold;">{stop_str} (7% di bawah entry) ⚠️</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; background-color: rgba(0,0,0,0.02);"><strong>Target 1 (20%):</strong></td>
                                <td style="padding: 10px; color: #2e7d32; font-weight: bold;">{target1_str} → Jual 30-50%</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; background-color: rgba(0,0,0,0.02);"><strong>Target 2 (40%):</strong></td>
                                <td style="padding: 10px; color: #2e7d32; font-weight: bold;">{target2_str} → Trailing stop</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; background-color: rgba(0,0,0,0.02);"><strong>Risk/Reward:</strong></td>
                                <td style="padding: 10px;">1 : {risk_reward:.1f} (ideal ≥ 3)</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; background-color: rgba(0,0,0,0.02);"><strong>RS / VCP:</strong></td>
                                <td style="padding: 10px;">RS: {rs} | VCP: {vcp}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; background-color: rgba(0,0,0,0.02);"><strong>Chart Patterns:</strong></td>
                                <td style="padding: 10px; color: {'#d32f2f' if 'BREAKOUT' in patterns else '#27ae60'}; font-weight: 500;">
                                    {patterns}
                                </td>
                            </tr>
                        </table>
                    </div>
                    """
                
                # Body email lengkap
                body = f"""
                <html>
                <head>
                    <style>
                        body {{ 
                            font-family: 'Segoe UI', Roboto, Arial, sans-serif; 
                            margin: 0;
                            padding: 20px;
                            background-color: #f0f2f5;
                        }}
                        .container {{
                            max-width: 1100px;
                            margin: 0 auto;
                            background-color: white;
                            padding: 30px;
                            border-radius: 20px;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                        }}
                        h2 {{ 
                            color: #1a237e; 
                            border-bottom: 4px solid #27ae60; 
                            padding-bottom: 15px;
                            margin-top: 0;
                            font-size: 28px;
                        }}
                        h3 {{
                            color: #2c3e50;
                            margin-top: 30px;
                            margin-bottom: 15px;
                            font-size: 22px;
                        }}
                        .summary-box {{
                            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
                            color: white;
                            padding: 25px;
                            border-radius: 15px;
                            margin: 25px 0;
                            box-shadow: 0 5px 15px rgba(46, 204, 113, 0.3);
                        }}
                        .summary-box p {{
                            font-size: 18px;
                            margin: 8px 0;
                        }}
                        .criteria-box {{
                            background-color: #f8f9fa;
                            padding: 20px;
                            border-radius: 12px;
                            margin: 25px 0;
                            border-left: 5px solid #3498db;
                        }}
                        .criteria-list {{
                            display: grid;
                            grid-template-columns: repeat(2, 1fr);
                            gap: 12px;
                            list-style: none;
                            padding: 0;
                        }}
                        .criteria-list li {{
                            padding: 10px;
                            background-color: white;
                            border-radius: 8px;
                            border-left: 3px solid #3498db;
                            font-size: 14px;
                        }}
                        table {{ 
                            border-collapse: collapse; 
                            width: 100%;
                            margin: 25px 0;
                            font-size: 13px;
                            background-color: white;
                            border-radius: 12px;
                            overflow: hidden;
                            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
                        }}
                        th {{ 
                            background-color: #27ae60; 
                            color: white; 
                            padding: 15px;
                            text-align: left;
                            font-size: 14px;
                        }}
                        td {{ 
                            border: 1px solid #e0e0e0; 
                            padding: 12px; 
                        }}
                        tr:nth-child(even) {{ 
                            background-color: #f8f9fa; 
                        }}
                        tr:hover {{
                            background-color: #e8f5e9;
                        }}
                        .badge-8 {{
                            background-color: #27ae60;
                            color: white;
                            padding: 4px 12px;
                            border-radius: 20px;
                            font-weight: bold;
                            display: inline-block;
                            font-size: 12px;
                        }}
                        .badge-7 {{
                            background-color: #f39c12;
                            color: white;
                            padding: 4px 12px;
                            border-radius: 20px;
                            font-weight: bold;
                            display: inline-block;
                            font-size: 12px;
                        }}
                        .footer {{
                            margin-top: 40px;
                            padding-top: 20px;
                            border-top: 2px solid #e0e0e0;
                            text-align: center;
                            color: #7f8c8d;
                            font-size: 12px;
                        }}
                        .check-mark {{
                            color: #27ae60;
                            font-weight: bold;
                        }}
                        .x-mark {{
                            color: #e74c3c;
                            font-weight: bold;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h2>📈 MINERVINI SCREENER + GEMINI AI ANALYST</h2>
                        <p style="font-size: 16px; color: #555;">
                            <strong>Waktu Screening:</strong> {wib_time.strftime('%d-%m-%Y %H:%M:%S')} WIB
                        </p>
                        
                        <div class="summary-box">
                            <h3 style="color: white; margin-top: 0; margin-bottom: 15px;">📊 RINGKASAN</h3>
                            <p>✅ Total Saham 8/8: <strong style="font-size: 24px;">{total_8}</strong></p>
                            <p>🚀 Saham dengan Breakout: <strong style="font-size: 20px;">{breakout_count}</strong></p>
                        </div>
                        
                        {gemini_section}
                        
                        <div class="criteria-box">
                            <h3 style="margin-top: 0;">🎯 8 KRITERIA MINERVINI</h3>
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
                        <p style="font-size: 12px; color: #666;">
                            <span class="check-mark">✓</span> = Memenuhi kriteria | 
                            <span class="x-mark">✗</span> = Tidak memenuhi
                        </p>
                        {table_html}
                        
                        <h3>📊 TRADING PLAN DETAIL (8/8)</h3>
                        {trading_plans_html}
                        
                        <div class="footer">
                            <p>
                                <span style="background: #27ae60; color: white; padding: 3px 8px; border-radius: 12px;">🚀 BREAKOUT</span> = Harga mendekati resistance + Volume tinggi + Candle kuat<br>
                                <span style="background: #3498db; color: white; padding: 3px 8px; border-radius: 12px;">🤖 GEMINI AI</span> = Analisis oleh Google Gemini 2.5 Flash (gratis)
                            </p>
                            <p><i>Generated by Minervini Screener v12.0 • {wib_time.strftime('%d-%m-%Y %H:%M:%S')} WIB</i></p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                msg.attach(MIMEText(body, 'html'))
                
                # Lampirkan CSV
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
            <body style="font-family: Arial; background-color: #f5f5f5; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                    <h2 style="color: #2c3e50; border-bottom: 3px solid #e74c3c; padding-bottom: 10px;">📈 MINERVINI SCREENER</h2>
                    <p><strong>Waktu:</strong> {wib_time.strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                    <div style="background-color: #f8d7da; padding: 25px; border-radius: 10px; border-left: 5px solid #e74c3c;">
                        <h3 style="color: #721c24; margin-top: 0;">📭 TIDAK ADA HASIL SCREENING</h3>
                        <p style="color: #721c24;">Tidak ditemukan saham yang memenuhi kriteria 8/8 pada screening kali ini.</p>
                        <p style="color: #721c24; font-style: italic; margin-bottom: 0;">"Sit-out power - lebih baik tidak trading daripada memaksakan entry." - Mark Minervini</p>
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
        
        print("✅ EMAIL DENGAN GEMINI ANALYSIS BERHASIL DIKIRIM!")
        return True
        
    except Exception as e:
        print(f"❌ GAGAL KIRIM EMAIL: {e}")
        return False
