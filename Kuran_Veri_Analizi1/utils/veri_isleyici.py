# utils/veri_isleyici.py
import json

def veri_yukle():
    with open("veriler/kelime_manali_kuran_ve_turkce_meali.json", "r", encoding="utf-8") as f:
        return json.load(f)
