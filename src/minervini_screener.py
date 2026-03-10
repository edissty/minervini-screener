# ============================================
# FUNGSI RS RATING YANG DIPERBAIKI - LEBIH FLEKSIBEL
# ============================================
def calculate_rs_rating(self, stock_df):
    """
    RS Rating - Lebih fleksibel dalam mencari tanggal yang cocok
    """
    # PASTIKAN data IHSG ada
    if not self.index_fetched or self.index_data is None:
        self.logger.error("Data IHSG tidak tersedia")
        return None, None
    
    if stock_df is None or len(stock_df) < 100:
        return None, None
    
    try:
        # Fix timezone
        stock_df = self.fix_timezone(stock_df)
        index_df = self.fix_timezone(self.index_data)
        
        # ===== CARI TANGGAL YANG COCOK DENGAN METODE YANG LEBIH FLEKSIBEL =====
        
        # Ambil rentang tanggal saham
        stock_start = stock_df.index[0]
        stock_end = stock_df.index[-1]
        
        # Filter IHSG untuk periode yang sama
        idx_filtered = index_df[(index_df.index >= stock_start) & 
                                (index_df.index <= stock_end)]
        
        if len(idx_filtered) < 50:
            self.logger.debug(f"Data IHSG terlalu sedikit: {len(idx_filtered)}")
            return None, None
        
        # ===== CARI TANGGAL TERDEKAT (BUKAN HARUS PERSIS SAMA) =====
        # Ambil harga IHSG di tanggal terdekat dengan tanggal saham
        
        # Sampling: ambil harga di setiap akhir bulan atau minggu
        # Ini lebih fleksibel daripada mencari tanggal yang persis sama
        
        # Sampling mingguan (ambil setiap 5 hari)
        step = 5
        sampled_indices = range(0, min(len(stock_df), len(idx_filtered)), step)
        
        s_prices = []
        i_prices = []
        
        for i in sampled_indices:
            if i < len(stock_df) and i < len(idx_filtered):
                s_prices.append(stock_df['Close'].iloc[-i-1] if i > 0 else stock_df['Close'].iloc[-1])
                i_prices.append(idx_filtered['Close'].iloc[-i-1] if i > 0 else idx_filtered['Close'].iloc[-1])
        
        if len(s_prices) < 10:
            return None, None
        
        # ===== HITUNG PERFORMA RELATIF =====
        # Bandingkan perubahan harga dari awal ke akhir periode sampling
        
        # Performa saham
        stock_change = (s_prices[0] / s_prices[-1] - 1) * 100 if s_prices[-1] > 0 else 0
        
        # Performa IHSG
        index_change = (i_prices[0] / i_prices[-1] - 1) * 100 if i_prices[-1] > 0 else 0
        
        # RS Ratio
        if index_change != 0:
            rs_ratio = 1.0 + (stock_change - index_change) / 100
        else:
            rs_ratio = 1.0 + stock_change / 100
        
        rs_ratio = max(0.7, min(1.5, rs_ratio))
        
        # RS Score
        rs_score = 50 + (rs_ratio - 1.0) * 100
        rs_score = max(1, min(99, rs_score))
        
        self.logger.debug(f"{stock_df.name if hasattr(stock_df, 'name') else ''}: "
                         f"stock={stock_change:.1f}%, index={index_change:.1f}%, "
                         f"ratio={rs_ratio:.3f}, score={rs_score:.1f}")
        
        return round(rs_ratio, 3), round(rs_score, 1)
        
    except Exception as e:
        self.logger.debug(f"Error RS calculation: {e}")
        return None, None
