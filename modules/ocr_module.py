# modules/ocr_module.py
import cv2
import pytesseract
import base64
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class HybridOCR:
    def __init__(self, google_vision_key: str = None):
        self.google_vision_key = google_vision_key
        # Update to your tesseract location if needed
        self.tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

    def tesseract_ocr(self, image_path: str) -> List[Dict]:
        """Tesseract OCR - Offline yedek"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return []

            # Görüntü iyileştirme
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.medianBlur(gray, 3)
            gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

            # OCR with bounding boxes
            data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT, lang='eng+tur')

            texts = []
            for i in range(len(data['text'])):
                try:
                    conf = float(data['conf'][i])
                except:
                    conf = 0.0
                if conf > 60 and data['text'][i].strip():
                    texts.append({
                        'text': data['text'][i],
                        'bbox': {
                            'x': int(data['left'][i]),
                            'y': int(data['top'][i]),
                            'width': int(data['width'][i]),
                            'height': int(data['height'][i])
                        },
                        'confidence': conf
                    })
            return texts
        except Exception as e:
            logger.error(f"Tesseract OCR hatası: {e}")
            return []

    def google_vision_ocr(self, image_path: str):
        # (Opsiyonel) Google Vision implemantasyonu burada olabilir
        return []

    def hybrid_ocr(self, image_path: str) -> List[Dict]:
        """Hybrid OCR: Önce Google Vision, başarısızsa Tesseract"""
        logger.info("Hybrid OCR başlatılıyor...")
        if self.google_vision_key:
            g = self.google_vision_ocr(image_path)
            if g:
                logger.info(f"Google Vision başarılı: {len(g)} metin bulundu")
                return g
        t = self.tesseract_ocr(image_path)
        logger.info(f"Tesseract: {len(t)} metin bulundu")
        return t

# global instance
ocr_engine = HybridOCR(google_vision_key=None)

