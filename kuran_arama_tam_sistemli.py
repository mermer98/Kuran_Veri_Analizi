import sys
import json
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QTextEdit,
    QPushButton, QLabel, QHBoxLayout
)
from PyQt5.QtGui import QTextCursor

with open("kelime_manali_kuran_ve_turkce_meali.json", encoding="utf-8") as f:
    DATASET = json.load(f)

class QuranSearchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kur’an Arama - Sayfalama Özellikli")

        self.results = []
        self.current_page = 0
        self.results_per_page = 20

        self.layout = QVBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Aranacak kelimeyi yazın...")
        self.input.textChanged.connect(self.perform_search)
        self.layout.addWidget(self.input)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.layout.addWidget(self.result_box)

        self.page_info = QLabel("")
        self.layout.addWidget(self.page_info)

        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("◂ Geri")
        self.next_button = QPushButton("İleri ▸")
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        self.layout.addLayout(nav_layout)

        self.setLayout(self.layout)

    def highlight_keywords(self, metin, kelime):
        pattern = re.escape(kelime)
        return re.sub(f"({pattern})", r"<span style='background-color:yellow;'>\1</span>", metin, flags=re.IGNORECASE)

    def perform_search(self):
        query = self.input.text().strip()
        self.results = []
        self.current_page = 0
        if not query:
            self.result_box.setText("")
            self.page_info.setText("0/0")
            return

        for entry in DATASET:
            if any(
                query.lower() in entry.get(field, "").lower()
                for field in ["meal", "transkripsiyon", "arapca"]
            ):
                self.results.append(entry)

        self.show_results()

    def show_results(self):
        total = len(self.results)
        if total == 0:
            self.result_box.setHtml("<b>Sonuç bulunamadı.</b>")
            self.page_info.setText("0/0")
            return

        start = self.current_page * self.results_per_page
        end = start + self.results_per_page
        page_results = self.results[start:end]

        html_output = f"<p style='color:gray;'>Toplam {total} sonuç bulundu.</p>"
        for r in page_results:
            html_output += f"<p><b>Sure:</b> {r.get('sure')}<br>"
            html_output += f"<b>Ayet:</b> {r.get('ayet')}<br>"
            html_output += f"<b>Transkripsiyon:</b><br>{self.highlight_keywords(r.get('transkripsiyon', ''), self.input.text())}<br>"
            html_output += f"<b>Arapça:</b><br>{self.highlight_keywords(r.get('arapca', ''), self.input.text())}<br>"
            html_output += f"<b>Türkçe:</b><br>{self.highlight_keywords(r.get('turkce', ''), self.input.text())}</p><hr>"

        self.result_box.setHtml(html_output)
        self.page_info.setText(f"{self.current_page + 1}/{(total - 1) // self.results_per_page + 1}")
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
    window.resize(950, 700)
    window.show()
    sys.exit(app.exec_())
