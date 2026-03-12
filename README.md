# 📈 Minervini Stock Screener - Saham Syariah Indonesia

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-blue)](https://github.com/features/actions)
[![Python](https://img.shields.io/badge/Python-3.10-green)](https://python.org)
[![Saham Syariah](https://img.shields.io/badge/Saham-Syariah-brightgreen)](https://www.idx.co.id)

Automated stock screener yang secara otomatis memeriksa **saham syariah Indonesia** berdasarkan **8 kriteria Minervini** dan mengirimkan hasilnya ke email Anda setiap hari.

## ✨ **Fitur Utama**

✅ **8 Kriteria Minervini** - Harga > MA150/200, MA Alignment, RS Rating > 70  
✅ **PatternPy Integration** - Deteksi pola chart otomatis (Head & Shoulders, Double Top/Bottom, Triangles, dll)  
✅ **Breakout Detection** - Deteksi breakout dengan volume tinggi  
✅ **Multithreading** - Screening 800+ saham dalam 10-15 menit  
✅ **Email Report** - Laporan lengkap dengan trading plan  
✅ **Google Sheets** - Data historis tersimpan rapi  
✅ **Telegram Notifikasi** - Alert real-time  

## 📊 **8 Kriteria Minervini**

| Kode | Kriteria |
|------|----------|
| **C1** | Harga > MA150 & MA200 |
| **C2** | MA150 > MA200 |
| **C3** | MA200 Trending Up (1 bulan) |
| **C4** | MA50 > MA150 & MA200 |
| **C5** | Harga > MA50 |
| **C6** | Harga > 30% dari Low 52-W |
| **C7** | Harga dalam 25% dari High 52-W |
| **C8** | RS Rating > 70 |

## 📁 **Struktur Proyek**
minervini-screener/
├── .github/workflows/ # GitHub Actions
├── src/ # Source code screener
├── PatternPy/ # PatternPy library (submodule)
├── config/ # Daftar saham
├── results/ # Hasil screening (CSV)
├── main.py # Entry point
├── requirements.txt # Dependencies
└── README.md # Dokumentasi

text

## 🚀 **Cara Install**

```bash
# Clone repository
git clone https://github.com/edissty/minervini-screener.git
cd minervini-screener

# Install dependencies
pip install -r requirements.txt

# Jalankan screener
python main.py
📧 Konfigurasi Email
Tambahkan secrets di GitHub:

EMAIL_FROM: alamat Gmail

EMAIL_PASSWORD: App Password Gmail

EMAIL_TO: email tujuan

🤝 Kontribusi
Silakan fork repository ini dan buat pull request.

📜 Lisensi
MIT License

text

## 📋 **CARA MEMBUAT FILE DI CODESPACE**

```bash
# Buat file requirements.txt
cat > requirements.txt << 'EOF'
yfinance==0.2.28
pandas==2.0.3
numpy==1.24.3
curl_cffi==0.5.10
requests==2.31.0
pytz==2023.3
EOF

# Buat file README.md
cat > README.md << 'EOF'
# 📈 Minervini Stock Screener - Saham Syariah Indonesia

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-blue)](https://github.com/features/actions)
[![Python](https://img.shields.io/badge/Python-3.10-green)](https://python.org)
[![Saham Syariah](https://img.shields.io/badge/Saham-Syariah-brightgreen)](https://www.idx.co.id)

Automated stock screener untuk saham syariah Indonesia dengan 8 kriteria Minervini.
EOF
✅ CEK HASIL
bash
# Lihat apakah file sudah ada
ls -la requirements.txt README.md
🚀 COMMIT KE GITHUB
bash
git add requirements.txt README.md
git commit -m "Restore requirements.txt and README.md"
git push origin main
