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

Struktur File saat ini 
minervini-screener/
├── .github/workflows/
│   └── screener.yml                    
├── src/
│   ├── minervini_screener.py            
│   ├── email_sender.py                   
│   ├── sheets_sender.py                   
│   └── deepseek_analyst.py                
├── config/
│   └── stocks_list.txt                    
├── main.py                                 
├── requirements.txt                     
└── README.md                               

📧 Contoh Email dengan Analisis DeepSeek
📊 RINGKASAN
Total Saham 8/8: 21
Saham dengan Breakout: 2

🤖 SENIOR HEDGE FUND ANALYST INSIGHTS

🔥 PRIORITAS TRADING - SAHAM BREAKOUT
• ALKA: ENTRY - Breakout valid dengan volume 2x
• KUAS: WAIT - Breakout belum terkonfirmasi

📊 Analisis ALKA
[analisis teknikal, fundamental, dan rekomendasi entry]

🤝 Kontribusi
Silakan fork repository ini dan buat pull request

---

## 🔑 **LANGKAH TERAKHIR: TAMBAHKAN SECRET DI GITHUB**

1. Buka repository GitHub Anda
2. **Settings** → **Secrets and variables** → **Actions**
3. Klik **New repository secret**
4. Nama: `DEEPSEEK_API_KEY`
5. Value: [API Key Anda dari DeepSeek]

---

## 🚀 **RINGKASAN FILE YANG PERLU DIUPDATE/DITAMBAH**

| File | Status | Keterangan |
|------|--------|------------|
| `.github/workflows/screener.yml` | ✅ UPDATE | Tambah env DEEPSEEK_API_KEY |
| `requirements.txt` | ✅ UPDATE | Tambah `openai` |
| `src/deepseek_analyst.py` | ✅ **FILE BARU** | Analis Hedge Fund |
| `src/email_sender.py` | ✅ UPDATE | Integrasi DeepSeek di email |
| `README.md` | ⚠️ OPSIONAL | Update dokumentasi |

## 🎯 **SELESAI!**

Setelah semua file diupdate, setiap kali screening selesai, email Anda akan berisi:
1. ✅ Daftar saham 8/8 seperti biasa
2. ✅ Trading plan untuk setiap saham
3. ✅ **Analisis Senior Hedge Fund dari DeepSeek** untuk prioritas trading

**Selamat menikmati analisis profesional di setiap email!** 🚀📊

