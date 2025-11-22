import socket
import threading
import json
import time
import logging
import os
import subprocess
import sys

logger = logging.getLogger("SocketBridge")
HOST = "127.0.0.1"
PORT = 8888

client_conn = None
is_connected = False
overlay_process = None
#json veri doğrulama fonksiyonu
def validata_json_data(data):
    if(len(str(data))>10000): #çok büyük verilerde sorun çıkabilir max 10kb
        raise ValueError("Veri çok büyük")
    allowed_keys = {"type", "translations",'text','x','y','width','height','confidence'}
    def _validata_obj(obj):
        if isinstance(obj, dict):
            for key in obj.keys():
                if key not in allowed_keys:
                    raise ValueError(f"Geçersiz anahtar: {key}")
            for value in obj.values():
                _validata_obj(value)
        elif isinstance(obj, list):
            for item in obj:
                _validata_obj(item)
        elif not isinstance(obj, (str, int, float, bool))and obj is not None:
            raise ValueError(f"Geçersiz veri türü: {type(obj)}")
        _validata_obj(data)
        return True 
    
def handle_client(conn, addr):
    global client_conn, is_connected
    logger.info(f"✅ Overlay bağlandı: {addr}")
    client_conn = conn
    is_connected = True
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
    except Exception as e:
        logger.warning(f"Overlay bağlantı hatası: {e}")
    finally:
        conn.close()
        client_conn = None
        is_connected = False
        logger.info("Overlay bağlantısı kapandı")

def start_server():
    """Python tarafındaki TCP server'ı başlatır ve overlay.exe'yi otomatik açar."""
    def server_thread():
        global client_conn, is_connected, overlay_process
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, PORT))
            server.listen(1)
            logger.info(f"✅ Socket server dinlemede: {HOST}:{PORT}")

            # Overlay'ı otomatik başlat
            threading.Thread(target=start_overlay_exe, daemon=True).start()

            while True:
                try:
                    conn, addr = server.accept()
                    client_thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                    client_thread.start()
                except Exception as e:
                    logger.error(f"Server accept hatası: {e}")
                    break

    threading.Thread(target=server_thread, daemon=True).start()

def start_overlay_exe():
    """Overlay C++ uygulamasını otomatik olarak çalıştırır."""
    global overlay_process
    
    try:
        # Farklı konumlarda exe'yi ara
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "overlay_core", "build", "overlay_app.exe"),
            os.path.join(os.path.dirname(__file__), "..", "overlay_app.exe"),
            os.path.join(os.getcwd(), "overlay_app.exe"),
            "overlay_app.exe"
        ]
        
        exe_path = None
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                exe_path = abs_path
                break
        
        if exe_path:
            logger.info(f"🎯 Overlay exe bulundu: {exe_path}")
            
            # Önceki process'i temizle
            if overlay_process:
                try:
                    overlay_process.terminate()
                    overlay_process.wait(timeout=3)
                except:
                    overlay_process.kill()
            
            # Yeni process'i başlat
            overlay_process = subprocess.Popen(
                [exe_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            logger.info("⏳ Overlay başlatıldı, bağlantı bekleniyor...")
            # Bağlantı kurulmasını bekle
            for i in range(50):
                if is_connected:
                    logger.info("✅ Overlay bağlantısı kuruldu!")
                    return
                time.sleep(0.2)
            
            logger.warning("⚠️ Overlay bağlanamadı, manuel başlatmayı deneyin")
            
        else:
            logger.error("❌ Overlay exe bulunamadı! ")
            
    except Exception as e:
        logger.error(f"❌ Overlay başlatma hatası: {e}")

def send_text_to_overlay(data):
    """Çeviri sonucunu overlay'e JSON formatında gönderir."""
    global client_conn, is_connected
    
    if not is_connected or client_conn is None:
        logger.warning("⚠️ Overlay bağlı değil, mesaj gönderilemedi")
        return False

    try:
        message = json.dumps(data, ensure_ascii=False) + "\n"
        client_conn.sendall(message.encode("utf-8"))
        logger.debug(f"📨 Overlay'e gönderildi: {len(data.get('translations', []))} metin")
        return True
    except Exception as e:
        logger.error(f"❌ Mesaj gönderilemedi: {e}")
        return False