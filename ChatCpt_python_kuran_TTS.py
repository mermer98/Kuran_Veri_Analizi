
import sys
import os
import json
import re
import tempfile
from collections import Counter
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QTextEdit, QListWidget, QListWidgetItem,
                             QLabel, QSplitter, QComboBox, QCheckBox, QTabWidget, QMessageBox,
                             QTreeWidget, QTreeWidgetItem, QHeaderView, QGroupBox, QSpinBox,
                             QTextBrowser, QToolTip, QFileDialog, QDialog, QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, QSize, QPoint, QUrl, QEvent
from PyQt5.QtGui import QFont, QIcon, QColor, QCursor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

import numpy as np
from wordcloud import WordCloud
import arabic_reshaper
from bidi.algorithm import get_display
import colorsys
import sqlite3
from gtts import gTTS


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

        # Ses oynatıcı
        self.player = QMediaPlayer(None)

        # GUI bileşenlerini oluştur
        self.init_ui()
        self._ensure_tooltip_store()  # Tooltip deposu

    # -------------------- Veri Yükleme --------------------
    def load_data(self):
        try:
            with open('kelime_manali_kuran_ve_turkce_meali.json', 'r', encoding='utf-8') as f:
                self.verse_data = json.load(f)

            with open('kurani_kerimdeki_tum_kelimeler.json', 'r', encoding='utf-8') as f:
                self.word_data = json.load(f)

            self.create_additional_data_structures()

        except FileNotFoundError:
            QMessageBox.critical(self, "Hata", "JSON dosyaları bulunamadı!")
            sys.exit(1)

    def create_additional_data_structures(self):
        self.word_index = {(w['sureNo'], w['ayetNo'], w['kelimeNo']): w for w in self.word_data}
        self.verse_index = {(v['sure'], v['ayet']): v for v in self.verse_data}

        self.root_index = {}
        for w in self.word_data:
            root = (w.get('kok') or '').strip()
            if root:
                self.root_index.setdefault(root, []).append(w)

        self.turkish_index = {}
        for w in self.word_data:
            tr = (w.get('turkce') or '').lower().strip()
            tr = re.sub(r'[%&]', '', tr)
            if tr:
                self.turkish_index.setdefault(tr, []).append(w)

        self.arabic_index = {}
        for w in self.word_data:
            ar = (w.get('arapca') or '').strip()
            if ar:
                self.arabic_index.setdefault(ar, []).append(w)

    # -------------------- Sözlük DB --------------------
    def _init_dictionary_db(self):
        self.dict_conn = sqlite3.connect(self.dict_db_path)
        cur = self.dict_conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS entries(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kelime  TEXT UNIQUE,
                telaffuz TEXT,
                koken    TEXT,
                anlam    TEXT,
                ornek    TEXT
            )
        """)
        self.dict_conn.commit()

    # -------------------- Favoriler --------------------
    def load_favorites(self):
        try:
            with open('favorites.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def save_favorites(self):
        with open('favorites.json', 'w', encoding='utf-8') as f:
            json.dump(self.favorites, f, ensure_ascii=False, indent=2)

    # -------------------- UI --------------------
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Sol panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        search_group = QGroupBox("Arama")
        search_layout = QVBoxLayout(search_group)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Arama yapın... (örn: 1/1, adalet, a:الله, kök:ع ل م)")
        self.search_input.returnPressed.connect(self.search)
        search_layout.addWidget(self.search_input)

        self.search_button = QPushButton("Ara")
        self.search_button.clicked.connect(self.search)
        search_layout.addWidget(self.search_button)

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

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.show_verse_details)
        left_layout.addWidget(self.results_list)

        # Sağ panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.tabs = QTabWidget()

        # Ayet detayları
        self.verse_tab = QWidget()
        verse_layout = QVBoxLayout(self.verse_tab)

        self.verse_display = QTextBrowser()
        self.verse_display.setOpenExternalLinks(False)
        self.verse_display.setOpenLinks(False)
        self.verse_display.highlighted.connect(self._on_anchor_hover)
        self.verse_display.anchorClicked.connect(self._on_anchor_clicked)
        self.verse_display.viewport().installEventFilter(self)
        self.verse_display.setMouseTracking(True)
        verse_layout.addWidget(self.verse_display)

        context_buttons = QHBoxLayout()
        self.prev_button = QPushButton("Önceki Ayet")
        self.prev_button.clicked.connect(self.show_previous_verse)
        context_buttons.addWidget(self.prev_button)

        # 🔊 TTS düğmesi
        self.tts_button = QPushButton("🔊 Ayeti Oku")
        self.tts_button.clicked.connect(self.play_current_verse_audio)
        context_buttons.addWidget(self.tts_button)

        self.next_button = QPushButton("Sonraki Ayet")
        self.next_button.clicked.connect(self.show_next_verse)
        context_buttons.addWidget(self.next_button)

        verse_layout.addLayout(context_buttons)

        self.favorite_button = QPushButton("Favorilere Ekle")
        self.favorite_button.clicked.connect(self.toggle_favorite)
        verse_layout.addWidget(self.favorite_button)

        self.tabs.addTab(self.verse_tab, "Ayet Detayları")

        # İstatistikler
        self.stats_tab = QWidget()
        stats_layout = QVBoxLayout(self.stats_tab)
        self.stats_display = QTextEdit(); self.stats_display.setReadOnly(True)
        stats_layout.addWidget(self.stats_display)
        self.tabs.addTab(self.stats_tab, "İstatistikler")

        # Kavram Ağı
        self.network_tab = QWidget()
        network_layout = QVBoxLayout(self.network_tab)
        self.network_canvas = FigureCanvas(plt.figure())
        network_layout.addWidget(self.network_canvas)
        self.tabs.addTab(self.network_tab, "Kavram Ağı")

        # Kelime Bulutu
        self.wordcloud_tab = QWidget()
        wordcloud_layout = QVBoxLayout(self.wordcloud_tab)
        self.wordcloud_canvas = FigureCanvas(plt.figure())
        wordcloud_layout.addWidget(self.wordcloud_canvas)
        self.tabs.addTab(self.wordcloud_tab, "Kelime Bulutu")

        right_layout.addWidget(self.tabs)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 1000])
        main_layout.addWidget(splitter)

        self.statusBar().showMessage("Hazır")

    # -------------------- Tooltip --------------------
    def _ensure_tooltip_store(self):
        if not hasattr(self, "kelime_tooltips"):
            self.kelime_tooltips = {}

    def _on_anchor_hover(self, url):
        s = url.toString() if hasattr(url, "toString") else str(url)
        if not s:
            QToolTip.hideText(); return
        tip = self.kelime_tooltips.get(s, "")
        if tip:
            QToolTip.showText(QCursor.pos(), tip)

    # -------------------- Tıkla → Sözlük --------------------
    def _on_anchor_clicked(self, url):
        try:
            u = url if isinstance(url, QUrl) else QUrl(str(url))
            if u.scheme() != "kelime":
                return

            # Öncelik: kelime:s/a/k (host yok)
            path = u.path().lstrip("/")           # "s/a/k" veya "a/k"
            parts = [p for p in path.split("/") if p]

            if len(parts) == 3 and all(p.isdigit() for p in parts):
                sure, ayet, kelime_no = map(int, parts)
            else:
                # Eski stil: kelime://s/a/k → host=s, path="/a/k"
                host = u.host()
                if host.isdigit():
                    parts2 = [host] + [p for p in path.split("/") if p]
                    if len(parts2) == 3 and all(p.isdigit() for p in parts2):
                        sure, ayet, kelime_no = map(int, parts2)
                    else:
                        return
                else:
                    return

            w = next((x for x in self.word_data
                      if x['sureNo'] == sure and x['ayetNo'] == ayet and x['kelimeNo'] == kelime_no), None)
            if not w:
                return
            kel = (w.get('turkce') or '').strip()
            self._show_dictionary_popup(kel, w)

        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Tıklama işlenemedi:\n{e}")

    def _fetch_dict_entry(self, kelime):
        cur = self.dict_conn.cursor()
        cur.execute("SELECT kelime,telaffuz,koken,anlam,ornek FROM entries WHERE kelime=?", (kelime,))
        row = cur.fetchone()
        if row:
            return {"kelime":row[0], "telaffuz":row[1], "koken":row[2], "anlam":row[3], "ornek":row[4]}
        return None

    def _show_dictionary_popup(self, kelime, word_data):
        data = self._fetch_dict_entry(kelime)

        dlg = QDialog(self); dlg.setWindowTitle(f"Sözlük: {kelime}")
        lay = QVBoxLayout(dlg)

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

        btn_add.clicked.connect(lambda: self._show_add_entry_dialog(kelime))
        btn_close.clicked.connect(dlg.reject)
        dlg.exec_()

    def _show_add_entry_dialog(self, kelime_default=""):
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
            kelime = e_k.text().strip()
            telaffuz = e_t.text().strip()
            koken = e_ko.text().strip()
            anlam = e_a.toPlainText().strip()
            ornek = e_o.toPlainText().strip()

            if not kelime or not anlam:
                QMessageBox.warning(dlg, "Uyarı", "Kelime ve Anlam alanları boş bırakılamaz.")
                return

            try:
                cur = self.dict_conn.cursor()
                cur.execute("""
                    INSERT OR REPLACE INTO entries(kelime,telaffuz,koken,anlam,ornek)
                    VALUES(?,?,?,?,?)
                """, (kelime, telaffuz, koken, anlam, ornek))
                self.dict_conn.commit()
                QMessageBox.information(dlg, "Başarılı", "Kayıt eklendi/güncellendi.")
                dlg.accept()
            except Exception as e:
                QMessageBox.critical(dlg, "Hata", f"Veritabanı hatası: {e}")

        btns.accepted.connect(save)
        btns.rejected.connect(dlg.reject)
        dlg.exec_()

    # -------------------- Arama --------------------
    def search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        self.results_list.clear()

        t = self.search_type.currentText()
        if t == "Sure/Ayet" or re.match(r'^\d+/\d+$', query):
            if '/' in query:
                p = query.split('/')
                if len(p) == 2 and p[0].isdigit() and p[1].isdigit():
                    self.search_by_sure_ayet(int(p[0]), int(p[1]))
        elif t == "Kök" or query.startswith('kök:'):
            root = query[4:] if query.startswith('kök:') else query
            self.search_by_root(root)
        elif query.startswith('a:'):
            self.search_arabic(query[2:])
        elif query.startswith('t:'):
            self.search_turkish(query[2:])
        else:
            self.search_general(query)

    def search_by_sure_ayet(self, sure, ayet):
        for verse in self.verse_data:
            if verse['sure'] == sure and verse['ayet'] == ayet:
                it = QListWidgetItem(f"{sure}/{ayet} - {verse['turkce'][:50]}...")
                it.setData(Qt.UserRole, (sure, ayet))
                self.results_list.addItem(it)
                break

    def search_by_root(self, root):
        if root in self.root_index:
            verses = {(w['sureNo'], w['ayetNo']) for w in self.root_index[root]}
            for s, a in sorted(verses):
                v = self.verse_index.get((s, a))
                if v:
                    it = QListWidgetItem(f"{s}/{a} - {v['turkce'][:50]}...")
                    it.setData(Qt.UserRole, (s, a))
                    self.results_list.addItem(it)

    def search_arabic(self, query):
        for ar, words in self.arabic_index.items():
            if query in ar:
                verses = {(w['sureNo'], w['ayetNo']) for w in words}
                for s, a in sorted(verses):
                    v = self.verse_index.get((s, a))
                    if v:
                        it = QListWidgetItem(f"{s}/{a} - {v['turkce'][:50]}...")
                        it.setData(Qt.UserRole, (s, a))
                        self.results_list.addItem(it)

    def search_turkish(self, query):
        query = query.lower()
        for tr, words in self.turkish_index.items():
            if query in tr:
                verses = {(w['sureNo'], w['ayetNo']) for w in words}
                for s, a in sorted(verses):
                    v = self.verse_index.get((s, a))
                    if v:
                        it = QListWidgetItem(f"{s}/{a} - {v['turkce'][:50]}...")
                        it.setData(Qt.UserRole, (s, a))
                        self.results_list.addItem(it)

    def search_general(self, query):
        query = query.lower()
        found = set()
        for tr, words in self.turkish_index.items():
            if query in tr:
                for w in words:
                    found.add((w['sureNo'], w['ayetNo']))
        for ar, words in self.arabic_index.items():
            if query in ar:
                for w in words:
                    found.add((w['sureNo'], w['ayetNo']))
        for s, a in sorted(found):
            v = self.verse_index.get((s, a))
            if v:
                it = QListWidgetItem(f"{s}/{a} - {v['turkce'][:50]}...")
                it.setData(Qt.UserRole, (s, a))
                self.results_list.addItem(it)

    # -------------------- Ayet Gösterim --------------------
    def show_verse_details(self, item):
        sure, ayet = item.data(Qt.UserRole)
        verse = self.verse_index.get((sure, ayet))
        if not verse:
            return

        self._ensure_tooltip_store()
        ayet_kelimeleri = [w for w in self.word_data if w['sureNo'] == sure and w['ayetNo'] == ayet]
        renkler = self.assign_colors_to_roots(ayet_kelimeleri)

        # Türkçe anlamı renklendir + link
        highlighted_turkish = verse['turkce']
        for k in sorted(ayet_kelimeleri, key=lambda x: -len(x.get('turkce', ''))):
            tr = k.get('turkce', '')
            kok = (k.get('kok') or '').strip()
            if not tr:
                continue
            url = f"kelime:{sure}/{ayet}/{k['kelimeNo']}"
            tip = f"Arapça: {k.get('arapca','-')}\nKök: {kok or '-'}\nAnlam: {tr or '-'}"
            self.kelime_tooltips[url] = tip
            repl = (f"<a href='{url}' style='text-decoration:none; color:{renkler.get(kok,'black')}; "
                    f"font-weight:bold'>{tr}</a>")
            highlighted_turkish = re.sub(fr"\b{re.escape(tr)}\b", repl, highlighted_turkish, flags=re.IGNORECASE)

        display_text = f"<h2>{sure}. sure, {ayet}. ayet</h2>"
        display_text += "<h3>Arapça:</h3>"
        display_text += f"<p style='font-size: 16pt; text-align: right;'>{verse['arapca']}</p>"
        display_text += "<h3>Türkçe Anlam:</h3>"
        display_text += f"<p>{highlighted_turkish}</p>"

        # Kelime Analizi tablosu
        display_text += "<h3>Kelime Analizi:</h3>"
        display_text += "<table border='1'><tr><th>Kelime</th><th>Arapça</th><th>Anlam</th><th>Kök</th></tr>"
        for k in sorted(ayet_kelimeleri, key=lambda x: x['kelimeNo']):
            kok = (k.get('kok') or '').strip()
            tr = k.get('turkce', '')
            ar = k.get('arapca', '')
            url = f"kelime:{sure}/{ayet}/{k['kelimeNo']}"
            self.kelime_tooltips[url] = f"Arapça: {ar or '-'}\nKök: {kok or '-'}\nAnlam: {tr or '-'}"
            anlam_html = f"<a href='{url}' style='text-decoration:none; color:{renkler.get(kok,'black')}'>{tr}</a>"
            display_text += (f"<tr><td>{k['kelimeNo']}</td>"
                             f"<td style='text-align: right;'>{ar}</td>"
                             f"<td>{anlam_html}</td><td>{kok}</td></tr>")
        display_text += "</table>"

        self.verse_display.setHtml(display_text)

        self.show_stats(sure, ayet)
        self.create_concept_network(sure, ayet)
        self.create_wordcloud(sure, ayet)
        self.update_favorite_button(sure, ayet)
        self.current_verse = (sure, ayet)

    def assign_colors_to_roots(self, items):
        roots = sorted(set((w.get('kok') or '').strip() for w in items if w.get('kok')))
        n = max(1, len(roots))
        colors = {}
        for i, r in enumerate(roots):
            h = i / n; l = 0.5; s = 0.7
            R, G, B = colorsys.hls_to_rgb(h, l, s)
            colors[r] = '#%02x%02x%02x' % (int(R*255), int(G*255), int(B*255))
        return colors

    # -------------------- TTS --------------------
    def play_current_verse_audio(self):
        if not hasattr(self, 'current_verse'):
            QMessageBox.information(self, "Bilgi", "Önce bir ayet seçin.")
            return
        s, a = self.current_verse
        verse = self.verse_index.get((s, a))
        if not verse:
            return
        text = verse.get('arapca', '').strip()
        if not text:
            QMessageBox.warning(self, "Uyarı", "Arapça metin bulunamadı.")
            return
        self._speak_arabic(text, s, a)

    def _speak_arabic(self, text, sure, ayet):
        try:
            # gTTS (internet gerekir)
            tts = gTTS(text=text, lang='ar')
            tmp_path = os.path.join(tempfile.gettempdir(), f"kuran_{sure}_{ayet}.mp3")
            tts.save(tmp_path)

            # Çal
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(tmp_path)))
            self.player.play()
        except Exception as e:
            QMessageBox.critical(self, "Ses Hatası", f"Ses oluşturulamadı.\nİnternet bağlantınızı kontrol edin.\n\n{e}")

    # -------------------- Ayetler arası geçiş --------------------
    def show_previous_verse(self):
        if hasattr(self, 'current_verse'):
            s, a = self.current_verse
            if a > 1:
                self.show_verse_by_number(s, a - 1)
            elif s > 1:
                ps = s - 1
                pa = max([v['ayet'] for v in self.verse_data if v['sure'] == ps])
                self.show_verse_by_number(ps, pa)

    def show_next_verse(self):
        if hasattr(self, 'current_verse'):
            s, a = self.current_verse
            na = a + 1
            if any(v['sure'] == s and v['ayet'] == na for v in self.verse_data):
                self.show_verse_by_number(s, na)
            else:
                ns = s + 1
                if any(v['sure'] == ns for v in self.verse_data):
                    self.show_verse_by_number(ns, 1)

    def show_verse_by_number(self, sure, ayet):
        v = self.verse_index.get((sure, ayet))
        if v:
            it = QListWidgetItem(f"{sure}/{ayet} - {v['turkce'][:50]}...")
            it.setData(Qt.UserRole, (sure, ayet))
            self.show_verse_details(it)

    # -------------------- İstatistik / Ağ / Bulut --------------------
    def show_stats(self, sure, ayet):
        stats_text = f"<h2>{sure}. sure, {ayet}. ayet İstatistikleri</h2>"
        words = [w for w in self.word_data if w['sureNo'] == sure and w['ayetNo'] == ayet]
        stats_text += f"<p>Toplam kelime sayısı: {len(words)}</p>"

        roots = [w.get('kok', '') for w in words if w.get('kok')]
        kok_say = Counter(roots)
        if kok_say:
            stats_text += "<h3>Kök Dağılımı:</h3><ul>"
            for k, s in kok_say.most_common():
                stats_text += f"<li>{k}: {s} kez</li>"
            stats_text += "</ul>"

        similar = set()
        for k in kok_say:
            for w in self.root_index.get(k, []):
                if not (w['sureNo'] == sure and w['ayetNo'] == ayet):
                    similar.add((w['sureNo'], w['ayetNo']))
        if similar:
            stats_text += "<h3>Benzer Ayetler (Aynı Kökler):</h3><ul>"
            for s, a in sorted(similar)[:10]:
                v = self.verse_index.get((s, a))
                if v:
                    stats_text += f"<li>{s}/{a}: {v['turkce'][:50]}...</li>"
            stats_text += "</ul>"

        self.stats_display.setHtml(stats_text)

    def create_concept_network(self, sure, ayet):
        self.network_canvas.figure.clear()
        ax = self.network_canvas.figure.add_subplot(111)

        G = nx.Graph()
        words = [w for w in self.word_data if w['sureNo'] == sure and w['ayetNo'] == ayet]
        roots = [w.get('kok', '') for w in words if w.get('kok')]

        for r in set(roots):
            G.add_node(r)

        for i, r1 in enumerate(roots):
            for r2 in roots[i+1:]:
                if r1 == r2:
                    continue
                if G.has_edge(r1, r2):
                    G[r1][r2]['weight'] += 1
                else:
                    G.add_edge(r1, r2, weight=1)

        if G.nodes():
            pos = nx.spring_layout(G)
            nx.draw_networkx_nodes(G, pos, node_size=700, ax=ax)
            nx.draw_networkx_edges(G, pos, ax=ax)
            nx.draw_networkx_labels(G, pos, ax=ax)
            ax.set_title(f"{sure}. sure, {ayet}. ayet Kavram Ağı")
            self.network_canvas.draw()

    def create_wordcloud(self, sure, ayet):
        self.wordcloud_canvas.figure.clear()
        ax = self.wordcloud_canvas.figure.add_subplot(111)
        v = self.verse_index.get((sure, ayet))
        if v:
            text = re.sub(r'[%&]', '', v['turkce'])
            wc = WordCloud(width=800, height=400, background_color='white').generate(text)
            ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
            ax.set_title(f"{sure}. sure, {ayet}. ayet Kelime Bulutu")
            self.wordcloud_canvas.draw()

    # -------------------- Favoriler --------------------
    def toggle_favorite(self):
        if hasattr(self, 'current_verse'):
            s, a = self.current_verse
            vid = f"{s}/{a}"
            if vid in self.favorites:
                self.favorites.remove(vid)
                self.favorite_button.setText("Favorilere Ekle")
            else:
                self.favorites.append(vid)
                self.favorite_button.setText("Favorilerden Çıkar")
            self.save_favorites()

    def update_favorite_button(self, sure, ayet):
        vid = f"{sure}/{ayet}"
        self.favorite_button.setText("Favorilerden Çıkar" if vid in self.favorites else "Favorilere Ekle")

    def closeEvent(self, event):
        self.save_favorites()
        try:
            if getattr(self, 'dict_conn', None):
                self.dict_conn.close()
        finally:
            event.accept()

    # -------------------- Event Filter (tıklamayı garanti yakala) --------------------
    def eventFilter(self, obj, event):
        if obj is self.verse_display.viewport() and event.type() == QEvent.MouseButtonRelease:
            cursor = self.verse_display.cursorForPosition(event.pos())
            fmt = cursor.charFormat()
            if fmt.isAnchor():
                href = fmt.anchorHref() or (fmt.anchorNames()[0] if fmt.anchorNames() else "")
                if href:
                    self._on_anchor_clicked(QUrl(href))
                    return True
        return super().eventFilter(obj, event)


def main():
    app = QApplication(sys.argv)
    window = QuranAnalyzerApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
