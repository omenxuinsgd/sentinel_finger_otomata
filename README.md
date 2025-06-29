🔒 Sistem Pengenalan Sidik Jari Modern
Sistem Pengenalan Sidik Jari ini adalah solusi komprehensif yang memungkinkan pendaftaran (enrollment) dan identifikasi biometrik menggunakan perangkat keras pemindai sidik jari. Sistem ini dirancang dengan arsitektur modular, memisahkan logika antarmuka pengguna, manajemen data, dan interaksi perangkat keras untuk skalabilitas dan pemeliharaan yang lebih baik.

✨ Fitur Utama
Inisialisasi Perangkat Otomatis: Deteksi dan inisialisasi pemindai sidik jari.

Pratinjau Langsung Sidik Jari: Tampilan real-time dari sidik jari yang dipindai saat pengambilan.

Pendaftaran Sidik Jari (Enrollment Otomatis 4-4-2):

Proses terpandu untuk merekam 10 jari (4 jari kiri, 4 jari kanan, 2 jempol).

Penyimpanan data pengguna (Nama, Nomor ID) bersama dengan template sidik jari ke database SQLite.

Verifikasi Sidik Jari (1:1):

Kemampuan untuk mengambil dua template sidik jari secara manual dan membandingkannya (verifikasi satu-ke-satu).

Identifikasi Sidik Jari (1:N):

Identifikasi satu sidik jari yang dipindai terhadap semua template yang tersimpan dalam database untuk menemukan kecocokan.

Arsitektur Fleksibel: Desain yang memisahkan Frontend, Backend (Node.js), dan Agen Python untuk pemrosesan sidik jari.

Komunikasi Real-time: Menggunakan WebSocket untuk umpan balik langsung dari perangkat ke antarmuka pengguna.

🏛️ Arsitektur Sistem
Sistem ini terbagi menjadi tiga komponen utama yang saling berinteraksi:

Antarmuka Pengguna (Frontend - Next.js):

Dibangun dengan React (Next.js).

Menyediakan antarmuka grafis yang intuitif bagi pengguna untuk berinteraksi dengan sistem.

Mengirim permintaan HTTP ke Node.js Backend dan menerima pembaruan real-time melalui WebSocket.

Layanan Backend (Node.js/Express):

Dibangun dengan Node.js menggunakan framework Express.js.

Berfungsi sebagai API Gateway utama, menerima permintaan dari Frontend.

Mengelola Database SQLite untuk menyimpan data pengguna dan template sidik jari.

Bertindak sebagai Proxy antara Frontend dan Python Agent untuk permintaan HTTP dan WebSocket, meneruskan data yang relevan.

Agen Sidik Jari (Python/Flask-SocketIO/ctypes):

Dibangun dengan Python menggunakan Flask-SocketIO.

Ini adalah inti yang berinteraksi langsung dengan perangkat keras pemindai sidik jari.

Menggunakan pustaka ctypes untuk memanggil fungsi dari DLL (Dynamic Link Libraries) perangkat keras.

Melakukan pemrosesan gambar, ekstraksi template (FMR), dan algoritma pencocokan biometrik.

Mengirim pratinjau langsung dan status operasi kembali ke Node.js Backend melalui WebSocket.

graph LR
    A[Frontend: Next.js] -- HTTP API & WebSocket --> B(Backend: Node.js/Express)
    B -- HTTP API & WebSocket --> C(Python Agent: Flask/ctypes)
    C -- Interaksi Langsung (DLLs) --> D[Perangkat Keras Pemindai Sidik Jari]
    B -- Database Interaksi --> E[SQLite Database]

🛠️ Prasyarat
Sebelum Anda dapat menjalankan sistem ini, pastikan Anda memiliki hal-hal berikut terinstal:

Node.js: Unduh & Instal Node.js (disertakan npm).

Python: Unduh & Instal Python.

PENTING: Karena interaksi dengan DLL Windows, sangat disarankan untuk menggunakan Python versi 32-bit jika Anda menggunakan sistem operasi Windows 64-bit.

DLL Perangkat Keras Sidik Jari: Pastikan Anda memiliki file DLL yang diperlukan (ZAZ_FpStdLib.dll, GALSXXYY.dll, Gamc.dll, FpSplit.dll, imagecut.dll) yang disediakan oleh produsen perangkat keras pemindai sidik jari Anda. File-file ini tidak termasuk dalam repositori ini.

🚀 Instalasi & Penyiapan
Ikuti langkah-langkah di bawah ini untuk menyiapkan dan menjalankan aplikasi:

Klon Repositori (Jika berlaku):

