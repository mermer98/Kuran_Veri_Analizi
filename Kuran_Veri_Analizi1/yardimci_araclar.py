def kelime_sayaci(veri):
    sayac = {}
    for ayet in veri:
        kelimeler = ayet["meal"].split()
        for kelime in kelimeler:
            kelime = kelime.lower().strip(".,;:!?()[]{}\"'“”‘’")
            if kelime:
                sayac[kelime] = sayac.get(kelime, 0) + 1
    return sayac

def vurgula(metin, kelime):
    return metin.replace(kelime, f"<b>{kelime}</b>")

def transkripsiyon_olustur(arapca_metin):
    # Basit bir örnekleme
    return arapca_metin[::-1]  # Gerçek transkripsiyon için daha fazla iş gerekir