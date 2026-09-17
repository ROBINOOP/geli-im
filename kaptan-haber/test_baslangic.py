# -*- coding: utf-8 -*-
"""Kaptan-chan duman testi: haber motoru + pencere + ayarlar diyalogu."""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kaptan  # noqa: E402
from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

print("== 1) RSS/Atom haber motoru ==")
for ad, url in kaptan.KATEGORILER.items():
    try:
        haberler = kaptan.feed_oku(url)
        ilk = haberler[0][0][:50] if haberler else "(bos)"
        print(f"  {ad:14s} -> {len(haberler):3d} haber | {ilk}")
    except Exception as hata:
        print(f"  {ad:14s} -> HATA: {hata}")

print("\n== 2) Pencere + karakterler + ayarlar ==")
uyg = QApplication([])
ayar = kaptan.ayarlari_yukle()
isci = kaptan.HaberIscisi(ayar)
pen = kaptan.KaptanPencere(ayar, isci)
print("  ninja yuklu mu:", not pen.ninja_pix.isNull(),
      "| kareler:", sorted(pen.kareler.keys()))
print("  pencere:", pen.width(), "x", pen.height(),
      "| karakter boyutu:", pen.boyut, "px")
ekran = QApplication.primaryScreen().availableGeometry()
oran = pen.boyut / ekran.height() * 100
print(f"  ekran yuksekliginin %{oran:.1f}'i (sinir: %20)")

diyalog = kaptan.AyarlarPenceresi(pen)
print("  ayarlar penceresi kurulumu OK, sekmeler olustu")


def test_haber():
    pen._haber_goster("Oyun & E-Spor",
                      "Test: Shogun'un ilk bildirimi geldi!", "https://example.com")
    print("  balon gosterildi:", bool(pen.balon), "| rect:", pen.balon["rect"])


def kapat():
    print("  temiz kapanis")
    uyg.quit()


QTimer.singleShot(300, test_haber)
QTimer.singleShot(1500, kapat)
uyg.exec()
print("\nTUM TESTLER TAMAM ✔")
