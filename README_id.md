# macOS Diagnostic Tool

Script gratis dan open-source untuk cek kesehatan Mac kamu. Jalankan kapanpun Mac terasa lambat.

**Tidak perlu pengalaman coding.**

🌐 [English](README.md) | **Bahasa Indonesia**

---

## Latar Belakang

Script ini awalnya dibuat ketika Mac saya mulai melambat dan butuh cara untuk mengeceknya. Ternyata cukup berguna untuk dipakai rutin, jadi saya rasa mungkin bisa berguna juga untuk orang lain.

---

## Yang Dicek

| Pemeriksaan | Keterangan |
|---|---|
| Memory & Swap | Tekanan RAM, penggunaan swap disesuaikan dengan kapasitas Mac kamu |
| GPU Memory | VRAM berlebihan dari app dengan grafis berat |
| Orphan Daemons | Background service sisa dari app yang sudah dihapus |
| System Extensions | Terlalu banyak add-on tingkat OS yang bikin lambat |
| Disk Space | Peringatan disk hampir penuh, urutan size folder terbesar |
| Fan/Thermal | Suhu CPU, peringatan log thermal |
| Processes | Zombie process, proses yang memakan CPU/memory paling banyak |
| Network | Background service mencurigakan yang aktif di port tertentu |
| Preference Files | File config sisa dari app yang sudah diuninstall |
| Cache Cleanup | Cara cepat membebaskan ruang penyimpanan |

**Output:** HTML report + file JSON, tersimpan di `~/Desktop/diagnostic_reports/`.

---

## Cara Pakai

### Langkah 1 — Buka Terminal

Terminal adalah app bawaan Mac untuk menjalankan perintah — umpamanya seperti mengirim instruksi teks ke Mac kamu.

**Cara buka:** Tekan `Cmd + Space`, ketik `terminal`, tekan `Enter`.

### Langkah 2 — Jalankan 3 perintah ini

Copy-paste satu per satu, tekan `Enter` setelah masing-masing:

```bash
git clone https://github.com/watashiwatasha/macos-diagnostic-tool.git ~/Documents/macos-diagnostic-tool
```

```bash
chmod +x ~/Documents/macos-diagnostic-tool/run_diagnostic.sh
```

```bash
bash ~/Documents/macos-diagnostic-tool/run_diagnostic.sh
```

> **Tidak punya Git?** Klik tombol hijau **Code** di halaman ini → **Download ZIP** → unzip → pindahkan folder ke `~/Documents/macos-diagnostic-tool/` → jalankan dua perintah terakhir di atas.

### Langkah 3 — Tunggu ~30 detik

Kamu akan lihat proses scan berjalan satu per satu. Mungkin kamu akan diminta mengetik **password** di tengah proses — ini normal dan aman. Beberapa pengecekan butuh akses admin untuk baca data sistem. Password kamu tidak pernah disimpan atau dikirim ke mana pun.

HTML report akan terbuka otomatis di browser setelah selesai.

![Terminal menjalankan diagnostic scan](screenshots/terminal.png)

---

## Tampilan Report

![Lampiran HTML menampilkan info sistem dan status](screenshots/report-header.png)

---

## Jalankan Ulang

Cukup jalankan satu perintah ini setiap kamu hendak melakukan scan:

```bash
bash ~/Documents/macos-diagnostic-tool/run_diagnostic.sh
```

---

## Cara Membaca Report

Report menggunakan tiga kriteria:

**🚨 Critical** — Perbaiki sekarang. Contoh:
- Swap terlalu tinggi untuk RAM Mac kamu
- Disk sudah terisi lebih dari 90%
- Sisa app lama masih jalan di background

**⚠️ Warning** — Pantau terus. Contoh:
- Disk sudah terisi lebih dari 80%
- App pakai memory yang tidak wajar
- Suhu CPU naik

**ℹ️ Info** — Perlu diketahui, tidak mendesak. Contoh:
- File preference sisa dari app lama
- Folder Downloads atau Caches yang besar
- Trash belum dikosongkan

---

## Minta Bantuan AI (Opsional)

Setelah scan, kamu bisa paste hasilnya ke AI assistant mana saja (Claude, ChatGPT, dll.) dan minta penjelasan.

Contoh prompt:
```
Saya baru menjalankan macOS diagnostic. Ini hasilnya — mana yang harus diperbaiki lebih dahulu?

[paste report di sini]
```

AI akan memprioritaskan masalah, menjelaskan artinya, dan memberikan langkah-langkah perbaikan.

---

## Kebutuhan

- macOS 10.15 Catalina atau lebih baru
- Python 3 (sudah ada di Mac modern)
- Tidak perlu install package tambahan

**Tidak yakin punya Python 3?** Buka Terminal dan jalankan:
```bash
python3 --version
```
Jika muncul `Python 3.x.x`, tandanya sudah siap. Kalau tidak:
```bash
xcode-select --install
```

---

## Privasi & Keamanan

- Jalan sepenuhnya di Mac kamu — tidak ada yang diupload
- Hanya baca nama proses, statistik memory, dan ukuran file — bukan isi file
- Report tersimpan di `~/Desktop/diagnostic_reports/` — milik kamu
- Open source — bisa baca sendiri setiap baris kodenya
- Tidak ada dependency pihak ketiga

---

## Troubleshooting

**Diminta password — normal?**

Ya, normal. Beberapa pengecekan butuh akses admin untuk baca data sistem. Password kamu tidak pernah disimpan atau dikirim ke mana pun. Ketik saja lalu tekan `Enter` (password tidak akan kelihatan saat diketik — itu juga normal).

**Error "Permission denied"**

```bash
sudo -K
bash ~/Documents/macos-diagnostic-tool/run_diagnostic.sh
```

**"python3: command not found"**

```bash
xcode-select --install
```

**Report tidak terbuka otomatis**

1. Buka Finder
2. Masuk ke `Desktop > diagnostic_reports`
3. Double-click file `.html` terbaru

**Script jalan tetapi tidak ada masalah yang ditemukan**

Bagus! Artinya sistem kamu sehat. Jalankan kapanpun ingin cek kondisi Mac.

---

## File Report

Setiap scan menghasilkan dua file di `~/Desktop/diagnostic_reports/`:

| File | Fungsi |
|---|---|
| `diagnostic_YYYYMMDD_HHMMSS.html` | Visual report — buka di browser mana saja |
| `diagnostic_YYYYMMDD_HHMMSS.json` | Data mentah — berguna untuk membandingkan scan dari waktu ke waktu |

Simpan report lama untuk memantau tren seiring waktu.

---

## Alur Pemakaian

```
1. Buka Terminal
2. Jalankan: bash ~/Documents/macos-diagnostic-tool/run_diagnostic.sh
3. Report terbuka otomatis di browser
4. Lihat sekilas alert merah/kuning
5. Perbaiki masalah critical jika ada
6. Simpan report untuk perbandingan berikutnya
```

Total waktu: ~2 menit.

---

## Changelog

Lihat [CHANGELOG.md](CHANGELOG.md).

---

## Lisensi

MIT — bebas dipakai, dimodifikasi, dan dibagikan. Lihat [LICENSE](LICENSE).
