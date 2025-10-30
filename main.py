# kuran_veri_analiz/main.py

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton,
    QLabel, QTextEdit, QScrollArea, QMessageBox, QCheckBox, QHBoxLayout, QComboBox, QTabWidget, QTableWidget, QTableWidgetItem, QDialog, QListWidget, QListWidgetItem, QGroupBox, QSpinBox, QMenu, QAbstractItemView
)
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
from PyQt5.QtCore import Qt
import sys
import re
import json
import os
import difflib
from gtts import gTTS
import playsound
from qalsadi.lemmatizer import Lemmatizer
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from utils.veri_isleyici import veri_yukle, turkce_transkript_yukle, kuran_kelimeleri_hazirla, normalize_text, normalize_arabic
from yardimci_araclar import vurgu_ekle, vurgu_ekle as vurgu_ekle
try:
    import zemberek
    from zemberek import TurkishMorphology
    ZEMBEREK_AVAILABLE = True
except ImportError:
    ZEMBEREK_AVAILABLE = False

def basit_kok_bul(word):
    """Gelişmiş Arapça kök bulma algoritması"""
    word = normalize_arabic(word)

    # Çok kısa kelimeler için
    if len(word) < 3:
        return word

    # Özel durumlar - bilinen kelimeler için doğru kökler
    special_cases = {
        'باسمائهم': 'اسم',  # bismā'ihim -> ism (isim)
        'بسم': 'اسم',      # bism -> ism
        'اسما': 'اسم',     # ismā -> ism
        'الرحمن': 'رحم',   # ar-rahman -> rahman
        'الرحيم': 'رحم',   # ar-raheem -> rahman
        'الله': 'اله',     # allah -> ilah
        'محمد': 'حمد',     # muhammed -> hamd
        'قرآن': 'قرء',     # quran -> qara'a
        'كتاب': 'كتب',     # kitab -> kataba
        'رسول': 'رسل',     # rasul -> rasala
        'نبي': 'نبا',      # nebiy -> naba
        'صلاة': 'صلي',     # salat -> salaa
        'زكاة': 'زكي',     # zakat -> zaka
        'صيام': 'صوم',     # sawm -> sama
        'حج': 'حجج',       # hac -> hajja
        'جهاد': 'جهد',     # jihad -> jahada
        'ايمان': 'امن',    # iman -> amina
        'اسلام': 'سلم',    # islam -> salima
        'مؤمن': 'امن',     # mu'min -> amina
        'كافر': 'كفر',     # kafir -> kafara
        'مشرك': 'شرك',     # mushrik -> ashraaka
        'منافق': 'نفق',    # munafiq -> nafaqa
        'مؤمنون': 'امن',   # mu'minun -> amina
        'مؤمنات': 'امن',   # mu'minat -> amina
    }

    # Özel durum kontrolü
    if word in special_cases:
        return special_cases[word]

    # Ön ekleri çıkar (ba-, la-, sa-, ka-, fa-, ta-, ya-, na-, ha-, wa-, bi-, li-, si-, ki-, fi-, ti-, yi-, ni-, hi-, wi-)
    on_ekler = [
        'ب', 'ل', 'س', 'ك', 'ف', 'ت', 'ي', 'ن', 'ه', 'و',  # Tek harf ön ekler
        'بِ', 'لِ', 'سِ', 'كِ', 'فِ', 'تِ', 'يِ', 'نِ', 'هِ', 'وِ',  # bi-, li-, si-, etc.
        'بَ', 'لَ', 'سَ', 'كَ', 'فَ', 'تَ', 'يَ', 'نَ', 'هَ', 'وَ',  # ba-, la-, sa-, etc.
        'بْ', 'لْ', 'سْ', 'كْ', 'فْ', 'تْ', 'يْ', 'نْ', 'هْ', 'وْ',  # bu-, lu-, su-, etc.
        'ال', 'وال', 'بال', 'فال', 'كال', 'لل'  # Elif-lam ile başlayanlar
    ]

    for on_ek in sorted(on_ekler, key=len, reverse=True):  # Uzun eklerden başla
        if word.startswith(on_ek):
            word = word[len(on_ek):]
            break

    # Son ekleri çıkar
    son_ekler = [
        'ون', 'ين', 'ان', 'ات', 'ون', 'ين', 'ان', 'ات',  # -ūn, -īn, -ān, -āt
        'هم', 'هن', 'كم', 'كن', 'نا', 'ها', 'هو', 'هي',  # -hum, -hin, -kum, -kin, -nā, -hā, -hu, -hi
        'وا', 'وا', 'وا', 'وا', 'وا', 'وا', 'وا', 'وا',  # -ū, -ā, -ī (uzatmalar)
        'ي', 'ى', 'ة', 'ات', 'ون', 'ین', 'ین', 'ها', 'کم', 'کن', 'نا', 'وا',  # Eski ekler
        'ا', 'و', 'ي', 'ة', 'ت', 'ن', 'ه', 'ك', 'م', 'ه'  # Tek harf son ekler
    ]

    for son_ek in sorted(son_ekler, key=len, reverse=True):  # Uzun eklerden başla
        if word.endswith(son_ek):
            word = word[:-len(son_ek)]
            break

    # Özel durumlar için ek kontroller
    # Eğer kelime hala çok uzunsa, morfolojik analiz yap
    if len(word) > 6:
        # Muhtemelen bileşik kelime, ortadaki harfleri dene
        # Örneğin: "bismillahirrahmanirrahim" -> "ism"
        # Veya "bismā'ihim" -> "ism"
        candidates = []

        # 3 harfli kök adayları
        for i in range(len(word) - 2):
            candidate = word[i:i+3]
            if len(candidate) == 3 and all('\u0600' <= c <= '\u06FF' for c in candidate):
                candidates.append(candidate)

        # En olası kökleri seç (ortadaki harfler daha olası)
        if candidates:
            # Orta kısımda olan adayları tercih et
            mid = len(candidates) // 2
            if mid > 0:
                return candidates[mid-1] if len(candidates) > 1 else candidates[0]
            else:
                return candidates[0]

    # 3-4 harfli kök döndür
    if len(word) >= 3:
        return word[:3]
    else:
        return word

def normalize_arabic(text):
    """Arapça metindeki harekeleri ve özel karakterleri çıkarır"""
    if not text:
        return ""
    # Arapça hareke karakterleri (fatha, kasra, damma, sukun, şedde, med vb.)
    harekeler = r'[\u064b-\u065f\u0670\u06d6-\u06ed]'
    # Özel karakterleri kaldır: % & '
    text = re.sub(r'[%&\'"]', '', text)
    # Harekeleri kaldır
    text = re.sub(harekeler, '', text)
    # Küçük harfe çevir (Latin harfler için)
    return text.lower()

def normalize_kok(kok):
    """Kökten boşlukları çıkarır"""
    return kok.replace(" ", "")

def strip_html_tags(text):
    """HTML etiketlerini metinden çıkarır"""
    import re
    # HTML etiketlerini kaldır
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def is_arabic_root(word):
    """Kelimenin Arapça kök formatında olup olmadığını kontrol eder"""
    if len(word) != 3:
        return False
    # Arapça harfler: \u0600-\u06FF aralığı
    return all('\u0600' <= char <= '\u06FF' for char in word)

def get_root_words_from_ayet(arapca_html, root):
    """Ayetteki kök eşleşen kelimeleri döndürür"""
    root_normalized = normalize_kok(root)
    words = []
    koks = re.findall(r'<span[^>]*kok="([^"]*)"[^>]*>([^<]+)</span>', arapca_html)
    for kok, kelime in koks:
        if normalize_kok(kok) == root_normalized:
            words.append(kelime)
    return words

def get_kok_from_db(word, veriler):
    """Veri tabanından kelimenin kökünü alır"""
    word_normalized = normalize_arabic(word)
    for item in veriler:
        arapca_html = item.get('arapca', '')
        koks = re.findall(r'<span[^>]*kok="([^"]*)"[^>]*>([^<]+)</span>', arapca_html)
        for kok, kelime in koks:
            if normalize_arabic(kelime) == word_normalized:
                return normalize_kok(kok)
    return None

def gelismis_kok_bul(word):
    """qalsadi lemmatizer kullanarak gelişmiş kök bulma"""
    try:
        # qalsadi lemmatizer'ı kullan
        lem = Lemmatizer()
        lemmas = lem.lemmatize(word)

        if lemmas:
            # İlk lemma'nın kökünü al
            lemma = lemmas[0]
            # Lemma'dan kök çıkar (genellikle lemma kökü içerir)
            lemma_normalized = normalize_arabic(lemma)

            # Eğer lemma 3 harfli ise doğrudan döndür
            if len(lemma_normalized) == 3:
                return lemma_normalized

            # Lemma'dan kök çıkar (morfolojik analiz)
            return basit_kok_bul(lemma)
        else:
            # qalsadi başarısız olursa basit algoritma kullan
            return basit_kok_bul(word)
    except Exception as e:
        # Herhangi bir hata olursa basit algoritma kullan
        return basit_kok_bul(word)

def turkce_kok_bul(word):
    """Zemberek kullanarak Türkçe kelimenin kökünü bulur"""
    if not ZEMBEREK_AVAILABLE:
        return word.lower().strip()
    
    try:
        morphology = TurkishMorphology.create_with_defaults()
        results = morphology.analyze(word)
        
        if results and results.analysis_results:
            # İlk analiz sonucunun kökünü al
            analysis = results.analysis_results[0]
            root = analysis.get_stem()
            if root:
                return root.lower().strip()
        
        # Kök bulunamazsa orijinal kelimeyi döndür
        return word.lower().strip()
    except Exception as e:
        # Hata olursa orijinal kelimeyi döndür
        return word.lower().strip()

def kok_eslesmesi_bul(arama_koku, kelime_listesi):
    """Verilen kök ile eşleşen kelimeleri bulur (verimli versiyon)"""
    eslesen_kelimeler = set()
    
    for kelime in kelime_listesi:
        try:
            kelime_koku = turkce_kok_bul(kelime)
            if kelime_koku == arama_koku:
                eslesen_kelimeler.add(kelime)
        except:
            # Kök bulunamazsa geç
            continue
    
    return eslesen_kelimeler

