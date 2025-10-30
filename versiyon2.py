import sys
import json
import re
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QTextEdit
from PyQt5.QtGui import QTextCursor

KAVRAMLAR = {
    "adalet": ["adalet", "adil", "muadil", "ya’dil"],
    "küfür": ["küfür", "kafir", "küfretmek", "inkâr"],
    "cin": ["cin", "cinler", "cinni"]
}

class QuranSearchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kur'an-ı Kerim Arama (PyQt5)")

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Ayet veya kelime ara:")
        self.search_box.textChanged.connect(self.search)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.search_box)
        layout.addWidget(self.result_box)
        self.setLayout(layout)

        with open("kelime_manali_kuran_ve_turkce_meali.json", "r", encoding="utf-8") as f:
            self.dataset = json.load(f)

    def search(self):
        keyword = self.search_box.text().strip()
        results = []

        kelimeler = KAVRAMLAR.get(keyword, [keyword])

        for entry in self.dataset:
            arapca = entry.get("arapca", "")
            turkce = entry.get("turkce", "")
            if any(k in arapca or k in turkce for k in kelimeler):
                results.append(entry)

        self.display_results(results, kelimeler)

    def highlight_keywords(self, text, kelimeler):
        total_matches = 0
        for kelime in kelimeler:
            pattern = re.escape(kelime)
            text, count = re.subn(f"({pattern})", r"<span style='background-color: yellow;'>\1</span>", text, flags=re.IGNORECASE)
            total_matches += count
        return text, total_matches

    def display_results(self, results, kelimeler):
        self.result_box.clear()

        if not results:
            self.result_box.setText("❗ Sonuç bulunamadı.")
            return

        html_output = ""
        total_occurrences = 0

        for r in results:
            sure = r.get("sure")
            ayet = r.get("ayet")
            arapca_raw = r.get("arapca", "").strip()
            turkce_raw = r.get("turkce", "").strip()

            arapca, count_ar = self.highlight_keywords(arapca_raw, kelimeler)
            turkce, count_tr = self.highlight_keywords(turkce_raw, kelimeler)
            total_occurrences += count_ar + count_tr

            html_output += f'<p style="color:blue; font-weight:bold;">🧷 {sure}/{ayet}</p>'
            html_output += f'<p style="color:#007A22; font-size:22px; direction:rtl; text-align:right;">{arapca}</p>'
            html_output += f'<p style="color:#000000; font-size:14px;">{turkce}</p><hr>'

        # Arama özeti en başta gösterilsin:
        summary = f"<p style='color:gray;'>🔍 Aranan kelime(ler) <b>{len(results)}</b> ayette, <b>{total_occurrences}</b> defa geçti.</p><hr>"
        html_output = summary + html_output

        self.result_box.setHtml(html_output)
        self.result_box.moveCursor(QTextCursor.Start)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QuranSearchApp()
    window.resize(900, 700)
    window.show()
    sys.exit(app.exec_())
