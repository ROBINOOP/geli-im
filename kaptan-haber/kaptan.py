# -*- coding: utf-8 -*-
"""
Kaptan-chan / Shogun — Masaüstü Anime Haber Asistanı
=====================================================
Ekranın sağ alt köşesinde (18 px kenar boşluğuyla) yaşayan anime karakteri;
seçtiğin kategorilerdeki güncel haberleri konuşma balonu ile bildirir.

Sağ tık → Ayarlar Penceresi: kategoriler, karakter seçimi, boyut, sıklık.

Çalıştırma:  python kaptan.py   (veya baslat.bat'a çift tıkla)
"""

import html
import json
import math
import random
import re
import sys
import threading
import time
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtCore import (QByteArray, QRect, QRectF, QSize, Qt, QTimer,
                            QPoint, Signal, QObject)
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QIcon,
                           QPainter, QPainterPath, QPen, QPixmap, QPolygon,
                           QRegion, QAction, QCursor)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                               QHBoxLayout, QLabel, QMenu, QPushButton,
                               QRadioButton, QScrollArea, QSlider,
                               QSystemTrayIcon, QTabWidget, QVBoxLayout,
                               QWidget)

# ----------------------------------------------------------------------------
# Sabitler ve ayarlar
# ----------------------------------------------------------------------------

KATEGORILER = {
    "Son Dakika":    "https://www.ntv.com.tr/son-dakika.rss",
    "Gündem":        "https://www.ntv.com.tr/turkiye.rss",
    "Dünya":         "https://www.ntv.com.tr/dunya.rss",
    "Ekonomi":       "https://www.ntv.com.tr/ekonomi.rss",
    "Teknoloji":     "https://www.ntv.com.tr/teknoloji.rss",
    "Spor":          "https://www.ntv.com.tr/sporskor.rss",
    "Oyun & E-Spor": "https://www.tamindir.com/rss/haberler.xml",
    "Bilim":         "https://evrimagaci.org/rss.xml",
    "Sağlık":        "https://www.ntv.com.tr/saglik.rss",
    "Eğitim":        "https://www.ntv.com.tr/egitim.rss",
    "Yaşam":         "https://www.ntv.com.tr/yasam.rss",
}

KATEGORI_RENKLERI = {
    "Son Dakika":    "#d43f3f",
    "Gündem":        "#e0485a",
    "Dünya":         "#3b82c4",
    "Ekonomi":       "#2e9e6b",
    "Teknoloji":     "#8a5cd6",
    "Spor":          "#e08a2e",
    "Oyun & E-Spor": "#4f8f3b",
    "Bilim":         "#2ea3a3",
    "Sağlık":        "#d65a8a",
    "Eğitim":        "#b0882e",
    "Yaşam":         "#d655a0",
}

KARAKTERLER = {
    "kaptan": "Kaptan-chan ⚓",
    "ninja":  "Shogun 🥷",
}

BOYUT_MIN, BOYUT_MAX = 150, 240     # karakter yüksekliği (px)
KENAR_BOSLUK = 18                   # sağ alt köşeden iç boşluk (px)
BALON_G = 344                       # konuşma balonu genişliği

KONUSMA_SATIRLARI = [
    "Ay ay Kaptan! ⚓ Gözcü kulesi benim, gözüm hep haberlerde!",
    "Bugün hava çok güzel... haberler de öyle!",
    "Beni rahat bırakırsan daha çok haber yakalarım, Kaptan!",
    "Twin-tail... pardon, topuzum rüzgârda, haberler yolda!",
    "Sessiz sedasız bekliyorum... haber kokusu aldım sanki!",
    "Bir kaptan en iyi asistanını tanır! ⚓",
    "Yelpazem hazır, katandam hazır, haberler yolda! 🥷",
]

AYAR_DOSYASI = Path(__file__).resolve().parent / "ayarlar.json"
NINJA_DOSYASI = Path(__file__).resolve().parent / "varliklar" / "ninja.png"

VARSAYILAN_AYARLAR = {
    "kategoriler": ["Son Dakika", "Teknoloji", "Oyun & E-Spor"],
    "siklik_dk": 5,
    "karakter": "ninja",
    "boyut": 200,
    "konum": None,
}


def ayarlari_yukle() -> dict:
    ayarlar = dict(VARSAYILAN_AYARLAR)
    try:
        veri = json.loads(AYAR_DOSYASI.read_text(encoding="utf-8"))
        if isinstance(veri, dict):
            ayarlar.update(veri)
    except (OSError, ValueError):
        pass
    gecerli = set(KATEGORILER)
    ayarlar["kategoriler"] = [k for k in ayarlar.get("kategoriler", []) if k in gecerli]
    if ayarlar["siklik_dk"] not in (1, 5, 10, 30):
        ayarlar["siklik_dk"] = 5
    if ayarlar.get("karakter") not in KARAKTERLER:
        ayarlar["karakter"] = "ninja"
    try:
        b = int(ayarlar.get("boyut", 200))
    except (TypeError, ValueError):
        b = 200
    ayarlar["boyut"] = max(BOYUT_MIN, min(BOYUT_MAX, b))
    return ayarlar


