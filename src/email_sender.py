import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

def send_email_report(df, email_to, email_from, password, criteria, smtp_server='smtp.gmail.com', port=587):
    """
    Mengirim laporan hasil screening ke email dengan panduan trading ala Minervini + POLA CHART
    """
    print("\n" + "=" * 50)
    print("📧 PROSES KIRIM EMAIL")
    print("=" * 50)
    
    try:
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = f"📊 Minervini Screener + Chart Patterns - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        if df is not None and not df.empty:
            total_8 = len(df[df['Status'] == '8/8']) if 'Status' in df.columns else 0
            total_7 = len(df[df['Status'] == '7/8']) if 'Status' in df.columns else 0
            
            table_html = df.to_html(index=False, escape=False)
            
            # Tambahkan panduan trading untuk setiap saham
            trading_guide_html = ""
            for idx, row in df.iterrows():
                ticker = row['Ticker']
                harga = row['Harga']
                rs = row['RS'] if 'RS' in row else '70'
                vcp = row['VCP'] if 'VCP' in row else 'N/A'
                patterns = row['Patterns'] if 'Patterns' in row else 'Tidak ada pola'
                rr = row['RR_Ratio'] if 'RR_Ratio' in row else '2.86'
                
                # Parsing harga
                try:
                    harga_clean = str(harga).replace('Rp ', '').replace('.', '')
                    harga_numeric = float(harga_clean)
                    
                    entry_price = harga_numeric
                    stop_loss = entry_price * 0.93  # 7% stop loss
                    target1 = entry_price * 1.20
                    target2 = entry_price * 1.40
                    
                    risk = entry_price - stop_loss
                    reward = target1 - entry_price
                    risk_reward = reward / risk if risk > 0 else 0
                    
                    entry_str = f"Rp {entry_price:,.0f}".replace(',', '.')
                    stop_str = f"Rp {stop_loss:,.0f}".replace(',', '.')
                    target1_str = f"Rp {target1:,.0f}".replace(',', '.')
                    target2_str = f"Rp {target2:,.0f}".replace(',', '.')
                    
                except Exception as e:
                    entry_str = harga
                    stop_str = "-"
                    target1_str = "-"
                    target2_str = "-"
                    risk_reward = 0
                
                trading_guide_html += f"""
                <div style="background-color: #f0f7ff; padding: 15px; margin: 10px 0; border-left: 5px solid #3498db; border-radius: 5px;">
                    <h4 style="margin-top: 0; color: #2c3e50;">📈 {ticker} - Trading Plan</h4>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; width: 30%;"><strong>Entry Point:</strong></td>
                            <td style="padding: 8px;">{entry_str} (harga saat ini)</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;"><strong>Stop Loss:</strong></td>
                            <td style="padding: 8px;">{stop_str} (7% di bawah entry) ⚠️</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;"><strong>Target 1 (20%):</strong></td>
                            <td style="padding: 8px;">{target1_str} → Jual 30-50% posisi</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;"><strong>Target 2 (40%):</strong></td>
                            <td style="padding: 8px;">{target2_str} → Trailing stop</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;"><strong>Risk/Reward:</strong></td>
                            <td style="padding: 8px;">1 : {risk_reward:.1f} (minimal 2:1 ideal)</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;"><strong>VCP Score:</strong></td>
                            <td style="padding: 8px;">{vcp} / 100 (≥70 sangat baik)</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;"><strong>Chart Patterns:</strong></td>
                            <td style="padding: 8px; color: {'green' if patterns != 'Tidak ada pola' else 'gray'};">
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
                    body {{ font-family: Arial, sans-serif; margin: 20px; color: #333; }}
                    h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                    .summary {{ background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #3498db; }}
                    .criteria-box {{ background-color: #f0f7ff; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    th {{ background-color: #3498db; color: white; padding: 12px; }}
                    td {{ border: 1px solid #ddd; padding: 10px; }}
                    .badge-8 {{ background-color: #27ae60; color: white; padding: 3px 10px; border-radius: 15px; }}
                    .badge-7 {{ background-color: #f39c12; color: white; padding: 3px 10px; border-radius: 15px; }}
                    .pattern-tag {{
                        display: inline-block;
                        background-color: #e1f5fe;
                        color: #0277bd;
                        padding: 3px 8px;
                        border-radius: 12px;
                        font-size: 11px;
                        margin: 2px;
                    }}
                </style>
            </head>
            <body>
                <h2>📈 MINERVINI SCREENER + CHART PATTERNS</h2>
                <p><strong>Waktu Screening:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                
                <div class="summary">
                    <h3>📊 RINGKASAN HASIL</h3>
                    <ul>
                        <li>Total Saham Lolos: <strong>{len(df)}</strong></li>
                        <li>Saham <span class="badge-8">8/8</span>: <strong>{total_8}</strong></li>
                        <li>Saham <span class="badge-7">7/8</span>: <strong>{total_7}</strong></li>
                    </ul>
                </div>
                
                <div class="criteria-box">
                    <h3>🎯 8 KRITERIA MINERVINI</h3>
                    <ul style="columns: 2;">
                        <li><strong>C1:</strong> Harga > MA150 & MA200</li>
                        <li><strong>C2:</strong> MA150 > MA200</li>
                        <li><strong>C3:</strong> MA200 Menanjak (1 bulan)</li>
                        <li><strong>C4:</strong> MA50 > MA150 & MA200</li>
                        <li><strong>C5:</strong> Harga > MA50</li>
                        <li><strong>C6:</strong> Harga > 30% dari 52-Week Low</li>
                        <li><strong>C7:</strong> Harga dalam 25% dari 52-Week High</li>
                        <li><strong>C8:</strong> Relative Strength > 70</li>
                    </ul>
                </div>
                
                <h3>📋 DETAIL SAHAM LOLOS SCREENING</h3>
                <p><small>✓ = Memenuhi kriteria | ✗ = Tidak memenuhi</small></p>
                {table_html}
                
                <h3>📊 TRADING PLAN + CHART PATTERNS</h3>
                {trading_guide_html}
                
                <div style="margin-top: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 5px;">
                    <h4>📌 Interpretasi Chart Patterns:</h4>
                    <ul>
                        <li><span class="pattern-tag">VCP Kuat</span> - Volatility Contraction Pattern, siap breakout</li>
                        <li><span class="pattern-tag">Support/Resistance</span> - Level harga penting</li>
                        <li><span class="pattern-tag">Uptrend</span> - Higher highs, higher lows</li>
                        <li><span class="pattern-tag">Perfect Order</span> - MA20 > MA50 > MA150 > MA200</li>
                        <li><span class="pattern-tag">Breakout Signal</span> - Harga breakout dengan volume tinggi</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p><i>Disclaimer: Analisis pola chart otomatis mungkin tidak 100% akurat. Selalu lakukan verifikasi manual.</i></p>
                    <p>Generated by Minervini Screener v6.0 • {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</p>
                </div>
            </body>
            </html>
            """
            
            # Lampirkan CSV
            csv_data = df.to_csv(index=False)
            attachment = MIMEApplication(csv_data.encode('utf-8'))
            attachment.add_header('Content-Disposition', 'attachment', 
                                filename=f"minervini_screening_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
            msg.attach(attachment)
            
        else:
            body = f"""
            <html>
            <body>
                <h2>📈 MINERVINI SCREENER</h2>
                <p><strong>Waktu Screening:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                <div style="background-color: #f8d7da; padding: 20px; border-radius: 10px;">
                    <h3>📭 TIDAK ADA HASIL SCREENING</h3>
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
        
        print("✅ EMAIL DENGAN CHART PATTERNS BERHASIL DIKIRIM!")
        return True
        
    except Exception as e:
        print(f"❌ GAGAL KIRIM EMAIL: {e}")
        return False
