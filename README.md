# 🧬 Fingerprint Enrollment Server (Node.js + Python Agent + SQLite)

Sistem backend untuk **pendaftaran sidik jari** yang terhubung dengan agen Python untuk akuisisi, pemrosesan, dan penyimpanan data biometrik lengkap, termasuk template FMR dan gambar jari 4-4-2.

---

## 🚀 Fitur Utama

* 🔗 **Integrasi langsung dengan agen Python sidik jari**
* 📀 **Penyimpanan SQLite** untuk FMR dan gambar dalam format `BLOB`
* 📡 **API HTTP & WebSocket** untuk komunikasi real-time dengan client/frontend
* 🧠 **Konsolidasi data sidik jari per pengguna** (10 FMR + 13 gambar)
* ✅ Transaksi database aman (atomic `BEGIN/COMMIT/ROLLBACK`)
* 🔒 Validasi ID unik & rollback saat gagal

---

## 🗂️ Struktur Database SQLite

### Tabel: `users_and_templates`

Menyimpan identitas pengguna dan **10 template FMR** per jari.

| Kolom                                 | Tipe                 |
| ------------------------------------- | -------------------- |
| id                                    | INTEGER PRIMARY KEY  |
| id\_number                            | TEXT NOT NULL UNIQUE |
| name                                  | TEXT NOT NULL        |
| enrollment\_date                      | DATETIME             |
| fmr\_right\_thumb → fmr\_left\_little | BLOB (per jari)      |

---

### Tabel: `fingerprint_images`

Menyimpan **gambar individual per jari (10)** dan **3 gambar slap (4-4-2)**.

| Kolom                                 | Tipe                |
| ------------------------------------- | ------------------- |
| id                                    | INTEGER PRIMARY KEY |
| user\_id (FK)                         | INTEGER             |
| img\_right\_thumb → img\_left\_little | BLOB                |
| img\_slap\_right\_four                | BLOB                |
| img\_slap\_left\_four                 | BLOB                |
| img\_slap\_two\_thumbs                | BLOB                |

---

## 🧪 API Endpoint

### 🔹 `/api/start_enrollment`

Trigger proses perekaman awal ke agen Python.

### 🔹 `/api/save_enrollment`

Ambil data dari agen Python (FMR + gambar), simpan ke DB (otomatis transaksi dan validasi).

### 🔹 `/api/get-all-templates`

Ambil semua FMR pengguna, digabung sebagai `base64`.

### 🔹 `/api/init-device`, `/api/config`

Inisialisasi dan konfigurasi perangkat biometrik dari agen Python.

### 🔹 `/api/create_template`, `/api/match_templates`

Pemrosesan template di sisi agen.

### 🔹 `/api/identify`

Trigger proses identifikasi (1\:N).

---

## 🌐 WebSocket Events

| Event Name              | Fungsi                   |
| ----------------------- | ------------------------ |
| `live_preview`          | Stream citra langsung    |
| `enrollment_step`       | Progres pendaftaran      |
| `capture_result`        | Hasil capture jari       |
| `identification_step`   | Status pencocokan        |
| `identification_result` | Hasil identifikasi akhir |

---

## ⚙️ Teknologi Digunakan

* **Node.js + Express** untuk HTTP API dan server
* **SQLite3** sebagai database ringan lokal
* **Socket.IO** untuk komunikasi realtime
* **Axios** sebagai proxy HTTP ke agen Python
* **Python Agent** sebagai pengolah biometrik

---

## 📦 Instalasi

```bash
npm install
node server.js
```

Pastikan agen Python sidik jari berjalan di `http://127.0.0.1:5000`.

---

## 📁 Struktur File

```
📆 server/
 ├── server.js           # Entry point backend
 └── fingerprint_database.sqlite
```

---

## 👤 Penulis

**Nur Rokhman**
RnD MajoreIT
