import ctypes
import os
import sys
import time
import threading
import traceback
from enum import Enum
import cv2
import numpy as np
import base64
from flask import Flask, jsonify, request
# Menggunakan eventlet untuk performa WebSocket yang lebih baik
# Pastikan untuk menginstal: pip install eventlet
import eventlet
eventlet.monkey_patch()
import requests

from flask_socketio import SocketIO
# --- TAMBAHAN: Impor sqlite3 ---
import sqlite3
# -----------------------------

# =============================================
# DEFINISI & KONFIGURASI
# =============================================
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

CAPTURE_DELAY_AFTER_QUALITY_MET = 2.0  # Detik
# --- TAMBAHAN: Definisikan path database secara global ---
NODE_SERVER_API_URL = 'http://localhost:3000/api'
# ----------------------------------------------------
FMR_TEMPLATE_SIZE = 1024 

class CaptureType(Enum):
    LEFT_FOUR = "left_four"
    RIGHT_FOUR = "right_four"
    TWO_THUMBS = "two_thumbs"
    # --- TAMBAHAN: Tipe baru untuk proses identifikasi ---
    IDENTIFY = "identify_any"
    # --------------------------------------------------

def log_debug(message):
    """Fungsi pembantu untuk logging debug"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[DEBUG][{timestamp}] {message}")

def log_error(message, error=None):
    """Fungsi pembantu untuk logging error"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[ERROR][{timestamp}] {message}")
    if error:
        print(traceback.format_exc())

# =============================================
# PEMUATAN DLL & DEFINISI STRUKTUR
# =============================================
try:
    log_debug("Starting DLL loading process...")
    
    dll_path = os.path.dirname(os.path.abspath(__file__))
    zaz_dll_path = os.path.join(dll_path, 'ZAZ_FpStdLib.dll')
    gals_dll_path = os.path.join(dll_path, 'GALSXXYY.dll')
    gamc_dll_path = os.path.join(dll_path, 'Gamc.dll')
    fpsplit_dll_path = os.path.join(dll_path, 'FpSplit.dll')
    imagecut_dll_path = os.path.join(dll_path, 'imagecut.dll')

    zaz_dll = ctypes.WinDLL(zaz_dll_path)
    gals_dll = ctypes.WinDLL(gals_dll_path)
    gamc_dll = ctypes.WinDLL(gamc_dll_path)
    fpsplit_dll = ctypes.WinDLL(fpsplit_dll_path)
    imagecut_dll = ctypes.WinDLL(imagecut_dll_path)
    
    log_debug("Configuring DLL function argument types...")
    gals_dll.LIVESCAN_GetFPRawData.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_ubyte)]
    gamc_dll.MOSAIC_FingerQuality.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int, ctypes.c_int]
    zaz_dll.ZAZ_FpStdLib_CreateISOTemplate.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_ubyte)]
    zaz_dll.ZAZ_FpStdLib_CompareTemplates.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_ubyte)]
    imagecut_dll.imagecut.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int, ctypes.c_int, ctypes.c_int]
    
    log_debug("DLL loading and configuration completed successfully")

except Exception as e:
    log_error("CRITICAL ERROR LOADING DLLs. Pastikan semua DLL ada dan Anda menggunakan interpreter Python 32-bit.", e)
    sys.exit(1)

class FPSPLIT_INFO(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int), ("top", ctypes.c_int), ("left", ctypes.c_int), ("angle", ctypes.c_int), ("quality", ctypes.c_int), ("pOutBuf", ctypes.POINTER(ctypes.c_ubyte))]

fpsplit_dll.FPSPLIT_DoSplit.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(FPSPLIT_INFO)]

