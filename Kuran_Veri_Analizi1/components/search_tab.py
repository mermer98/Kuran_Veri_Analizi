# components/search_tab.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTextEdit, QPushButton, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
from utils.veri_isleyici import veri_yukle

class SearchTab(QWidget):
    def __init__(self):
        super().__init__()
        self.veriler = veri_yukle()
        self.current_page = 0
        self.results_per_page = 20
        self.filtered = []

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.input = QLineEdit()
        self.input.setPlaceholderText("Kelime, kök veya ayet numarası yazın...")
        self.input.textChanged.connect(self.guncelle_sayfa)
        layout.addWidget(self.input)

        self.info_label = QLabel("")
        layout.addWidget(self.info_label)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        layout.addWidget(self.result_box)

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("← Geri")
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn = QPushButton("İleri →")
        self.next_btn.clicked.connect(self.next_page)

        self.page_label = QLabel("Sayfa: 1")
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(self.next_btn)
        layout.addLayout(nav_layout)

        self.setLayout(layout)

    def guncelle_sayfa(self):
        aranan = self.input.text().strip().lower()
        self.filtered = []

        if aranan.isdigit():
            # ID'ye göre arama
            id_no = int(aranan)
            for ayet in self.veriler:
                if ayet['id'] == id_no:
                    self.filtered = [ayet]
                    break
        elif '/' in aranan and aranan.replace('/', '').isdigit():
            # Sure/Ayet formatı: 114/6
            parts = aranan.split('/')
            if len(parts) == 2:
                sure, ayet = int(parts[0]), int(parts[1])
                for verse in self.veriler:
                    if verse['sure'] == sure and verse['ayet'] == ayet:
                        self.filtered = [verse]
                        break
        else:
            # Metin arama
            for ayet in self.veriler:
                if aranan in ayet['turkce'].lower() or aranan in ayet['arapca'].lower():
                    self.filtered.append(ayet)

        self.current_page = 0
        self.show_results()

    def show_results(self):
        total = len(self.filtered)
        if total == 0:
            self.result_box.setText("Sonuç bulunamadı.")
            self.page_label.setText("Sayfa: -")
            self.info_label.setText("")
            return

        start = self.current_page * self.results_per_page
        end = start + self.results_per_page
        current_results = self.filtered[start:end]

        text = ""
        for ayet in current_results:
            turkce = ayet['turkce'].replace(self.input.text(), f"<b><span style='color:green'>{self.input.text()}</span></b>")
            arapca = ayet['arapca'].replace(self.input.text(), f"<b><span style='color:darkred'>{self.input.text()}</span></b>")
            text += (
                f"<b>Süre {ayet['sure']} Ayet {ayet['ayet']}:</b><br>"
                f"<span style='color:darkblue'>Türkçe:</span> {turkce}<br>"
                f"<span style='color:brown'>Arapça:</span> <div dir='rtl'>{arapca}</div><br><hr>"
            )

        self.result_box.setHtml(text)
        toplam_sayfa = (len(self.filtered) - 1) // self.results_per_page + 1
        self.page_label.setText(f"Sayfa: {self.current_page + 1} / {toplam_sayfa}")
        self.info_label.setText(f"Toplam {len(self.filtered)} eşleşme bulundu.")

    def next_page(self):
        if (self.current_page + 1) * self.results_per_page < len(self.filtered):
            self.current_page += 1
            self.show_results()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_results()
