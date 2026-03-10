# ============================================
# FUNGSI PROCESS ONE TICKER (DENGAN RS_RATING LENGKAP)
# ============================================
def process_one_ticker(self, ticker, index, total):
    """Fungsi yang akan dijalankan oleh masing-masing thread"""
    result = None
    error_msg = None
    
    # Ambil data
    df, display_name, error = self.get_stock_data(ticker)
    
    if df is None:
        with self.lock:
            self.saham_error.append(display_name)
            self.request_count += 1
        return None, display_name, error
    
    with self.lock:
        self.saham_ok.append(display_name)
        self.request_count += 1
    
    # Cek likuiditas
    is_liquid, avg_turnover = self.check_liquidity(df)
    if not is_liquid:
        return None, display_name, f"Likuiditas rendah: Rp {avg_turnover/1e6:.1f}M"
    
    # Hitung indikator
    price = df['Close'].iloc[-1]
    ma50 = df['Close'].rolling(50).mean().iloc[-1]
    ma150 = df['Close'].rolling(150).mean().iloc[-1]
    ma200 = df['Close'].rolling(200).mean().iloc[-1]
    
    if len(df) >= 222:
        ma200_22 = df['Close'].rolling(200).mean().iloc[-22]
    else:
        ma200_22 = ma200
    
    low_52 = df['Low'].tail(252).min()
    high_52 = df['High'].tail(252).max()
    
    # ===== RS RATIO (Perbandingan vs IHSG) =====
    rs_ratio, rs_score = self.calculate_rs_rating(df)
    
    # Jika masih 0, paksa ke nilai default
    if rs_ratio == 0:
        rs_ratio = 1.0
        rs_score = 50.0
    
    # ===== ANALISIS RS UNTUK DEBUG =====
    # Hitung return 3 bulan dan 6 bulan untuk analisis
    ret_3m = ((price / df['Close'].iloc[-63]) - 1) * 100 if len(df) > 63 else 0
    ret_6m = ((price / df['Close'].iloc[-126]) - 1) * 100 if len(df) > 126 else 0
    
    # Bandingkan dengan IHSG (jika ada)
    ihsg_perf_3m = 0
    ihsg_perf_6m = 0
    if self.index_data is not None and len(self.index_data) > 126:
        try:
            ihsg_price = self.index_data['Close'].iloc[-1]
            ihsg_3m = self.index_data['Close'].iloc[-63] if len(self.index_data) > 63 else ihsg_price
            ihsg_6m = self.index_data['Close'].iloc[-126] if len(self.index_data) > 126 else ihsg_price
            ihsg_perf_3m = ((ihsg_price / ihsg_3m) - 1) * 100
            ihsg_perf_6m = ((ihsg_price / ihsg_6m) - 1) * 100
        except:
            pass
    
    # Buat analisis RS
    rs_analysis = f"3m:{ret_3m:.1f}% vs IHSG {ihsg_perf_3m:.1f}% | 6m:{ret_6m:.1f}% vs IHSG {ihsg_perf_6m:.1f}%"
    
    # ===== KONVERSI KE RS RATING (0-99) =====
    # Ini akan di-update setelah semua saham diproses
    # Tapi untuk sementara, kita gunakan rs_score
    rs_rating = rs_score  # Sementara pakai rs_score
    
    # VCP Score
    vcp_total, vcp_tight, vcp_vol = self.calculate_vcp_score(df)
    
    # Evaluasi kriteria
    c1 = price > ma150 and price > ma200
    c2 = ma150 > ma200
    c3 = ma200 > ma200_22 if len(df) >= 222 else False
    c4 = ma50 > ma150 and ma50 > ma200
    c5 = price > ma50
    c6 = price > (low_52 * 1.30) if low_52 > 0 else False
    c7 = price > (high_52 * 0.75) if high_52 > 0 else False
    
    # C8: Relative Strength (menggunakan rs_rating > 70)
    c8 = rs_rating > 70
    
    conditions = [c1, c2, c3, c4, c5, c6, c7, c8]
    score = sum(conditions)
    
    pct_from_low = ((price / low_52) - 1) * 100 if low_52 > 0 else 0
    pct_from_high = (1 - (price / high_52)) * 100 if high_52 > 0 else 0
    
    # Buat result dengan RS_Rating dan Analisis
    result = {
        'Ticker': display_name,
        'Harga': f"Rp {int(price):,}".replace(',', '.'),
        'Skor': f"{score}/8",
        'Status': '8/8' if score == 8 else '7/8',
        # ===== TAMBAHKAN INI =====
        'RS_Ratio': f"{rs_ratio:.3f}",
        'RS_Rating': f"{rs_rating:.1f}",
        'RS_Analysis': rs_analysis,  # Analisis detail kenapa RS tertentu
        # =========================
        'VCP': vcp_total,
        'Turnover_M': f"{avg_turnover/1e6:.1f}M",
        'Low': f"{pct_from_low:.1f}%",
        'High': f"{pct_from_high:.1f}%",
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
        if score >= 7:
            self.saham_lolos += 1
    
    return result, display_name, None


# ============================================
# FUNGSI UNTUK KALIBRASI RS_RATING (POST-PROCESSING)
# ============================================
def calibrate_rs_ratings(self, results_df):
    """
    Kalibrasi RS_Rating berdasarkan percentile dari semua RS_Ratio
    Ini akan membuat RS_Rating lebih akurat (0-99)
    """
    if results_df is None or results_df.empty:
        return results_df
    
    # Ambil semua RS_Ratio
    all_ratios = []
    for _, row in results_df.iterrows():
        try:
            ratio = float(row['RS_Ratio']) if row['RS_Ratio'] else 1.0
            all_ratios.append(ratio)
        except:
            all_ratios.append(1.0)
    
    if not all_ratios:
        return results_df
    
    # Urutkan untuk percentile
    all_ratios.sort()
    
    # Hitung percentile untuk setiap saham
    new_ratings = []
    for _, row in results_df.iterrows():
        try:
            ratio = float(row['RS_Ratio'])
            # Hitung berapa banyak yang lebih kecil
            less_than = sum(1 for r in all_ratios if r < ratio)
            total = len(all_ratios)
            percentile = (less_than / total) * 99
            percentile = max(1, min(99, round(percentile, 1)))
            new_ratings.append(percentile)
        except:
            new_ratings.append(50.0)
    
    # Update kolom RS_Rating
    results_df['RS_Rating'] = new_ratings
    
    # Update C8 berdasarkan RS_Rating baru
    results_df['C8'] = results_df['RS_Rating'].apply(lambda x: '✓' if x > 70 else '✗')
    
    return results_df


# ============================================
# FUNGSI SCREEN (DIPERBAIKI DENGAN CALIBRATION)
# ============================================
def screen(self, tickers):
    """
    Fungsi utama screening dengan multithreading
    """
    # ... (kode awal sama sampai results terkumpul) ...
    
    # Buat DataFrame hasil
    if self.results:
        df_results = pd.DataFrame(self.results)
        
        # Kalibrasi RS_Rating
        df_results = self.calibrate_rs_ratings(df_results)
        
        # Pilih kolom untuk output
        output_cols = [
            'Ticker', 'Harga', 'Skor', 'Status', 
            'RS_Ratio', 'RS_Rating', 'RS_Analysis',  # TAMBAHKAN INI
            'VCP', 'Turnover_M', 'Low', 'High',
            'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8'
        ]
        df_results = df_results[output_cols]
        
        # Urutkan
        df_results = df_results.sort_values(
            ['Skor', 'RS_Rating', 'VCP'], 
            ascending=[False, False, False]
        )
    else:
        df_results = pd.DataFrame()
    
    # ... (sisa kode sama) ...
    
    return df_results
