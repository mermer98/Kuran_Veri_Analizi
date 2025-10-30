import sys
import json
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit
from PyQt5.QtCore import Qt

class QuranSearchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kur'an-ı Kerim Arama (PyQt5)")

        self.layout = QVBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Ayet veya kelime ara:")
        self.search_box.textChanged.connect(self.search)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)

        self.layout.addWidget(self.search_box)
        self.layout.addWidget(self.result_box)
        self.setLayout(self.layout)

        # JSON dosyasını yükle
        with open("kelime_manali_kuran_ve_turkce_meali.json", "r", encoding="utf-8") as f:
            self.dataset = json.load(f)

    def search(self):
        keyword = self.search_box.text().strip()
        results = []

        for entry in self.dataset:
            arapca = entry.get("arapca", "")
            turkce = entry.get("turkce", "")
            if keyword in arapca or keyword in turkce:
                results.append(entry)

        self.display_results(results)

    def display_results(self, results):
        self.result_box.clear()

        if not results:
            self.result_box.setText("🔍 Sonuç bulunamadı.")
            return

        for r in results:
            sure = r.get("sure")
            ayet = r.get("ayet")
            arapca = r.get("arapca", "").strip()
            turkce = r.get("turkce", "").strip()

            # Başlık (sure/ayet)
            self.result_box.append(f'<p style="color:blue;">📘 {sure}/{ayet}</p>')

            # Arapça (yeşil ve sağdan sola)
            self.result_box.append(
                f'<p style="color:#007A22; font-size:22px; font-family:\'Scheherazade\'; direction:rtl; text-align:right;">{arapca}</p>'
            )

            # Türkçe (siyah)
            self.result_box.append(
                f'<p style="color:#000000; font-size:14px; font-family:Arial;">{turkce}</p><hr>'
            )

        self.result_box.moveCursor(self.result_box.textCursor().Start)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QuranSearchApp()
    window.resize(900, 700)
    window.show()
    sys.exit(app.exec_())
