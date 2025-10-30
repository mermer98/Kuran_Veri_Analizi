# components/analysis_tab.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from utils.veri_isleyici import veri_yukle
from collections import Counter
import re

class AnalysisTab(QWidget):
    def __init__(self):
        super().__init__()
        self.veriler = veri_yukle()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        layout.addWidget(QLabel("📊 Kur’an Verileri Analizi"))
        layout.addWidget(self.result_area)

        self.setLayout(layout)
        self.analyze()

    def analyze(self):
        toplam_ayet = len(self.veriler)
        sure_ayet_sayilari = {}
        turkce_tum_kelime = []
        arapca_tum_kelime = []

        for ayet in self.veriler:
            sure = ayet['sure']
            sure_ayet_sayilari[sure] = sure_ayet_sayilari.get(sure, 0) + 1

            turkce_kelimeler = re.findall(r'\b\w+\b', ayet['turkce'].lower())
            arapca_kelimeler = re.findall(r'\b\w+\b', ayet['arapca'])

            turkce_tum_kelime.extend(turkce_kelimeler)
            arapca_tum_kelime.extend(arapca_kelimeler)

        en_uzun_sure = max(sure_ayet_sayilari.items(), key=lambda x: x[1])
        en_kisa_sure = min(sure_ayet_sayilari.items(), key=lambda x: x[1])

        turkce_sayac = Counter(turkce_tum_kelime)
        arapca_sayac = Counter(arapca_tum_kelime)

        en_sik_turkce = turkce_sayac.most_common(10)
        en_sik_arapca = arapca_sayac.most_common(10)

        html = "<b>Toplam Ayet:</b> {}<br>".format(toplam_ayet)
        html += "<b>Toplam Sure:</b> {}<br><br>".format(len(sure_ayet_sayilari))

        html += "<b>📘 En Uzun Sure:</b> {} ({} ayet)<br>".format(en_uzun_sure[0], en_uzun_sure[1])
        html += "<b>📗 En Kısa Sure:</b> {} ({} ayet)<br><br>".format(en_kisa_sure[0], en_kisa_sure[1])

        html += "<b>🔡 En Sık Geçen Türkçe Kelimeler:</b><br>"
        for kelime, adet in en_sik_turkce:
            html += f"&nbsp;&nbsp;• <span style='color:green'>{kelime}</span>: {adet} kez<br>"

        html += "<br><b>🔠 En Sık Geçen Arapça Kelimeler:</b><br>"
        for kelime, adet in en_sik_arapca:
            html += f"&nbsp;&nbsp;• <span style='color:maroon'>{kelime}</span>: {adet} kez<br>"

        self.result_area.setHtml(html)
