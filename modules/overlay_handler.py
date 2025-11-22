#overlay kontrolu python tarafı
# modules/overlay_handler.py
import pyautogui
import time
import threading
import logging
import hashlib
from modules.ocr_module import ocr_engine
from modules.translation_module import translator
from modules.socket_bridge import start_server, send_text_to_overlay

logger = logging.getLogger(__name__)

class OverlayHandler:
    def __init__(self):
        self.is_running = False
        self.target_language = 'tr'
        self.interval = 1.5  # saniye - optimize edilmiş
        self.thread = None
        self.last_translations_hash = None  # Flickering önleyici
        self.consecutive_errors = 0

    def start_overlay(self, target_lang: str):
        """Overlay sistemi başlat"""
        if self.is_running:
            self.stop_overlay()
            time.sleep(1)  # Temiz başlangıç için bekle

        self.target_language = target_lang
        self.is_running = True
        self.last_translations_hash = None
        self.consecutive_errors = 0

        # Socket bridge başlat
        start_server()

        # İşlem thread'i başlat
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()

        logger.info(f"🎯 Overlay başlatıldı - Hedef dil: {target_lang}")

    def stop_overlay(self):
        """Overlay sistemi durdur"""
        self.is_running = False
        try:
            send_text_to_overlay({"type": "clear"})
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Temizleme gönderilemedi: {e}")
        
        self.last_translations_hash = None
        logger.info("⏹️ Overlay durduruldu")

    def _create_translations_hash(self, translations):
        """Translations listesinin hash'ini oluştur (flickering önleme)"""
        if not translations:
            return "empty"
        
        # Sadece metin ve konum bilgilerini hash'ler
        key_data = []
        for t in translations:
            key_data.append(f"{t['text']}_{t['x']}_{t['y']}_{t['width']}_{t['height']}")
        
        return hashlib.md5("|".join(key_data).encode()).hexdigest()

    def _process_loop(self):
        """Geliştirilmiş işlem döngüsü - hata toleranslı ve debug loglu"""
        last_text=""
        while self.is_running:
            try:
                # Ekran görüntüsü al
                screenshot = pyautogui.screenshot()
                screenshot_path = "temp_screen.png"
                screenshot.save(screenshot_path)

                # OCR ile metinleri ve konumları al
                text_elements = ocr_engine.hybrid_ocr(screenshot_path)
                
                logger.info(f"🔍 OCR buldu: {len(text_elements)} metin")
                
                # DEBUG: Tüm bulunan metinleri göster
                for i, element in enumerate(text_elements):
                    confidence = element.get('confidence', 0)
                    original_text = element['text'].strip()
                    logger.info(f"📝 [{i}] '{original_text}' - Güven: {confidence}%")
                    
                    #tekrar eden metin kontrolü
                    if original_text == last_text or original_text.strip() =="":
                        continue
                    last_text = original_text
                # Çevirileri hazırla (DEBUG modu - filtreleri gevşet)
                translations = []
                filtered_count = 0
                
                for element in text_elements:
                    confidence = element.get('confidence', 0)
                    original_text = element['text'].strip()
                    
                    # DEBUG: Gevşetilmiş güvenilirlik filtresi
                    if confidence < 30:  # %30'a düşürdük
                        logger.info(f"❌ Filtre: Düşük güven ({confidence}%): '{original_text}'")
                        filtered_count += 1
                        continue
                    
                    # DEBUG: Gevşetilmiş uzunluk filtresi
                    if len(original_text) < 2 or original_text.isdigit():
                        logger.info(f"❌ Filtre: Kısa metin: '{original_text}'")
                        filtered_count += 1
                        continue
                    
                    # Çeviri yap
                    translated_text = translator.translate_text(
                        original_text,
                        target_lang=self.target_language
                    )
                    
                    logger.info(f"🔄 Çeviri: '{original_text}' -> '{translated_text}'")
                    
                    translations.append({
                        'text': translated_text,
                        'x': element['bbox']['x'],
                        'y': element['bbox']['y'],
                        'width': element['bbox']['width'],
                        'height': element['bbox']['height'],
                        'confidence': confidence
                    })

                logger.info(f"📊 Filtreleme: {len(text_elements)} metinden {filtered_count} filtrelendi, {len(translations)} çeviri hazır")
                
                # FLICKERING ÖNLEME: Aynı çevirileri tekrar gönderme
                current_hash = self._create_translations_hash(translations)
                if current_hash == self.last_translations_hash:
                    logger.debug("🔄 Aynı çeviriler, güncelleme atlandı")
                    time.sleep(self.interval)
                    continue
                
                self.last_translations_hash = current_hash

                # C++ overlay'a gönder
                if translations:
                    success = send_text_to_overlay({
                        "type": "update",
                        "translations": translations
                    })
                    if success:
                        logger.info(f"✅ {len(translations)} metin overlay'a gönderildi")
                        self.consecutive_errors = 0
                    else:
                        logger.warning("⚠️ Overlay'a gönderilemedi")
                else:
                    # Hiç çeviri yoksa temizle
                    send_text_to_overlay({"type": "clear"})
                    logger.info("🔄 Ekran temizlendi (çeviri yok)")

            except Exception as e:
                self.consecutive_errors += 1
                logger.error(f"❌ İşlem döngüsü hatası ({self.consecutive_errors}/3): {e}")
                
                # Çok fazla hata varsa durdur
                if self.consecutive_errors >= 3:
                    logger.error("🚨 Çok fazla hata, overlay durduruluyor")
                    self.is_running = False
                    break

            time.sleep(self.interval)

# global instance
overlay_handler = OverlayHandler()