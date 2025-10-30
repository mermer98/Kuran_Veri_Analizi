# ------------------------------
# kuran_veri_analiz/main.py
# ------------------------------

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton,
    QLabel, QTextEdit, QHBoxLayout, QTabWidget, QScrollArea, QMessageBox
)
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
from PyQt5.QtCore import Qt
import sys
from utils.veri_isleyici import veri_yukle
from yardimci_araclar import vurgula, kelime_sayaci, transkripsiyon_olustur


class QuranAnalyzer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kuran Veri Analiz Programı")
        self.resize(1200, 800)
        self.veriler = veri_yukle()
        self.sayfa = 0
        self.satirSayisi = 20

        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        # Arama barı
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Kelime, kök, ayet no veya sıra giriniz")
        self.search_input.textChanged.connect(self.guncelle_sayfa)
        self.layout.addWidget(self.search_input)

        # Sekmeli alan
        self.tabs = QTabWidget()
        self.arama_tab = QWidget()
        self.arama_layout = QVBoxLayout(self.arama_tab)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget) # Create layout here
        self.scroll_area.setWidget(self.scroll_widget)

        self.arama_layout.addWidget(self.scroll_area)
        self.tabs.addTab(self.arama_tab, "Arama")

        self.layout.addWidget(self.tabs)

        # Sayfalama
        sayfalama = QHBoxLayout()
        self.onceki_btn = QPushButton("◀ Önceki")
        self.sonraki_btn = QPushButton("Sonraki ▶")
        self.onceki_btn.clicked.connect(self.onceki_sayfa)
        self.sonraki_btn.clicked.connect(self.sonraki_sayfa)
        sayfalama.addWidget(self.onceki_btn)
        sayfalama.addWidget(self.sonraki_btn)
        self.layout.addLayout(sayfalama)

        self.guncelle_sayfa()

    def guncelle_sayfa(self):
        # Clear existing widgets in the layout
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        kelime = self.search_input.text().strip()
        if kelime == "":
            sonuclar = self.veriler
        else:
            sonuclar = [v for v in self.veriler if kelime in v["arapca"] or kelime in v["turkce"]]

        self.toplam_sayfa = max(1, len(sonuclar) // self.satirSayisi + (1 if len(sonuclar) % self.satirSayisi else 0))
        basla = self.sayfa * self.satirSayisi
        bitis = basla + self.satirSayisi
        for v in sonuclar[basla:bitis]:
            kutu = QTextEdit()
            kutu.setReadOnly(True)
            kutu.setStyleSheet("background-color: #f1f1f1; padding: 10px; border-radius: 8px;")
            arapca = vurgula(v["arapca"], kelime)
            turkce = vurgula(v["turkce"], kelime)
            transcript = transkripsiyon_olustur(v["arapca"])
            kutu.setHtml(f"""
                <b><u>{v['sure']}/{v['ayet']}</u></b><br><br>
                <div style='font-size:20px; color:#2e5aa7'>{arapca}</div>
                <div style='font-size:15px; color:#555'><i>{transcript}</i></div><br>
                <div style='font-size:16px; color:#000'>{turkce}</div>
            """)
            self.scroll_layout.addWidget(kutu)

        # Sonuç sayısı
        if kelime:
            adet = kelime_sayaci(sonuclar, kelime)
            label = QLabel(f"<b>Kelime:</b> '{kelime}' <b>{adet}</b> kez geçiyor.")
            self.scroll_layout.addWidget(label)


    def onceki_sayfa(self):
        if self.sayfa > 0:
            self.sayfa -= 1
            self.guncelle_sayfa()

    def sonraki_sayfa(self):
        if self.sayfa < self.toplam_sayfa - 1:
            self.sayfa += 1
            self.guncelle_sayfa()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QuranAnalyzer()
    window.show()
    sys.exit(app.exec_())