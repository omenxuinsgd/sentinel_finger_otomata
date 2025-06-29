# Flask Fingerprint Agent with DLL Integration & 1\:N Matching

This Python Flask application serves as a local **fingerprint processing agent** for a biometric system. It uses native Windows DLLs to communicate with a fingerprint scanner, handle segmentation, ISO template creation, and perform 1:1 and 1\:N matching. It connects to a Node.js backend for storage and template retrieval.

## ✨ Features

* Real-time fingerprint capture with **quality check & preview**
* Supports **4-4-2 fingerprint enrollment** (4 left fingers, 4 right fingers, 2 thumbs)
* Auto segmentation with `FpSplit.dll`
* Template creation with `ZAZ_FpStdLib.dll`
* Image quality scoring with `Gamc.dll`
* Live preview over WebSocket (`flask-socketio`)
* **1:1 template matching** (manual)
* **1\:N identification** against a database via Node.js API
* DLL loading and validation on startup
* Base64 exchange of templates/images with Node.js server

## ⚙ Requirements

* Python 3.9 (32-bit recommended)
* Windows OS (for DLL support)
* Fingerprint scanner compatible with GALSXXYY.dll
* Installed Python packages:

  ```bash
  pip install flask flask-socketio eventlet opencv-python numpy requests
  ```
* Native DLLs (place in the same folder):

  * `ZAZ_FpStdLib.dll`
  * `GALSXXYY.dll`
  * `Gamc.dll`
  * `FpSplit.dll`
  * `imagecut.dll`

## 🔧 How It Works

### Enrollment Flow (4-4-2)

1. Capture 4 left fingers
2. Capture 4 right fingers
3. Capture 2 thumbs
4. Segment each finger and create templates
5. Store base64-encoded templates/images in memory
6. POST to Node.js backend

### Manual 1:1 Match

* Create template 1 from any scan
* Create template 2 from a different scan
* Match with ZAZ DLL scoring (threshold ≥ 45)

### Identification (1\:N)

* Capture any finger
* Create ISO templates for each detected finger
* Retrieve all combined templates from Node.js
* Iterate and compare one-by-one (score ≥ 55)
* Stop and return match on first hit

## ♻ API Endpoints

| Method | Endpoint                   | Description                          |
| ------ | -------------------------- | ------------------------------------ |
| POST   | `/api/init`                | Initialize scanner device            |
| POST   | `/api/start_enrollment`    | Begin 4-4-2 capture workflow         |
| GET    | `/api/get_enrollment_data` | Get last captured templates/images   |
| POST   | `/api/create_template`     | Capture one template manually        |
| POST   | `/api/match_templates`     | Match two manually created templates |
| POST   | `/api/identify`            | Identify single finger to DB         |
| POST   | `/api/config`              | Adjust quality threshold, timeout    |
| GET    | `/api/status`              | Get device status and init status    |

## 📲 SocketIO Events

| Event                   | Direction       | Data Format                                     |
| ----------------------- | --------------- | ----------------------------------------------- |
| `live_preview`          | server → client | `{ image_data: base64 JPEG }`                   |
| `enrollment_step`       | server → client | `{ step: number, message: text }`               |
| `capture_result`        | server → client | `{ success: bool, message: text }`              |
| `identification_step`   | server → client | `{ message: text }`                             |
| `identification_result` | server → client | `{ success, found, name?, id_number?, score? }` |

## 🚀 Run the Agent

```bash
python agent.py
```

> Flask server runs on `http://127.0.0.1:5000`

## 🏆 DLL Function Summary

| DLL                              | Function Purpose                           |
| -------------------------------- | ------------------------------------------ |
| `LIVESCAN_GetFPRawData`          | Capture live raw fingerprint image         |
| `MOSAIC_FingerQuality`           | Assess image quality score                 |
| `FPSPLIT_DoSplit`                | Segment slap image into individual fingers |
| `ZAZ_FpStdLib_CreateISOTemplate` | Generate ISO template from finger image    |
| `ZAZ_FpStdLib_CompareTemplates`  | Compare two ISO templates                  |

## ✨ Tips & Notes

* Use `template_no: 1` and `template_no: 2` to match different fingers
* Image size assumed: `1600x1500`
* Matching threshold:

  * 1:1: score ≥ 45
  * 1\:N: score ≥ 55
* Left hand images & templates are reversed after capture
* Database handled by Node.js using SQLite

## ⚖ Architecture Diagram (High-Level)

```
+-----------+           WebSocket/API           +------------+           
| Web App   | <---------Node.js Server--------> | Flask Agent| 
+-----------+           SQLite (Templates)      +------------+          
                                                | DLLs
                                                |-- ZAZ_FpStdLib.dll
                                                |-- Gamc.dll
                                                |-- FpSplit.dll
                                                |-- GALSXXYY.dll
                                                |-- imagecut.dll
```

## 🚫 Error Handling

* If DLL fails to load: Make sure you're on Python 32-bit & DLLs exist
* If device not found: Check hardware connection
* If capture fails: Adjust lighting and finger placement

---

> Need help or improvements? Contribute or ask in Issues!

---
