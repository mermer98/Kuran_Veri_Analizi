#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kur'an Veri Analizi Programi - Ana Dosya
Tam işlevli Kur'an Arama ve Veri Analizi Arayüzü
"""

import sys
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QLineEdit, QTextBrowser, QPushButton, QTabWidget, 
                             QHBoxLayout, QGridLayout)
from PyQt5.QtGui import QTextCursor, QFont
from PyQt5.QtCore import Qt

# Global Sabitler
SONUC_SAYISI = 20
VERI_YOLU = "kuran_veri.json"

class KuranArama(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kur'an Arama ve Veri Analizi")
        self.resize(1000, 700)

        self.sonuc_index = 0
        self.sonuc_listesi = []

        # Ana Sekmeler
        self.tabs = QTabWidget()
        self.kelime_tab = QWidget()
        self.analiz_tab = QWidget()
        self.tabs.addTab(self.kelime_tab, "Kelime Arama")
        self.tabs.addTab(self.analiz_tab, "Veri Analizi")

        self.arayuz_kelime_arama()
        self.arayuz_veri_analiz()

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.veri_yukle()

    def veri_yukle(self):
        with open(VERI_YOLU, "r", encoding="utf-8") as f:
            self.veri = json.load(f)

    # --- Sekme 1: Kelime Arama ---
    def arayuz_kelime_arama(self):
        layout = QVBoxLayout()

        self.ara_input = QLineEdit()
        self.ara_input.setPlaceholderText("Bir kelime yazın...")
        self.ara_input.returnPressed.connect(self.ara)

        self.sonuc_goster = QTextBrowser()
        self.sonuc_goster.setFont(QFont("Courier", 11))
        self.sonuc_goster.setOpenExternalLinks(True)

        self.label_bilgi = QLabel("Sonuç bilgisi burada görünür")

        # Sayfalama
        sayfa_kutu = QHBoxLayout()
        self.btn_geri = QPushButton("< Geri")
        self.btn_ileri = QPushButton("İleri >")
        self.sayfa_label = QLabel("Sayfa 0/0")
        self.btn_geri.clicked.connect(self.sayfa_geri)
        self.btn_ileri.clicked.connect(self.sayfa_ileri)
        sayfa_kutu.addWidget(self.btn_geri)
        sayfa_kutu.addWidget(self.sayfa_label)
        sayfa_kutu.addWidget(self.btn_ileri)

        layout.addWidget(self.ara_input)
        layout.addWidget(self.label_bilgi)
        layout.addWidget(self.sonuc_goster)
        layout.addLayout(sayfa_kutu)

        self.kelime_tab.setLayout(layout)

    def ara(self):
        kelime = self.ara_input.text().strip()
        if not kelime:
            return

        self.sonuc_listesi = []
        for veri in self.veri:
            if kelime.lower() in veri["turkce"].lower():
                self.sonuc_listesi.append(veri)

        self.sonuc_index = 0
        self.guncelle_sonuc()

    def guncelle_sonuc(self):
        toplam = len(self.sonuc_listesi)
        if toplam == 0:
            self.label_bilgi.setText("Sonuç bulunamadı.")
            self.sonuc_goster.clear()
            self.sayfa_label.setText("0/0")
            return

        basla = self.sonuc_index * SONUC_SAYISI
        bitir = basla + SONUC_SAYISI
        gosterilecekler = self.sonuc_listesi[basla:bitir]

        html = ""
        for i, ayet in enumerate(gosterilecekler):
            html += f"""
            <div style='background-color:#f0f0f0; margin:10px; padding:10px;'>
                <b>Sure {ayet['sure']}, Ayet {ayet['ayet']}</b><br>
                <i>Arapça:</i> {ayet['arapca']}<br>
                <i>Transkripsiyon:</i> {ayet.get('transkripsiyon', '-') }<br>
                <i>Meali:</i> {ayet['turkce'].replace(self.ara_input.text(), f"<span style='color:green;font-weight:bold'>{self.ara_input.text()}</span>")}
            </div>
            """

        self.sonuc_goster.setHtml(html)
        sayfa_sayisi = (len(self.sonuc_listesi) - 1) // SONUC_SAYISI + 1
        self.sayfa_label.setText(f"Sayfa {self.sonuc_index+1} / {sayfa_sayisi}")
        self.label_bilgi.setText(f"Toplam {len(self.sonuc_listesi)} sonuç bulundu.")

    def sayfa_ileri(self):
        if (self.sonuc_index + 1) * SONUC_SAYISI < len(self.sonuc_listesi):
            self.sonuc_index += 1
            self.guncelle_sonuc()

    def sayfa_geri(self):
        if self.sonuc_index > 0:
            self.sonuc_index -= 1
            self.guncelle_sonuc()

    # --- Sekme 2: Veri Analizi (Hazırlanacak) ---
    def arayuz_veri_analiz(self):
        layout = QVBoxLayout()
        label = QLabel("Veri analizi burada görüntülenecek. (Hazırlanıyor...)")
        layout.addWidget(label)
        self.analiz_tab.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pencere = KuranArama()
    pencere.show()
    sys.exit(app.exec_())
