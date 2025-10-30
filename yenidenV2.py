from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QTabWidget, QHBoxLayout
)
import json
import re
import sys

# --- JSON Yükleme ---
with open("kelime_manali_kuran_ve_turkce_meali.json", "r", encoding="utf-8") as f1:
    MEAL_DATA = json.load(f1)
with open("kurani_kerimdeki_tum_kelimeler.json", "r", encoding="utf-8") as f2:
    KELIME_DATA = json.load(f2)

# --- Ortak Araçlar ---
def highlight(text, keyword):
    pattern = re.escape(keyword)
    return re.sub(f"({pattern})", r"<span style='background-color: yellow'><b>\1</b></span>", text, flags=re.I)

def clean_html(html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', html)

# --- Sekme 1: Mealli Arama ---
class MealTab(QWidget):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_page = 0
        self.results_per_page = 20

        layout = QVBoxLayout()
        self.input = QLineEdit()
        self.result_box = QTextEdit()
        self.page_info = QLabel()
        self.result_box.setReadOnly(True)
        search_button = QPushButton("Ara")
        search_button.clicked.connect(self.search)
        self.input.returnPressed.connect(self.search)

        nav = QHBoxLayout()
        prev = QPushButton("← Geri")
        next = QPushButton("İleri →")
        prev.clicked.connect(self.prev_page)
        next.clicked.connect(self.next_page)
        nav.addWidget(prev)
        nav.addWidget(next)

        layout.addWidget(self.input)
        layout.addWidget(self.result_box)
        layout.addWidget(self.page_info)
        layout.addLayout(nav)
        layout.addWidget(search_button)
        self.setLayout(layout)

    def search(self):
        keyword = self.input.text().strip()
        self.results = [e for e in MEAL_DATA if keyword.lower() in e["turkce"].lower()]
        self.current_page = 0
        self.show_results()

    def show_results(self):
        start = self.current_page * self.results_per_page
        end = start + self.results_per_page
        display = self.results[start:end]
        out = f"<b>Toplam ({len(self.results)}) eşleşme bulundu.</b><br><br>"

        for e in display:
            out += f"<b>Sure:</b> {e['sure']} | <b>Ayet:</b> {e['ayet']}<br>"
            out += f"<b>Transkripsiyon:</b><br> <i>{clean_html(e.get('arapca', ''))}</i><br>"
            out += f"<b>Arapça:</b><br> {e.get('arapca', '')}<br>"
            out += f"<b>Türkçe:</b><br> {highlight(e['turkce'], self.input.text())}<br><hr>"

        self.page_info.setText(f"{self.current_page+1}/{(len(self.results)-1)//self.results_per_page+1}")
        self.result_box.setHtml(out)

    def next_page(self):
        if (self.current_page + 1) * self.results_per_page < len(self.results):
            self.current_page += 1
            self.show_results()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_results()

# --- Sekme 2: Kelime Arama ---
class KelimeTab(QWidget):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_page = 0
        self.results_per_page = 20

        layout = QVBoxLayout()
        self.input = QLineEdit()
        self.result_box = QTextEdit()
        self.page_info = QLabel()
        self.result_box.setReadOnly(True)
        search_button = QPushButton("Ara")
        search_button.clicked.connect(self.search)
        self.input.returnPressed.connect(self.search)

        nav = QHBoxLayout()
        prev = QPushButton("← Geri")
        next = QPushButton("İleri →")
        prev.clicked.connect(self.prev_page)
        next.clicked.connect(self.next_page)
        nav.addWidget(prev)
        nav.addWidget(next)

        layout.addWidget(self.input)
        layout.addWidget(self.result_box)
        layout.addWidget(self.page_info)
        layout.addLayout(nav)
        layout.addWidget(search_button)
        self.setLayout(layout)

    def search(self):
        keyword = self.input.text().strip().lower()
        self.results = [e for e in KELIME_DATA if keyword in json.dumps(e, ensure_ascii=False).lower()]
        self.current_page = 0
        self.show_results()

    def show_results(self):
        start = self.current_page * self.results_per_page
        end = start + self.results_per_page
        display = self.results[start:end]
        out = f"<b>Toplam ({len(self.results)}) eşleşme bulundu.</b><br><br>"

        for e in display:
            for k, v in e.items():
                out += f"<b>{k}:</b> {highlight(str(v), self.input.text())}<br>"
            out += "<hr>"

        self.page_info.setText(f"{self.current_page+1}/{(len(self.results)-1)//self.results_per_page+1}")
        self.result_box.setHtml(out)

    def next_page(self):
        if (self.current_page + 1) * self.results_per_page < len(self.results):
            self.current_page += 1
            self.show_results()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_results()

# --- Ana Uygulama ---
class QuranApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kur'an Arama Sistemi (İkili Veri)")
        layout = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(MealTab(), "Mealli Arama")
        tabs.addTab(KelimeTab(), "Kelime Arama")
        layout.addWidget(tabs)
        self.setLayout(layout)

app = QApplication(sys.argv)
window = QuranApp()
window.resize(950, 700)
window.show()
sys.exit(app.exec_())

