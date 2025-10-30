import sys
import json
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QTextBrowser,
    QPushButton, QLabel, QHBoxLayout
)
from PyQt5.QtGui import QTextCursor

# JSON VERİSİNİ YÜKLE
with open("kelime_manali_kuran_ve_turkce_meali.json", "r", encoding="utf-8") as f:
    DATASET = json.load(f)

class QuranSearchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kur'an Arama - Sayfalama Özellikli")
        self.results = []
        self.current_page = 0
        self.results_per_page = 20

        # Arayüz bileşenleri
        self.layout = QVBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Aranacak kelime (arapça, kök, meal, transkripsiyon)...")
        self.input.textChanged.connect(self.perform_search)
        self.result_box = QTextBrowser()
        self.result_info = QLabel("Toplam (0) eşleşme bulundu.")

        # Sayfa geçiş tuşları
        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("◀ Geri")
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button = QPushButton("İleri ▶")
        self.next_button.clicked.connect(self.next_page)
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)

        self.layout.addWidget(self.input)
        self.layout.addWidget(self.result_info)
        self.layout.addWidget(self.result_box)
        self.layout.addLayout(nav_layout)
        self.setLayout(self.layout)

    def highlight_keywords(self, text, keyword):
        pattern = re.escape(keyword)
        return re.sub(f"({pattern})", r"<span style='background-color:yellow'><b>\1</b></span>", text, flags=re.IGNORECASE)

    def perform_search(self):
        query = self.input.text().strip()
        self.results = []

        if not query:
            self.result_info.setText("Toplam (0) eşleşme bulundu.")
            self.result_box.clear()
            return

        for entry in DATASET:
            arapca = entry.get("arapca", "")
            turkce = entry.get("turkce", "")
            trans = entry.get("transkripsiyon", "")
            if (query.lower() in arapca.lower() or
                query.lower() in turkce.lower() or
                query.lower() in trans.lower()):
                self.results.append(entry)

        self.current_page = 0
        self.show_results()

    def show_results(self):
        total = len(self.results)
        self.result_info.setText(f"Toplam ({total}) eşleşme bulundu.")

        if total == 0:
            self.result_box.setText("Sonuç bulunamadı.")
            return

        start = self.current_page * self.results_per_page
        end = start + self.results_per_page
        page_results = self.results[start:end]

        output = ""
        for entry in page_results:
            sure = entry.get("sure", "-")
            ayet = entry.get("ayet", "-")
            arapca = entry.get("arapca", "")
            turkce = entry.get("turkce", "")
            trans = entry.get("transkripsiyon", "")

            arapca = self.strip_html(arapca)
            arapca = self.highlight_keywords(arapca, self.input.text())
            turkce = self.highlight_keywords(turkce, self.input.text())
            trans = self.highlight_keywords(trans, self.input.text())

            output += f"<b>Sure:</b> {sure} | <b>Ayet:</b> {ayet}<br>"
            if trans:
                output += f"<b>Transkripsiyon:</b> {trans}<br>"
            output += f"<b>Arapça:</b> {arapca}<br>"
            output += f"<b>Türkçe:</b> {turkce}<br><hr>"

        self.result_box.setHtml(output)
        self.result_box.moveCursor(QTextCursor.Start)

    def strip_html(self, html):
        # Etiketleri temizler
        clean = re.compile('<.*?>')
        return re.sub(clean, '', html)

    def next_page(self):
        if (self.current_page + 1) * self.results_per_page < len(self.results):
            self.current_page += 1
            self.show_results()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_results()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QuranSearchApp()
    window.resize(950, 700)
    window.show()
    sys.exit(app.exec_())
