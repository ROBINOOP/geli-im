# -*- coding: utf-8 -*-
"""Aday RSS beslemelerini dener."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
import kaptan

adaylar = {
    "espor-ntvspor3": "https://www.ntvspor.net/rss/kategori/espor",
    "espor-tamindir": "https://www.tamindir.com/rss/haberler.xml",
    "bilim-evrim": "https://evrimagaci.org/rss.xml",
}
for ad, u in adaylar.items():
    try:
        h = kaptan.feed_oku(u)
        ilk = h[0][0][:45] if h else "(bos)"
        print(f"{ad:12s} -> {len(h):3d} haber | {ilk}")
    except Exception as e:
        print(f"{ad:12s} -> HATA: {e}")
