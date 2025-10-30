
import sys
import json
import re
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit
from PyQt5.QtGui import QTextCursor

# JSON dosyasını yükle
with open("kelime_manali_kuran_ve_turkce_meali.json", "r", encoding="utf-8") as f:
    DATASET = json.load(f)

class QuranSearchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kur'an Arama - Gri Kutulu")
        self.results = []
        self.current_page = 0
        self.results_per_page = 20

        self.layout = QVBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Bir kelime yazın...")
        self.input.textChanged.connect(self.perform_search)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_info = QLabel("")

        self.prev_button = QPushButton("◀ Geri")
        self.next_button = QPushButton("İleri ▶")
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)

        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.result_info)
        nav_layout.addWidget(self.next_button)

        self.layout.addWidget(self.input)
        self.layout.addWidget(self.result_box)
        self.layout.addLayout(nav_layout)
        self.setLayout(self.layout)

    def highlight_keywords(self, text):
        keyword = self.input.text().strip()
        pattern = re.escape(keyword)
        return re.sub(f"({pattern})", r"<span style='background-color: yellow;'>\1</span>", text, flags=re.IGNORECASE)

    def strip_html(self, html):
        return re.sub("<.*?>", "", html)

    def perform_search(self):
        query = self.input.text().strip().lower()
        self.results = []
        self.current_page = 0

        if not query:
            self.result_box.clear()
            self.result_info.setText("0/0")
            return

        for entry in DATASET:
            if query in entry.get("meal", "").lower() or query in entry.get("transkripsiyon", "").lower():
                self.results.append(entry)

        self.show_results()

    def show_results(self):
        total = len(self.results)
        if total == 0:
            self.result_box.setHtml("<b>Sonuç bulunamadı.</b>")
            self.result_info.setText("0/0")
            return

        start = self.current_page * self.results_per_page
        end = start + self.results_per_page
        page_results = self.results[start:end]

        output = f"<p style='color:gray'>Toplam ({total}) eşleşme bulundu.</p><br>"
        for entry in page_results:
            output += "<div style='background-color:#f0f0f0; padding:10px; margin-bottom:10px; border-radius:5px;'>"
            output += f"<b>Sure:</b> {entry.get('sure','-')}<br>"
            output += f"<b>Ayet:</b> {entry.get('ayet','-')}<br>"
            
            trans = entry.get("transkripsiyon", "").strip()
            if trans:
                output += f"<b>Transkripsiyon:</b><br><div dir='rtl'>{self.highlight_keywords(trans)}</div><br>"

            arapca = entry.get("arapca", "").strip()
            if arapca:
                output += f"<b>Arapça:</b><br><div dir='rtl'>{self.strip_html(arapca)}</div><br>"

            turkce = entry.get("meal", "").strip()
            if turkce:
                output += f"<b>Türkçe:</b><br>{self.highlight_keywords(turkce)}<br>"

            output += "</div>"

        self.result_box.setHtml(output)
        self.result_info.setText(f"{self.current_page + 1}/{(total - 1) // self.results_per_page + 1}")
        self.result_box.moveCursor(QTextCursor.Start)

    def next_page(self):
        if (self.current_page + 1) * self.results_per_page < len(self.results):
            self.current_page += 1
            self.show_results()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_results()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QuranSearchApp()
    window.resize(950, 750)
    window.show()
    sys.exit(app.exec_())
