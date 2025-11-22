#akıllı çeviri işlemleri
# modules/translation_module.py
import requests
import logging
from langdetect import detect

logger = logging.getLogger(__name__)

class SmartTranslator:
    def __init__(self):
        self.cache = {}
        self.supported_languages = ['tr', 'en', 'de', 'fr', 'es']
        self.google_api_key = None 

    def google_translate(self, text: str, target_lang: str, source_lang: str = 'auto') -> str:
        if not self.google_api_key:
            logger.info("🔶 Google Translate: API anahtarı yok")
            return text
        try:
            url = "https://translation.googleapis.com/language/translate/v2"
            params = {
                'q': text,
                'target': target_lang,
                'source': source_lang,
                'key': self.google_api_key
            }
            response = requests.post(url, data=params, timeout=5)
            if response.status_code == 200:
                result = response.json()
                translated = result['data']['translations'][0]['translatedText']
                logger.info(f"🌐 Google Translate: '{text}' -> '{translated}'")
                return translated
            else:
                logger.warning(f"❌ Google Translate HTTP hatası: {response.status_code}")
        except Exception as e:
            logger.warning(f"❌ Google Translate hatası: {e}")
        return text

    def _looks_like_turkish(self, text: str) -> bool:
        """Metnin Türkçe olup olmadığını  kontrol eder"""
        turkish_chars = set('çğıöşüÇĞİÖŞÜ')
        turkish_words = [
            'merhaba', 'teşekkür', 'lütfen', 'evet', 'hayır', 'dil', 'hata',
            'başlat', 'durdur', 'çeviri', 'metin', 'kelime', 'cümle', 'yeniden',
            'güzel', 'kötü', 'iyi', 'büyük', 'küçük', 'hızlı', 'yavaş', 'aç',
            'susuz', 'yorgun', 'mutlu', 'üzgün', 'kızgın', 'korkmuş', 'şaşkın'
        ]
        
        text_lower = text.lower()
        
        # Türkçe karakter kontrolü
        if any(char in turkish_chars for char in text):
            return True
        
        # Türkçe kelime kontrolü
        if any(word in text_lower for word in turkish_words):
            return True
            
        return False

    def offline_translate(self, text: str, target_lang: str, source_lang: str) -> str:
        #DAHA GENİŞ offline sözlük
        dictionary = {
            'tr-en': {
                'merhaba': 'hello', 'dünya': 'world', 'evet': 'yes', 'hayır': 'no',
                'teşekkürler': 'thank you', 'lütfen': 'please', 'günaydın': 'good morning',
                'iyi': 'good', 'kötü': 'bad', 'tamam': 'okay', 'hoşçakal': 'goodbye',
                'nasılsın': 'how are you', 'ad': 'name', 'ne': 'what', 'nerede': 'where',
                'zaman': 'time', 'bugün': 'today', 'yarın': 'tomorrow', 'dün': 'yesterday',
                'büyük': 'big', 'küçük': 'small', 'güzel': 'beautiful', 'kötü': 'bad',
                'hızlı': 'fast', 'yavaş': 'slow', 'sıcak': 'hot', 'soğuk': 'cold',
                'aç': 'hungry', 'susuz': 'thirsty', 'yorgun': 'tired', 'mutlu': 'happy',
                'üzgün': 'sad', 'kızgın': 'angry', 'korkmuş': 'scared', 'şaşkın': 'surprised',
                'dil': 'language', 'hata': 'error', 'başlat': 'start', 'durdur': 'stop',
                'çeviri': 'translation', 'metin': 'text', 'kelime': 'word', 'cümle': 'sentence',
                'yeniden': 'again', 'şimdi': 'now', 'sonra': 'later', 'önce': 'before',
                'yukarı': 'up', 'aşağı': 'down', 'sağ': 'right', 'sol': 'left',
                'erkek': 'man', 'kadın': 'woman', 'çocuk': 'child', 'aile': 'family',
                'arkadaş': 'friend', 'okul': 'school', 'ev': 'home', 'iş': 'work',
                'su': 'water', 'yemek': 'food', 'kitap': 'book', 'kalem': 'pencil',
                'masa': 'table', 'sandalye': 'chair', 'kapı': 'door', 'pencere': 'window',
                'bilgisayar': 'computer', 'telefon': 'phone', 'internet': 'internet',
                'program': 'program', 'yazılım': 'software', 'donanım': 'hardware'
            },
            'en-tr': {
                'hello': 'merhaba', 'world': 'dünya', 'yes': 'evet', 'no': 'hayır',
                'thank you': 'teşekkürler', 'please': 'lütfen', 'good morning': 'günaydın',
                'good': 'iyi', 'bad': 'kötü', 'okay': 'tamam', 'goodbye': 'hoşçakal',
                'how are you': 'nasılsın', 'name': 'ad', 'what': 'ne', 'where': 'nerede',
                'time': 'zaman', 'today': 'bugün', 'tomorrow': 'yarın', 'yesterday': 'dün',
                'big': 'büyük', 'small': 'küçük', 'beautiful': 'güzel', 'bad': 'kötü',
                'fast': 'hızlı', 'slow': 'yavaş', 'hot': 'sıcak', 'cold': 'soğuk',
                'hungry': 'aç', 'thirsty': 'susuz', 'tired': 'yorgun', 'happy': 'mutlu',
                'sad': 'üzgün', 'angry': 'kızgın', 'scared': 'korkmuş', 'surprised': 'şaşkın',
                'language': 'dil', 'error': 'hata', 'start': 'başlat', 'stop': 'durdur',
                'translation': 'çeviri', 'text': 'metin', 'word': 'kelime', 'sentence': 'cümle',
                'again': 'yeniden', 'now': 'şimdi', 'later': 'sonra', 'before': 'önce',
                'up': 'yukarı', 'down': 'aşağı', 'right': 'sağ', 'left': 'sol',
                'man': 'erkek', 'woman': 'kadın', 'child': 'çocuk', 'family': 'aile',
                'friend': 'arkadaş', 'school': 'okul', 'home': 'ev', 'work': 'iş',
                'water': 'su', 'food': 'yemek', 'book': 'kitap', 'pencil': 'kalem',
                'table': 'masa', 'chair': 'sandalye', 'door': 'kapı', 'window': 'pencere',
                'computer': 'bilgisayar', 'phone': 'telefon', 'internet': 'internet',
                'program': 'program', 'software': 'yazılım', 'hardware': 'donanım'
            },
            'tr-de': {
                'merhaba': 'hallo', 'teşekkürler': 'danke', 'lütfen': 'bitte',
                'evet': 'ja', 'hayır': 'nein', 'günaydın': 'guten morgen'
            },
            'de-tr': {
                'hallo': 'merhaba', 'danke': 'teşekkürler', 'bitte': 'lütfen',
                'ja': 'evet', 'nein': 'hayır', 'guten morgen': 'günaydın'
            },
            'tr-fr': {
                'merhaba': 'bonjour', 'teşekkürler': 'merci', 'lütfen': 's\'il vous plaît',
                'evet': 'oui', 'hayır': 'non', 'günaydın': 'bonjour'
            },
            'fr-tr': {
                'bonjour': 'merhaba', 'merci': 'teşekkürler', 's\'il vous plaît': 'lütfen',
                'oui': 'evet', 'non': 'hayır', 'bonjour': 'günaydın'
            }
        }
        
        key = f"{source_lang}-{target_lang}"
        if key in dictionary:
            lower_text = text.lower()
            if lower_text in dictionary[key]:
                translated = dictionary[key][lower_text]
                logger.info(f"📚 Offline çeviri: '{text}' -> '{translated}'")
                return translated
        
        logger.info(f"🔶 Offline çeviri bulunamadı: '{text}' ({source_lang}->{target_lang})")
        return text

    def translate_text(self, text: str, target_lang: str, source_lang: str = 'auto') -> str:
        # metni temizleme (gereksiz boşlukları kaldırır)
        original_text = text
        text = text.strip()
        
        # Kısa veya anlamsız metinleri çevirme
        if len(text) < 2 or text.isdigit():
            logger.debug(f"🔶 Kısa metin atlandı: '{text}'")
            return text
            
        #  DİL TESPİTİ
        if source_lang == 'auto':
            # Önce Türkçe kontrolü
            if self._looks_like_turkish(text):
                source_lang = 'tr'
                logger.info(f"🔤 Türkçe metin tespit edildi: '{text}'")
            else:
                try:
                    detected_lang = detect(text)
                    source_lang = detected_lang
                    logger.info(f"🌍 Langdetect: '{text}' -> {source_lang}")
                except Exception as e:
                    source_lang = 'en'
                    logger.warning(f"❌ Dil tespiti hatası: {e}, varsayılan: {source_lang}")
                
        # DEBUG: Dil bilgilerini logla
        logger.info(f"🎯 Çeviri başlıyor: '{text}' ({source_lang} -> {target_lang})")
        
        # Aynı dilse çevirme
        if source_lang == target_lang:
            logger.info(f"⚠️ Aynı dil, çeviri atlandı: {source_lang} -> {target_lang}")
            return text
            
        cache_key = f"{text}_{source_lang}_{target_lang}"
        if cache_key in self.cache:
            logger.info(f"💾 Önbellekten: '{text}' -> '{self.cache[cache_key]}'")
            return self.cache[cache_key]
            
        # Önce offline çeviriyi denenir
        translated = self.offline_translate(text, target_lang, source_lang)
        
        # Eğer offline çeviri işe yaramazsa Google Translate denenir
        if translated == text:
            if self.google_api_key:
                google_translated = self.google_translate(text, target_lang, source_lang)
                if google_translated != text:
                    translated = google_translated
            else:
                logger.info("🔶 Google API anahtarı yok, sadece offline çeviri")
        
        # Sonuç
        if translated != original_text:
            logger.info(f"✅ Çeviri başarılı: '{original_text}' -> '{translated}'")
        else:
            logger.info(f"❌ Çeviri başarısız: '{original_text}' değişmedi")
            
        self.cache[cache_key] = translated
        return translated

translator = SmartTranslator()