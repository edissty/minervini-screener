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
