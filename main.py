import sys
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import tkinter as tk
from tkinter import ttk
import threading
import logging
from modules.overlay_handler import overlay_handler


# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FourYourLanguageApp:
    def __init__(self, root):
        self.root = root
        self.setup_ui()
        
    def setup_ui(self):
        self.root.title("FourYourLanguage - Gerçek Zamanlı Çeviri")
        self.root.geometry("400x300+100+100")
        self.root.resizable(True, True)
        
     
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 12))
        style.configure('TLabel', font=('Arial', 11))
        
        #ana çerçeve
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # başlık
        title_label = ttk.Label(main_frame, text="🚀 FourYourLanguage", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # dil seçimi
        lang_label = ttk.Label(main_frame, text="Hedef Dil:")
        lang_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.lang_combo = ttk.Combobox(main_frame, 
                                      values=["Türkçe", "İngilizce", "Almanca", "Fransızca", "İspanyolca"],
                                      state="readonly", width=15)
        self.lang_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        self.lang_combo.set("İngilizce")
        
        # kontrol butonları
        self.start_btn = ttk.Button(main_frame, text="▶️ Çeviriyi Başlat", 
                                   command=self.start_translation)
        self.start_btn.grid(row=2, column=0, columnspan=2, pady=15, sticky=tk.EW)
        
        self.stop_btn = ttk.Button(main_frame, text="⏹️ Durdur", 
                                  command=self.stop_translation, state=tk.DISABLED)
        self.stop_btn.grid(row=3, column=0, columnspan=2, pady=5, sticky=tk.EW)
        
        # durum etiketi
        self.status_label = ttk.Label(main_frame, text="Hazır", foreground="green")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=10)
        
        # bilgi metni
        instructions = """
Kullanım:
1. Hedef dili seçin
2. 'Çeviriyi Başlat' butonuna tıklayın
3. C++ overlay otomatik başlayacak
4. Ekrandaki metinler gerçek zamanlı çevrilecek
5. 'Durdur' butonu ile bitirin

Özellikler:
• Google Lens benzeri overlay
• Hybrid OCR (Google Vision + Tesseract)
• Gerçek zamanlı çeviri
• Yüksek performanslı C++ overlay
        """
        
        info_text = tk.Text(main_frame, height=8, width=45, font=('Arial', 9))
        info_text.grid(row=5, column=0, columnspan=2, pady=10)
        info_text.insert(tk.END, instructions)
        info_text.config(state=tk.DISABLED)
        
    def start_translation(self):
        lang_map = {
            "Türkçe": "tr",
            "İngilizce": "en", 
            "Almanca": "de",
            "Fransızca": "fr",
            "İspanyolca": "es"
        }
        
        target_lang = lang_map.get(self.lang_combo.get(), "en")
        
        # başlatma işlemini ayrı bir thread'de yap
        def start_overlay():
            try:
                overlay_handler.start_overlay(target_lang)
                self.root.after(0, self._on_start_success)
            except Exception as e:
                self.root.after(0, lambda e=e: self._on_start_error(str(e)))
        
        threading.Thread(target=start_overlay, daemon=True).start()
        self.status_label.config(text="Başlatılıyor...", foreground="orange")
        
    def _on_start_success(self):
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Çalışıyor - C++ Overlay Aktif", foreground="green")
        
    def _on_start_error(self, error_msg):
        self.status_label.config(text=f"Hata: {error_msg}", foreground="red")
        
    def stop_translation(self):
        overlay_handler.stop_overlay()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Durduruldu", foreground="red")

def main():
    root = tk.Tk()
    app = FourYourLanguageApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()