import sys
import json
import re
from collections import Counter
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QTextEdit, QListWidget, QListWidgetItem,
                             QLabel, QSplitter, QComboBox, QCheckBox, QTabWidget, QMessageBox,
                             QTreeWidget, QTreeWidgetItem, QHeaderView, QGroupBox, QSpinBox,
                             QTextBrowser, QToolTip, QFileDialog, QDialog, QFormLayout, QDialogButtonBox) # Added QFileDialog, QDialog, QFormLayout, QDialogButtonBox
from PyQt5.QtCore import Qt, QSize, QPoint, QUrl, QEvent # Added QEvent
from PyQt5.QtGui import QFont, QIcon, QColor, QCursor
import numpy as np
from wordcloud import WordCloud
import arabic_reshaper
from bidi.algorithm import get_display
import colorsys
import sqlite3 # Added sqlite3

class QuranAnalyzerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kur'an Veri Analiz Uygulaması")
        self.setGeometry(100, 100, 1400, 900)

        # Verileri yükle
        self.load_data()

        # Favorileri yükle
        self.favorites = self.load_favorites()

        # Sözlük veritabanını aç
        self.dict_db_path = 'sozluk_veritabani.db'   # aynı klasörde
        self._init_dictionary_db()

        # GUI bileşenlerini oluştur
        self.init_ui()
        self._ensure_tooltip_store() # Initialize tooltip storage

    def load_data(self):
        # JSON dosyalarını yükle
        try:
            with open('kelime_manali_kuran_ve_turkce_meali.json', 'r', encoding='utf-8') as f:
                self.verse_data = json.load(f)

            with open('kurani_kerimdeki_tum_kelimeler.json', 'r', encoding='utf-8') as f:
                self.word_data = json.load(f)

            # Ek veri yapıları oluştur
            self.create_additional_data_structures()

        except FileNotFoundError:
            QMessageBox.critical(self, "Hata", "JSON dosyaları bulunamadı!")
            sys.exit(1)

    def create_additional_data_structures(self):
        # Kelime indeksi oluştur
        self.word_index = {}
        for word in self.word_data:
            key = (word['sureNo'], word['ayetNo'], word['kelimeNo'])
            self.word_index[key] = word

        # Ayet indeksi oluştur
        self.verse_index = {}
        for verse in self.verse_data:
            key = (verse['sure'], verse['ayet'])
            self.verse_index[key] = verse

        # Kök indeksi oluştur
        self.root_index = {}
        for word in self.word_data:
            root = word.get('kok', '').strip()
            if root:
                if root not in self.root_index:
                    self.root_index[root] = []
                self.root_index[root].append(word)

        # Türkçe kelime indeksi oluştur
        self.turkish_index = {}
        for word in self.word_data:
            turkce = word.get('turkce', '').lower().strip()
            # Özel karakterleri temizle
            turkce = re.sub(r'[%&]', '', turkce)
            if turkce:
                if turkce not in self.turkish_index:
                    self.turkish_index[turkce] = []
                self.turkish_index[turkce].append(word)

        # Arapça kelime indeksi oluştur
        self.arabic_index = {}
        for word in self.word_data:
            arapca = word.get('arapca', '').strip()
            if arapca:
                if arapca not in self.arabic_index:
                    self.arabic_index[arapca] = []
                self.arabic_index[arapca].append(word)

    def _init_dictionary_db(self):
        self.dict_conn = sqlite3.connect(self.dict_db_path)
        cur = self.dict_conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS entries(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kelime TEXT UNIQUE,
                telaffuz TEXT,
                koken TEXT,
                anlam TEXT,
                ornek TEXT
            )
        """)
        self.dict_conn.commit()

    def load_favorites(self):
        try:
            with open('favorites.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def save_favorites(self):
        with open('favorites.json', 'w', encoding='utf-8') as f:
            json.dump(self.favorites, f, ensure_ascii=False, indent=2)

    def init_ui(self):
        # Merkezi widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Ana layout
        main_layout = QHBoxLayout(central_widget)

        # Sol panel (arama ve sonuçlar)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Arama grubu
        search_group = QGroupBox("Arama")
        search_layout = QVBoxLayout(search_group)

        # Arama satırı
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Arama yapın... (örn: 1/1, adalet, a:الله, kök:ع ل م)")
        self.search_input.returnPressed.connect(self.search)
        search_layout.addWidget(self.search_input)

        self.search_button = QPushButton("Ara")
        self.search_button.clicked.connect(self.search)
        search_layout.addWidget(self.search_button)

        # Arama seçenekleri
        options_row = QHBoxLayout()

        self.search_type = QComboBox()
        self.search_type.addItems(["Tümü", "Arapça", "Türkçe", "Kök", "Sure/Ayet"])
        options_row.addWidget(QLabel("Arama Türü:"))
        options_row.addWidget(self.search_type)

        self.mekki_check = QCheckBox("Mekki")
        self.medeni_check = QCheckBox("Medeni")
        options_row.addWidget(self.mekki_check)
        options_row.addWidget(self.medeni_check)

        search_layout.addLayout(options_row)

        left_layout.addWidget(search_group)

        # Sonuçlar listesi
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.show_verse_details)
        left_layout.addWidget(self.results_list)

        # Sağ panel (ayet detayları ve analiz)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Sekmeler
        self.tabs = QTabWidget()

        # Ayet detayları sekmesi
        self.verse_tab = QWidget()
        verse_layout = QVBoxLayout(self.verse_tab)

        # self.verse_display = QTextEdit() # Original QTextEdit
        # self.verse_display.setReadOnly(True) # Original readOnly setting

        self.verse_display = QTextBrowser() # Changed to QTextBrowser
        self.verse_display.setOpenExternalLinks(False)
        self.verse_display.setOpenLinks(False)
        self.verse_display.highlighted.connect(self._on_anchor_hover)
        # self.verse_display.anchorClicked.connect(self._on_anchor_clicked) # Connected anchorClicked


        verse_layout.addWidget(self.verse_display)

        # ↓↓↓ fare olaylarını biz de dinleyelim
        self.verse_display.viewport().installEventFilter(self)


        verse_layout.addWidget(self.verse_display)

        # Bağlam butonları
        context_buttons = QHBoxLayout()
        self.prev_button = QPushButton("Önceki Ayet")
        self.prev_button.clicked.connect(self.show_previous_verse)
        context_buttons.addWidget(self.prev_button)

        self.next_button = QPushButton("Sonraki Ayet")
        self.next_button.clicked.connect(self.show_next_verse)
        context_buttons.addWidget(self.next_button)

        verse_layout.addLayout(context_buttons)

        # Favori butonu
        self.favorite_button = QPushButton("Favorilere Ekle")
        self.favorite_button.clicked.connect(self.toggle_favorite)
        verse_layout.addWidget(self.favorite_button)

        self.tabs.addTab(self.verse_tab, "Ayet Detayları")

        # İstatistikler sekmesi
        self.stats_tab = QWidget()
        stats_layout = QVBoxLayout(self.stats_tab)

        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        # Set a larger font for the statistics display
        font = self.stats_display.font()
        font.setPointSize(12) # You can adjust this size as needed
        self.stats_display.setFont(font)
        stats_layout.addWidget(self.stats_display)

        self.tabs.addTab(self.stats_tab, "İstatistikler")

        # Kavram ağı sekmesi
        self.network_tab = QWidget()
        network_layout = QVBoxLayout(self.network_tab)

        self.network_canvas = FigureCanvas(plt.figure())
        network_layout.addWidget(self.network_canvas)

        self.tabs.addTab(self.network_tab, "Kavram Ağı")

        # Kelime bulutu sekmesi
        self.wordcloud_tab = QWidget()
        wordcloud_layout = QVBoxLayout(self.wordcloud_tab)

        self.wordcloud_canvas = FigureCanvas(plt.figure())
        wordcloud_layout.addWidget(self.wordcloud_canvas)

        self.tabs.addTab(self.wordcloud_tab, "Kelime Bulutu")

        right_layout.addWidget(self.tabs)

        # Bölücü
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 1000])

        main_layout.addWidget(splitter)

        # Durum çubuğu
        self.statusBar().showMessage("Hazır")

    def _ensure_tooltip_store(self):
        if not hasattr(self, "kelime_tooltips"):
            self.kelime_tooltips = {}  # key: "kelime://<sure>/<ayet>/<kelimeNo>"

    def _on_anchor_hover(self, url):
        s = str(url) if url else ""
        if not s:
            QToolTip.hideText()
            return
        tip = getattr(self, "kelime_tooltips", {}).get(s, "")
        if tip:
            QToolTip.showText(QCursor.pos(), tip)

    def _on_anchor_clicked(self, url):
        print(f"DEBUG: _on_anchor_clicked called with url: {url}")
        try:
            if not isinstance(url, QUrl):
                print("DEBUG: url is not QUrl")
                return
            if url.scheme() != "kelime":
                print(f"DEBUG: url scheme is not 'kelime': {url.scheme()}")
                return

            path = url.path().lstrip("/")
            print(f"DEBUG: Original URL path: {path}")

            # Split the entire path by '/'
            parts = path.split("/")
            print(f"DEBUG: Parts after splitting by '/': {parts}")

            sure = -1
            ayet = -1
            kelime_no = -1

            if len(parts) == 3:
                # Process the first part to extract the sure number
                first_part = parts[0]
                if first_part.startswith("0.0.0."):
                    sure_part = first_part.split("0.0.0.")[1]
                    if sure_part.isdigit():
                        sure = int(sure_part)
                    else:
                        print(f"DEBUG: Could not extract sure from '{first_part}' after removing '0.0.0.'")
                        return
                elif first_part.isdigit():
                    # Handle the case where there is no "0.0.0." prefix
                    sure = int(first_part)
                else:
                    print(f"DEBUG: First part is not a valid sure number: {first_part}")
                    return

                # Process the second and third parts for ayet and kelime_no
                if parts[1].isdigit() and parts[2].isdigit():
                    ayet = int(parts[1])
                    kelime_no = int(parts[2])
                else:
                    print(f"DEBUG: Ayet or kelime_no parts are not digits: {parts[1]}, {parts[2]}")
                    return
            else:
                # This case is reached when path is like "13/10" resulting in parts ['13', '10']
                # We need to handle this specific format correctly.
                if len(parts) == 2 and all(p.isdigit() for p in parts):
                     # Assuming the format is ayet/kelimeNo when 0.0.0.sure is missing
                     # This might be an incorrect assumption based on the anchor format
                     print("DEBUG: Assuming path is ayet/kelimeNo format, attempting to use current verse sure.")
                     if hasattr(self, 'current_verse') and self.current_verse:
                          sure = self.current_verse[0]
                          ayet = int(parts[0])
                          kelime_no = int(parts[1])
                          print(f"DEBUG: Extracted using current verse sure - Sure: {sure}, Ayet: {ayet}, KelimeNo: {kelime_no}")
                     else:
                          print("DEBUG: Cannot parse ayet/kelimeNo format without a current verse.")
                          return

                else:
                    print("DEBUG: Incorrect number of parts in URL path or parts are not digits.")
                    return


            print(f"DEBUG: Extracted Sure: {sure}, Ayet: {ayet}, KelimeNo: {kelime_no}")

            # Validate extracted numbers (optional, as isdigit() check is done above)
            if sure <= 0 or ayet <= 0 or kelime_no <= 0:
                 print("DEBUG: Extracted numbers are not valid positive integers")
                 return


            w = next((x for x in self.word_data
                      if x['sureNo']==sure and x['ayetNo']==ayet and x['kelimeNo']==kelime_no), None)
            print(f"DEBUG: Found word data: {w}")

            if not w:
                print("DEBUG: Word data not found")
                return
            turkce = w.get('turkce','').strip()
            print(f"DEBUG: Turkish word: {turkce}")
            # Sözlük penceresini aç
            self._show_dictionary_popup(turkce, w)
            print("DEBUG: _show_dictionary_popup called")

        except Exception as e:
            print(f"DEBUG: Exception in _on_anchor_clicked: {e}")
            QMessageBox.warning(self, "Hata", f"Tıklama işlenemedi:\n{e}")


    def _fetch_dict_entry(self, kelime):
        cur = self.dict_conn.cursor()
        cur.execute("SELECT kelime,telaffuz,koken,anlam,ornek FROM entries WHERE kelime=?", (kelime,))
        row = cur.fetchone()
        if row:
            return {"kelime":row[0], "telaffuz":row[1], "koken":row[2], "anlam":row[3], "ornek":row[4]}
        return None


    def _show_dictionary_popup(self, kelime, word_data):
        print(f"DEBUG: _show_dictionary_popup called with kelime: {kelime}")
        data = self._fetch_dict_entry(kelime)
        print(f"DEBUG: Dictionary data fetched: {data}")

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Sözlük: {kelime}")
        lay = QVBoxLayout(dlg)

        # gösterim alanı
        text = QTextEdit(); text.setReadOnly(True)
        if data:
            text.setHtml(
                f"<h3>{data['kelime']}</h3>"
                f"<p><b>Telaffuz:</b> {data['telaffuz'] or '-'}<br>"
                f"<b>Köken:</b> {data['koken'] or '-'}<br>"
                f"<b>Anlam:</b> {data['anlam'] or '-'}<br>"
                f"<b>Örnek:</b> {data['ornek'] or '-'}</p>"
            )
        else:
            text.setHtml("<i>Bu kelime sözlükte bulunamadı.</i>")
        lay.addWidget(text)

        btns = QDialogButtonBox()
        btn_add = btns.addButton("Yeni Ekle", QDialogButtonBox.ActionRole)
        btn_close = btns.addButton("Kapat", QDialogButtonBox.RejectRole)
        lay.addWidget(btns)

        def add_new():
            self._show_add_entry_dialog(kelime)

        btn_add.clicked.connect(add_new)
        btn_close.clicked.connect(dlg.reject)
        print("DEBUG: Executing dictionary dialog")
        dlg.exec_()
        print("DEBUG: Dictionary dialog closed")
        # --- Çift tıklama sonrası kelime seçimini temizle ---
        if hasattr(self, 'verse_display'):
            self.verse_display.setTextCursor(self.verse_display.textCursor())
            self.verse_display.moveCursor(self.verse_display.textCursor().End)
            self.verse_display.setTextCursor(self.verse_display.textCursor())


    def _show_add_entry_dialog(self, kelime_default=""):
        print(f"DEBUG: _show_add_entry_dialog called with kelime_default: {kelime_default}")
        dlg = QDialog(self); dlg.setWindowTitle("Yeni Kelime Ekle")
        form = QFormLayout(dlg)

        e_k = QLineEdit(kelime_default)
        e_t = QLineEdit()
        e_ko = QLineEdit()
        e_a = QTextEdit()
        e_o = QTextEdit()

        form.addRow("Kelime:", e_k)
        form.addRow("Telaffuz:", e_t)
        form.addRow("Köken:", e_ko)
        form.addRow("Anlam:", e_a)
        form.addRow("Örnek:", e_o)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        form.addRow(btns)

        def save():
            print("DEBUG: Save button clicked")
            kelime = e_k.text().strip()
            telaffuz = e_t.text().strip()
            koken = e_ko.text().strip()
            anlam = e_a.toPlainText().strip()
            ornek = e_o.toPlainText().strip()

            if not kelime or not anlam:
                print("DEBUG: Kelime or Anlam is empty")
                QMessageBox.warning(dlg, "Uyarı", "Kelime ve Anlam alanları boş bırakılamaz.")
                return

            cur = self.dict_conn.cursor()
            try:
                print(f"DEBUG: Inserting entry: {kelime}, {telaffuz}, {koken}, {anlam}, {ornek}")
                cur.execute("""
                    INSERT INTO entries (kelime, telaffuz, koken, anlam, ornek)
                    VALUES (?, ?, ?, ?, ?)
                """, (kelime, telaffuz, koken, anlam, ornek))
                self.dict_conn.commit()
                print("DEBUG: Insert successful, commit done")
                QMessageBox.information(dlg, "Başarılı", "Kelime sözlüğe eklendi.")
                dlg.accept()
                print("DEBUG: Add entry dialog accepted")
            except sqlite3.IntegrityError:
                print(f"DEBUG: IntegrityError: {kelime} already exists")
                QMessageBox.warning(dlg, "Uyarı", f"'{kelime}' kelimesi zaten sözlükte mevcut.")
            except Exception as e:
                print(f"DEBUG: Exception during save: {e}")
                QMessageBox.critical(dlg, "Hata", f"Tıklama işlenemedi:\n{e}")


        btns.accepted.connect(save)
        btns.rejected.connect(dlg.reject)

        print("DEBUG: Executing add entry dialog")
        dlg.exec_()
        print("DEBUG: Dictionary dialog closed")


    def search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        self.results_list.clear()

        # Arama türüne göre filtrele
        search_type = self.search_type.currentText()

        if search_type == "Sure/Ayet" or re.match(r'^\d+/\d+$', query):
            # Sure/ayet formatı: 1/1
            if '/' in query:
                parts = query.split('/')
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    sure, ayet = int(parts[0]), int(parts[1])
                    self.search_by_sure_ayet(sure, ayet)
        elif search_type == "Kök" or query.startswith('kök:'):
            # Kök arama
            root = query[4:] if query.startswith('kök:') else query
            self.search_by_root(root)
        elif query.startswith('a:'):
            # Arapça arama
            arabic_query = query[2:]
            self.search_arabic(arabic_query)
        elif query.startswith('t:'):
            # Türkçe arama
            turkish_query = query[2:]
            self.search_turkish(turkish_query)
        else:
            # Genel arama (hem Arapça hem Türkçe)
            self.search_general(query)

    def search_by_sure_ayet(self, sure, ayet):
        # Belirli bir sure ve ayeti ara
        for verse in self.verse_data:
            if verse['sure'] == sure and verse['ayet'] == ayet:
                item = QListWidgetItem(f"{sure}/{ayet} - {verse['turkce'][:50]}...")
                item.setData(Qt.UserRole, (sure, ayet))
                self.results_list.addItem(item)
                self.show_verse_details(item)  # Otomatik olarak detayı göster
                break

    def search_by_root(self, root):
        # Kök arama
        if root in self.root_index:
            words = self.root_index[root]
            # Benzersiz ayetleri bul
            verses = set()
            for word in words:
                verses.add((word['sureNo'], word['ayetNo']))

            # Sonuçları listele
            for sure, ayet in sorted(verses):
                verse = self.verse_index.get((sure, ayet))
                if verse:
                    item = QListWidgetItem(f"{sure}/{ayet} - {verse['turkce'][:50]}...")
                    item.setData(Qt.UserRole, (sure, ayet))
                    self.results_list.addItem(item)

    def search_arabic(self, query):
        # Arapça arama
        for arapca, words in self.arabic_index.items():
            if query in arapca:
                # Benzersiz ayetleri bul
                verses = set()
                for word in words:
                    verses.add((word['sureNo'], word['ayetNo']))

                # Sonuçları listele
                for sure, ayet in sorted(verses):
                    verse = self.verse_index.get((sure, ayet))
                    if verse:
                        item = QListWidgetItem(f"{sure}/{ayet} - {verse['turkce'][:50]}...")
                        item.setData(Qt.UserRole, (sure, ayet))
                        self.results_list.addItem(item)

    def search_turkish(self, query):
        # Türkçe arama
        query = query.lower()
        for turkce, words in self.turkish_index.items():
            if query in turkce:
                # Benzersiz ayetleri bul
                verses = set()
                for word in words:
                    verses.add((word['sureNo'], word['ayetNo']))

                # Sonuçları listele
                for sure, ayet in sorted(verses):
                    verse = self.verse_index.get((sure, ayet))
                    if verse:
                        item = QListWidgetItem(f"{sure}/{ayet} - {verse['turkce'][:50]}...")
                        item.setData(Qt.UserRole, (sure, ayet))
                        self.results_list.addItem(item)

    def search_general(self, query):
        # Genel arama (hem Arapça hem Türkçe)
        query = query.lower()

        # Önce Türkçe arama
        found_verses = set()
        for turkce, words in self.turkish_index.items():
            if query in turkce:
                for word in words:
                    found_verses.add((word['sureNo'], word['ayetNo']))

        # Sonra Arapça arama
        for arapca, words in self.arabic_index.items():
            if query in arapca:
                for word in words:
                    found_verses.add((word['sureNo'], word['ayetNo']))

        # Sonuçları listele
        for sure, ayet in sorted(found_verses):
            verse = self.verse_index.get((sure, ayet))
            if verse:
                item = QListWidgetItem(f"{sure}/{ayet} - {verse['turkce'][:50]}...")
                item.setData(Qt.UserRole, (sure, ayet))
                self.results_list.addItem(item)

    def show_verse_details(self, item):
        sure, ayet = item.data(Qt.UserRole)
        verse = self.verse_index.get((sure, ayet))

        if verse:
            self._ensure_tooltip_store()
            # Bu ayete ait kelimeleri al
            ayet_kelimeleri = [w for w in self.word_data if w['sureNo'] == sure and w['ayetNo'] == ayet]
            renkler = self.assign_colors_to_roots(ayet_kelimeleri)

            # --- Türkçe anlamı renklendir + tooltip’li link yap ---
            highlighted_turkish = verse['turkce']
            # uzun olanları önce değiştir (yanlış eşleşmeyi azaltır)
            for kelime in sorted(ayet_kelimeleri, key=lambda x: -len(x.get('turkce', ''))):
                turkce = kelime.get('turkce', '')
                kok = kelime.get('kok', '').strip()
                renk = renkler.get(kok, "black")
                url = f"kelime://{sure}/{ayet}/{kelime['kelimeNo']}"
                # tooltip metni
                tip = f"Arapça: {kelime.get('arapca', '-')}\nKök: {kok or '-'}\nAnlam: {turkce or '-'}"
                self.kelime_tooltips[url] = tip
                # anchor ile sar
                if turkce: # Only create a link if there is a Turkish word
                    repl = (f"<a href='{url}' style='text-decoration:none; color:{renk}; font-weight:bold'>"
                            f"{turkce}</a>")
                    highlighted_turkish = re.sub(fr"\b{re.escape(turkce)}\b", repl, highlighted_turkish, flags=re.IGNORECASE)

            # --- HTML’yi kur ---
            display_text = f"<h2>{sure}. sure, {ayet}. ayet</h2>"
            display_text += f"<h3>Arapça:</h3>"
            display_text += f"<p style='font-size: 16pt; text-align: right;'>{verse['arapca']}</p>"
            display_text += f"<h3>Türkçe Anlam:</h3>"
            display_text += f"<p>{highlighted_turkish}</p>"

            # Kelime Analizi tablosu (Anlam hücresini de tooltip’li link yapıyoruz)
            display_text += f"<h3>Kelime Analizi:</h3>"
            display_text += "<table border='1'><tr><th>Kelime</th><th>Arapça</th><th>Anlam</th><th>Kök</th></tr>"
            for kelime in sorted(ayet_kelimeleri, key=lambda x: x['kelimeNo']):
                kok = kelime.get('kok', '').strip()
                turkce = kelime.get('turkce', '')
                arapca = kelime.get('arapca', '')
                renk = renkler.get(kok, "black")
                url = f"kelime://{sure}/{ayet}/{kelime['kelimeNo']}"
                # tooltip metni
                tip = f"Arapça: {arapca or '-'}\nKök: {kok or '-'}\nAnlam: {turkce or '-'}"
                self.kelime_tooltips[url] = tip
                # Anlam hücresini link yap
                linked_turkce = f"<a href='{url}' style='text-decoration:none; color:{renk}'>{turkce}</a>"
                display_text += f"<tr><td>{kelime['kelimeNo']}</td><td style='text-align: right;'>{arapca}</td><td>{linked_turkce}</td><td>{kok}</td></tr>"
            display_text += "</table>"


            self.verse_display.setHtml(display_text)

            # İstatistikleri göster
            self.show_stats(sure, ayet)

            # Kavram ağı oluştur
            self.create_concept_network(sure, ayet)

            # Kelime bulutu oluştur
            self.create_wordcloud(sure, ayet)

            # Favori durumunu güncelle
            self.update_favorite_button(sure, ayet)

            # Geçerli ayeti sakla
            self.current_verse = (sure, ayet)

    def assign_colors_to_roots(self, ayet_kelimeleri):
        # Kökleri al
        kokler = sorted(list(set(w.get('kok', '').strip() for w in ayet_kelimeleri if w.get('kok'))))
        num_roots = len(kokler)
        colors = {}
        # Generate distinct colors using HSL
        for i, kok in enumerate(kokler):
            # Vary hue across the spectrum, keep saturation and lightness moderate
            hue = i / num_roots
            lightness = 0.5
            saturation = 0.7
            rgb = colorsys.hls_to_rgb(hue, lightness, saturation)
            # Convert to hex color
            hex_color = '#%02x%02x%02x' % (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
            colors[kok] = hex_color
        return colors


    def show_previous_verse(self):
        if hasattr(self, 'current_verse'):
            sure, ayet = self.current_verse
            if ayet > 1:
                self.show_verse_by_number(sure, ayet - 1)
            elif sure > 1:
                # Önceki surenin son ayetine git
                prev_sure = sure - 1
                # Önceki surenin ayet sayısını bul (basit bir yaklaşım)
                prev_ayet = max([v['ayet'] for v in self.verse_data if v['sure'] == prev_sure])
                self.show_verse_by_number(prev_sure, prev_ayet)

    def show_next_verse(self):
        if hasattr(self, 'current_verse'):
            sure, ayet = self.current_verse
            # Sonraki ayeti bul
            next_ayet = ayet + 1
            if any(v['sure'] == sure and v['ayet'] == next_ayet for v in self.verse_data):
                self.show_verse_by_number(sure, next_ayet)
            else:
                # Sonraki surenin ilk ayetine git
                next_sure = sure + 1
                if any(v['sure'] == next_sure for v in self.verse_data):
                    self.show_verse_by_number(next_sure, 1)

    def show_verse_by_number(self, sure, ayet):
        verse = self.verse_index.get((sure, ayet))
        if verse:
            item = QListWidgetItem(f"{sure}/{ayet} - {verse['turkce'][:50]}...")
            item.setData(Qt.UserRole, (sure, ayet))
            self.show_verse_details(item)


    def show_stats(self, sure, ayet):
        # İstatistikleri göster
        stats_text = f"<h2>{sure}. sure, {ayet}. ayet İstatistikleri</h2>"

        # Kelime sayıları
        ayet_kelimeleri = [w for w in self.word_data if w['sureNo'] == sure and w['ayetNo'] == ayet]
        stats_text += f"<p>Toplam kelime sayısı: {len(ayet_kelimeleri)}</p>"

        # Kök dağılımı
        kokler = [w.get('kok', '') for w in ayet_kelimeleri if w.get('kok')]
        kok_sayilari = Counter(kokler)

        if kok_sayilari:
            stats_text += "<h3>Kök Dağılımı:</h3><ul>"
            for kok, sayi in kok_sayilari.most_common():
                stats_text += f"<li>{kok}: {sayi} kez</li>"
            stats_text += "</ul>"

        # Benzer ayetler (aynı kökleri paylaşan)
        benzer_ayetler = set()
        for kok in kok_sayilari:
            if kok in self.root_index:
                for word in self.root_index[kok]:
                    if not (word['sureNo'] == sure and word['ayetNo'] == ayet):
                        benzer_ayetler.add((word['sureNo'], word['ayetNo']))

        if benzer_ayetler:
            stats_text += "<h3>Benzer Ayetler (Aynı Kökler):</h3><ul>"
            for s, a in sorted(benzer_ayetler)[:10]:  # İlk 10 taneyi göster
                verse = self.verse_index.get((s, a))
                if verse:
                    stats_text += f"<li>{s}/{a}: {verse['turkce'][:50]}...</li>"
            stats_text += "</ul>"

        self.stats_display.setHtml(stats_text)

    def create_concept_network(self, sure, ayet):
        # Kavram ağı oluştur
        self.network_canvas.figure.clear()
        ax = self.network_canvas.figure.add_subplot(111)

        # Basit bir kavram ağı örneği
        G = nx.Graph()

        # Ayetteki kökleri düğüm olarak ekle
        ayet_kelimeleri = [w for w in self.word_data if w['sureNo'] == sure and w['ayetNo'] == ayet]
        kokler = [w.get('kok', '') for w in ayet_kelimeleri if w.get('kok')]

        for kok in set(kokler):
            G.add_node(kok)

        # Kökler arasında bağlantılar ekle
        for i, kok1 in enumerate(kokler):
            for kok2 in kokler[i+1:]:
                if kok1 != kok2:
                    if G.has_edge(kok1, kok2):
                        G[kok1][kok2]['weight'] += 1
                    else:
                        G.add_edge(kok1, kok2, weight=1)

        # Grafiği çiz
        if G.nodes():
            pos = nx.spring_layout(G)
            nx.draw_networkx_nodes(G, pos, node_size=700, ax=ax)
            nx.draw_networkx_edges(G, pos, ax=ax)
            nx.draw_networkx_labels(G, pos, ax=ax)

            ax.set_title(f"{sure}. sure, {ayet}. ayet Kavram Ağı")
            self.network_canvas.draw()

    def create_wordcloud(self, sure, ayet):
        # Kelime bulutu oluştur
        self.wordcloud_canvas.figure.clear()
        ax = self.wordcloud_canvas.figure.add_subplot(111)

        # Ayetin Türkçe meali
        verse = self.verse_index.get((sure, ayet))
        if verse:
            text = verse['turkce']
            # Özel karakterleri temizle
            text = re.sub(r'[%&]', '', text)

            # Kelime bulutu oluştur
            wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)

            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            ax.set_title(f"{sure}. sure, {ayet}. ayet Kelime Bulutu")
            self.wordcloud_canvas.draw()

    def toggle_favorite(self):
        if hasattr(self, 'current_verse'):
            sure, ayet = self.current_verse
            verse_id = f"{sure}/{ayet}"

            if verse_id in self.favorites:
                self.favorites.remove(verse_id)
                self.favorite_button.setText("Favorilerden Çıkar")
            else:
                self.favorites.append(verse_id)
                self.favorite_button.setText("Favorilere Ekle")

            self.save_favorites()

    def update_favorite_button(self, sure, ayet):
        verse_id = f"{sure}/{ayet}"
        if verse_id in self.favorites:
            self.favorite_button.setText("Favorilerden Çıkar")
        else:
            self.favorite_button.setText("Favorilere Ekle")

    def closeEvent(self, event):
        # Uygulama kapanırken favorileri kaydet
        self.save_favorites()
        # Close database connection
        if hasattr(self, 'dict_conn') and self.dict_conn:
            self.dict_conn.close()
        event.accept()

    # Event filter to capture mouse clicks on QTextBrowser viewport
    def eventFilter(self, obj, event):
        if obj == self.verse_display.viewport() and event.type() == QEvent.MouseButtonPress:
            print(f"DEBUG: MouseButtonPress event captured at position: {event.pos()}") # Added debug print
            # Get the URL at the mouse click position
            anchor = self.verse_display.anchorAt(event.pos())
            print(f"DEBUG: anchorAt returned: {anchor}") # Added debug print
            if anchor:
                # Call the anchor clicked handler with the URL
                self._on_anchor_clicked(QUrl(anchor))
                return True # Event handled
        return super().eventFilter(obj, event)

def main():
    print("DEBUG: Starting main application") # Debug print at the start of main
    app = QApplication(sys.argv)
    window = QuranAnalyzerApp()
    window.show()
    sys.exit(app.exec_())
    print("DEBUG: Main application finished") # Debug print at the end of main

if __name__ == '__main__':
    main()