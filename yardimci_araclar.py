from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor

def vurgu_ekle(metin, kelime, renk="yellow"):
    if not kelime:
        return metin
    if isinstance(kelime, str):
        return metin.replace(kelime, f"<span style='background-color:{renk}'>{kelime}</span>")
    else:
        # kelime listesi ise
        for k in kelime:
            metin = metin.replace(k, f"<span style='background-color:{renk}'>{k}</span>")
        return metin

def vurgula(metin, kelime, renk="yellow"):
    return vurgu_ekle(metin, kelime, renk)

def transkripsiyon_olustur(html):
    import re
    matches = re.findall(r'>([^<]+)<', html)
    return ' '.join(matches)

def kelime_sayaci(veriler, kelime):
    toplam = 0
    ayet_seti = set()
    for v in veriler:
        if kelime in v["arapca"] or kelime in v["turkce"]:
            toplam += v["arapca"].count(kelime) + v["turkce"].count(kelime)
            ayet_seti.add((v["sure"], v["ayet"]))
    return toplam, len(ayet_seti)