# =============================================
# KELAS PERANGKAT SIDIK JARI
# =============================================
class FingerprintDevice:
    def __init__(self):
        log_debug("Initializing FingerprintDevice...")
        self.device_handle = None
        self.is_initialized = False
        self.quality_threshold = 40
        self.capture_timeout = 15
        self.fog_removal = False
        self.is_capturing = False
        self.capture_lock = threading.Lock()
        self.template1 = None
        self.template2 = None
        self.enrollment_data = {}
        self._clear_enrollment_data()

    def _clear_enrollment_data(self):
        log_debug("Clearing previous enrollment data.")
        self.enrollment_data = {"templates": {}, "images": {}}
    
    def get_status(self):
        return {"initialized": self.is_initialized, "status": "ready" if self.is_initialized else "not initialized", "templates": {"template1": bool(self.template1), "template2": bool(self.template2)}}

    def initialize_device(self):
        log_debug("Starting device initialization...")
        with self.capture_lock:
            try:
                if gals_dll.LIVESCAN_Init() != 1: raise Exception("Inisialisasi Perangkat Keras Gagal")
                if gamc_dll.MOSAIC_Init() != 1: raise Exception("Algoritma Mosaic Gagal")
                self.device_handle = zaz_dll.ZAZ_FpStdLib_OpenDevice()
                if self.device_handle == 0: raise Exception("Inisialisasi Algoritma Gagal")
                self.is_initialized = True
                return {"success": True, "message": "Semua sistem berhasil diinisialisasi"}
            except Exception as e:
                log_error("Initialization crashed", e)
                self.is_initialized = False
                return {"success": False, "message": str(e)}

    def _stream_and_capture_task(self, capture_type, is_enrollment, template_no=None):
        w, h = 1600, 1500
        start_time = time.time()
        best_quality = 0
        best_image = None
        quality_met_time = None
        
        log_debug(f"Starting stream & capture for type {capture_type.value}")

        try:
            while time.time() - start_time < self.capture_timeout:
                if not self.is_capturing:
                    log_debug("Capture task was cancelled externally.")
                    break

                data = (ctypes.c_ubyte * (w * h))()
                if gals_dll.LIVESCAN_GetFPRawData(0, data) == 1:
                    np_image = np.ctypeslib.as_array(data).reshape((h, w))
                    small_preview = cv2.resize(np_image, (400, 375))
                    _, buffer = cv2.imencode('.jpg', small_preview)
                    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                    socketio.emit('live_preview', {'image_data': 'data:image/jpeg;base64,' + jpg_as_text})

                    quality = gamc_dll.MOSAIC_FingerQuality(data, w, h)
                    if quality > best_quality:
                        best_quality = quality
                        best_image = bytes(data)
                    
                    if quality > self.quality_threshold and quality_met_time is None:
                        log_debug(f"Quality threshold met. Starting {CAPTURE_DELAY_AFTER_QUALITY_MET}s delay.")
                        quality_met_time = time.time()
                    
                    if quality_met_time and (time.time() - quality_met_time > CAPTURE_DELAY_AFTER_QUALITY_MET):
                        log_debug("Final capture delay passed.")
                        break
                
                socketio.sleep(0.1)

            log_debug("Streaming loop finished.")
            
            if best_image:
                self._process_captured_image(best_image, w, h, best_quality, capture_type, is_enrollment, template_no)
            else:
                log_error("No valid image could be captured.")
                socketio.emit('capture_result', {'success': False, 'message': 'Gagal mengambil gambar.'})

        except Exception as e:
            log_error("Error during capture task", e)
            socketio.emit('capture_result', {'success': False, 'message': 'Terjadi kesalahan saat pengambilan.'})
        finally:
            if not is_enrollment:
                self.is_capturing = False
                log_debug("Capture flag set to False for manual capture/identification.")

    def _get_finger_positions(self, capture_type):
        if capture_type == CaptureType.LEFT_FOUR: return ["left_index", "left_middle", "left_ring", "left_little"]
        if capture_type == CaptureType.RIGHT_FOUR: return ["right_index", "right_middle", "right_ring", "right_little"]
        if capture_type == CaptureType.TWO_THUMBS: return ["right_thumb", "left_thumb"]
        if capture_type == CaptureType.IDENTIFY: return ["finger1", "finger2", "finger3", "finger4"]
        return []

    def _process_captured_image(self, image_bytes, w, h, quality, capture_type, is_enrollment, template_no=None):
        log_debug(f"Processing image for {capture_type.value} with quality {quality}")
        
        finger_num_ptr = ctypes.c_int(0)
        info_array = (FPSPLIT_INFO * 10)()
        split_buffers = [(ctypes.c_ubyte * (256 * 360))() for _ in range(10)]
        for i, buf in enumerate(split_buffers): info_array[i].pOutBuf = ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte))

        img_buffer_full = (ctypes.c_ubyte * len(image_bytes))(*image_bytes)
        ret = fpsplit_dll.FPSPLIT_DoSplit(img_buffer_full, w, h, 1, 256, 360, ctypes.byref(finger_num_ptr), info_array)
        finger_num = finger_num_ptr.value
        
        if ret != 0:
            log_error(f"Fingerprint split failed. Code: {ret}")
            socketio.emit('capture_result', {"success": False, "message": "Segmentasi sidik jari gagal."})
            return

        if capture_type != CaptureType.IDENTIFY:
            finger_positions = self._get_finger_positions(capture_type)
            if len(finger_positions) != finger_num:
                socketio.emit('capture_result', {"success": False, "message": "Jumlah jari yang terdeteksi tidak cocok."})
                return

        if is_enrollment:
            slap_key = f"img_slap_{capture_type.value}"
            self.enrollment_data["images"][slap_key] = image_bytes

        templates = []
        for i in range(finger_num):
            position_key = self._get_finger_positions(capture_type)[i] if capture_type != CaptureType.IDENTIFY else f"probe_{i+1}"
            
            p_out_buf = info_array[i].pOutBuf
            img_data_bytes = ctypes.string_at(p_out_buf, 256 * 360)
            
            if is_enrollment:
                self.enrollment_data["images"][f"img_{position_key}"] = img_data_bytes
            
            img_buffer_single = (ctypes.c_ubyte * len(img_data_bytes))(*img_data_bytes)
            template = (ctypes.c_ubyte * 1024)()
            if zaz_dll.ZAZ_FpStdLib_CreateISOTemplate(self.device_handle, img_buffer_single, template) != 0:
                template_bytes = bytes(template)
                templates.append(template_bytes)
                if is_enrollment:
                    self.enrollment_data["templates"][f"fmr_{position_key}"] = template_bytes

        if not templates:
            log_error("No valid templates were created from split images.")
            socketio.emit('capture_result', {"success": False, "message": "Tidak dapat membuat template dari gambar."})
            return
            
        if capture_type == CaptureType.LEFT_FOUR and is_enrollment:
            log_debug("Reversing template and image order for left hand enrollment.")
            original_positions = self._get_finger_positions(capture_type)
            reversed_positions = list(reversed(original_positions))
            
            # Buat salinan untuk menghindari masalah saat iterasi dan modifikasi
            current_templates = self.enrollment_data["templates"].copy()
            current_images = self.enrollment_data["images"].copy()
            
            for i in range(len(original_positions)):
                original_pos_key = original_positions[i]
                source_pos_key = reversed_positions[i]
                
                # Update FMR
                self.enrollment_data["templates"][f"fmr_{original_pos_key}"] = current_templates[f"fmr_{source_pos_key}"]
                # Update Gambar Jari
                self.enrollment_data["images"][f"img_{original_pos_key}"] = current_images[f"img_{source_pos_key}"]
            log_debug(f"Reversal complete. Final template keys for left hand: {list(self.enrollment_data['templates'].keys())}")

        if capture_type == CaptureType.IDENTIFY:
            self._perform_1_to_n_match(templates)
            return

        if not is_enrollment:
            combined_templates = b"".join(templates)
            if template_no == 1: self.template1 = combined_templates
            else: self.template2 = combined_templates

        socketio.emit('capture_result', {"success": True, "message": f"Pengambilan {capture_type.name} berhasil.", "template_no": template_no})

    def create_template_manual(self, template_no, capture_type_str):
        with self.capture_lock:
            if not self.is_initialized: return {"success": False, "message": "Perangkat belum diinisialisasi."}
            if self.is_capturing: return {"success": False, "message": "Proses lain sedang berjalan."}
            try: capture_type = CaptureType(capture_type_str)
            except ValueError: return {"success": False, "message": f"Tipe pengambilan tidak valid: {capture_type_str}"}
            self.is_capturing = True
        
        socketio.start_background_task(self._stream_and_capture_task, capture_type, is_enrollment=False, template_no=template_no)
        return {"success": True, "message": "Proses pengambilan manual dimulai..."}

    def start_enrollment_sequence(self):
        with self.capture_lock:
            if not self.is_initialized: return {"success": False, "message": "Perangkat belum diinisialisasi."}
            if self.is_capturing: return {"success": False, "message": "Proses lain sedang berjalan."}
            self._clear_enrollment_data()
        
        socketio.start_background_task(self._enrollment_flow)
        return {"success": True, "message": "Proses enrollment dimulai..."}

    def _enrollment_flow(self):
        try:
            self.is_capturing = True
            socketio.emit('enrollment_step', {"step": 1, "message": "Letakkan 4 Jari Kiri Anda..."})
            self._stream_and_capture_task(CaptureType.LEFT_FOUR, is_enrollment=True)
            while self.is_capturing: socketio.sleep(0.5)

            self.is_capturing = True
            socketio.emit('enrollment_step', {"step": 2, "message": "Berhasil! Jeda 4 detik sebelum jari kanan..."})
            socketio.sleep(4)
            socketio.emit('enrollment_step', {"step": 2, "message": "Sekarang, letakkan 4 Jari Kanan Anda..."})
            self._stream_and_capture_task(CaptureType.RIGHT_FOUR, is_enrollment=True)
            while self.is_capturing: socketio.sleep(0.5)

            self.is_capturing = True
            socketio.emit('enrollment_step', {"step": 3, "message": "Berhasil! Jeda 4 detik sebelum jempol..."})
            socketio.sleep(4)
            socketio.emit('enrollment_step', {"step": 3, "message": "Terakhir, letakkan 2 Jempol Anda..."})
            self._stream_and_capture_task(CaptureType.TWO_THUMBS, is_enrollment=True)
            while self.is_capturing: socketio.sleep(0.5)
            
            socketio.emit('enrollment_step', {"step": "finished", "message": "Semua sidik jari berhasil diambil!"})

        except Exception as e:
            log_error("Enrollment flow failed", e)
            socketio.emit('capture_result', {"success": False, "message": "Alur enrollment gagal."})
        finally:
            self.is_capturing = False
            log_debug("Enrollment flow finished. Capture flag set to False.")

    def match_templates(self):
        log_debug("Starting manual template matching...")
        if not self.template1 or not self.template2:
            return {"success": False, "message": "Satu atau kedua template manual tidak ada."}
        try:
            t1_buf = (ctypes.c_ubyte * len(self.template1))(*self.template1)
            t2_buf = (ctypes.c_ubyte * len(self.template2))(*self.template2)
            score = zaz_dll.ZAZ_FpStdLib_CompareTemplates(self.device_handle, t1_buf, t2_buf)
            matched = score >= 45
            log_debug(f"Manual match result: score={score}, matched={matched}")
            return {"success": True, "score": score, "matched": matched}
        except Exception as e:
            log_error("Manual matching failed", e)
            return {"success": False, "message": f"Pencocokan manual gagal: {str(e)}"}
            
    # --- TAMBAHAN: Logika baru untuk identifikasi 1:N ---
    def start_identification(self):
        """Memulai proses identifikasi 1:N."""
        with self.capture_lock:
            if not self.is_initialized: return {"success": False, "message": "Perangkat belum diinisialisasi."}
            if self.is_capturing: return {"success": False, "message": "Proses lain sedang berjalan."}
            self.is_capturing = True
        
        socketio.emit('identification_step', {"message": "Letakkan jari apapun untuk identifikasi..."})
        socketio.start_background_task(self._stream_and_capture_task, CaptureType.IDENTIFY, is_enrollment=False)
        return {"success": True, "message": "Proses identifikasi dimulai..."}

    def _perform_1_to_n_match(self, probe_templates):
        """Mencocokkan probe_templates dengan semua data di DB melalui server Node.js."""
        log_debug(f"Starting 1:N match with {len(probe_templates)} probe template(s).")
        
        try:
            # --- MODIFIKASI: Mengambil data template dari server Node.js ---
            response = requests.get(f"{NODE_SERVER_API_URL}/get-all-templates")
            response.raise_for_status() # Akan memunculkan HTTPError untuk status respons buruk (4xx atau 5xx)

            all_users_data = response.json()

            if not all_users_data or not all_users_data.get('success') or not all_users_data.get('data'):
                log_error("Identification failed: No user data received from Node.js server or data is empty.")
                socketio.emit('identification_result', {"success": False, "message": "Database kosong atau gagal mengambil data dari server Node.js."})
                return

            all_users = all_users_data['data']
            log_debug(f"Found {len(all_users)} users in Node.js database to check against.")

            for user in all_users:
                for probe_template_bytes in probe_templates:
                    # Probe template buffer must be of FMR_TEMPLATE_SIZE
                    # This assumes the probe template itself is already a single 1024-byte template
                    probe_buffer = (ctypes.c_ubyte * FMR_TEMPLATE_SIZE)(*probe_template_bytes)

                    stored_combined_template_b64 = user.get('combined_template_base64')
                    if not stored_combined_template_b64: continue

                    stored_combined_template_bytes = base64.b64decode(stored_combined_template_b64)
                    
                    # Iterate through the combined template in chunks of FMR_TEMPLATE_SIZE
                    # to compare against each individual stored finger template
                    for i in range(0, len(stored_combined_template_bytes), FMR_TEMPLATE_SIZE):
                        single_stored_template_bytes = stored_combined_template_bytes[i:i + FMR_TEMPLATE_SIZE]

                        # Ensure the chunk is exactly FMR_TEMPLATE_SIZE, otherwise it might be incomplete
                        if len(single_stored_template_bytes) != FMR_TEMPLATE_SIZE:
                            log_error(f"Incomplete stored template chunk found for user {user.get('id_number')} at offset {i}. Skipping this chunk.")
                            continue

                        stored_buffer = (ctypes.c_ubyte * FMR_TEMPLATE_SIZE)(*single_stored_template_bytes)
                        
                        score = zaz_dll.ZAZ_FpStdLib_CompareTemplates(self.device_handle, probe_buffer, stored_buffer)
                        
                        if score > 55: 
                            log_debug(f"MATCH FOUND! User: {user['name']}, ID: {user['id_number']}, Score: {score}")
                            socketio.emit('identification_result', {
                                "success": True,
                                "found": True,
                                "name": user['name'],
                                "id_number": user['id_number'],
                                "score": score
                                })
                            return # Hentikan setelah menemukan kecocokan pertama

            log_debug("No match found after checking all records.")
            socketio.emit('identification_result', { "success": True, "found": False, "message": "Sidik jari tidak ditemukan di dalam database."})

        except requests.exceptions.RequestException as e:
            log_error(f"Failed to fetch templates from Node.js server: {e}")
            socketio.emit('identification_result', {"success": False, "message": "Gagal terhubung ke server Node.js untuk data identifikasi."})
        except Exception as e:
            log_error("1:N matching process failed", e)
            socketio.emit('identification_result', {"success": False, "message": "Terjadi error saat proses identifikasi."})