def ayarlari_kaydet(ayarlar: dict) -> None:
    try:
        AYAR_DOSYASI.write_text(
            json.dumps(ayarlar, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


# ----------------------------------------------------------------------------
# RSS / Atom okuyucu
# ----------------------------------------------------------------------------

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _temizle(metin: str) -> str:
    metin = re.sub(r"<[^>]+>", " ", metin or "")
    metin = html.unescape(metin)
    return re.sub(r"\s+", " ", metin).strip()


def feed_oku(url: str):
    """RSS 2.0 veya Atom beslemesinden (baslik, link) listesi döndürür."""
    istek = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    })
    with urllib.request.urlopen(istek, timeout=15) as yanit:
        veri = yanit.read()
    kok = ET.fromstring(veri)
    sonuc = []
    for dugum in kok.iter():
        etiket = dugum.tag.rsplit("}", 1)[-1]
        if etiket not in ("item", "entry"):
            continue
        baslik, link = "", ""
        for alt in dugum:
            t = alt.tag.rsplit("}", 1)[-1]
            if t == "title" and baslik == "":
                baslik = _temizle(alt.text)
            elif t == "link":
                link = (alt.attrib.get("href") or (alt.text or "").strip()) or link
        if baslik and link:
            sonuc.append((baslik, link))
    return sonuc


# ----------------------------------------------------------------------------
# Karakter 1: Kaptan-chan (anime SVG) — göz durumu ile kareler üretilir
# ----------------------------------------------------------------------------

def _gozler(durum: str) -> str:
    """Sol + sağ göz SVG parçası. cx: 112 / 188, cy: ~164"""
    def tek(cx: str) -> str:
        if durum == "acik":
            return f"""
              <ellipse cx="{cx}" cy="164" rx="15" ry="19" fill="#ffffff" stroke="#5a3a2e" stroke-width="2"/>
              <ellipse cx="{cx}" cy="166" rx="11" ry="15" fill="url(#iris)"/>
              <ellipse cx="{cx}" cy="167" rx="6" ry="8.5" fill="#1c2b3a"/>
              <circle cx="{float(cx) + 3:.0f}" cy="158" r="4" fill="#ffffff"/>
              <circle cx="{float(cx) - 4:.0f}" cy="173" r="2" fill="#ffffff" opacity="0.8"/>
              <path d="M {float(cx) - 16:.0f} 147 Q {cx} 139 {float(cx) + 16:.0f} 148" stroke="#5a3a2e" stroke-width="3.5" fill="none" stroke-linecap="round"/>
              <path d="M {float(cx) + 14:.0f} 152 l 8 -4" stroke="#5a3a2e" stroke-width="2.5" stroke-linecap="round"/>
            """
        if durum == "yarim":
            return f"""
              <ellipse cx="{cx}" cy="167" rx="14" ry="12" fill="#ffffff" stroke="#5a3a2e" stroke-width="2"/>
              <ellipse cx="{cx}" cy="169" rx="10" ry="9" fill="url(#iris)"/>
              <ellipse cx="{cx}" cy="170" rx="5" ry="5" fill="#1c2b3a"/>
              <circle cx="{float(cx) + 3:.0f}" cy="164" r="3" fill="#ffffff"/>
              <path d="M {float(cx) - 15:.0f} 158 Q {cx} 151 {float(cx) + 15:.0f} 158" stroke="#5a3a2e" stroke-width="4" fill="none" stroke-linecap="round"/>
            """
        if durum == "kapali":
            return (f'<path d="M {float(cx) - 14:.0f} 166 Q {cx} 174 '
                    f'{float(cx) + 14:.0f} 166" stroke="#5a3a2e" stroke-width="3.5" '
                    'fill="none" stroke-linecap="round"/>')
        # mutlu (^ ^)
        return (f'<path d="M {float(cx) - 14:.0f} 168 Q {cx} 154 '
                f'{float(cx) + 14:.0f} 168" stroke="#5a3a2e" stroke-width="4" '
                'fill="none" stroke-linecap="round"/>')

    return tek("112") + tek("188")


