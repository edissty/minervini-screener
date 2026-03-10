# ============================================
# FUNGSI RS RATING YANG DIPERBAIKI
# ============================================
def calculate_rs_rating(self, stock_df):
    """
    RS Rating dengan multiple timeframe (12m, 6m, 3m, 1m)
    Return: (rs_ratio, rs_score_0_100)
    """
    # Jika tidak ada data IHSG, return default
    if self.index_data is None or stock_df is None or len(stock_df) < 100:
        return 1.0, 50  # Default netral
    
    try:
        # Pastikan index_data sudah difetch
        if self.index_data is None or self.index_data.empty:
            self.logger.warning("⚠️ Data IHSG tidak tersedia, menggunakan fallback")
            return 1.0, 50
        
        # Sinkronisasi tanggal - ambil periode yang sama
        # Gunakan data 1 tahun terakhir
        end_date = stock_df.index[-1]
        start_date = end_date - timedelta(days=365)
        
        # Filter IHSG untuk periode yang sama
        idx_filtered = self.index_data[(self.index_data.index >= start_date) & 
                                       (self.index_data.index <= end_date)]
        
        if len(idx_filtered) < 50:
            self.logger.debug(f"Data IHSG tidak cukup: {len(idx_filtered)}")
            return 1.0, 50
        
        # Ambil harga saham untuk periode yang sama
        stock_filtered = stock_df[stock_df.index.isin(idx_filtered.index)]
        
        if len(stock_filtered) < 50:
            return 1.0, 50
        
        # Hitung return untuk berbagai periode dalam 1 tahun
        # Periode: 1, 3, 6, 12 bulan
        periods = [21, 63, 126, 252]
        weights = [0.1, 0.2, 0.3, 0.4]
        
        stock_perf = 0
        index_perf = 0
        
        for period, weight in zip(periods, weights):
            if len(stock_filtered) > period and len(idx_filtered) > period:
                # Return saham
                s_ret = (stock_filtered['Close'].iloc[-1] / stock_filtered['Close'].iloc[-period] - 1)
                # Return IHSG
                i_ret = (idx_filtered['Close'].iloc[-1] / idx_filtered['Close'].iloc[-period] - 1)
                
                # Weighted return
                stock_perf += (1 + s_ret) * weight
                index_perf += (1 + i_ret) * weight
        
        # Hindari division by zero
        if index_perf <= 0:
            rs_ratio = 1.0
        else:
            rs_ratio = stock_perf / index_perf
        
        # Batasi rs_ratio antara 0.5 dan 2.0 untuk menghindari outlier
        rs_ratio = max(0.5, min(2.0, rs_ratio))
        
        # Konversi ke skala 0-100
        # 1.0 = 50, 1.5 = 75, 2.0 = 100
        rs_score = 50 + (rs_ratio - 1.0) * 50
        rs_score = max(1, min(99, rs_score))
        
        return round(rs_ratio, 3), round(rs_score, 1)
        
    except Exception as e:
        self.logger.debug(f"Error RS Rating: {e}")
        return 1.0, 50  # Return netral jika error


# ============================================
# FUNGSI FETCH IHSG YANG DIPERBAIKI
# ============================================
def fetch_ihsg_data(self, force_refresh=False):
    """Mengambil data IHSG dengan multiple fallback"""
    if self.index_data is not None and not force_refresh:
        self.logger.info("📊 Menggunakan data IHSG dari cache")
        return self.index_data
    
    self.logger.info("📊 Mengambil data benchmark IHSG (^JKSE)...")
    max_retries = 3
    
    # Beberapa opsi ticker untuk IHSG
    ihsg_tickers = ["^JKSE", "JKSE", "IDX:COMPOSITE"]
    
    for ticker in ihsg_tickers:
        for attempt in range(max_retries):
            try:
                session = requests.Session()
                session.impersonate = "chrome120"
                
                self.logger.info(f"   Mencoba {ticker}...")
                self.index_data = yf.download(
                    ticker, 
                    period="2y", 
                    interval="1d", 
                    progress=False,
                    session=session
                )
                
                if self.index_data is not None and not self.index_data.empty:
                    self.logger.info(f"✅ Data IHSG berhasil dimuat dari {ticker} ({len(self.index_data)} data points)")
                    return self.index_data
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 * (attempt + 1)
                    time.sleep(wait)
                else:
                    self.logger.warning(f"❌ Gagal dengan {ticker}: {str(e)[:50]}")
    
    # Jika semua gagal, buat data dummy berdasarkan saham-saham besar
    self.logger.warning("⚠️ Menggunakan data IHSG sintetis (fallback)")
    self.index_data = self.create_synthetic_ihsg()
    return self.index_data