git clone <URL_REPOSITORI_ANDA>
cd <nama_folder_proyek>

Penyiapan Backend (Node.js):
Navigasi ke direktori server.js Anda (asumsikan berada di root proyek atau di folder backend/).

cd path/ke/folder/server_node
npm install

Penyiapan Agen Python:
Navigasi ke direktori agent.py Anda.

cd path/ke/folder/agent_python
pip install Flask Flask-SocketIO eventlet requests opencv-python numpy

Tempatkan file DLL (.dll) yang diperlukan (disebutkan di bagian Prasyarat) di direktori yang sama dengan file agent.py.

Penyiapan Frontend (Next.js):
Navigasi ke direktori page.js Anda (asumsikan ini adalah bagian dari proyek Next.js).

cd path/ke/folder/frontend_nextjs
npm install

Catatan untuk react-toastify: Jika Anda mengalami masalah CSS dengan react-toastify, pastikan import 'react-toastify/dist/ReactToastify.css'; ada di file _app.js (untuk Pages Router) atau di file CSS global yang diimpor di layout.js (untuk App Router) di proyek Next.js Anda.

▶️ Menjalankan Aplikasi
PENTING: Urutan menjalankan komponen sangat krusial!

Mulai Layanan Backend Node.js:
Buka terminal baru, navigasi ke direktori server.js Anda, dan jalankan:

node server.js

Anda akan melihat output konsol yang menunjukkan database SQLite telah diinisialisasi dan server berjalan pada http://localhost:3000.

Mulai Agen Python:
Buka terminal baru (biarkan terminal Node.js tetap berjalan), navigasi ke direktori agent.py Anda, dan jalankan:

python agent.py

Anda akan melihat output konsol yang menunjukkan agen Python memulai server Flask-SocketIO pada http://127.0.0.1:5000.

Mulai Aplikasi Frontend Next.js:
Buka terminal baru (biarkan kedua terminal lainnya tetap berjalan), navigasi ke direktori proyek Next.js Anda (tempat page.js berada), dan jalankan:

npm run dev
# atau
yarn dev

Aplikasi frontend akan terbuka di browser Anda (biasanya http://localhost:3001).

👨‍💻 Penggunaan Aplikasi
Setelah semua komponen berjalan:

Inisialisasi Perangkat: Klik tombol "Inisialisasi Perangkat" di bagian "Kontrol Perangkat". Anda harus melihat status berubah menjadi "READY".

Enrollment Otomatis (4-4-2):

Isi kolom "Nama" dan "Nomor ID".

Klik "Mulai Enrollment Otomatis".

Ikuti instruksi di layar (atau di pratinjau langsung) untuk meletakkan jari Anda. Sistem akan memandu Anda melalui pengambilan 4 jari kiri, 4 jari kanan, dan 2 jempol.

Verifikasi Manual (1:1):

Di bagian "Verifikasi Manual (1:1)", gunakan tombol "4 Jari Kiri", "4 Jari Kanan", atau "2 Jempol" untuk mengambil "Template Manual 1" dan "Template Manual 2".

Setelah kedua template diambil, tombol "Cocokkan Template 1 vs 2" akan aktif. Klik untuk melihat hasil perbandingan.

Identifikasi (1:N):

Di bagian "Identifikasi (1:N)", klik tombol "Mulai Identifikasi".

Letakkan jari apa pun pada pemindai. Sistem akan mencoba mencocokkan sidik jari yang dipindai dengan semua template yang tersimpan dalam database dan menampilkan hasil kecocokan.

⚠️ Pemecahan Masalah Umum
sqlite3.OperationalError: no such table: users_and_templates di agent.py:

Ini berarti agen Python mencoba mengakses database sebelum tabelnya dibuat. Pastikan Anda selalu menjalankan server.js terlebih dahulu dan menunggu hingga database diinisialisasi sepenuhnya sebelum menjalankan agent.py.

ECONNREFUSED atau masalah koneksi:

Periksa apakah server.js (port 3000) dan agent.py (port 5000) sedang berjalan dengan benar dan tidak ada firewall yang memblokir port tersebut.

Masalah DLL loading di agent.py:

Pastikan Anda menggunakan interpretasi Python 32-bit (terutama di Windows 64-bit).

Pastikan semua file DLL yang diperlukan berada di direktori yang sama dengan agent.py.

Gaya react-toastify tidak muncul di frontend:

Pastikan import 'react-toastify/dist/ReactToastify.css'; diimpor di file _app.js atau file layout utama lainnya dalam proyek Next.js Anda.

Made with ❤️ by Your Name/Team
