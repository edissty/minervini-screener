import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

def send_email_report(df, email_to, email_from, password, criteria, smtp_server='smtp.gmail.com', port=587):
    """
    Mengirim laporan hasil screening ke email dengan panduan trading ala Minervini
    """
    print("\n" + "=" * 50)
    print("📧 PROSES KIRIM EMAIL")
    print("=" * 50)
    
    try:
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = f"📊 Minervini Screener + Trading Guide - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
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
                
                # Hitung harga entry, stop loss, target berdasarkan aturan Minervini [citation:2][citation:4]
                # Asumsi harga dalam format "Rp 2.5K" atau "Rp 2,500"
                harga_clean = str(harga).replace('Rp ', '').replace('K', '000').replace(',', '')
                try:
                    if 'K' in str(harga):
                        harga_numeric = float(harga_clean.replace('K', '')) * 1000
                    else:
                        harga_numeric = float(harga_clean)
                    
                    # Entry bisa di harga saat ini atau sedikit di bawah
                    entry_price = harga_numeric
                    
                    # Stop loss 7-8% di bawah entry [citation:2][citation:4]
                    stop_loss = entry_price * 0.93  # 7% di bawah
                    
                    # Target 1: 20-30% (take profit sebagian) [citation:5]
                    target1 = entry_price * 1.20
                    
                    # Target 2: 50% (jika kuat) [citation:5]
                    target2 = entry_price * 1.50
                    
                    # Format untuk tampilan
                    if entry_price >= 1000:
                        entry_str = f"Rp {entry_price/1000:.1f}K"
                        stop_str = f"Rp {stop_loss/1000:.1f}K"
                        target1_str = f"Rp {target1/1000:.1f}K"
                        target2_str = f"Rp {target2/1000:.1f}K"
                    else:
                        entry_str = f"Rp {entry_price:,.0f}"
                        stop_str = f"Rp {stop_loss:,.0f}"
                        target1_str = f"Rp {target1:,.0f}"
                        target2_str = f"Rp {target2:,.0f}"
                    
                except:
                    entry_str = harga
                    stop_str = "-"
                    target1_str = "-"
                    target2_str = "-"
                
                trading_guide_html += f"""
                <div style="background-color: #f0f7ff; padding: 15px; margin: 10px 0; border-left: 5px solid #3498db; border-radius: 5px;">
                    <h4 style="margin-top: 0; color: #2c3e50;">📈 {ticker} - Trading Plan</h4>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; width: 30%;"><strong>Entry Point:</strong></td>
                            <td style="padding: 8px;">{entry_str} (harga saat ini atau saat breakout) [citation:2]</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;"><strong>Stop Loss:</strong></td>
                            <td style="padding: 8px;">{stop_str} (7-8% di bawah entry) ⚠️ [citation:2][citation:4]</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;"><strong>Target 1 (20%):</strong></td>
                            <td style="padding: 8px;">{target1_str} → Jual 30-50% posisi [citation:5]</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;"><strong>Target 2 (50%):</strong></td>
                            <td style="padding: 8px;">{target2_str} → Trailing stop untuk sisa posisi</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;"><strong>Risk/Reward:</strong></td>
                            <td style="padding: 8px;">1 : {((target1/entry_price-1)*100/((entry_price-stop_loss)/entry_price*100)):.1f} (minimal 2:1 ideal) [citation:8]</td>
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
                    h3 {{ color: #34495e; margin-top: 25px; }}
                    .summary {{ background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #3498db; }}
                    .criteria-box {{ background-color: #f0f7ff; padding: 20px; border-radius: 10px; margin: 20px 0; border: 1px solid #bde0fe; }}
                    .criteria-list {{ columns: 2; list-style-type: none; padding: 0; }}
                    .criteria-list li {{ margin: 10px 0; padding: 8px; background-color: white; border-radius: 5px; border-left: 3px solid #3498db; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; font-size: 14px; box-shadow: 0 2px 3px rgba(0,0,0,0.1); }}
                    th {{ background-color: #3498db; color: white; padding: 12px; text-align: left; }}
                    td {{ border: 1px solid #ddd; padding: 10px; }}
                    tr:nth-child(even) {{ background-color: #f8f9fa; }}
                    .badge-8 {{ background-color: #27ae60; color: white; padding: 3px 10px; border-radius: 15px; font-weight: bold; display: inline-block; }}
                    .badge-7 {{ background-color: #f39c12; color: white; padding: 3px 10px; border-radius: 15px; font-weight: bold; display: inline-block; }}
                    .rules {{ background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                    .footer {{ margin-top: 30px; font-size: 12px; color: #7f8c8d; border-top: 1px solid #eee; padding-top: 15px; text-align: center; }}
                </style>
            </head>
            <body>
                <h2>📈 MINERVINI STOCK SCREENER + TRADING GUIDE</h2>
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
                
                <h3>📊 TRADING PLAN - LANGKAH SELANJUTNYA</h3>
                <p>Berdasarkan aturan Minervini, berikut panduan entry, stop loss, dan target untuk setiap saham:</p>
                
                {trading_guide_html}
                
                <div class="rules">
                    <h4>⚠️ 10 Aturan Emas Minervini [citation:1][citation:6]</h4>
                    <ol>
                        <li><strong>Gunakan stop loss SETIAP saat</strong> - jangan pernah entry tanpa stop loss</li>
                        <li><strong>Tentukan stop loss SEBELUM entry</strong> - bukan setelah membeli</li>
                        <li><strong>Jangan pernah merata-rata posisi rugi (averaging down)</strong> [citation:1]</li>
                        <li><strong>Jangan biarkan profit besar berubah jadi rugi</strong> - trailing stop</li>
                        <li><strong>Risiko maksimal 1-2% dari total modal per trade</strong> [citation:2]</li>
                        <li><strong>Jual saat menguat, bukan saat melemah</strong> [citation:6]</li>
                        <li><strong>Fokus pada 4-8 posisi terbaik, jangan terlalu diversifikasi</strong> [citation:6]</li>
                        <li><strong>Lakukan post-analysis rutin</strong> - pelajari pola winner & loser [citation:6]</li>
                        <li><strong>Konsisten dengan gaya trading - jangan ganti-ganti strategi</strong> [citation:6]</li>
                        <li><strong>Sit-out power</strong> - mampu tidak trading saat tidak ada setup bagus [citation:6]</li>
                    </ol>
                </div>
                
                <div class="rules" style="background-color: #e8f4fd;">
                    <h4>📌 Strategi Entry & Exit Minervini [citation:2][citation:5]</h4>
                    <ul>
                        <li><strong>Entry:</strong> Tunggu breakout dengan volume >150% rata-rata</li>
                        <li><strong>Stop Loss:</strong> 7-8% dari harga entry (WAJIB!)</li>
                        <li><strong>Take Profit 1 (20-30%):</strong> Jual 30-50% posisi, trailing stop sisanya</li>
                        <li><strong>Take Profit 2 (50%+):</strong> Gunakan trailing stop (MA10 atau MA20)</li>
                        <li><strong>Time Stop:</strong> Jika dalam 4-8 minggu tidak progres, exit [citation:2]</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p><i>Disclaimer: Screening ini menggunakan data Yahoo Finance. Harga entry dan stop loss adalah estimasi. Selalu lakukan analisis sendiri dan sesuaikan dengan modal Anda.</i></p>
                    <p><i>Risk Management: Jangan pernah risiko >2% modal per trade. Untuk modal Rp 100jt, risiko maksimal Rp 2jt per trade.</i></p>
                    <p>Generated by Minervini Screener GitHub Actions • {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</p>
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
            # Email ketika tidak ada hasil (tetap kasih panduan umum)
            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h2 {{ color: #2c3e50; }}
                    .no-results {{ background-color: #f8d7da; padding: 20px; border-radius: 10px; }}
                </style>
            </head>
            <body>
                <h2>📈 MINERVINI STOCK SCREENER</h2>
                <p><strong>Waktu Screening:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} WIB</p>
                
                <div class="no-results">
                    <h3>📭 TIDAK ADA HASIL SCREENING</h3>
                    <p>Tidak ditemukan saham yang memenuhi kriteria 7/8 atau 8/8 pada screening kali ini.</p>
                    <p>Tetaap patuhi aturan Minervini: "Sit-out power" - lebih baik tidak trading daripada memaksakan entry di saham yang tidak memenuhi kriteria. [citation:1]</p>
                </div>
            </body>
            </html>
            """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Kirim email
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(email_from, password)
        server.send_message(msg)
        server.quit()
        
        print("✅ EMAIL DENGAN TRADING GUIDE BERHASIL DIKIRIM!")
        return True
        
    except Exception as e:
        print(f"❌ GAGAL KIRIM EMAIL: {e}")
        return False