# ============================================
# FUNGSI MEMBUAT IHSG SINTETIS (FALLBACK)
# ============================================
def create_synthetic_ihsg(self):
    """Membuat data IHSG sintetis dari saham-saham LQ45"""
    self.logger.info("📊 Membuat data IHSG sintetis dari saham blue chip...")
    
    # Daftar saham blue chip untuk sintesis IHSG
    bluechips = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK"]
    
    all_prices = []
    for ticker in bluechips:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y")
            if not df.empty:
                # Normalisasi ke 100 di awal periode
                df['Normalized'] = df['Close'] / df['Close'].iloc[0] * 100
                all_prices.append(df['Normalized'])
        except:
            continue
    
    if all_prices:
        # Rata-rata dari semua saham
        synthetic = pd.concat(all_prices, axis=1).mean(axis=1)
        synthetic_df = pd.DataFrame({'Close': synthetic.values}, index=synthetic.index)
        self.logger.info(f"✅ Data IHSG sintetis dibuat dengan {len(synthetic_df)} data points")
        return synthetic_df
    
    return None


# ============================================
# FUNGSI PROCESS ONE TICKER (DIPERBAIKI)
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
    
    # RS dan VCP - dengan fallback jika IHSG tidak ada
    rs_ratio, rs_score = self.calculate_rs_rating(df)
    vcp_total, vcp_tight, vcp_vol = self.calculate_vcp_score(df)
    
    # Evaluasi kriteria dengan toleransi
    c1 = price > ma150 and price > ma200
    c2 = ma150 > ma200
    c3 = ma200 > ma200_22 if len(df) >= 222 else False
    c4 = ma50 > ma150 and ma50 > ma200
    c5 = price > ma50
    c6 = price > (low_52 * 1.30) if low_52 > 0 else False
    c7 = price > (high_52 * 0.75) if high_52 > 0 else False
    
    # C8: Relative Strength dengan ambang batas yang lebih realistis
    # Untuk IHSG, RS_Ratio > 1.05 dianggap outperform
    # Untuk data sintetis, gunakan threshold yang berbeda
    if self.index_data is not None and len(self.index_data) > 100:
        # Data IHSG real atau sintetis
        c8 = rs_ratio > 1.03  # Outperform 3% lebih baik dari IHSG
    else:
        # Fallback: gunakan return absolut
        returns_3m = (price / df['Close'].iloc[-63] - 1) * 100 if len(df) > 63 else 0
        c8 = returns_3m > 5  # Return 3 bulan > 5% dianggap bagus
    
    conditions = [c1, c2, c3, c4, c5, c6, c7, c8]
    score = sum(conditions)
    
    pct_from_low = ((price / low_52) - 1) * 100 if low_52 > 0 else 0
    pct_from_high = (1 - (price / high_52)) * 100 if high_52 > 0 else 0
    
    # Format C8 untuk output
    c8_symbol = '✓' if c8 else '✗'
    
    # Buat result
    result = {
        'Ticker': display_name,
        'Harga': int(price),
        'Harga_Str': f"Rp {int(price):,}".replace(',', '.'),
        'Skor': f"{score}/8",
        'Status': '8/8' if score == 8 else '7/8',
        'RS_Ratio': rs_ratio,
        'RS_Score': rs_score,
        'VCP': vcp_total,
        'Turnover': avg_turnover,
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
        'C8': c8_symbol,
    }
    
    with self.lock:
        if score >= 7:
            self.saham_lolos += 1
    
    return result, display_name, None


# ============================================
# FUNGSI FETCH IHSG DI __init__ (PASTIKAN ADA)
# ============================================
def __init__(self, min_turnover=500_000_000, max_workers=20, log_level=logging.INFO):
    # ... kode yang sudah ada ...
    
    self.index_data = None
    
    # Langsung fetch IHSG saat inisialisasi
    try:
        self.fetch_ihsg_data()
    except:
        self.logger.warning("⚠️ Gagal fetch IHSG saat init, akan dicoba ulang nanti")
