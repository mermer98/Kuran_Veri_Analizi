
import sys
import json
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QTextBrowser, QPushButton, QLabel
from PyQt5.QtGui import QTextCursor

class QuranSearchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kur'an Arama - Sayfalama Özellikli")

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Kelime veya kök ara...")
        self.search_box.textChanged.connect(self.perform_search)
        self.layout.addWidget(self.search_box)

        self.result_box = QTextBrowser()
        self.layout.addWidget(self.result_box)

        self.page_info = QLabel("0/0")
        self.layout.addWidget(self.page_info)

        self.prev_button = QPushButton("◀ Geri")
        self.prev_button.clicked.connect(self.prev_page)
        self.layout.addWidget(self.prev_button)

        self.next_button = QPushButton("İleri ▶")
        self.next_button.clicked.connect(self.next_page)
        self.layout.addWidget(self.next_button)

        self.results = []
        self.results_per_page = 20
        self.current_page = 0

        with open("kelime_manali_kuran_ve_turkce_meali.json", "r", encoding="utf-8") as f:
            self.dataset = json.load(f)

    def perform_search(self):
        query = self.search_box.text().strip()
        self.results = []
        self.current_page = 0

        for entry in self.dataset:
            if query.lower() in entry.get("turkce", "").lower() or query.lower() in entry.get("transkripsiyon", "").lower():
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

        html_output = f"<p style='color:gray;'>Toplam ({total}) eşleşme bulundu.</p><br>"
        for r in page_results:
            html_output += f"<p><b>Süre:</b> {r['sure']}<br>"
            html_output += f"<b>Ayet:</b> {r['ayet']}<br>"
            html_output += f"<b>Transkripsiyon:</b> {r.get('transkripsiyon', '')}<br>"
            html_output += f"<b>Arapça:</b> {r.get('arapca', '')}<br>"
            html_output += f"<b>Türkçe:</b> {r.get('turkce', '')}</p><hr>"

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
    window.resize(900, 700)
    window.show()
    sys.exit(app.exec_())
