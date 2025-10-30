import sys
import json
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QTextEdit,
    QPushButton, QTabWidget, QHBoxLayout, QLabel
)
from PyQt5.QtGui import QFont

# === Verileri Yükle ===
with open("kelime_manali_kuran_ve_turkce_meali.json", "r", encoding="utf-8") as f:
    MEAL_DATA = json.load(f)

with open("kurani_kerimdeki_tum_kelimeler.json", "r", encoding="utf-8") as f:
    KELIME_DATA = json.load(f)

# === Ortak Yardımcı Fonksiyonlar ===
def highlight(text, keyword):
    pattern = re.escape(keyword)
    return re.sub(f"({pattern})", r"<span style='background-color: yellow'><b>\1</b></span>", text, flags=re.I)

def clean_html(html):
    return re.sub(r'<.*?>', '', html)

# === Sekme 1: Mealli Arama ===
class MealTab(QWidget):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_page = 0
        self.results_per_page = 20

        layout = QVBoxLayout()
        self.input = QLineEdit()
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.info_label = QLabel()
        self.page_label = QLabel()

        search_button = QPushButton("Ara")
        search_button.clicked.connect(self.search)
        self.input.returnPressed.connect(self.search)

        nav = QHBoxLayout()
        self.prev = QPushButton("← Geri")
        self.next = QPushButton("İleri →")
        self.prev.clicked.connect(self.prev_page)
        self.next.clicked.connect(self.next_page)
        nav.addWidget(self.prev)
        nav.addWidget(self.next)

        layout.addWidget(self.input)
        layout.addWidget(self.info_label)
        layout.addWidget(self.result_box)
        layout.addWidget(self.page_label)
        layout.addLayout(nav)
        layout.addWidget(search_button)
        self.setLayout(layout)

    def search(self):
        keyword = self.input.text().strip().lower()
        self.results = []

        for entry in MEAL_DATA:
            arapca = clean_html(entry.get("arapca", ""))
            turkce = entry.get("turkce", "")
            trans = entry.get("transkripsiyon", "")
            if keyword in arapca.lower() or keyword in turkce.lower() or keyword in trans.lower():
                self.results.append(entry)

        self.current_page = 0
        self.show_results()

    def show_results(self):
        total = len(self.results)
        self.info_label.setText(f"Toplam ({total}) eşleşme bulundu.")
        if total == 0:
            self.result_box.setHtml("Sonuç bulunamadı.")
            self.page_label.clear()
            return

        start = self.current_page * self.results_per_page
        end = start + self.results_per_page
        display = self.results[start:end]

        output = ""
        for e in display:
            sure = e.get("sure", "")
            ayet = e.get("ayet", "")
            arapca = clean_html(e.get("arapca", ""))
            trans = e.get("transkripsiyon", "")
            turkce = e.get("turkce", "")

            output += f"<b>Sure:</b> {sure} | <b>Ayet:</b> {ayet}<br>"
            if trans:
                output += f"<b>Transkripsiyon:</b> {highlight(trans, self.input.text())}<br><br>"
            # Added styling for Arabic and Turkish texts with spacing
            output += f"<p style='color: blue; margin-bottom: 5px;'><b>Arapça:</b> {highlight(arapca, self.input.text())}</p>"
            output += f"<p style='color: green; margin-top: 5px;'><b>Türkçe:</b> {highlight(turkce, self.input.text())}</p><hr>"


        page_total = (total - 1) // self.results_per_page + 1
        self.page_label.setText(f"{self.current_page + 1}/{page_total}")
        self.result_box.setHtml(output)

    def next_page(self):
        if (self.current_page + 1) * self.results_per_page < len(self.results):
            self.current_page += 1
            self.show_results()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_results()

# === Sekme 2: Kelime Arama ===
class WordTab(QWidget):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_page = 0
        self.results_per_page = 20

        layout = QVBoxLayout()
        self.input = QLineEdit()
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.info_label = QLabel()
        self.page_label = QLabel()

        search_button = QPushButton("Ara")
        search_button.clicked.connect(self.search)
        self.input.returnPressed.connect(self.search)

        nav = QHBoxLayout()
        self.prev = QPushButton("← Geri")
        self.next = QPushButton("İleri →")
        self.prev.clicked.connect(self.prev_page)
        self.next.clicked.connect(self.next_page)
        nav.addWidget(self.prev)
        nav.addWidget(self.next)

        layout.addWidget(self.input)
        layout.addWidget(self.info_label)
        layout.addWidget(self.result_box)
        layout.addWidget(self.page_label)
        layout.addLayout(nav)
        layout.addWidget(search_button)
        self.setLayout(layout)

    def search(self):
        keyword = self.input.text().strip().lower()
        self.results = [entry for entry in KELIME_DATA if keyword in json.dumps(entry, ensure_ascii=False).lower()]
        self.current_page = 0
        self.show_results()

    def show_results(self):
        total = len(self.results)
        self.info_label.setText(f"Toplam ({total}) eşleşme bulundu.")
        if total == 0:
            self.result_box.setHtml("Sonuç bulunamadı.")
            self.page_label.clear()
            return

        start = self.current_page * self.results_per_page
        end = start + self.results_per_page
        display = self.results[start:end]

        output = ""
        for entry in display:
            for key, val in entry.items():
                output += f"<b>{key}:</b> {highlight(str(val), self.input.text())}<br>"
            output += "<hr>"

        page_total = (total - 1) // self.results_per_page + 1
        self.page_label.setText(f"{self.current_page + 1}/{page_total}")
        self.result_box.setHtml(output)

    def next_page(self):
        if (self.current_page + 1) * self.results_per_page < len(self.results):
            self.current_page += 1
            self.show_results()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_results()

# === Ana Uygulama ===
class QuranApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kur'an Arama Sistemi (2 Verili)")
        layout = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(MealTab(), "Mealli Arama")
        tabs.addTab(WordTab(), "Kelime Arama")
        layout.addWidget(tabs)
        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QuranApp()
    window.resize(1000, 700)
    window.show()
    sys.exit(app.exec_())