# =============================================
# FLASK & SOCKETIO ENDPOINTS
# =============================================
fingerprint_device = FingerprintDevice()

@app.route('/api/status')
def status(): return jsonify(fingerprint_device.get_status())

@app.route('/api/init', methods=['POST'])
def init_device(): return jsonify(fingerprint_device.initialize_device())

@app.route('/api/config', methods=['POST'])
def config():
    data = request.get_json()
    if "quality_threshold" in data: fingerprint_device.quality_threshold = int(data["quality_threshold"])
    if "fog_removal" in data: fingerprint_device.fog_removal = bool(data["fog_removal"])
    if "capture_timeout" in data: fingerprint_device.capture_timeout = int(data["capture_timeout"])
    return jsonify({"success": True, "message": "Pengaturan diperbarui"})

@app.route('/api/create_template', methods=['POST'])
def create_template_manual():
    data = request.get_json()
    if not data or 'template_no' not in data or 'capture_type' not in data:
        return jsonify({"success": False, "message": "Data tidak lengkap"}), 400
    return jsonify(fingerprint_device.create_template_manual(data['template_no'], data['capture_type']))

@app.route('/api/match_templates', methods=['POST'])
def match_templates(): return jsonify(fingerprint_device.match_templates())

@app.route('/api/start_enrollment', methods=['POST'])
def start_enrollment():
    return jsonify(fingerprint_device.start_enrollment_sequence())