def karakter_svg(goz_durumu: str) -> str:
    pariltilar = ""
    if goz_durumu == "mutlu":
        pariltilar = """
          <path d="M 258 34 l 3 9 9 3 -9 3 -3 9 -3 -9 -9 -3 9 -3 z" fill="#ffd76e"/>
          <path d="M 42 66 l 2.5 7 7 2.5 -7 2.5 -2.5 7 -2.5 -7 -7 -2.5 7 -2.5 z" fill="#ffd76e"/>
        """

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 360" width="300" height="360">
  <defs>
    <radialGradient id="iris" cx="50%" cy="40%" r="70%">
      <stop offset="0%" stop-color="#7de3e0"/>
      <stop offset="55%" stop-color="#3ec6c9"/>
      <stop offset="100%" stop-color="#1f7f96"/>
    </radialGradient>
    <linearGradient id="sac" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#9a6a50"/>
      <stop offset="100%" stop-color="#7a4a3a"/>
    </linearGradient>
  </defs>

  <path d="M 66 116 C 24 136 8 208 24 276 C 30 298 50 306 62 296 C 50 242 54 172 78 132 Z" fill="url(#sac)"/>
  <path d="M 234 116 C 276 136 292 208 276 276 C 270 298 250 306 238 296 C 250 242 246 172 222 132 Z" fill="url(#sac)"/>
  <path d="M 40 180 C 36 216 38 248 46 274" stroke="#b58263" stroke-width="5" fill="none" stroke-linecap="round" opacity="0.7"/>
  <path d="M 260 180 C 264 216 262 248 254 274" stroke="#b58263" stroke-width="5" fill="none" stroke-linecap="round" opacity="0.7"/>

  <rect x="140" y="228" width="20" height="18" fill="#ffdcc9"/>
  <path d="M 96 246 C 112 238 188 238 204 246 L 220 344 C 220 356 80 356 80 344 Z" fill="#2c3e6b"/>
  <rect x="72" y="262" width="24" height="58" rx="12" fill="#2c3e6b"/>
  <rect x="204" y="262" width="24" height="58" rx="12" fill="#2c3e6b"/>
  <circle cx="84" cy="326" r="10" fill="#ffdcc9"/>
  <circle cx="216" cy="326" r="10" fill="#ffdcc9"/>
  <path d="M 106 246 L 150 286 L 194 246 L 176 238 L 150 264 L 124 238 Z" fill="#f7f7fa" stroke="#d0d4e0" stroke-width="1.5"/>
  <path d="M 150 282 l -18 10 l 18 12 l 18 -12 z" fill="#e0485a"/>
  <circle cx="150" cy="284" r="5" fill="#c23a4c"/>

  <ellipse cx="150" cy="155" rx="88" ry="82" fill="#ffe3d3"/>

  {_gozler(goz_durumu)}
  <path d="M 97 140 Q 112 133 127 139" stroke="#6e4433" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M 173 139 Q 188 133 203 140" stroke="#6e4433" stroke-width="3" fill="none" stroke-linecap="round"/>
  <ellipse cx="94" cy="192" rx="13" ry="7" fill="#ffb3ba" opacity="0.55"/>
  <ellipse cx="206" cy="192" rx="13" ry="7" fill="#ffb3ba" opacity="0.55"/>
  <path d="M 139 207 Q 150 218 161 207" stroke="#b3574d" stroke-width="3.5" fill="none" stroke-linecap="round"/>

  <path d="M 62 148 C 55 192 58 224 72 254 C 81 257 92 254 96 249 C 82 216 80 182 84 150 Z" fill="url(#sac)"/>
  <path d="M 238 148 C 245 192 242 224 228 254 C 219 257 208 254 204 249 C 218 216 220 182 216 150 Z" fill="url(#sac)"/>

  <path d="M 62 152 C 58 92 105 58 150 58 C 195 58 242 92 238 152
           L 224 132 L 210 154 L 196 128 L 180 152 L 165 126 L 150 152
           L 135 126 L 120 152 L 104 128 L 90 154 L 76 132 Z" fill="url(#sac)"/>
  <path d="M 118 76 C 132 66 168 66 184 78" stroke="#b58263" stroke-width="5" fill="none" stroke-linecap="round" opacity="0.7"/>

  <path d="M 150 26 C 146 8 166 2 174 12 C 164 10 156 16 158 26 Z" fill="url(#sac)"/>
  <path d="M 78 70 C 78 38 118 24 150 24 C 182 24 222 38 222 70 Z" fill="#f7f7fa" stroke="#2c3e6b" stroke-width="2"/>
  <rect x="74" y="58" width="152" height="15" rx="7" fill="#2c3e6b"/>
  <ellipse cx="150" cy="74" rx="80" ry="9" fill="#f7f7fa" stroke="#2c3e6b" stroke-width="2"/>
  <circle cx="150" cy="50" r="9" fill="#f5c542" stroke="#b8912f" stroke-width="1.5"/>
  <path d="M 150 44 v 12 M 145 49 h 10 M 146 54 q 4 4 8 0" stroke="#7a5a10" stroke-width="1.6" fill="none" stroke-linecap="round"/>

  {pariltilar}
</svg>"""


GOZ_DURUMLARI = ("acik", "yarim", "kapali", "mutlu")


# ----------------------------------------------------------------------------
# Haber işçisi (arka plan thread'i)
# ----------------------------------------------------------------------------

class HaberIscisi(QObject):
    haber_geldi = Signal(str, str, str)   # kategori, baslik, link
    durum = Signal(str)                   # karakterin söyleyeceği satır

    def __init__(self, ayarlar: dict):
        super().__init__()
        self.ayarlar = ayarlar
        self.bitir = threading.Event()
        self.hemen = threading.Event()
        self.gorulen = set()
        self.sonraki = time.monotonic() + 6  # açılıştan kısa süre sonra ilk haber

    def baslat(self):
        self.is_parcasi = threading.Thread(target=self.dongu, daemon=True)
        self.is_parcasi.start()

    def durdur(self):
        self.bitir.set()

    def simdi(self):
        self.hemen.set()

    def dongu(self):
        while not self.bitir.is_set():
            if self.hemen.is_set() or time.monotonic() >= self.sonraki:
                self.hemen.clear()
                try:
                    self.getir_ve_yayinla()
                except Exception as hata:  # ağ hataları vb.
                    print("Haber hatası:", hata)
                aralik = self.ayarlar.get("siklik_dk", 5) * 60
                self.sonraki = time.monotonic() + aralik
            self.bitir.wait(1)

    def getir_ve_yayinla(self):
        kategoriler = list(self.ayarlar.get("kategoriler") or [])
        if not kategoriler:
            self.durum.emit("Kaptan! Ayarlardan en az bir haber kategorisi seçmelisin. ⚙️")
            return
        random.shuffle(kategoriler)
        for kategori in kategoriler:
            url = KATEGORILER.get(kategori)
            if not url:
                continue
            try:
                haberler = feed_oku(url)
            except Exception:
                continue
            random.shuffle(haberler)
            for baslik, link in haberler:
                anahtar = link[:200]
                if anahtar in self.gorulen:
                    continue
                self.gorulen.add(anahtar)
                if len(self.gorulen) > 500:
                    self.gorulen = set(list(self.gorulen)[-300:])
                self.haber_geldi.emit(kategori, baslik, link)
                return
        self.durum.emit("Şimdilik her şeyi yakaladım Kaptan, haber bülteni sessiz! 🔍")


# ----------------------------------------------------------------------------
# Ayarlar penceresi (sekmeli: Kategoriler + Görünüm)
# ----------------------------------------------------------------------------

class AyarlarPenceresi(QDialog):
    def __init__(self, ana_pencere):
        super().__init__(None, Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("⚙️ Asistan Ayarları")
        self.setMinimumWidth(420)
        self.ana_pencere = ana_pencere
        self.ayarlar = ana_pencere.ayarlar

        kok = QVBoxLayout(self)
        sekmeler = QTabWidget()
        kok.addWidget(sekmeler)

        # ---- Sekme 1: Kategoriler ----
        kategori_sekme = QWidget()
        kv = QVBoxLayout(kategori_sekme)
        kv.addWidget(QLabel("Bildirim istediğin haber kategorilerini seç:"))

        icerik = QWidget()
        iv = QVBoxLayout(icerik)
        iv.setContentsMargins(4, 4, 4, 4)
        self.kategori_kutulari = {}
        for ad in KATEGORILER:
            kutu = QCheckBox(ad)          # kutucuk solda, kategori adı sağında
            kutu.setChecked(ad in self.ayarlar["kategoriler"])
            iv.addWidget(kutu)
            self.kategori_kutulari[ad] = kutu
        iv.addStretch(1)

        kaydira = QScrollArea()
        kaydira.setWidgetResizable(True)
        kaydira.setWidget(icerik)
        kv.addWidget(kaydira)
        sekmeler.addTab(kategori_sekme, "📰 Kategoriler")

        # ---- Sekme 2: Görünüm (kişiselleştirme) ----
        gorunum = QWidget()
        gv = QVBoxLayout(gorunum)

        gv.addWidget(QLabel("🥷 Asistan Karakteri:"))
        karakter_satir = QHBoxLayout()
        self.r_kaptan = QRadioButton(KARAKTERLER["kaptan"])
        self.r_ninja = QRadioButton(KARAKTERLER["ninja"])
        karakter_satir.addWidget(self.r_kaptan)
        karakter_satir.addWidget(self.r_ninja)
        karakter_satir.addStretch(1)
        gv.addLayout(karakter_satir)

        # küçük önizlemeler
        onizleme_satir = QHBoxLayout()
        for tur, radio in (("kaptan", self.r_kaptan), ("ninja", self.r_ninja)):
            hucre = QVBoxLayout()
            etiket = QLabel()
            etiket.setFixedSize(72, 72)
            etiket.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pix = ana_pencere.karakter_onizleme(tur, 64)
            etiket.setPixmap(pix)
            hucre.addWidget(etiket)
            hucre.addWidget(radio)
            hucre.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            onizleme_satir.addLayout(hucre)
        onizleme_satir.addStretch(1)
        gv.addLayout(onizleme_satir)

        if self.ayarlar["karakter"] == "ninja":
            self.r_ninja.setChecked(True)
        else:
            self.r_kaptan.setChecked(True)

        gv.addSpacing(10)
        self.boyut_etiket = QLabel()
        self.boyut_kaydirici = QSlider(Qt.Orientation.Horizontal)
        self.boyut_kaydirici.setRange(BOYUT_MIN, BOYUT_MAX)
        self.boyut_kaydirici.setValue(self.ayarlar["boyut"])
        self.boyut_kaydirici.valueChanged.connect(
            lambda v: self.boyut_etiket.setText(f"Karakter boyutu: {v} px"))
        self.boyut_etiket.setText(f"Karakter boyutu: {self.ayarlar['boyut']} px")
        gv.addWidget(self.boyut_etiket)
        gv.addWidget(self.boyut_kaydirici)
        ipucu = QLabel(f"(ekran yüksekliğinin en fazla %20'si — "
                       f"{BOYUT_MIN}–{BOYUT_MAX} px arası)")
        ipucu.setStyleSheet("color: gray; font-size: 8pt;")
        gv.addWidget(ipucu)

        gv.addSpacing(10)
        gv.addWidget(QLabel("⏱️ Bildirim sıklığı:"))
        self.siklik_kutu = QComboBox()
        for dk in (1, 5, 10, 30):
            self.siklik_kutu.addItem(f"{dk} dakikada bir", dk)
            if dk == self.ayarlar["siklik_dk"]:
                self.siklik_kutu.setCurrentIndex(self.siklik_kutu.count() - 1)
        gv.addWidget(self.siklik_kutu)

        gv.addStretch(1)
        sekmeler.addTab(gorunum, "🎨 Görünüm")

        # ---- düğmeler ----
        dugmeler = QHBoxLayout()
        btn_simdi = QPushButton("🔔 Şimdi Haber Getir")
        btn_simdi.clicked.connect(lambda: self.ana_pencere.isci.simdi())
        btn_kaydet = QPushButton("💾 Kaydet ve Uygula")
        btn_kaydet.setDefault(True)
        btn_kaydet.clicked.connect(self._uygula)
        btn_kapat = QPushButton("Kapat")
        btn_kapat.clicked.connect(self.close)
        dugmeler.addWidget(btn_simdi)
        dugmeler.addStretch(1)
        dugmeler.addWidget(btn_kapat)
        dugmeler.addWidget(btn_kaydet)
        kok.addLayout(dugmeler)

    def _uygula(self):
        self.ayarlar["kategoriler"] = [
            ad for ad, kutu in self.kategori_kutulari.items() if kutu.isChecked()
        ]
        self.ayarlar["karakter"] = "ninja" if self.r_ninja.isChecked() else "kaptan"
        self.ayarlar["boyut"] = self.boyut_kaydirici.value()
        self.ayarlar["siklik_dk"] = self.siklik_kutu.currentData()
        ayarlari_kaydet(self.ayarlar)
        self.ana_pencere._gorsel_yenile()
        self.accept()


# ----------------------------------------------------------------------------
# Ana pencere: karakter + konuşma balonu, şeffaf ve her zaman üstte
# ----------------------------------------------------------------------------

class KaptanPencere(QWidget):
    def __init__(self, ayarlar: dict, isci: HaberIscisi):
        super().__init__()
        self.ayarlar = ayarlar
        self.isci = isci

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # ---- karakter görselleri (doğal boyut, çizimde ölçeklenir) ----
        olcek = max(2.0, QApplication.primaryScreen().devicePixelRatio() or 1.0)
        self.kareler = {}
        for durum in GOZ_DURUMLARI:
            r = QSvgRenderer(QByteArray(karakter_svg(durum).encode("utf-8")))
            boy = r.defaultSize()
            pix = QPixmap(int(boy.width() * olcek), int(boy.height() * olcek))
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            r.render(p)
            p.end()
            pix.setDevicePixelRatio(olcek)
            self.kareler[durum] = pix

        self.ninja_pix = QPixmap(str(NINJA_DOSYASI))
        if self.ninja_pix.isNull():
            print("UYARI: ninja.png yüklenemedi, Kaptan-chan kullanılacak.")
            self.ayarlar["karakter"] = "kaptan"
        else:
            self.ninja_pix.setDevicePixelRatio(olcek)

        # ---- animasyon durumu ----
        self.goz = "acik"
        self.bob_faz = random.random() * math.tau
        self.zipla_t0 = None
        self.balon = None
        self.balon_kapat_z = 0.0

        # ---- zamanlayıcılar ----
        self.bob_zamanlayici = QTimer(self)
        self.bob_zamanlayici.timeout.connect(self._bob_adimi)
        self.bob_zamanlayici.start(50)

        self._goz_kapat_zamanlayici = QTimer(self)
        self._goz_kapat_zamanlayici.setSingleShot(True)
        self._goz_kapat_zamanlayici.timeout.connect(lambda: self._goz_degistir("acik"))

        self._kirp_zamanlayici = QTimer(self)
        self._kirp_zamanlayici.timeout.connect(self._kirp)
        self._kirp_zamanlayici.start(random.randint(2600, 5200))

        self.balon_zamanlayici = QTimer(self)
        self.balon_zamanlayici.timeout.connect(self._balon_kapat)

        isci.haber_geldi.connect(self._haber_goster)
        isci.durum.connect(self._durum_goster)

        self._gorsel_yenile(ilk=True)

        self.tray = None

        QTimer.singleShot(600, lambda: self._balon_goster(
            "Selam Kaptan! ⚓ Ben hazırım! Sağ tık → Ayarlar'dan kategorileri, "
            "karakteri ve boyutu seçebilirsin!", sure=12))

    # ---- görsel yerleşim ----

    def _gorsel_yenile(self, ilk=False):
        """Karakter/boyut değişince pencereyi yeniden ölçekle ve konumla."""
        ekran = QApplication.primaryScreen().availableGeometry()
        # toplam ekran yüksekliğinin en fazla %20'si
        self.boyut = min(self.ayarlar["boyut"], int(ekran.height() * 0.20))
        self.boyut = max(BOYUT_MIN, self.boyut)

        kaynak = (self.ninja_pix if self.ayarlar["karakter"] == "ninja"
                  and not self.ninja_pix.isNull() else self.kareler["acik"])
        dogal_g = kaynak.width() / kaynak.devicePixelRatio()
        dogal_y = kaynak.height() / kaynak.devicePixelRatio()
        self.karakterW = self.boyut * (dogal_g / dogal_y)
        self.karakterH = self.boyut

        self.PENCERE_G = max(int(self.karakterW) + 8, BALON_G + 8)
        self.PENCERE_Y = self.boyut + 184
        self.resize(self.PENCERE_G, self.PENCERE_Y)

        self.karakterX = self.PENCERE_G - int(self.karakterW) - 4
        self.karakterY = self.PENCERE_Y - self.boyut - 4

        konum = self.ayarlar.get("konum")
        if konum and ekran.contains(QPoint(konum[0], konum[1])):
            self.move(QPoint(konum[0], konum[1]))
        else:
            self.move(ekran.right() - self.PENCERE_G + 1 - KENAR_BOSLUK + 4,
                      ekran.bottom() - self.PENCERE_Y + 1 - KENAR_BOSLUK + 4)
        self._maske_guncelle()
        self.update()

    def karakter_onizleme(self, tur: str, kose: int) -> QPixmap:
        kaynak = (self.ninja_pix if tur == "ninja" and not self.ninja_pix.isNull()
                  else self.kareler["acik"])
        return kaynak.scaled(kose, kose,
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)

    # ---- animasyon ----

    def _bob_adimi(self):
        self.bob_faz += 0.07
        if self.zipla_t0 is not None:
            if time.monotonic() - self.zipla_t0 > 0.75:
                self.zipla_t0 = None
        if self.balon and time.monotonic() >= self.balon_kapat_z:
            self._balon_kapat()
        self._maske_guncelle()
        self.update()

    def _kirp(self):
        if self.ayarlar["karakter"] == "kaptan":
            self._goz_degistir("yarim")
            self._goz_kapat_zamanlayici.start(130)
        self._kirp_zamanlayici.start(random.randint(2600, 5600))

    def _goz_degistir(self, durum):
        if self.goz != durum:
            self.goz = durum
            self.update()

    def _karakter_bob(self) -> int:
        ofset = int(math.sin(self.bob_faz) * 3)
        if self.zipla_t0 is not None:
            t = (time.monotonic() - self.zipla_t0) / 0.75
            ofset -= int(40 * math.sin(min(1.0, t) * math.pi))
        return ofset

    # ---- balon ----

    def _balon_goster(self, metin: str, kategori=None, link=None, sure=15):
        self.balon = {"kategori": kategori, "baslik": metin, "link": link,
                      "rect": None}
        self.balon_kapat_z = time.monotonic() + sure
        self._maske_guncelle()
        self.update()

    def _balon_kapat(self):
        self.balon = None
        self._maske_guncelle()
        self.update()

    def _haber_goster(self, kategori, baslik, link):
        self._goz_degistir("mutlu")
        self.zipla_t0 = time.monotonic()
        QTimer.singleShot(1800, lambda: self._goz_degistir("acik"))
        QApplication.beep()
        self._balon_goster(baslik, kategori=kategori, link=link, sure=16)

    def _durum_goster(self, metin):
        self._balon_goster(metin, kategori=None, link=None, sure=10)

    def _balon_hesapla(self) -> QRect:
        if not self.balon:
            return QRect()
        baslik_f = QFont("Segoe UI", 10)
        chip_f = QFont("Segoe UI", 9, QFont.Weight.Bold)
        ipucu_f = QFont("Segoe UI", 8)

        fm = QFontMetrics(baslik_f)
        metin = self.balon["baslik"]
        sinir = fm.boundingRect(QRect(0, 0, BALON_G - 28, 10000),
                                Qt.TextFlag.TextWordWrap, metin)
        satirlar = min(4, max(1, math.ceil(sinir.height() / fm.height())))
        yukseklik = 14 + 22 + 8 + satirlar * fm.height() + 6 + 18 + 12

        by = self.karakterY - yukseklik - 14 + self._karakter_bob()
        bx = self.PENCERE_G - BALON_G - 4
        rect = QRect(bx, max(4, by), BALON_G, yukseklik)

        self.balon["rect"] = rect
        self.balon["_baslik_f"] = baslik_f
        self.balon["_chip_f"] = chip_f
        self.balon["_ipucu_f"] = ipucu_f
        self.balon["_satir_y"] = fm.height()
        return rect

    # ---- çizim ----

    def paintEvent(self, olay):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # --- konuşma balonu ---
        if self.balon:
            rect = self._balon_hesapla()
            kafa_merkez_x = self.karakterX + int(self.karakterW * 0.5)
            kuyruk = QPolygon([
                QPoint(kafa_merkez_x + 34, rect.bottom() - 1),
                QPoint(kafa_merkez_x + 74, rect.bottom() - 1),
                QPoint(kafa_merkez_x + 44, rect.bottom() + 16),
            ])

            yol = QPainterPath()
            yol.addRoundedRect(QRectF(rect), 16, 16)
            p.setPen(QPen(QColor("#ff8fb3"), 2))
            p.setBrush(QBrush(QColor(255, 255, 255, 244)))
            p.drawPath(yol)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 244))
            p.drawPolygon(kuyruk)
            p.setPen(QPen(QColor("#ff8fb3"), 2))
            p.drawLine(QPoint(kafa_merkez_x + 34, rect.bottom() - 1),
                       QPoint(kafa_merkez_x + 44, rect.bottom() + 16))
            p.drawLine(QPoint(kafa_merkez_x + 74, rect.bottom() - 1),
                       QPoint(kafa_merkez_x + 44, rect.bottom() + 16))

            x = rect.x() + 14
            y = rect.y() + 12
            if self.balon["kategori"]:
                ad = self.balon["kategori"]
                renk = QColor(KATEGORI_RENKLERI.get(ad, "#888888"))
                cf = self.balon["_chip_f"]
                cfm = QFontMetrics(cf)
                cw = cfm.horizontalAdvance(ad.upper()) + 18
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(renk)
                p.drawRoundedRect(QRectF(x, y, cw, 20), 10, 10)
                p.setPen(QColor("#ffffff"))
                p.setFont(cf)
                p.drawText(QRect(int(x), int(y), int(cw), 20),
                           Qt.AlignmentFlag.AlignCenter, ad.upper())
                x += cw + 8

            fm = QFontMetrics(self.balon["_baslik_f"])
            metin = self.balon["baslik"]
            while metin and fm.boundingRect(
                    QRect(0, 0, BALON_G - 28, 10000),
                    Qt.TextFlag.TextWordWrap, metin).height() > 4 * fm.height():
                metin = metin[:-2].rstrip() + "…"
            p.setPen(QColor("#26303e"))
            p.setFont(self.balon["_baslik_f"])
            p.drawText(QRect(rect.x() + 14, rect.y() + 38,
                             BALON_G - 28, 4 * fm.height()),
                       Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignTop,
                       metin)

            if self.balon["link"]:
                p.setPen(QColor("#b06a85"))
                p.setFont(self.balon["_ipucu_f"])
                p.drawText(QRect(rect.x() + 14, rect.bottom() - 24,
                                 BALON_G - 28, 16),
                           Qt.AlignmentFlag.AlignRight,
                           "habere gitmek için tıkla →")

        # --- karakter ---
        ofset = self._karakter_bob()
        kaynak = (self.ninja_pix if self.ayarlar["karakter"] == "ninja"
                  and not self.ninja_pix.isNull() else self.kareler[self.goz])
        hedef = QRectF(self.karakterX, self.karakterY + ofset,
                       self.karakterW, self.karakterH)
        p.drawPixmap(hedef, kaynak, QRectF(kaynak.rect()))

        # ninja için mutluluk pırıltıları (SVG'de hazır gelir)
        if self.goz == "mutlu" and kaynak is self.ninja_pix:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#ffd76e"))
            for (sx, sy, boy) in (
                    (self.karakterX + self.karakterW - 20, self.karakterY + ofset - 2, 13),
                    (self.karakterX + 4, self.karakterY + ofset + self.boyut * 0.25, 10)):
                yol = QPainterPath()
                yol.moveTo(sx, sy - boy)
                yol.lineTo(sx + boy * 0.3, sy - boy * 0.3)
                yol.lineTo(sx + boy, sy)
                yol.lineTo(sx + boy * 0.3, sy + boy * 0.3)
                yol.lineTo(sx, sy + boy)
                yol.lineTo(sx - boy * 0.3, sy + boy * 0.3)
                yol.lineTo(sx - boy, sy)
                yol.lineTo(sx - boy * 0.3, sy - boy * 0.3)
                yol.closeSubpath()
                p.drawPath(yol)

    # ---- maske ----

    def _maske_guncelle(self):
        ofset = self._karakter_bob()
        karakter_bolgesi = QRect(self.karakterX, self.karakterY + ofset,
                                 int(self.karakterW) + 2, self.boyut + 2)
        bolge = QRegion(karakter_bolgesi)
        if self.balon:
            rect = self._balon_hesapla()
            if not rect.isNull():
                kafa_merkez_x = self.karakterX + int(self.karakterW * 0.5)
                bolge += QRegion(rect)
                bolge += QRegion(QPolygon([
                    QPoint(kafa_merkez_x + 34, rect.bottom() - 2),
                    QPoint(kafa_merkez_x + 74, rect.bottom() - 2),
                    QPoint(kafa_merkez_x + 44, rect.bottom() + 16),
                ]))
        self.setMask(bolge)

    # ---- fare etkileşimi ----

    def _karakterde_mi(self, pozisyon: QPoint) -> bool:
        ofset = self._karakter_bob()
        return QRect(self.karakterX, self.karakterY + ofset,
                     int(self.karakterW) + 2, self.boyut + 2).contains(pozisyon)

    def mousePressEvent(self, olay):
        if olay.button() == Qt.MouseButton.LeftButton:
            self._tasma = olay.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._suruklendi = False
        elif olay.button() == Qt.MouseButton.RightButton:
            if self.tray:
                self.tray.menu().popup(olay.globalPosition().toPoint())

    def mouseMoveEvent(self, olay):
        if olay.buttons() & Qt.MouseButton.LeftButton and hasattr(self, "_tasma"):
            yeni = olay.globalPosition().toPoint() - self._tasma
            if (yeni - self.frameGeometry().topLeft()).manhattanLength() > 8:
                self._suruklendi = True
                self.move(yeni)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)
                       if self._karakterde_mi(olay.position().toPoint())
                       else QCursor(Qt.CursorShape.ArrowCursor))

    def mouseReleaseEvent(self, olay):
        if olay.button() != Qt.MouseButton.LeftButton:
            return
        if getattr(self, "_suruklendi", False):
            self.ayarlar["konum"] = [self.x(), self.y()]
            ayarlari_kaydet(self.ayarlar)
            return
        pozisyon = olay.position().toPoint()
        if self.balon and self.balon.get("rect") and \
                self.balon["rect"].contains(pozisyon):
            link = self.balon.get("link")
            if link:
                webbrowser.open(link)
                self._balon_kapat()
            return
        if self._karakterde_mi(pozisyon):
            if olay.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.isci.simdi()
            else:
                self._balon_goster(random.choice(KONUSMA_SATIRLARI),
                                   kategori=None, link=None, sure=7)

    def mouseDoubleClickEvent(self, olay):
        if self._karakterde_mi(olay.position().toPoint()):
            self.isci.simdi()


# ----------------------------------------------------------------------------
# Ana program: tepsi simgesi + menü
# ----------------------------------------------------------------------------

def _tepsi_ikonu(pencere) -> QIcon:
    pix = pencere.karakter_onizleme(pencere.ayarlar["karakter"], 64)
    return QIcon(pix)


def main():
    random.seed()
    uygulama = QApplication(sys.argv)
    uygulama.setQuitOnLastWindowClosed(False)
    uygulama.setApplicationName("Kaptan-chan Haber Asistanı")

    ayarlar = ayarlari_yukle()
    isci = HaberIscisi(ayarlar)
    pencere = KaptanPencere(ayarlar, isci)

    # ---- menü ----
    menu = QMenu()

    def ayarlar_ac():
        diyalog = AyarlarPenceresi(pencere)
        diyalog.exec()

    islem_ayarlar = QAction("⚙️ Ayarlar Penceresi", menu)
    islem_ayarlar.triggered.connect(ayarlar_ac)
    menu.addAction(islem_ayarlar)

    islem_simdi = QAction("🔔 Şimdi Haber Getir", menu)
    islem_simdi.triggered.connect(isci.simdi)
    menu.addAction(islem_simdi)

    def gorunurluk_degisti():
        if pencere.isVisible():
            pencere.hide()
            islem_gorunur.setText("👁️ Karakteri Göster")
        else:
            pencere.show()
            islem_gorunur.setText("🙈 Karakteri Gizle")

    islem_gorunur = QAction("🙈 Karakteri Gizle", menu)
    islem_gorunur.triggered.connect(gorunurluk_degisti)
    menu.addAction(islem_gorunur)

    menu.addSeparator()
    islem_cik = QAction("❌ Çıkış", menu)
    islem_cik.triggered.connect(uygulama.quit)
    menu.addAction(islem_cik)

    # ---- tepsi simgesi ----
    tepsi = QSystemTrayIcon(_tepsi_ikonu(pencere))
    tepsi.setToolTip("Kaptan-chan — Haber Asistanı")
    tepsi.setContextMenu(menu)
    tepsi.activated.connect(lambda neden: isci.simdi()
                            if neden == QSystemTrayIcon.ActivationReason.DoubleClick
                            else None)
    tepsi.show()
    pencere.tray = tepsi

    isci.baslat()

    def temizle():
        ayarlar["konum"] = [pencere.x(), pencere.y()]
        ayarlari_kaydet(ayarlar)
        isci.durdur()

    uygulama.aboutToQuit.connect(temizle)

    sys.exit(uygulama.exec())


if __name__ == "__main__":
    main()
