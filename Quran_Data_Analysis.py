import sys
import json
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QLabel, QTextEdit,
    QLineEdit, QPushButton, QHBoxLayout, QTextBrowser
)
from PyQt5.QtGui import QTextCursor, QFont


with open("kelime_manali_kuran_ve_turkce_meali.json", encoding="utf-8") as f:
    KELIME_DATA = json.load(f)

class QuranAnalyzer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kur'an Veri Analizi")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Buraya analizler gelecek..."))
        self.setLayout(layout)

class QuranSearch(QWidget):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_page = 0
        self.results_per_page = 20

        self.input = QLineEdit()
        self.input.setPlaceholderText("Bir kelime yazın...")
        self.input.returnPressed.connect(self.search)

        self.search_button = QPushButton("Ara")
        self.search_button.clicked.connect(self.search)

        self.info_label = QLabel("")

        self.result_box = QTextBrowser()
        self.result_box.setOpenExternalLinks(True)

        self.prev_button = QPushButton("< Geri")
        self.prev_button.clicked.connect(self.prev_page)

        self.next_button = QPushButton("İleri >")
        self.next_button.clicked.connect(self.next_page)

        self.page_label = QLabel("")

        nav = QHBoxLayout()
        nav.addWidget(self.prev_button)
        nav.addWidget(self.page_label)
        nav.addWidget(self.next_button)

        top = QHBoxLayout()
        top.addWidget(self.input)
        top.addWidget(self.search_button)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.info_label)
        layout.addWidget(self.result_box)
        layout.addLayout(nav)
        self.setLayout(layout)

    def highlight(self, text, keyword):
        return re.sub(f"({re.escape(keyword)})", r'<b style="background:yellow">\1</b>', text, flags=re.IGNORECASE)

    def search(self):
        keyword = self.input.text().strip()
        if not keyword:
            return
        self.results = [entry for entry in KELIME_DATA if keyword in entry.get("turkce", "")]
        self.current_page = 0
        self.update_results()

    def update_results(self):
        total = len(self.results)
        if total == 0:
            self.info_label.setText("Sonuç bulunamadı.")
            self.result_box.setText("")
            self.page_label.setText("")
            return

        self.info_label.setText(f"Toplam {total} eşleşme bulundu.")
        start = self.current_page * self.results_per_page
        end = start + self.results_per_page
        display = self.results[start:end]

        output = ""
        for entry in display:
            output += """
                <div style='background:#eee; padding:10px; margin-bottom:10px;'>
                <b>Süre:</b> {sure} <b>Ayet:</b> {ayet}<br>
                <b>Türkçe:</b> {turkce}<br>
                <b>(Okunuş: Eklenmedi)</b><br>
                <b>Arapça:</b><br><div dir='rtl'>{arapca}</div>
                </div>
            """.format(
                sure=entry.get("sure", "-"),
                ayet=entry.get("ayet", "-"),
                turkce=self.highlight(entry.get("turkce", ""), self.input.text()),
                arapca=self.highlight(entry.get("arapca", ""), self.input.text())
            )

        total_pages = (total - 1) // self.results_per_page + 1
        self.page_label.setText(f"Sayfa {self.current_page+1} / {total_pages}")
        self.result_box.setHtml(output)
        self.result_box.moveCursor(QTextCursor.Start)

    def next_page(self):
        if self.current_page < (len(self.results) - 1) // self.results_per_page:
            self.current_page += 1
            self.update_results()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_results()


class QuranApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kur'an Arama ve Analiz")
        layout = QVBoxLayout()

        tabs = QTabWidget()
        tabs.addTab(QuranSearch(), "Kelime Arama")
        tabs.addTab(QuranAnalyzer(), "Veri Analizi")

        layout.addWidget(tabs)
        self.setLayout(layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QuranApp()
    window.resize(1000, 700)
    window.show()
    sys.exit(app.exec_())