@app.route('/api/get_enrollment_data', methods=['GET'])
def get_enrollment_data():
    if len(fingerprint_device.enrollment_data["templates"]) < 10 or len(fingerprint_device.enrollment_data["images"]) < 13:
        return jsonify({"success": False, "message": "Data enrollment tidak lengkap atau tidak ada."}), 404
        
    templates_b64 = {key: base64.b64encode(val).decode('utf-8') for key, val in fingerprint_device.enrollment_data["templates"].items()}
    images_b64 = {key: base64.b64encode(val).decode('utf-8') for key, val in fingerprint_device.enrollment_data["images"].items()}

    response_data = { "success": True, "templates_base64": templates_b64, "images_base64": images_b64 }
    
    fingerprint_device._clear_enrollment_data()
    return jsonify(response_data)

# --- TAMBAHAN: Endpoint baru untuk identifikasi ---
@app.route('/api/identify', methods=['POST'])
def identify():
    return jsonify(fingerprint_device.start_identification())
# --- AKHIR TAMBAHAN ---


@socketio.on('connect')
def handle_connect(): log_debug(f'Klien terhubung: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect(): log_debug(f'Klien terputus: {request.sid}')

# =============================================
# MAIN EXECUTION
# =============================================
if __name__ == '__main__':
    log_debug("Memulai server Flask-SocketIO...")
    socketio.run(app, host='127.0.0.1', port=5000, debug=False)
