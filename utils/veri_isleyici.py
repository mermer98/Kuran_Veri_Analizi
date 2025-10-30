import json
import os
import csv
import re
from zemberek import TurkishMorphology

def normalize_text(text):
    """Metindeki özel karakterleri çıkarır ve küçük harfe çevirir"""
    if not text:
        return ""
    # Özel karakterleri kaldır: % & ' " _ - ve boşluklar
    text = re.sub(r'[%&\'"\s_-]', '', text)
    # Küçük harfe çevir
    return text.lower().strip()

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

def turkce_kelime_ayir(text):
    """Bitişik Türkçe kelimeleri basit yaklaşım ile ayırmaya çalışır"""
    if not text:
        return text
    
    # Özel durumlar için manuel ayırma
    special_cases = {
        'kesinlikledönersiniz': 'kesinlikle dönersiniz',
        'sizidöndürmelerinedek': 'sizi döndürmelerine dek',
        'veardınadönüpbak': 've ardına dönüp bak',
        'vesonradöndürüleceksiniz': 've sonra döndürüleceksiniz',
        'aceleistemelerigibi': 'acele iste meleri gibi',
        'aceleistiyorsunuz': 'acele istiyorsunuz',
        'acizbırakmayaçalışanlarolarak': 'aciz bırakmaya çalışanlar olarak',
        'adaletetmemiçin': 'adalet etmem için',
        'benihidâyeteerdirecektir': 'beni hidayete erdirecektir',
        'aceleederek': 'acele ederek',
        'aceleettiyse': 'acele ettiyse',
        'aceleistediniz': 'acele istediniz',
        'aceleister': 'acele ister',
        'aceleistiyor': 'acele istiyor',
        'aceleistiyordunuz': 'acele istiyordunuz',
        'aceleistiyorlar': 'acele istiyorlar',
        'acelemiettiniz': 'acele mi ettiniz',
        'aceleolanı': 'acele olanı',
        'acelever': 'acele ver',
        'aceleyleverseydi': 'aceleyle verseydi',
        'acizbıraka': 'aciz bırak a',
        'acizbırakacakkimseler': 'aciz bırakacak kimseler',
        'acizbırakanlar': 'aciz bırakanlar',
        'acizbırakıcılar': 'aciz bırakıcılar',
        'adaklarını': 'adaklarını',
        'adaletigerçekleştirirler': 'adaleti gerçekleştirirler',
        'adaletlehükmederler': 'adaletle hükmederler',
        'adaletliol': 'adaletli ol',
        'adaletliolma': 'adaletli olma',
        'adaletliolmanıza': 'adaletli olmanıza',
        'adaletsizdavranıyorlar': 'adaletsiz davranıyorlar',
        'adalettenayrıl': 'adaletten ayrıl',
        'adalettenşaşarak': 'adaletten şaşarak',
        'adetigibidir': 'adet gibidir',
        'adetadet': 'adet adet',
        'adilolun': 'adil olun',
        'adilolanları': 'adil olanları',
        'akabindeatıldılar': 'akabinde atıldılar',
        'akabindeoanda': 'akabinde o anda',
        'akabindeyöneldiler': 'akabinde yöneldiler',
        'aklıbaşında': 'aklı başında',
        'aklıermezlere': 'aklı ermezlere',
        'aklınoksan': 'aklın oksan',
        'aklınıkullan': 'aklını kullan',
        'aklınıkullanıyorlar': 'aklını kullanıyorlar',
        'aklınızıkullanırsınız': 'aklınızı kullanırsınız',
        'aklınızıkullanıyorsunuz': 'aklınızı kullanıyorsunuz',
        'akrabalıkbağlarınızı': 'akrabalık bağlarınızı',
        'akılerdirirsiniz': 'akı edirirsiniz',
        'akılerdiriyorlar': 'akı ediriyorlar',
        'akılerdiriyoruz': 'akı ediriyoruz',
        'akıllarınıkullan': 'akıllarını kullan',
        'akıllarınıkullanacaklar': 'akıllarını kullanacaklar',
        'akıllarınıkullanıyorlar': 'akıllarını kullanıyorlar',
        'akıpgiderdi': 'akıp giderdi',
        'akıpgidenler': 'akıp gidenler',
        'akınettiniz': 'akı ettiniz',
        'akınediyorlar': 'akın ediyorlar',
        'akıpgidiyor': 'akıp gidiyor',
        'akıpgidiyordu': 'akıp gidiyordu',
        'akıpgidiyorlar': 'akıp gidiyorlar',
        'akıpgitmesiiçin': 'akıp gitmesi için',
        'akıttıkçaakıttık': 'akıttıkça akıttık',
        'akşamagirersiniz': 'akşam agirersiniz',
        'akşamleyingetirirsiniz': 'akşamleyin getirirsiniz'
    }
    
    if text in special_cases:
        return special_cases[text]
    
    # Genel yaklaşım: ünlü harf paternlerine göre böl
    # Kaldırıldı çünkü yanlış sonuçlar veriyor
    return text

def veri_yukle(meal="Diyanet İşleri Meali (Yeni)"):
    # Mevcut JSON veriyi yükle
    klasor = os.path.join(os.path.dirname(__file__), "../veriler")
    dosya = os.path.join(klasor, "kelime_manali_kuran_ve_turkce_meali.json")
    with open(dosya, "r", encoding="utf-8") as f:
        data = json.load(f)

    # CSV'den seçilen meal'i yükle
    csv_dosya = os.path.join(os.path.dirname(__file__), "../../tum_kuran_mealler.csv")
    meal_dict = {}
    with open(csv_dosya, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Hocalar'].strip() == meal:
                key = (int(row['sure']), int(row['ayet']))
                meal_dict[key] = row['meal']

    # Veriye meal ekle/güncelle
    for item in data:
        key = (item['sure'], item['ayet'])
        if key in meal_dict:
            item['meal'] = meal_dict[key]

    return data

def turkce_transkript_yukle():
    """Kelime bazlı Türkçe transkript verisini yükler"""
    try:
        klasor = os.path.join(os.path.dirname(__file__), "../veriler")
        dosya = os.path.join(klasor, "kurani_kerimdeki_tum_kelimeler.json")
        with open(dosya, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Türkçe transkript verisi yüklenirken hata: {e}")
        return []

def kuran_kelimeleri_hazirla():
    """Kuranda geçen tüm Türkçe ve Arapça kelimeleri hazırlar"""
    try:
        klasor = os.path.join(os.path.dirname(__file__), "../veriler")
        dosya = os.path.join(klasor, "kurani_kerimdeki_tum_kelimeler.json")

        with open(dosya, "r", encoding="utf-8") as f:
            data = json.load(f)

        turkce_kelimeler = set()
        arapca_kelimeler = set()

        for item in data:
            # Türkçe kelimeler
            turkce = item.get("turkce", "").strip()
            if turkce and turkce != " ":
                turkce_kelimeler.add(turkce_kelime_ayir(turkce))

            # Arapça kelimeler
            arapca = item.get("arapca", "").strip()
            if arapca and arapca != " ":
                arapca_kelimeler.add(normalize_arabic(arapca))

        # Alfabetik sıralama
        turkce_listesi = sorted(list(turkce_kelimeler), key=lambda x: x.lower())
        arapca_listesi = sorted(list(arapca_kelimeler))

        return {
            "turkce": turkce_listesi,
            "arapca": arapca_listesi
        }

    except Exception as e:
        print(f"Kuran kelimeleri hazırlanırken hata: {e}")
        return {"turkce": [], "arapca": []}