class QuranAnalyzer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kur’an Veri Analiz Programı")
        self.resize(1200, 800)
        self.sayfa = 0
        self.satirSayisi = 20
        self.secili_meal = "Diyanet İşleri Meali (Yeni)"
        self.veriler = veri_yukle(self.secili_meal)
        self.turkce_transkript_verisi = turkce_transkript_yukle()  # Kelime bazlı Türkçe transkript verisi
        self.kuran_kelimeleri = kuran_kelimeleri_hazirla()  # Kuranda geçen tüm kelimeler
        self.kelime_sikliklari = self.kelime_sikliklarini_hesapla()  # Kelime sıklıkları
        # self.kelime_kokleri = self.kelime_koklerini_hazirla()  # Kelime kökleri sözlüğü - çok yavaş, arama sırasında hesaplanacak
        self.sureler = sorted(set(item['sure'] for item in self.veriler))
        self.sure_isimleri = [
            "Fatiha", "Bakara", "Al-i İmran", "Nisa", "Maide", "En'am", "A'raf", "Enfal", "Tevbe",
            "Yunus", "Hud", "Yusuf", "Ra'd", "İbrahim", "Hicr", "Nahl", "İsrâ", "Kehf", "Meryem",
            "Taha", "Enbiya", "Hac", "Mü'minun", "Nur", "Furkan", "Şuara", "Neml", "Kasas",
            "Ankebut", "Rum", "Lokman", "Secde", "Ahzab", "Sebe", "Fatır", "Yasin", "Saffat",
            "Sad", "Zümer", "Mü'min", "Fussilet", "Şura", "Zuhruf", "Duhân", "Casiye", "Ahkaf",
            "Muhammed", "Fetih", "Hucurat", "Kaf", "Zariyat", "Tur", "Necm", "Kamer", "Rahman",
            "Vakia", "Hadid", "Mücadele", "Haşr", "Mümtehine", "Saff", "Cuma", "Münafikun",
            "Tegabun", "Talak", "Tahrim", "Mülk", "Kalem", "Hakka", "Me'aric", "Nuh", "Cin",
            "Müzzemmil", "Müddessir", "Kıyame", "İnsan", "Mürselat", "Nebe", "Naziat", "Abese",
            "Tekvir", "İnfitar", "Mutaffifin", "İnşikak", "Buruc", "Tarık", "A'lâ", "Gaşiye",
            "Fecr", "Beled", "Şems", "Leyl", "Duhâ", "İnşirah", "Tin", "Alak", "Kadir", "Beyyine",
            "Zilzal", "Adiyat", "Karia", "Tekasur", "Asr", "Humeze", "Fil", "Kureyş", "Ma'un",
            "Kevser", "Kafirun", "Nasr", "Tebbet", "İhlas", "Felak", "Nas"
        ]
        if os.path.exists('favorites.json'):
            with open('favorites.json', 'r', encoding='utf-8') as f:
                self.favorites = json.load(f)
        else:
            self.favorites = []
        self.init_ui()

    def kelime_sikliklarini_hesapla(self):
        """Türkçe kelimelerin sıklıklarını hesaplar"""
        sikliklar = {}
        for item in self.turkce_transkript_verisi:
            kelime = normalize_text(item.get('turkce', ''))
            if kelime:
                sikliklar[kelime] = sikliklar.get(kelime, 0) + 1
        return sikliklar

    def get_sure_adi(self, sure_no):
        """Sure numarasından sure adını döndürür"""
        if 1 <= sure_no <= len(self.sure_isimleri):
            return self.sure_isimleri[sure_no - 1]
        return f"Sûre {sure_no}"

    def init_ui(self):
        self.tabs = QTabWidget()

        # Arama Sekmesi
        self.arama_tab = QWidget()
        arama_main_layout = QVBoxLayout()

        # Üst kısım - Kontroller
        ust_layout = QVBoxLayout()

        # Meal seçici
        ust_layout.addWidget(QLabel("Meal Seçimi:"))
        self.meal_secici = QComboBox()
        self.meal_secici.addItems([
            "Diyanet İşleri Meali (Yeni)",
            "Elmalılı Hamdi Yazır Meali",
            "Hasan Basri Çantay Meali",
            "Abdulbaki Gölpınarlı Meali",
            "Ahmet Tekin Meali",
            "Ali Bulaç Meali",
            "Besim Atalay Meali (1965)",
            "Cemal Külünkoğlu Meali",
            "Edip Yüksel Meali",
            "Erhan Aktaş Meali",
            "Bahaeddin Sağlam Meali",
            "Bayraktar Bayraklı Meali",
            "Emrah Demiryent Meali",
            "Ali Fikri Yavuz Meali",
            "Ahmet Varol Meali"
        ])
        self.meal_secici.setCurrentText(self.secili_meal)
        self.meal_secici.currentTextChanged.connect(self.meal_degistir)
        ust_layout.addWidget(self.meal_secici)

        # Arama kontrolleri
        arama_kontrol_layout = QHBoxLayout()
        self.arama_kutusu = QLineEdit()
        self.arama_kutusu.setPlaceholderText("Kelime girin...")
        self.arama_kutusu.returnPressed.connect(self.guncelle_sayfa)
        arama_kontrol_layout.addWidget(self.arama_kutusu)

        self.ara_buton = QPushButton("Ara")
        self.ara_buton.clicked.connect(self.guncelle_sayfa)
        arama_kontrol_layout.addWidget(self.ara_buton)

        self.sonuc_sayisi_label = QLabel("")
        arama_kontrol_layout.addWidget(self.sonuc_sayisi_label)

        # Favoriye ekle ve sesli oku butonları
        self.favori_ekle_btn = QPushButton("⭐ Favoriye Ekle")
        self.favori_ekle_btn.clicked.connect(self.secili_ayeti_favoriye_ekle)
        self.favori_ekle_btn.setEnabled(False)
        arama_kontrol_layout.addWidget(self.favori_ekle_btn)

        self.sesli_oku_btn = QPushButton("🔊 Sesli Oku")
        self.sesli_oku_btn.clicked.connect(self.secili_ayeti_sesli_oku)
        self.sesli_oku_btn.setEnabled(False)
        arama_kontrol_layout.addWidget(self.sesli_oku_btn)

        ust_layout.addLayout(arama_kontrol_layout)

        # Filtre checkbox'ları
        filtre_checkbox_layout = QHBoxLayout()
        self.case_sensitive = QCheckBox("Büyük/Küçük Harf Duyarlı")
        filtre_checkbox_layout.addWidget(self.case_sensitive)

        self.regex_search = QCheckBox("Regex Arama")
        filtre_checkbox_layout.addWidget(self.regex_search)

        self.multi_word = QCheckBox("Çoklu Kelime (VE)")
        filtre_checkbox_layout.addWidget(self.multi_word)

        ust_layout.addLayout(filtre_checkbox_layout)

        # Gelişmiş filtreler grubu
        filtre_group = QGroupBox("Gelişmiş Filtreler")
        filtre_layout = QVBoxLayout()

        # Sure filtresi
        sure_filtresi_layout = QHBoxLayout()
        sure_filtresi_layout.addWidget(QLabel("Sure Filtresi:"))
        self.sure_filtresi = QComboBox()
        self.sure_filtresi.addItem("Tüm Sureler", 0)
        for i, isim in enumerate(self.sure_isimleri):
            self.sure_filtresi.addItem(f"{i+1}-{isim}", i+1)
        sure_filtresi_layout.addWidget(self.sure_filtresi)
        filtre_layout.addLayout(sure_filtresi_layout)

        # Ayet aralığı filtresi
        ayet_filtresi_layout = QHBoxLayout()
        ayet_filtresi_layout.addWidget(QLabel("Ayet Aralığı:"))
        self.ayet_min = QSpinBox()
        self.ayet_min.setMinimum(0)
        self.ayet_min.setMaximum(286)
        self.ayet_min.setValue(0)
        self.ayet_min.setPrefix("Min: ")
        ayet_filtresi_layout.addWidget(self.ayet_min)

        self.ayet_max = QSpinBox()
        self.ayet_max.setMinimum(0)
        self.ayet_max.setMaximum(286)
        self.ayet_max.setValue(286)
        self.ayet_max.setPrefix("Max: ")
        ayet_filtresi_layout.addWidget(self.ayet_max)
        filtre_layout.addLayout(ayet_filtresi_layout)

        # Kelime uzunluğu filtresi
        uzunluk_filtresi_layout = QHBoxLayout()
        uzunluk_filtresi_layout.addWidget(QLabel("Kelime Uzunluğu:"))
        self.uzunluk_min = QSpinBox()
        self.uzunluk_min.setMinimum(0)
        self.uzunluk_min.setMaximum(20)
        self.uzunluk_min.setValue(0)
        self.uzunluk_min.setPrefix("Min: ")
        uzunluk_filtresi_layout.addWidget(self.uzunluk_min)

        self.uzunluk_max = QSpinBox()
        self.uzunluk_max.setMinimum(0)
        self.uzunluk_max.setMaximum(20)
        self.uzunluk_max.setValue(20)
        self.uzunluk_max.setPrefix("Max: ")
        uzunluk_filtresi_layout.addWidget(self.uzunluk_max)
        filtre_layout.addLayout(uzunluk_filtresi_layout)

        # Mekki/Medeni filtresi
        vahiy_filtresi_layout = QHBoxLayout()
        vahiy_filtresi_layout.addWidget(QLabel("Vahiy Türü:"))
        self.vahiy_filtresi = QComboBox()
        self.vahiy_filtresi.addItem("Tümü", "all")
        self.vahiy_filtresi.addItem("Mekki", "mekki")
        self.vahiy_filtresi.addItem("Medeni", "medeni")
        vahiy_filtresi_layout.addWidget(self.vahiy_filtresi)
        filtre_layout.addLayout(vahiy_filtresi_layout)

        # Arama türü filtresi
        arama_turu_layout = QHBoxLayout()
        arama_turu_layout.addWidget(QLabel("Arama Türü:"))
        self.arama_turu = QComboBox()
        self.arama_turu.addItem("Her İkisi", "both")
        self.arama_turu.addItem("Sadece Türkçe", "turkish")
        self.arama_turu.addItem("Sadece Arapça", "arabic")
        arama_turu_layout.addWidget(self.arama_turu)
        filtre_layout.addLayout(arama_turu_layout)

        # Filtre uygulama butonu
        self.filtre_uygula = QCheckBox("Filtreleri Uygula")
        self.filtre_uygula.setChecked(True)
        filtre_layout.addWidget(self.filtre_uygula)

        filtre_group.setLayout(filtre_layout)
        ust_layout.addWidget(filtre_group)

        # Sayfa kontrol butonları
        sayfa_layout = QHBoxLayout()
        self.geri_buton = QPushButton("← Geri")
        self.geri_buton.clicked.connect(self.sayfa_geri)
        sayfa_layout.addWidget(self.geri_buton)

        self.ileri_buton = QPushButton("İleri →")
        self.ileri_buton.clicked.connect(self.sayfa_ileri)
        sayfa_layout.addWidget(self.ileri_buton)

        ust_layout.addLayout(sayfa_layout)

        arama_main_layout.addLayout(ust_layout)

        # Ana panel - Sol: Arama sonuçları, Sağ: Türkçe transkript
        panel_layout = QHBoxLayout()

        # Sol panel - Arama sonuçları
        sol_panel = QWidget()
        sol_layout = QVBoxLayout()
        sol_layout.addWidget(QLabel("Arama Sonuçları:"))

        self.sonuc_alani = QScrollArea()
        self.sonuc_alani.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_widget.setLayout(self.scroll_layout)
        self.sonuc_alani.setWidget(self.scroll_widget)
        sol_layout.addWidget(self.sonuc_alani)

        sol_panel.setLayout(sol_layout)
        panel_layout.addWidget(sol_panel)

        # Sağ panel - Türkçe transkript
        sag_panel = QWidget()
        sag_layout = QVBoxLayout()
        sag_layout.addWidget(QLabel("Türkçe Transkript (Okunuş):"))

        self.turkce_transkript = QTextEdit()
        self.turkce_transkript.setPlaceholderText("Seçili ayetin Türkçe okunuşu burada görünecek...")
        self.turkce_transkript.setReadOnly(True)
        sag_layout.addWidget(self.turkce_transkript)

        sag_panel.setLayout(sag_layout)
        panel_layout.addWidget(sag_panel)

        arama_main_layout.addLayout(panel_layout)

        self.arama_tab.setLayout(arama_main_layout)
        self.tabs.addTab(self.arama_tab, "Arama")

        # İstatistikler Sekmesi
        self.istatistik_tab = QWidget()
        istatistik_layout = QVBoxLayout()

        self.istatistik_tabla = QTableWidget()
        self.istatistik_tabla.setColumnCount(3)
        self.istatistik_tabla.setHorizontalHeaderLabels(["Ölçüt", "Değer", "Açıklama"])
        istatistik_layout.addWidget(self.istatistik_tabla)

        self.guncelle_istatistik_buton = QPushButton("İstatistikleri Güncelle")
        self.guncelle_istatistik_buton.clicked.connect(self.guncelle_istatistikler)
        istatistik_layout.addWidget(self.guncelle_istatistik_buton)

        self.istatistik_tab.setLayout(istatistik_layout)
        self.tabs.addTab(self.istatistik_tab, "İstatistikler")

        # Karşılaştırmalı Meal Sekmesi
        self.karsilastirma_tab = QWidget()
        karsilastirma_layout = QVBoxLayout()

        karsilastirma_layout.addWidget(QLabel("Ayet Arama:"))
        self.ayet_arama = QLineEdit()
        self.ayet_arama.setPlaceholderText("1/7 veya 7 veya 6236")
        self.ayet_arama.returnPressed.connect(self.ayet_ara)
        karsilastirma_layout.addWidget(self.ayet_arama)

        # Meal seçiciler
        meal_layout = QHBoxLayout()
        meal_layout.addWidget(QLabel("Birinci Meal:"))
        self.birinci_meal_secici = QComboBox()
        self.birinci_meal_secici.addItems([
            "Diyanet İşleri Meali (Yeni)",
            "Elmalılı Hamdi Yazır Meali",
            "Hasan Basri Çantay Meali",
            "Abdulbaki Gölpınarlı Meali",
            "Ahmet Tekin Meali",
            "Ali Bulaç Meali",
            "Besim Atalay Meali (1965)",
            "Cemal Külünkoğlu Meali",
            "Edip Yüksel Meali",
            "Erhan Aktaş Meali",
            "Bahaeddin Sağlam Meali",
            "Bayraktar Bayraklı Meali",
            "Emrah Demiryent Meali",
            "Ali Fikri Yavuz Meali",
            "Ahmet Varol Meali"
        ])
        self.birinci_meal_secici.setCurrentText(self.secili_meal)
        self.birinci_meal_secici.currentTextChanged.connect(self.goster_sure)
        meal_layout.addWidget(self.birinci_meal_secici)

        meal_layout.addWidget(QLabel("İkinci Meal:"))
        self.ikinci_meal_secici = QComboBox()
        self.ikinci_meal_secici.addItems([
            "Diyanet İşleri Meali (Yeni)",
            "Elmalılı Hamdi Yazır Meali",
            "Hasan Basri Çantay Meali",
            "Abdulbaki Gölpınarlı Meali",
            "Ahmet Tekin Meali",
            "Ali Bulaç Meali",
            "Besim Atalay Meali (1965)",
            "Cemal Külünkoğlu Meali",
            "Edip Yüksel Meali",
            "Erhan Aktaş Meali",
            "Bahaeddin Sağlam Meali",
            "Bayraktar Bayraklı Meali",
            "Emrah Demiryent Meali",
            "Ali Fikri Yavuz Meali",
            "Ahmet Varol Meali"
        ])
        self.ikinci_meal_secici.setCurrentText("Elmalılı Hamdi Yazır Meali")
        self.ikinci_meal_secici.currentTextChanged.connect(self.goster_sure)
        meal_layout.addWidget(self.ikinci_meal_secici)
        karsilastirma_layout.addLayout(meal_layout)

        karsilastirma_layout.addWidget(QLabel("Sure Seçimi:"))
        self.sure_secici = QComboBox()
        self.sure_secici.addItems([f"{i+1}-{isim}" for i, isim in enumerate(self.sure_isimleri)])
        self.sure_secici.currentIndexChanged.connect(self.goster_sure)
        karsilastirma_layout.addWidget(self.sure_secici)

        self.sure_alani = QScrollArea()
        self.sure_alani.setWidgetResizable(True)
        self.sure_widget = QWidget()
        self.sol_layout = QVBoxLayout()
        self.sag_layout = QVBoxLayout()
        sure_ana_layout = QHBoxLayout()
        sure_ana_layout.addLayout(self.sol_layout)
        sure_ana_layout.addLayout(self.sag_layout)
        self.sure_widget.setLayout(sure_ana_layout)
        self.sure_alani.setWidget(self.sure_widget)
        karsilastirma_layout.addWidget(self.sure_alani)

        self.karsilastirma_tab.setLayout(karsilastirma_layout)
        self.tabs.addTab(self.karsilastirma_tab, "Karşılaştırmalı Meal")

        # Kök kelime analizi sekmesi
        self.kok_tab = QWidget()
        kok_layout = QVBoxLayout()
        kok_layout.addWidget(QLabel("Arapça Kelime Girin:"))
        self.kok_input = QLineEdit()
        kok_layout.addWidget(self.kok_input)
        self.kok_btn = QPushButton("Kök Bul")
        self.kok_btn.clicked.connect(self.kok_bul)
        kok_layout.addWidget(self.kok_btn)
        self.kok_result = QLabel()
        self.kok_result.setWordWrap(True)
        kok_layout.addWidget(self.kok_result)
        kok_layout.addWidget(QLabel("Türev Kelimeler:"))
        self.kok_turevler = QListWidget()
        self.kok_turevler.setMaximumHeight(150)
        self.kok_turevler.itemClicked.connect(self.turev_kelime_tiklandi)
        kok_layout.addWidget(self.kok_turevler)
        kok_layout.addWidget(QLabel("Örnek Ayet:"))
        self.kok_ornek = QLabel()
        self.kok_ornek.setWordWrap(True)
        kok_layout.addWidget(self.kok_ornek)
        self.kok_graf_btn = QPushButton("Frekans Grafiği Göster")
        self.kok_graf_btn.clicked.connect(self.kok_graf_goster)
        kok_layout.addWidget(self.kok_graf_btn)
        self.kok_ara_btn = QPushButton("Bu kök ile arama yap")
        self.kok_ara_btn.clicked.connect(self.kok_ile_ara)
        kok_layout.addWidget(self.kok_ara_btn)
        self.kok_tab.setLayout(kok_layout)
        self.tabs.addTab(self.kok_tab, "Kök Kelime Analizi")

        # Kelime Listesi Sekmesi
        self.kelime_tab = QWidget()
        kelime_layout = QVBoxLayout()

        # Ana panel - Sol: Türkçe kelimeler, Sağ: Arapça kelimeler
        kelime_panel_layout = QHBoxLayout()

        # Sol panel - Türkçe kelimeler
        sol_panel = QWidget()
        sol_layout = QVBoxLayout()
        sol_layout.addWidget(QLabel("📝 Kuranda Geçen Türkçe Kelimeler"))

        # Türkçe arama
        turkce_arama_layout = QHBoxLayout()
        turkce_arama_layout.addWidget(QLabel("Türkçe Arama:"))
        self.turkce_arama_kutusu = QLineEdit()
        self.turkce_arama_kutusu.setPlaceholderText("Türkçe kelime ara...")
        self.turkce_arama_kutusu.textChanged.connect(self.turkce_kelime_ara)
        turkce_arama_layout.addWidget(self.turkce_arama_kutusu)
        
        # Kök tabanlı arama seçeneği
        self.kok_arama_checkbox = QCheckBox("Kök tabanlı arama")
        self.kok_arama_checkbox.setChecked(True)  # Varsayılan olarak açık
        turkce_arama_layout.addWidget(self.kok_arama_checkbox)
        
        sol_layout.addLayout(turkce_arama_layout)

        # Harf bazlı filtreleme butonları (Türkçe)
        harf_layout = QVBoxLayout()
        harf_layout.addWidget(QLabel("Harf Filtresi:"))
        
        # Üst satır harfler
        ust_satir_layout = QHBoxLayout()
        ust_harfler = "ABCÇDEFGĞHIİJKLMN"
        self.turkce_harf_buttons = {}
        for harf in ust_harfler:
            btn = QPushButton(harf)
            btn.setFixedSize(30, 30)
            btn.clicked.connect(lambda checked, h=harf: self.turkce_harf_filtresi(h))
            ust_satir_layout.addWidget(btn)
            self.turkce_harf_buttons[harf] = btn
        harf_layout.addLayout(ust_satir_layout)
        
        # Alt satır harfler
        alt_satir_layout = QHBoxLayout()
        alt_harfler = "OÖPRSŞTUÜVYZ"
        for harf in alt_harfler:
            btn = QPushButton(harf)
            btn.setFixedSize(30, 30)
            btn.clicked.connect(lambda checked, h=harf: self.turkce_harf_filtresi(h))
            alt_satir_layout.addWidget(btn)
            self.turkce_harf_buttons[harf] = btn
        # Tümünü göster butonu
        btn_tum = QPushButton("Tümü")
        btn_tum.setFixedSize(50, 30)
        btn_tum.clicked.connect(self.turkce_tum_kelimeleri_goster)
        alt_satir_layout.addWidget(btn_tum)
        harf_layout.addLayout(alt_satir_layout)
        
        sol_layout.addLayout(harf_layout)

        # Türkçe kelime listesi
        self.turkce_liste = QListWidget()
        self.turkce_liste.setMaximumWidth(400)
        self.turkce_liste.setSelectionMode(QAbstractItemView.MultiSelection)
        self.turkce_liste.setContextMenuPolicy(Qt.CustomContextMenu)
        self.turkce_liste.customContextMenuRequested.connect(self.turkce_liste_sag_tik)
        self.turkce_liste.itemDoubleClicked.connect(self.turkce_kelime_detay)
        sol_layout.addWidget(self.turkce_liste)

        sol_panel.setLayout(sol_layout)
        kelime_panel_layout.addWidget(sol_panel)

        # Sağ panel - Arapça kelimeler
        sag_panel = QWidget()
        sag_layout = QVBoxLayout()
        sag_layout.addWidget(QLabel("📖 Kuranda Geçen Arapça Kelimeler"))

        # Arapça arama
        arapca_arama_layout = QHBoxLayout()
        arapca_arama_layout.addWidget(QLabel("Arapça Arama:"))
        self.arapca_arama_kutusu = QLineEdit()
        self.arapca_arama_kutusu.setPlaceholderText("Arapça kelime ara...")
        self.arapca_arama_kutusu.textChanged.connect(self.arapca_kelime_ara)
        arapca_arama_layout.addWidget(self.arapca_arama_kutusu)
        sag_layout.addLayout(arapca_arama_layout)

        # Harf bazlı filtreleme butonları (Arapça)
        arapca_harf_layout = QVBoxLayout()
        arapca_harf_layout.addWidget(QLabel("Harf Filtresi:"))
        
        # Üst satır harfler
        arapca_ust_satir_layout = QHBoxLayout()
        ust_harfler_arapca = "ABCÇDEFGĞHIİJKLMN"
        self.arapca_harf_buttons = {}
        for harf in ust_harfler_arapca:
            btn = QPushButton(harf)
            btn.setFixedSize(30, 30)
            btn.clicked.connect(lambda checked, h=harf: self.arapca_harf_filtresi(h))
            arapca_ust_satir_layout.addWidget(btn)
            self.arapca_harf_buttons[harf] = btn
        arapca_harf_layout.addLayout(arapca_ust_satir_layout)
        
        # Alt satır harfler
        arapca_alt_satir_layout = QHBoxLayout()
        alt_harfler_arapca = "OÖPRSŞTUÜVYZ"
        for harf in alt_harfler_arapca:
            btn = QPushButton(harf)
            btn.setFixedSize(30, 30)
            btn.clicked.connect(lambda checked, h=harf: self.arapca_harf_filtresi(h))
            arapca_alt_satir_layout.addWidget(btn)
            self.arapca_harf_buttons[harf] = btn
        # Tümünü göster butonu
        btn_tum_arapca = QPushButton("Tümü")
        btn_tum_arapca.setFixedSize(50, 30)
        btn_tum_arapca.clicked.connect(self.arapca_tum_kelimeleri_goster)
        arapca_alt_satir_layout.addWidget(btn_tum_arapca)
        arapca_harf_layout.addLayout(arapca_alt_satir_layout)
        
        sag_layout.addLayout(arapca_harf_layout)

        # Arapça kelime listesi
        self.arapca_liste = QListWidget()
        self.arapca_liste.setMaximumWidth(400)
        self.arapca_liste.setSelectionMode(QAbstractItemView.MultiSelection)
        self.arapca_liste.setContextMenuPolicy(Qt.CustomContextMenu)
        self.arapca_liste.customContextMenuRequested.connect(self.arapca_liste_sag_tik)
        self.arapca_liste.itemDoubleClicked.connect(self.arapca_kelime_detay)
        sag_layout.addWidget(self.arapca_liste)

        sag_panel.setLayout(sag_layout)
        kelime_panel_layout.addWidget(sag_panel)

        kelime_layout.addLayout(kelime_panel_layout)
        self.kelime_tab.setLayout(kelime_layout)
        self.tabs.addTab(self.kelime_tab, "Kelime Listesi")

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)
        self.guncelle_istatistikler()  # İlk açılışta istatistikleri doldur
        self.goster_sure()  # İlk sureyi göster
        self.kelime_listelerini_doldur()  # Kelime listelerini doldur

    def speak_text(self, text):
        try:
            import tempfile
            import time

            # Benzersiz geçici dosya oluştur
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name

            # TTS oluştur ve kaydet
            tts = gTTS(text=text, lang='tr')
            tts.save(temp_path)

            # pygame ile ses dosyasını oynat (daha güvenilir)
            try:
                import pygame

                # pygame mixer'ını başlat (eğer başlatılmamışsa)
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

                # Önceki müziği durdur ve temizle
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                pygame.mixer.music.unload()

                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.set_volume(0.8)  # Ses seviyesini %80'e ayarla
                pygame.mixer.music.play()

                # Oynatma bitene kadar bekle (maksimum 30 saniye)
                timeout = 0
                while pygame.mixer.music.get_busy() and timeout < 300:  # 30 saniye timeout
                    time.sleep(0.1)
                    timeout += 1

                pygame.mixer.music.stop()
                pygame.mixer.music.unload()  # Belleği temizle

            except Exception as pygame_error:
                # pygame başarısız olursa playsound'u dene
                try:
                    playsound.playsound(temp_path, block=True)
                except Exception as playsound_error:
                    # Her iki yöntem de başarısız olursa kullanıcıya bilgi ver
                    error_msg = f"Ses oynatma başarısız oldu:\n\n"
                    error_msg += f"pygame hatası: {str(pygame_error)}\n\n"
                    error_msg += f"playsound hatası: {str(playsound_error)}\n\n"
                    error_msg += "Öneriler:\n"
                    error_msg += "1. Ses sürücülerinizi kontrol edin\n"
                    error_msg += "2. Başka uygulamalarda ses çalışıyor mu?\n"
                    error_msg += "3. Sistem ses ayarlarını kontrol edin\n"
                    error_msg += "4. Gerekirse bilgisayarı yeniden başlatın"

                    QMessageBox.warning(self, "TTS Hata", error_msg)
                    return

            # Geçici dosyayı temizle
            try:
                os.remove(temp_path)
            except:
                pass  # Dosya silinemezse devam et

        except Exception as e:
            QMessageBox.warning(self, "TTS Hata", f"Sesli okuma hatası: {str(e)}")

    def guncelle_sayfa(self):
        kelime = self.arama_kutusu.text().strip()
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if not kelime:
            return

        flags = 0 if self.case_sensitive.isChecked() else re.IGNORECASE

        # Temel arama sonuçlarını al
        if self.regex_search.isChecked():
            try:
                pattern = re.compile(kelime, flags)
                arama_turu = self.arama_turu.currentData()
                if arama_turu == "turkish":
                    sonuclar = [v for v in self.veriler if pattern.search(v.get("meal", ""))]
                elif arama_turu == "arabic":
                    sonuclar = [v for v in self.veriler if re.search(kelime, v.get("arapca", ""), flags) or re.search(normalize_arabic(kelime), normalize_arabic(v.get("arapca", "")), flags)]
                else:  # both
                    sonuclar = [
                        v for v in self.veriler
                        if pattern.search(v.get("meal", "")) or re.search(kelime, v.get("arapca", ""), flags) or re.search(normalize_arabic(kelime), normalize_arabic(v.get("arapca", "")), flags)
                    ]
            except re.error:
                QMessageBox.warning(self, "Hata", "Geçersiz regex deseni")
                return
        else:
            if self.multi_word.isChecked():
                words = kelime.split()
                arama_turu = self.arama_turu.currentData()
                if arama_turu == "turkish":
                    if flags & re.IGNORECASE:
                        sonuclar = [
                            v for v in self.veriler
                            if all(word.lower() in v.get("meal", "").lower() for word in words)
                        ]
                    else:
                        sonuclar = [
                            v for v in self.veriler
                            if all(word in v.get("meal", "") for word in words)
                        ]
                elif arama_turu == "arabic":
                    if flags & re.IGNORECASE:
                        sonuclar = [
                            v for v in self.veriler
                            if all(normalize_arabic(word).lower() in normalize_arabic(v.get("arapca", "")).lower() for word in words)
                        ]
                    else:
                        sonuclar = [
                            v for v in self.veriler
                            if all(normalize_arabic(word) in normalize_arabic(v.get("arapca", "")) for word in words)
                        ]
                else:  # both
                    if flags & re.IGNORECASE:
                        sonuclar = [
                            v for v in self.veriler
                            if all(
                                any(word.lower() in field.lower() for field in [v.get("meal", ""), normalize_arabic(v.get("arapca", ""))])
                                for word in words
                            )
                        ]
                    else:
                        sonuclar = [
                            v for v in self.veriler
                            if all(
                                any(word in field for field in [v.get("meal", ""), normalize_arabic(v.get("arapca", ""))])
                                for word in words
                            )
                        ]
            else:
                arama_turu = self.arama_turu.currentData()
                if arama_turu == "turkish":
                    if flags & re.IGNORECASE:
                        sonuclar = [v for v in self.veriler if kelime.lower() in v.get("meal", "").lower()]
                    else:
                        sonuclar = [v for v in self.veriler if kelime in v.get("meal", "")]
                elif arama_turu == "arabic":
                    if flags & re.IGNORECASE:
                        sonuclar = [v for v in self.veriler if normalize_arabic(kelime).lower() in normalize_arabic(v.get("arapca", "")).lower()]
                    else:
                        sonuclar = [v for v in self.veriler if normalize_arabic(kelime) in normalize_arabic(v.get("arapca", ""))]
                else:  # both
                    if flags & re.IGNORECASE:
                        sonuclar = [
                            v for v in self.veriler
                            if kelime.lower() in v.get("meal", "").lower() or normalize_arabic(kelime).lower() in normalize_arabic(v.get("arapca", "")).lower()
                        ]
                    else:
                        sonuclar = [
                            v for v in self.veriler
                            if kelime in v.get("meal", "") or normalize_arabic(kelime) in normalize_arabic(v.get("arapca", ""))
                        ]

        # Gelişmiş filtreleri uygula
        if self.filtre_uygula.isChecked():
            # Mekki/Medeni filtresi
            vahiy_turu = self.vahiy_filtresi.currentData()
            mekki_sureler = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114]

            if vahiy_turu == "mekki":
                sonuclar = [v for v in sonuclar if v['sure'] in mekki_sureler]
            elif vahiy_turu == "medeni":
                sonuclar = [v for v in sonuclar if v['sure'] not in mekki_sureler]

            # Sure filtresi
            sure_no = self.sure_filtresi.currentData()
            if sure_no > 0:
                sonuclar = [v for v in sonuclar if v['sure'] == sure_no]

            # Ayet aralığı filtresi
            ayet_min = self.ayet_min.value()
            ayet_max = self.ayet_max.value()
            if ayet_min > 0 or ayet_max < 286:
                sonuclar = [v for v in sonuclar if ayet_min <= v['ayet'] <= ayet_max]

            # Kelime uzunluğu filtresi (sadece Arapça için)
            uzunluk_min = self.uzunluk_min.value()
            uzunluk_max = self.uzunluk_max.value()
            if uzunluk_min > 0 or uzunluk_max < 20:
                filtered_sonuclar = []
                for v in sonuclar:
                    arapca_words = re.findall(r'<span[^>]*>([^<]+)</span>', v.get("arapca", ""))
                    # En az bir kelime uzunluk kriterini sağlıyor mu kontrol et
                    has_matching_word = any(uzunluk_min <= len(normalize_arabic(word)) <= uzunluk_max for word in arapca_words)
                    if has_matching_word:
                        filtered_sonuclar.append(v)
                sonuclar = filtered_sonuclar

        toplam_sonuc = len(sonuclar)
        self.sonuc_sayisi_label.setText(f"Toplam sonuç: {toplam_sonuc}")
        toplam_sayfa = max(1, (len(sonuclar) + self.satirSayisi - 1) // self.satirSayisi)
        self.sayfa = min(self.sayfa, toplam_sayfa - 1)
        basla = self.sayfa * self.satirSayisi
        bitis = basla + self.satirSayisi

        for v in sonuclar[basla:bitis]:
            sure_adi = self.sure_isimleri[v['sure']-1]
            if is_arabic_root(kelime):
                # Kök arama: kök eşleşen kelimeleri vurgula
                root_words = get_root_words_from_ayet(v.get("arapca", ""), kelime)
                meal = vurgu_ekle(v.get("meal", ""), root_words, renk="orange")
                arapca = vurgu_ekle(v.get("arapca", ""), root_words, renk="yellow")
            else:
                # Normal arama
                if self.multi_word.isChecked():
                    kelimeler = kelime.split()
                else:
                    kelimeler = [kelime]
                meal = vurgu_ekle(v.get("meal", ""), kelimeler, renk="orange")
                arapca = vurgu_ekle(v.get("arapca", ""), kelimeler, renk="yellow")

            html = f"""
            <div style='font-size:12px; color:gray; margin-bottom:5px;'>{v['sure']}-{sure_adi}, Ayet {v['ayet']}</div>
            <div style='font-size:18px; font-weight:bold;'>{meal}</div>
            <div style='font-size:16px;'>{arapca}</div>
            """

            widget = QWidget()
            layout_h = QHBoxLayout()
            kutu = QLabel()
            kutu.setWordWrap(True)
            kutu.setTextInteractionFlags(Qt.TextSelectableByMouse)
            kutu.setStyleSheet("""
                QLabel {
                    background-color: #f1f1f1;
                    border: 1px solid #ccc;
                    padding: 10px;
                    margin-bottom: 8px;
                    font-size: 14px;
                }
                QLabel:hover {
                    background-color: #e8f4f8;
                    border: 1px solid #4a90e2;
                }
            """)
            kutu.setTextFormat(Qt.RichText)
            kutu.setText(html)
            # Ayet seçimi için tıklanabilir yap
            kutu.mousePressEvent = lambda ev, ayet=v: self.ayet_sec(ayet)
            layout_h.addWidget(kutu)
            widget.setLayout(layout_h)
            self.scroll_layout.addWidget(widget)

    def meal_degistir(self):
        self.secili_meal = self.meal_secici.currentText()
        self.veriler = veri_yukle(self.secili_meal)
        self.sayfa = 0
        self.guncelle_sayfa()

    def sayfa_geri(self):
        if self.sayfa > 0:
            self.sayfa -= 1
            self.guncelle_sayfa()

    def sayfa_ileri(self):
        self.sayfa += 1
        self.guncelle_sayfa()

    def ayet_sec(self, ayet):
        """Arama sonuçlarından bir ayet seçildiğinde çağrılır"""
        self.secili_ayet = ayet
        self.favori_ekle_btn.setEnabled(True)
        self.sesli_oku_btn.setEnabled(True)
        self.turkce_transkript_goster(ayet)

    def secili_ayeti_favoriye_ekle(self):
        """Üst buton ile seçili ayeti favoriye ekle"""
        if hasattr(self, 'secili_ayet') and self.secili_ayet:
            self.favoriye_ekle(self.secili_ayet)

    def secili_ayeti_sesli_oku(self):
        """Üst buton ile seçili ayeti sesli oku"""
        if hasattr(self, 'secili_ayet') and self.secili_ayet:
            text = self.secili_ayet.get("meal", "")
            self.speak_text(text)

    def turkce_transkript_goster(self, ayet):
        """Seçili ayetin Türkçe transkriptini göster"""
        if not ayet:
            self.turkce_transkript.setText("Seçili ayet yok")
            return

        sure_no = ayet['sure']
        ayet_no = ayet['ayet']
        sure_adi = self.sure_isimleri[sure_no-1]
        meal = ayet.get("meal", "")

        # Kelime bazlı Türkçe transkripti al
        transkript_kelimeler = []
        for kelime in self.turkce_transkript_verisi:
            if kelime['sureNo'] == sure_no and kelime['ayetNo'] == ayet_no:
                transkript_kelimeler.append(kelime['turkce'])

        # Transkripti oluştur
        transkript_metin = " ".join(transkript_kelimeler) if transkript_kelimeler else "Transkript bulunamadı"

        html = f"""
        <div style='font-size:12px; color:gray; margin-bottom:10px; border-bottom:1px solid #ccc; padding-bottom:5px;'>
            <b>Süre {sure_no} - {sure_adi}, Ayet {ayet_no}</b>
        </div>
        <div style='font-size:14px; margin-bottom:15px;'>
            <b>Tam Meal:</b><br>
            {meal}
        </div>
        <div style='font-size:14px; background-color:#f9f9f9; padding:10px; border-radius:5px;'>
            <b>Kelime Bazlı Türkçe Transkript:</b><br>
            {transkript_metin}
        </div>
        """

        self.turkce_transkript.setHtml(html)

    def favoriye_ekle(self, ayet):
        if ayet not in self.favorites:
            self.favorites.append(ayet)
            with open('favorites.json', 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, "Favori", "Ayet favorilere eklendi!")
        else:
            QMessageBox.information(self, "Favori", "Bu ayet zaten favorilerde.")

    def guncelle_istatistikler(self):
        if not self.veriler:
            return

        sureler = {}
        toplam_ayet = len(self.veriler)
        toplam_kelime_turkce = 0
        toplam_kelime_arapca = 0
        unique_words_turkce = set()
        unique_words_arapca = set()
        word_frequencies = {}
        letter_counts = {}
        word_lengths = {}
        mekki_sureler = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114]

        for item in self.veriler:
            sure = item['sure']
            if sure not in sureler:
                sureler[sure] = 0
            sureler[sure] += 1

            # Türkçe kelime analizi
            meal = item.get('meal', '')
            turkce_words = meal.split()
            toplam_kelime_turkce += len(turkce_words)
            for word in turkce_words:
                word_lower = word.lower().strip('.,!?;:')
                if word_lower:
                    unique_words_turkce.add(word_lower)
                    word_frequencies[word_lower] = word_frequencies.get(word_lower, 0) + 1

            # Arapça kelime analizi
            arapca_html = item.get('arapca', '')
            arapca_words = re.findall(r'<span[^>]*>([^<]+)</span>', arapca_html)
            toplam_kelime_arapca += len(arapca_words)
            for word in arapca_words:
                word_normalized = normalize_arabic(word)
                if word_normalized:
                    unique_words_arapca.add(word_normalized)
                    # Harf analizi
                    for char in word_normalized:
                        if char.isalpha():
                            letter_counts[char] = letter_counts.get(char, 0) + 1
                    # Kelime uzunluğu analizi
                    length = len(word_normalized)
                    word_lengths[length] = word_lengths.get(length, 0) + 1

        sure_sayisi = len(sureler)
        en_uzun_sure = max(sureler.values())
        en_kisa_sure = min(sureler.values())
        ortalama_ayet_sure = toplam_ayet / sure_sayisi if sure_sayisi > 0 else 0
        ortalama_kelime_ayet_turkce = toplam_kelime_turkce / toplam_ayet if toplam_ayet > 0 else 0
        ortalama_kelime_ayet_arapca = toplam_kelime_arapca / toplam_ayet if toplam_ayet > 0 else 0

        # Mekki ve Medeni sure sayıları
        mekki_sayisi = len([s for s in sureler.keys() if s in mekki_sureler])
        medeni_sayisi = sure_sayisi - mekki_sayisi

        # En sık kullanılan kelimeler (Türkçe)
        top_words = sorted(word_frequencies.items(), key=lambda x: x[1], reverse=True)[:10]

        # En sık kullanılan harfler
        top_letters = sorted(letter_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Kelime uzunluğu dağılımı
        avg_word_length = sum(k * v for k, v in word_lengths.items()) / sum(word_lengths.values()) if word_lengths else 0

        # İstatistikleri tabloya ekle
        self.istatistik_tabla.setRowCount(20)
        row = 0

        # Temel istatistikler
        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("Toplam Ayet"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(str(toplam_ayet)))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("Kuran'daki toplam ayet sayısı"))
        row += 1

        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("Sure Sayısı"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(str(sure_sayisi)))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("Kuran'daki sure sayısı"))
        row += 1

        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("Ortalama Ayet/Sure"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(f"{ortalama_ayet_sure:.1f}"))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("Her suredeki ortalama ayet sayısı"))
        row += 1

        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("En Uzun Sure (Ayet)"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(str(en_uzun_sure)))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("En çok ayet içeren sure"))
        row += 1

        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("En Kısa Sure (Ayet)"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(str(en_kisa_sure)))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("En az ayet içeren sure"))
        row += 1

        # Kelime istatistikleri
        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("Toplam Kelime (Türkçe)"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(str(toplam_kelime_turkce)))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("Meal metnindeki toplam kelime sayısı"))
        row += 1

        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("Toplam Kelime (Arapça)"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(str(toplam_kelime_arapca)))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("Arapça metindeki toplam kelime sayısı"))
        row += 1

        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("Ortalama Kelime/Ayet (Türkçe)"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(f"{ortalama_kelime_ayet_turkce:.1f}"))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("Her ayetteki ortalama kelime sayısı"))
        row += 1

        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("Ortalama Kelime/Ayet (Arapça)"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(f"{ortalama_kelime_ayet_arapca:.1f}"))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("Her ayetteki ortalama Arapça kelime sayısı"))
        row += 1

        # Benzersiz kelime sayısı
        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("Benzersiz Kelime (Türkçe)"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(str(len(unique_words_turkce))))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("Meal metnindeki benzersiz kelime sayısı"))
        row += 1

        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("Benzersiz Kelime (Arapça)"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(str(len(unique_words_arapca))))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("Arapça metindeki benzersiz kelime sayısı"))
        row += 1

        # Mekki/Medeni istatistikleri
        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("Mekki Sure Sayısı"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(str(mekki_sayisi)))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("Mekke'de inen sure sayısı"))
        row += 1

        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("Medeni Sure Sayısı"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(str(medeni_sayisi)))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("Medine'de inen sure sayısı"))
        row += 1

        # En sık kullanılan kelimeler
        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("En Sık Kelime 1"))
        if top_words:
            self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(f"{top_words[0][0]} ({top_words[0][1]})"))
        else:
            self.istatistik_tabla.setItem(row, 1, QTableWidgetItem("-"))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("En çok kullanılan Türkçe kelime"))
        row += 1

        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("En Sık Kelime 2-5"))
        if len(top_words) > 1:
            words_2_5 = [f"{word} ({count})" for word, count in top_words[1:5]]
            self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(", ".join(words_2_5)))
        else:
            self.istatistik_tabla.setItem(row, 1, QTableWidgetItem("-"))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("2-5. en çok kullanılan kelimeler"))
        row += 1

        # Harf istatistikleri
        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("En Sık Harfler"))
        if top_letters:
            letters_str = ", ".join([f"{letter} ({count})" for letter, count in top_letters])
            self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(letters_str))
        else:
            self.istatistik_tabla.setItem(row, 1, QTableWidgetItem("-"))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("En çok kullanılan Arapça harfler"))
        row += 1

        # Kelime uzunluğu
        self.istatistik_tabla.setItem(row, 0, QTableWidgetItem("Ortalama Kelime Uzunluğu"))
        self.istatistik_tabla.setItem(row, 1, QTableWidgetItem(f"{avg_word_length:.1f}"))
        self.istatistik_tabla.setItem(row, 2, QTableWidgetItem("Arapça kelimelerin ortalama harf sayısı"))
        row += 1

        self.istatistik_tabla.resizeColumnsToContents()

    def sure_ayet_bul(self, query):
        if '/' in query:
            sure, ayet = map(int, query.split('/'))
        else:
            num = int(query)
            # Her zaman toplam ayetlere göre hesapla
            cumulative = 0
            sure = 114  # fallback
            ayet = 6
            for s in range(1, 115):
                sure_ayet_sayisi = len([item for item in self.veriler if item['sure'] == s])
                if cumulative + sure_ayet_sayisi >= num:
                    sure = s
                    ayet = num - cumulative
                    break
                cumulative += sure_ayet_sayisi
        return sure, ayet

    def ayet_ara(self):
        query = self.ayet_arama.text().strip()
        if not query:
            return
        try:
            sure, ayet = self.sure_ayet_bul(query)
            ayet_item = next((item for item in self.veriler if item['sure'] == sure and item['ayet'] == ayet), None)
            if ayet_item:
                # Tek ayet göster
                for i in reversed(range(self.sol_layout.count())):
                    widget = self.sol_layout.itemAt(i).widget()
                    if widget:
                        widget.setParent(None)

                arapca = ayet_item.get('arapca', '')
                meal = ayet_item.get('meal', '')

                html = f"""
                <div style='font-size:16px; font-weight:bold; margin-bottom:10px;'>
                    <span style='color:blue;'>Süre {sure}, Ayet {ayet}:</span><br>
                    <span style='font-size:18px;'>{arapca}</span><br>
                    <span style='color:green;'>{meal}</span>
                </div>
                """

                kutu = QLabel()
                kutu.setWordWrap(True)
                kutu.setTextInteractionFlags(Qt.TextSelectableByMouse)
                kutu.setStyleSheet("""
                    QLabel {
                        background-color: #f9f9f9;
                        border: 1px solid #ddd;
                        padding: 15px;
                        margin-bottom: 10px;
                        font-size: 14px;
                    }
                """)
                kutu.setTextFormat(Qt.RichText)
                kutu.setText(html)
                self.sol_layout.addWidget(kutu)
                tts_btn = QPushButton("🔊 Sesli Oku")
                tts_btn.clicked.connect(lambda checked, text=meal: self.speak_text(text))
                self.sol_layout.addWidget(tts_btn)
            else:
                QMessageBox.warning(self, "Bulunamadı", f"Süre {sure}, Ayet {ayet} bulunamadı")
        except ValueError:
            QMessageBox.warning(self, "Hata", "Geçersiz format. Örnek: 1/7, 7, 6236")

    def kok_bul(self):
        word = self.kok_input.text().strip()
        if not word:
            return
        try:
            # Önce veri tabanından kök al, yoksa gelişmiş kök bulma kullan
            lemma = get_kok_from_db(word, self.veriler)
            if not lemma:
                lemma = gelismis_kok_bul(normalize_arabic(word))

            # Kökün geçerli olup olmadığını kontrol et
            if not lemma or len(lemma) < 2:
                lemma = basit_kok_bul(normalize_arabic(word))

            count = self.kok_frekans_hesapla(lemma)
            turevler = self.kok_turevleri_bul(lemma)
            ornek = self.kok_ornek_bul(lemma)
            self.kok_result.setText(f"Kök/Lemma: {lemma}\nFrekans: {count}")

            # QListWidget'i temizle ve türevleri ekle
            self.kok_turevler.clear()
            for turev in turevler:
                frekans = self.kelime_frekans_hesapla(turev)
                item_text = f"{turev} ({frekans})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, turev)  # Kelimeyi sakla
                self.kok_turevler.addItem(item)

            self.kok_ornek.setText(ornek)
        except Exception as e:
            self.kok_result.setText(f"Hata: {str(e)}")
            self.kok_turevler.clear()
            self.kok_ornek.setText("")

    def kok_frekans_hesapla(self, root):
        count = 0
        root_normalized = normalize_kok(root)
        for item in self.veriler:
            arapca_html = item.get('arapca', '')
            # HTML'den kök ve kelime çıkar
            koks = re.findall(r'<span[^>]*kok="([^"]*)"[^>]*>([^<]+)</span>', arapca_html)
            for kok, kelime in koks:
                if normalize_kok(kok) == root_normalized:
                    count += 1
        return count

    def kok_turevleri_bul(self, root):
        turevler = set()
        root_normalized = normalize_kok(root)
        for item in self.veriler:
            arapca_html = item.get('arapca', '')
            koks = re.findall(r'<span[^>]*kok="([^"]*)"[^>]*>([^<]+)</span>', arapca_html)
            for kok, kelime in koks:
                if normalize_kok(kok) == root_normalized:
                    turevler.add(kelime)
        return sorted(list(turevler))

    def kelime_frekans_hesapla(self, kelime):
        """Belirli bir kelimenin toplam frekansını hesaplar"""
        count = 0
        kelime_normalized = normalize_arabic(kelime)
        for item in self.veriler:
            arapca_html = item.get('arapca', '')
            words = re.findall(r'<span[^>]*>([^<]+)</span>', arapca_html)
            for word in words:
                if normalize_arabic(word) == kelime_normalized:
                    count += 1
        return count

    def kok_ornek_bul(self, root):
        """Kök için örnek ayet bul"""
        root_normalized = normalize_kok(root)
        for item in self.veriler:
            arapca_html = item.get('arapca', '')
            koks = re.findall(r'<span[^>]*kok="([^"]*)"[^>]*>([^<]+)</span>', arapca_html)
            for kok, kelime in koks:
                if normalize_kok(kok) == root_normalized:
                    sure = item['sure']
                    ayet = item['ayet']
                    meal = item.get('meal', '')
                    return f"Süre {sure}, Ayet {ayet}:\n{strip_html_tags(arapca_html)}\n{meal}"
        return "Örnek bulunamadı"

    def kok_graf_goster(self):
        root = self.kok_result.text().split('\n')[0].replace("Kök/Lemma: ", "")
        if root:
            count = self.kok_frekans_hesapla(root)
            plt.figure(figsize=(6,4))
            plt.bar([root], [count])
            plt.title(f"Kök '{root}' Frekansı")
            plt.ylabel("Geçiş Sayısı")
            plt.show()

    def turev_kelime_tiklandi(self, item):
        """Türev kelimeye tıklandığında arama yap"""
        kelime = item.data(Qt.UserRole)
        if kelime:
            self.tabs.setCurrentIndex(0)  # Arama sekmesine geç
            self.arama_kutusu.setText(kelime)
            self.guncelle_sayfa()

    def kok_ile_ara(self):
        root = self.kok_result.text().split('\n')[0].replace("Kök/Lemma: ", "")
        if root:
            self.tabs.setCurrentIndex(0)
            self.arama_kutusu.setText(root)
            self.guncelle_sayfa()

    def goster_sure(self):
        sure_text = self.sure_secici.currentText()
        if not sure_text:
            return
        sure_no = int(sure_text.split('-')[0])  # "1-Fatiha" -> 1

        # Önceki widget'ları temizle
        for i in reversed(range(self.sol_layout.count())):
            widget = self.sol_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        for i in reversed(range(self.sag_layout.count())):
            widget = self.sag_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        birinci_meal = self.birinci_meal_secici.currentText()
        ikinci_meal = self.ikinci_meal_secici.currentText()

        # Birinci veri
        if birinci_meal == self.secili_meal:
            birinci_veri = self.veriler
        else:
            birinci_veri = veri_yukle(birinci_meal)

        # İkinci veri
        if ikinci_meal == self.secili_meal:
            ikinci_veri = self.veriler
        else:
            ikinci_veri = veri_yukle(ikinci_meal)

        sure_ayetleri = [item for item in birinci_veri if item['sure'] == sure_no]
        sure_ayetleri.sort(key=lambda x: x['ayet'])

        for item in sure_ayetleri:
            ayet_no = item['ayet']
            arapca = item.get('arapca', '')
            birinci_meal_text = item.get('meal', '')

            # Sol sütun - Birinci meal
            html_sol = f"""
            <div style='font-size:14px; font-weight:bold; margin-bottom:10px;'>
                <span style='color:blue;'>Ayet {ayet_no}:</span><br>
                <span style='font-size:16px;'>{arapca}</span><br>
                <span style='color:green;'>{birinci_meal_text}</span>
            </div>
            """

            kutu_sol = QLabel()
            kutu_sol.setWordWrap(True)
            kutu_sol.setTextInteractionFlags(Qt.TextSelectableByMouse)
            kutu_sol.setStyleSheet("""
                QLabel {
                    background-color: #f0f8ff;
                    border: 1px solid #ddd;
                    padding: 10px;
                    margin-bottom: 5px;
                    font-size: 12px;
                }
            """)
            kutu_sol.setTextFormat(Qt.RichText)
            kutu_sol.setText(html_sol)
            widget_sol = QWidget()
            layout_sol_v = QVBoxLayout()
            layout_sol_v.addWidget(kutu_sol)
            tts_btn_sol = QPushButton("🔊 Sesli Oku")
            tts_btn_sol.clicked.connect(lambda checked, text=birinci_meal_text: self.speak_text(text))
            layout_sol_v.addWidget(tts_btn_sol)
            widget_sol.setLayout(layout_sol_v)
            self.sol_layout.addWidget(widget_sol)

            # Sağ sütun - İkinci meal
            ikinci_item = next((i for i in ikinci_veri if i['sure'] == sure_no and i['ayet'] == ayet_no), None)
            if ikinci_item:
                ikinci_meal_text = ikinci_item.get('meal', '')
            else:
                ikinci_meal_text = "Meal bulunamadı"

            html_sag = f"""
            <div style='font-size:14px; font-weight:bold; margin-bottom:10px;'>
                <span style='color:blue;'>Ayet {ayet_no}:</span><br>
                <span style='font-size:16px;'>{arapca}</span><br>
                <span style='color:red;'>{ikinci_meal_text}</span>
            </div>
            """

            kutu_sag = QLabel()
            kutu_sag.setWordWrap(True)
            kutu_sag.setTextInteractionFlags(Qt.TextSelectableByMouse)
            kutu_sag.setStyleSheet("""
                QLabel {
                    background-color: #fff0f5;
                    border: 1px solid #ddd;
                    padding: 10px;
                    margin-bottom: 5px;
                    font-size: 12px;
                }
            """)
            kutu_sag.setTextFormat(Qt.RichText)
            kutu_sag.setText(html_sag)
            widget_sag = QWidget()
            layout_sag_v = QVBoxLayout()
            layout_sag_v.addWidget(kutu_sag)
            tts_btn_sag = QPushButton("🔊 Sesli Oku")
            tts_btn_sag.clicked.connect(lambda checked, text=ikinci_meal_text: self.speak_text(text))
            layout_sag_v.addWidget(tts_btn_sag)
            widget_sag.setLayout(layout_sag_v)
            self.sag_layout.addWidget(widget_sag)

    def kelime_listelerini_doldur(self):
        """Kelime listelerini doldurur"""
        # Türkçe kelimeler
        self.turkce_liste.clear()
        for kelime in self.kuran_kelimeleri.get("turkce", []):
            siklik = self.kelime_sikliklari.get(normalize_text(kelime), 0)
            self.turkce_liste.addItem(f"{kelime} ({siklik})")

        # Arapça kelimeler
        self.arapca_liste.clear()
        for kelime in self.kuran_kelimeleri.get("arapca", []):
            self.arapca_liste.addItem(kelime)

    def turkce_kelime_ara(self, text):
        """Türkçe kelimelerde arama yapar (normal + kök tabanlı)"""
        self.turkce_liste.clear()
        arama = text.lower().strip()

        if not arama:
            # Arama kutusu boşsa tüm kelimeleri göster
            for kelime in self.kuran_kelimeleri.get("turkce", []):
                siklik = self.kelime_sikliklari.get(normalize_text(kelime), 0)
                self.turkce_liste.addItem(f"{kelime} ({siklik})")
        else:
            # Normalize edilmiş arama
            arama_normalized = normalize_text(arama)
            bulunan_kelimeler = set()
            
            # İlk olarak normalize edilmiş arama yap
            for kelime in self.kuran_kelimeleri.get("turkce", []):
                if arama_normalized in normalize_text(kelime):
                    bulunan_kelimeler.add(kelime)
            
            # Eğer az sonuç bulunduysa, benzer kelimeler ekle
            if len(bulunan_kelimeler) < 5:
                benzer_kelimeler = difflib.get_close_matches(arama, self.kuran_kelimeleri.get("turkce", []), n=10, cutoff=0.6)
                bulunan_kelimeler.update(benzer_kelimeler)
            
            # Kök tabanlı arama ekle (eğer Zemberek varsa ve checkbox işaretliyse)
            if ZEMBEREK_AVAILABLE and self.kok_arama_checkbox.isChecked() and len(bulunan_kelimeler) < 10:
                arama_koku = turkce_kok_bul(arama)
                kok_eslesenler = kok_eslesmesi_bul(arama_koku, self.kuran_kelimeleri.get("turkce", []))
                bulunan_kelimeler.update(kok_eslesenler)
            
            # Sonuçları listeye ekle
            for kelime in sorted(bulunan_kelimeler):
                siklik = self.kelime_sikliklari.get(normalize_text(kelime), 0)
                self.turkce_liste.addItem(f"{kelime} ({siklik})")

    def arapca_kelime_ara(self, text):
        """Arapça kelimelerde arama yapar"""
        self.arapca_liste.clear()
        arama = text.strip()

        if not arama:
            # Arama kutusu boşsa tüm kelimeleri göster
            for kelime in self.kuran_kelimeleri.get("arapca", []):
                self.arapca_liste.addItem(kelime)
        else:
            # Normalize edilmiş arama
            arama_normalized = normalize_arabic(arama)
            bulunan_kelimeler = set()
            
            # İlk olarak normalize edilmiş arama yap
            for kelime in self.kuran_kelimeleri.get("arapca", []):
                if arama_normalized in normalize_arabic(kelime):
                    bulunan_kelimeler.add(kelime)
            
            # Eğer az sonuç bulunduysa, benzer kelimeler ekle
            if len(bulunan_kelimeler) < 5:
                benzer_kelimeler = difflib.get_close_matches(arama, self.kuran_kelimeleri.get("arapca", []), n=10, cutoff=0.6)
                bulunan_kelimeler.update(benzer_kelimeler)
            
            # Sonuçları listeye ekle
            for kelime in sorted(bulunan_kelimeler):
                self.arapca_liste.addItem(kelime)

    def turkce_liste_sag_tik(self, position):
        """Türkçe kelime listesi için sağ tıklama menüsü"""
        selected_items = self.turkce_liste.selectedItems()
        if not selected_items:
            return

        menu = QMenu()
        if len(selected_items) == 1:
            kopyala_action = menu.addAction("📋 Kopyala")
            kopyala_action.triggered.connect(self.turkce_kelime_kopyala)
        else:
            kopyala_action = menu.addAction(f"📋 {len(selected_items)} Kelimeyi Kopyala")
            kopyala_action.triggered.connect(self.turkce_kelimeleri_kopyala)

        menu.exec_(self.turkce_liste.mapToGlobal(position))

    def arapca_liste_sag_tik(self, position):
        """Arapça kelime listesi için sağ tıklama menüsü"""
        selected_items = self.arapca_liste.selectedItems()
        if not selected_items:
            return

        menu = QMenu()
        if len(selected_items) == 1:
            kopyala_action = menu.addAction("📋 Kopyala")
            kopyala_action.triggered.connect(self.arapca_kelime_kopyala)
        else:
            kopyala_action = menu.addAction(f"📋 {len(selected_items)} Kelimeyi Kopyala")
            kopyala_action.triggered.connect(self.arapca_kelimeleri_kopyala)

        menu.exec_(self.arapca_liste.mapToGlobal(position))

    def turkce_harf_filtresi(self, harf):
        """Türkçe kelimeleri harf bazlı filtreler"""
        self.turkce_liste.clear()
        self.turkce_arama_kutusu.clear()  # Arama kutusunu temizle
        
        for kelime in self.kuran_kelimeleri.get("turkce", []):
            if kelime.lower().startswith(harf.lower()):
                siklik = self.kelime_sikliklari.get(normalize_text(kelime), 0)
                self.turkce_liste.addItem(f"{kelime} ({siklik})")

    def turkce_tum_kelimeleri_goster(self):
        """Türkçe tüm kelimeleri gösterir"""
        self.turkce_liste.clear()
        self.turkce_arama_kutusu.clear()
        
        for kelime in self.kuran_kelimeleri.get("turkce", []):
            siklik = self.kelime_sikliklari.get(normalize_text(kelime), 0)
            self.turkce_liste.addItem(f"{kelime} ({siklik})")

    def arapca_harf_filtresi(self, harf):
        """Arapça kelimeleri harf bazlı filtreler"""
        self.arapca_liste.clear()
        self.arapca_arama_kutusu.clear()  # Arama kutusunu temizle
        
        for kelime in self.kuran_kelimeleri.get("arapca", []):
            if kelime.startswith(harf):
                self.arapca_liste.addItem(kelime)

    def arapca_tum_kelimeleri_goster(self):
        """Arapça tüm kelimeleri gösterir"""
        self.arapca_liste.clear()
        self.arapca_arama_kutusu.clear()
        
        for kelime in self.kuran_kelimeleri.get("arapca", []):
            self.arapca_liste.addItem(kelime)

    def turkce_kelime_kopyala(self):
        """Seçili Türkçe kelimeyi panoya kopyalar"""
        current_item = self.turkce_liste.currentItem()
        if current_item:
            clipboard = QApplication.clipboard()
            clipboard.setText(current_item.text())

    def arapca_kelime_kopyala(self):
        """Seçili Arapça kelimeyi panoya kopyalar"""
        current_item = self.arapca_liste.currentItem()
        if current_item:
            clipboard = QApplication.clipboard()
            clipboard.setText(current_item.text())

    def turkce_kelimeleri_kopyala(self):
        """Seçili Türkçe kelimeleri panoya kopyalar"""
        selected_items = self.turkce_liste.selectedItems()
        if selected_items:
            kelimeler = [item.text() for item in selected_items]
            clipboard = QApplication.clipboard()
            clipboard.setText('\n'.join(kelimeler))

    def arapca_kelimeleri_kopyala(self):
        """Seçili Arapça kelimeleri panoya kopyalar"""
        selected_items = self.arapca_liste.selectedItems()
        if selected_items:
            kelimeler = [item.text() for item in selected_items]
            clipboard = QApplication.clipboard()
            clipboard.setText('\n'.join(kelimeler))

    def turkce_kelime_detay(self, item):
        """Türkçe kelimeye çift tıklayınca detay dialog'u açar"""
        kelime_text = item.text()
        
        # Sıklık göstergesini ayır (örn: "kelime (5)" -> "kelime")
        if " (" in kelime_text and kelime_text.endswith(")"):
            parantez_index = kelime_text.rfind(" (")
            kelime = kelime_text[:parantez_index]
        else:
            kelime = kelime_text
            
        normalized_kelime = normalize_text(kelime)
        
        # Kelime bazlı veriyi yükle
        kelime_verisi = turkce_transkript_yukle()
        
        # Bu kelimeye ait kayıtları bul
        ilgili_kayitlar = [k for k in kelime_verisi if normalize_text(k.get('turkce', '')) == normalized_kelime]
        
        if not ilgili_kayitlar:
            QMessageBox.information(self, "Bilgi", f"'{kelime}' kelimesi için detay bulunamadı.")
            return
        
        # Meal verilerini yükle
        meal_verisi = veri_yukle()
        meal_dict = {}
        for row in meal_verisi:
            key = (row['sure'], row['ayet'])
            meal_dict[key] = row.get('meal', '')
        
        # Dialog oluştur
        dialog = QDialog(self)
        dialog.setWindowTitle(f"📖 '{kelime}' Kelimesinin Geçtiği Ayetler")
        dialog.setModal(True)
        dialog.resize(800, 600)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border: 2px solid #4a90e2;
                border-radius: 10px;
            }
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333;
                margin: 10px;
            }
            QListWidget {
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Başlık
        baslik = QLabel(f"🔍 '{kelime}' kelimesi toplam {len(ilgili_kayitlar)} ayette geçmektedir:")
        layout.addWidget(baslik)
        
        # Liste widget
        liste = QListWidget()
        liste.setAlternatingRowColors(True)
        for kayit in ilgili_kayitlar:
            sure_no = kayit.get('sureNo', 0)
            ayet_no = kayit.get('ayetNo', 0)
            key = (sure_no, ayet_no)
            meal = meal_dict.get(key, 'Meal bulunamadı')
            
            # Formatlı item
            sure_adi = self.get_sure_adi(sure_no)  # Sure adını almak için fonksiyon ekleyeceğim
            item_text = f"📍 {sure_adi} (Sûre {sure_no}, Âyet {ayet_no})\n   {meal}"
            liste.addItem(item_text)
        
        layout.addWidget(liste)
        
        # İstatistik
        istatistik = QLabel(f"Toplam: {len(ilgili_kayitlar)} adet ayet")
        istatistik.setStyleSheet("font-weight: normal; color: #666;")
        layout.addWidget(istatistik)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        btn_kapat = QPushButton("❌ Kapat")
        btn_kapat.clicked.connect(dialog.close)
        button_layout.addWidget(btn_kapat)
        
        btn_kopyala = QPushButton("📋 Tümünü Kopyala")
        btn_kopyala.clicked.connect(lambda: self.kopyala_ayetler(ilgili_kayitlar, meal_dict))
        button_layout.addWidget(btn_kopyala)
        
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def arapca_kelime_detay(self, item):
        """Arapça kelimeye çift tıklayınca detay dialog'u açar"""
        kelime = item.text()
        normalized_kelime = normalize_arabic(kelime)
        
        # Kelime bazlı veriyi yükle
        kelime_verisi = turkce_transkript_yukle()  # Türkçe transkript, Arapça kelime için de meal var
        
        # Bu kelimeye ait kayıtları bul (Arapça eşleşmesi için)
        ilgili_kayitlar = [k for k in kelime_verisi if normalize_arabic(k.get('arapca', '')) == normalized_kelime]
        
        if not ilgili_kayitlar:
            QMessageBox.information(self, "Bilgi", f"'{kelime}' kelimesi için detay bulunamadı.")
            return
        
        # Meal verilerini yükle
        meal_verisi = veri_yukle()
        meal_dict = {}
        for row in meal_verisi:
            key = (row['sure'], row['ayet'])
            meal_dict[key] = row.get('meal', '')
        
        # Dialog oluştur
        dialog = QDialog(self)
        dialog.setWindowTitle(f"📖 '{kelime}' Kelimesinin Geçtiği Ayetler")
        dialog.setModal(True)
        dialog.resize(800, 600)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border: 2px solid #4a90e2;
                border-radius: 10px;
            }
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333;
                margin: 10px;
            }
            QListWidget {
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Başlık
        baslik = QLabel(f"🔍 '{kelime}' kelimesi toplam {len(ilgili_kayitlar)} ayette geçmektedir:")
        layout.addWidget(baslik)
        
        # Liste widget
        liste = QListWidget()
        liste.setAlternatingRowColors(True)
        for kayit in ilgili_kayitlar:
            sure_no = kayit.get('sureNo', 0)
            ayet_no = kayit.get('ayetNo', 0)
            key = (sure_no, ayet_no)
            meal = meal_dict.get(key, 'Meal bulunamadı')
            
            # Formatlı item
            sure_adi = self.get_sure_adi(sure_no)
            item_text = f"📍 {sure_adi} (Sûre {sure_no}, Âyet {ayet_no})\n   {meal}"
            liste.addItem(item_text)
        
        layout.addWidget(liste)
        
        # İstatistik
        istatistik = QLabel(f"Toplam: {len(ilgili_kayitlar)} adet ayet")
        istatistik.setStyleSheet("font-weight: normal; color: #666;")
        layout.addWidget(istatistik)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        btn_kapat = QPushButton("❌ Kapat")
        btn_kapat.clicked.connect(dialog.close)
        button_layout.addWidget(btn_kapat)
        
        btn_kopyala = QPushButton("📋 Tümünü Kopyala")
        btn_kopyala.clicked.connect(lambda: self.kopyala_ayetler(ilgili_kayitlar, meal_dict))
        button_layout.addWidget(btn_kopyala)
        
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def kopyala_ayetler(self, kayitlar, meal_dict):
        """Ayetleri panoya kopyalar"""
        text = ""
        for kayit in kayitlar:
            sure_no = kayit.get('sureNo', 0)
            ayet_no = kayit.get('ayetNo', 0)
            key = (sure_no, ayet_no)
            meal = meal_dict.get(key, 'Meal bulunamadı')
            sure_adi = self.get_sure_adi(sure_no)
            text += f"{sure_adi} (Sûre {sure_no}, Âyet {ayet_no}):\n{meal}\n\n"
        
        clipboard = QApplication.clipboard()
        clipboard.setText(text.strip())
        QMessageBox.information(self, "Bilgi", "Ayetler panoya kopyalandı!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QuranAnalyzer()
    window.show()
    sys.exit(app.exec_())
