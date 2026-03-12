    # ============================================
    # FUNGSI PROCESS ONE TICKER (HANYA 8/8 YANG DISIMPAN)
    # ============================================
    def process_one_ticker(self, ticker, index, total):
        """Fungsi yang akan dijalankan oleh masing-masing thread"""
        result = None
        error_msg = None
        
        df, display_name, error = self.get_stock_data(ticker)
        
        if df is None:
            with self.lock:
                self.saham_error.append(display_name)
                self.request_count += 1
            return None, display_name, error
        
        with self.lock:
            self.saham_ok.append(display_name)
            self.request_count += 1
        
        is_liquid, avg_turnover = self.check_liquidity(df)
        if not is_liquid:
            return None, display_name, f"Likuiditas rendah"
        
        try:
            # Hitung indikator teknikal
            price = df['Close'].iloc[-1]
            ma50 = df['Close'].rolling(50).mean().iloc[-1]
            ma150 = df['Close'].rolling(150).mean().iloc[-1] if len(df) >= 150 else price
            ma200 = df['Close'].rolling(200).mean().iloc[-1] if len(df) >= 200 else price
            
            if len(df) >= 200:
                ma200_22 = df['Close'].rolling(200).mean().iloc[-22] if len(df) >= 222 else ma200
            else:
                ma200_22 = ma200
            
            low_52 = df['Low'].tail(200).min()
            high_52 = df['High'].tail(200).max()
            
            # RS Rating (2 digit)
            rs_score = self.calculate_relative_strength(df)
            
            # VCP Score
            vcp_total, vcp_tight, vcp_vol = self.calculate_vcp_score(df)
            
            # ===== DETEKSI POLA CHART =====
            patterns_str = self.detect_chart_patterns(df)
            
            # Evaluasi kriteria
            c1 = price > ma150 and price > ma200 if not pd.isna(ma150) and not pd.isna(ma200) else False
            c2 = ma150 > ma200 if not pd.isna(ma150) and not pd.isna(ma200) else False
            c3 = ma200 > ma200_22 if not pd.isna(ma200) and not pd.isna(ma200_22) else False
            c4 = ma50 > ma150 and ma50 > ma200 if not pd.isna(ma50) and not pd.isna(ma150) and not pd.isna(ma200) else False
            c5 = price > ma50 if not pd.isna(ma50) else False
            c6 = price > (low_52 * 1.30) if low_52 > 0 else False
            c7 = price > (high_52 * 0.75) if high_52 > 0 else False
            c8 = rs_score > 70
            
            conditions = [c1, c2, c3, c4, c5, c6, c7, c8]
            score = sum(conditions)
            
            pct_from_low = ((price / low_52) - 1) * 100 if low_52 > 0 else 0
            pct_from_high = (1 - (price / high_52)) * 100 if high_52 > 0 else 0
            
            # Hitung Risk/Reward Ratio
            rr_ratio = self.calculate_risk_reward(price)
            
            # Hanya simpan jika score == 8 (8/8)
            if score == 8:
                # Buat entry price untuk keterangan
                entry_price = int(price)
                
                # Format harga untuk keterangan (tanpa Rp, angka saja)
                entry_str = f"{entry_price:,}".replace(',', '.')
                
                # ===== BUAT KETERANGAN UNTUK GOOGLE SHEETS =====
                # Format dasar
                keterangan = f"Minervini 8/8 VCP:{vcp_total} RS:{rs_score} | Entry: {entry_str}"
                
                # TAMBAHKAN PATTERN JIKA ADA (sama persis dengan yang di email)
                if patterns_str and patterns_str.strip() and patterns_str != "":
                    keterangan += f" | {patterns_str}"
                
                # Buat result - HANYA UNTUK 8/8
                result = {
                    'Ticker': display_name,
                    'Harga': f"Rp {entry_price:,}".replace(',', '.'),
                    'Status': '8/8',
                    'RS': rs_score,
                    'VCP': vcp_total,
                    'Patterns': patterns_str,  # Untuk email
                    'RR_Ratio': rr_ratio,
                    'Turnover_M': f"{avg_turnover/1e6:.1f}M",
                    'Low': f"{pct_from_low:.1f}%",
                    'High': f"{pct_from_high:.1f}%",
                    'Keterangan': keterangan,  # Untuk Google Sheets (SUDAH include pattern)
                    'C1': '✓' if c1 else '✗',
                    'C2': '✓' if c2 else '✗',
                    'C3': '✓' if c3 else '✗',
                    'C4': '✓' if c4 else '✗',
                    'C5': '✓' if c5 else '✗',
                    'C6': '✓' if c6 else '✗',
                    'C7': '✓' if c7 else '✗',
                    'C8': '✓' if c8 else '✗',
                }
                
                with self.lock:
                    self.saham_lolos += 1
                
                return result, display_name, None
            else:
                # Tidak simpan untuk 7/8 atau di bawahnya
                return None, display_name, f"Tidak lolos ({score}/8)"
            
        except Exception as e:
            return None, display_name, f"Error: {str(e)[:50]}"
