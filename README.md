# minervini-screener
Screener saham kriteria Minervini
# 📈 Minervini Stock Screener - Saham Syariah Indonesia

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-blue)](https://github.com/features/actions)
[![Python](https://img.shields.io/badge/Python-3.10-green)](https://python.org)
[![Yahoo Finance](https://img.shields.io/badge/Data-Yahoo%20Finance-orange)](https://finance.yahoo.com)
[![Saham Syariah](https://img.shields.io/badge/Saham-Syariah-brightgreen)](https://www.idx.co.id)

Automated stock screener yang secara otomatis memeriksa **saham syariah Indonesia** berdasarkan **8 kriteria Minervini** dan mengirimkan hasilnya ke email Anda setiap hari.

---

## 🎯 **Apa itu Minervini Screener?**

Screener ini dirancang untuk menemukan saham-saham syariah Indonesia yang memenuhi **8 kriteria ketat** ala Mark Minervini, trader legendaris dengan CAGR 220% selama 5 tahun. Kriteria ini dirancang untuk menemukan saham-saham dengan **momentum kuat** yang siap breakout.

---

## 📊 **8 Kriteria Minervini yang Digunakan**

| Kode | Kriteria | Deskripsi | Target |
|------|----------|-----------|--------|
| **C1** | Harga > MA150 & MA200 | Harga di atas moving average 150 dan 200 hari | Menunjukkan trend jangka panjang bullish |
| **C2** | MA150 > MA200 | Moving average 150 di atas 200 | Konfirmasi trend naik jangka panjang |
| **C3** | MA200 Menanjak | MA200 lebih tinggi dari 1 bulan lalu | Trend jangka panjang semakin menguat |
| **C4** | MA50 > MA150 & MA200 | MA50 di atas kedua MA jangka panjang | Trend jangka menengah menguat |
| **C5** | Harga > MA50 | Harga di atas MA50 | Saham dalam fase uptrend |
| **C6** | Harga > 30% dari 52-Week Low | Minimal 30% di atas harga terendah 1 tahun | Saham sudah keluar dari zona terendah |
| **C7** | Harga dalam 25% dari 52-Week High | Maksimal 25% di bawah harga tertinggi 1 tahun | Saham mendekati rekor tertinggi |
| **C8** | Relative Strength > 70 | Kinerja lebih baik dari 70% saham lainnya | Momentum penguatan |

---

## ✨ **Fitur Utama**

✅ **Otomatis Penuh** - Screening berjalan setiap hari tanpa perlu campur tangan  
✅ **Jadwal Terjadwal** - Berjalan setiap jam **08:00 dan 16:00 WIB**  
✅ **Email Report** - Hasil dikirim langsung ke email Anda dalam format HTML yang rapi  
✅ **Lampiran CSV** - Data lengkap bisa diolah lebih lanjut di Excel  
✅ **80+ Saham Syariah** - Fokus pada saham-saham syariah yang stabil di Yahoo Finance  
✅ **Delay Optimal** - 1-2 detik per saham untuk menghindari rate limiting Yahoo Finance  
✅ **Debug Mode** - Log detail untuk membandingkan hasil dengan TradingView  

---

## 🚀 **Cara Install**

### **1. Fork Repository Ini**
Klik tombol **Fork** di pojok kanan atas halaman ini.

### **2. Setup GitHub Secrets**
Tambahkan 3 secrets berikut di repository Anda:  
**Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Contoh Value | Keterangan |
|-------------|--------------|------------|
| `EMAIL_FROM` | `email.anda@gmail.com` | Alamat Gmail pengirim |
| `EMAIL_PASSWORD` | `abcdefghijklmnop` | App Password Gmail (16 digit, tanpa spasi) |
| `EMAIL_TO` | `xxx@gmail.com` | Email tujuan (ganti dengan email Anda) |

### **3. Cara Membuat App Password Gmail**
1. Aktifkan **2-Step Verification** di akun Gmail Anda
2. Buka [App Passwords](https://myaccount.google.com/apppasswords)
3. Pilih app: **Mail** dan device: **Other** (beri nama "Minervini Screener")
4. Copy password 16 digit yang dihasilkan
5. Paste ke GitHub secret `EMAIL_PASSWORD`

---

## 📝 **Cara Menggunakan**

### **Otomatis (Jadwal Default)**
Screening akan berjalan otomatis setiap:
- **08:00 WIB** (pagi)
- **16:00 WIB** (sore)

### **Manual (Untuk Testing)**
1. Klik tab **Actions**
2. Pilih **Minervini Stock Screener**
3. Klik **Run workflow** → **Run workflow**

---

## 📧 **Contoh Email yang Diterima**
📈 MINERVINI STOCK SCREENER RESULTS
Waktu Screening: 25-02-2026 08:00:30 WIB

📊 RINGKASAN HASIL

Total Saham Lolos: 8

Saham 8/8: 2

Saham 7/8: 6

🎯 8 KRITERIA MINERVINI
• C1: Harga > MA150 & MA200
• C2: MA150 > MA200
• C3: MA200 Menanjak (1 bulan terakhir)
• C4: MA50 > MA150 & MA200
• C5: Harga > MA50
• C6: Harga > 30% dari 52-Week Low
• C7: Harga dalam 25% dari 52-Week High
• C8: Relative Strength > 70

📋 DETAIL SAHAM LOLOS
Ticker | Skor | Status | Harga | RS | C1 | C2 | ...

ADRO | 8/8 | 8/8 | 2.5K | 85 | ✓ | ✓ | ...
ANTM | 7/8 | 7/8 | 1.9K | 72 | ✓ | ✓ | ...

---

## ⚙️ **Kustomisasi**

### **Mengubah Daftar Saham**
Edit file `config/stocks_list.txt`:
```txt
# Format: KODE.JK (WAJIB pakai .JK)
ADRO.JK  # Alamtri Resources Indonesia
ANTM.JK  # Aneka Tambang
ASII.JK  # Astra International
# ... dan seterusnya
Mengubah Jadwal Screening
Edit file .github/workflows/screener.yml:
schedule:
  - cron: '0 1,9 * * *'   # 08:00 dan 16:00 WIB
  # - cron: '0 1 * * *'    # 08:00 WIB saja
  # - cron: '0 0,6,12,18 * * *'  # 4x sehari
📊 Struktur Proyek
minervini-screener/
├── .github/
│   └── workflows/
│       └── screener.yml      # Konfigurasi GitHub Actions
├── src/
│   ├── minervini_screener.py # Engine screening utama
│   └── email_sender.py        # Pengirim email
├── config/
│   └── stocks_list.txt        # Daftar saham syariah
├── results/                    # Folder hasil screening (CSV)
├── main.py                     # Entry point program
├── requirements.txt            # Dependencies Python
└── README.md                   # Dokumentasi ini

 Troubleshooting
Error: "No data found, symbol may be delisted"
Pastikan format ticker benar (ADRO.JK, bukan ADRO saja)

Cek di Yahoo Finance manual: https://finance.yahoo.com/quote/ADRO.JK

Saham mungkin benar-benar delisted, hapus dari daftar

Email tidak masuk
Cek folder Spam

Pastikan App Password benar (16 digit, tanpa spasi)

Verifikasi 2FA sudah aktif di Gmail

Cek log Actions untuk detail error

Screening terlalu lambat
Delay default 1-2 detik per saham untuk hindari rate limiting

Untuk 80 saham, waktu normal 7-10 menit

Kurangi jumlah saham jika terlalu lama

🤝 Kontribusi
Silakan fork repository ini dan buat pull request untuk:

✅ Menambah daftar saham syariah atau non syariah

✅ Memperbaiki akurasi kriteria

✅ Menambah fitur baru

✅ Optimasi kecepatan

⚠️ Disclaimer
Screening ini menggunakan data dari Yahoo Finance. Hasil screening bukan rekomendasi beli/jual. Selalu lakukan analisis fundamental dan teknikal lebih lanjut sebelum mengambil keputusan investasi.

Penulis tidak bertanggung jawab atas kerugian investasi yang mungkin terjadi.

📜 Lisensi
MIT License - Silakan gunakan dan modifikasi sesuai kebutuhan Anda.

🙏 Kredit
Mark Minervini - Untuk strategi dan kriteria screening yang legendaris

Yahoo Finance - Penyedia data historis saham

GitHub Actions - Platform otomatisasi gratis

📞 Kontak & Diskusi
Issues: Gunakan fitur Issues di GitHub untuk laporan bug

Discussions: Untuk diskusi strategi dan pengembangan

Dibuat dengan ❤️ untuk investor syariah Indonesia

⭐ Star repository ini jika bermanfaat! ⭐
