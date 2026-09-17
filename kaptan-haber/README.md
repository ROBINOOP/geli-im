# ⚓🥷 Kaptan-chan — Masaüstü Anime Haber Asistanı

Ekranın **sağ alt köşesinde** (18 px kenar boşluğuyla) havada süzülen anime
asistanı. Seçtiğin kategorilerdeki güncel haberleri **konuşma balonu** ile
bildirir. İki karakterden birini seçebilirsin: **Kaptan-chan ⚓** veya
**Shogun 🥷**.

## 🚀 Çalıştırma

- **baslat.bat** dosyasına çift tıkla (konsol açılmadan başlar), **veya**
- Komut satırından: `python kaptan.py`

## ⚙️ Ayarlar Penceresi (sağ tık → Ayarlar)

### 📰 Kategoriler sekmesi
Kutucuk + kategori adı şeklinde, seçtiğin her kategoriden haber gelir:

Son Dakika • Gündem • Dünya • Ekonomi • Teknoloji • Spor • Oyun & E-Spor •
Bilim • Sağlık • Eğitim • Yaşam

Kaynaklar: ntv.com.tr, tamindir.com (Oyun & E-Spor), evrimagaci.org (Bilim).
Yeni kaynak eklemek için `kaptan.py` içindeki `KATEGORILER` sözlüğünü düzenle.

### 🎨 Görünüm sekmesi
- **Karakter seçimi:** Kaptan-chan ⚓ (SVG, animasyonlu göz kırpma) veya
  Shogun 🥷 (özel görsel, `varliklar/ninja.png`)
- **Boyut kaydırıcısı:** 150–240 px (ekran yüksekliğinin en fazla %20'si
  olacak şekilde sınırlandırılır)
- **Bildirim sıklığı:** 1 / 5 / 10 / 30 dakika

## 🎮 Kullanım

| Eylem | Sonuç |
|---|---|
| Karaktere **tek tık** | Tatlı bir konuşma satırı |
| Karaktere **çift tık** / **Ctrl+tık** | Hemen yeni haber getirir |
| Karakteri **sürükle** | Ekranın istediğin yerine taşı (hatırlanır) |
| Karaktere **sağ tık** | Menü (Ayarlar, hemen getir, gizle, çıkış) |
| Balona **tık** | Haberin orijinal sayfasını tarayıcıda açar |
| Tepsi simgesine **çift tık** | Hemen haber getirir |

## ✨ Animasyonlar

- Havada süzülme + (Kaptan-chan'da) rastgele göz kırpma
- Haber gelince: mutlu gözler, zıplama, pırıltı ✨ ve bip sesi
- Balonda kategori renk etiketi + "habere gitmek için tıkla →" ipucu

## 🖼️ Karakter görseli kuralları

- En/Boy oranı 1:1 veya 3:4, yükseklik 180–240 px, genişlik 150–200 px
- Toplam ekran yüksekliğinin maksimum %15–20'si
- Sağ alt köşeden (görev çubuğu üzerinden) 15–20 px iç boşluk
- Yeni karakter eklemek için şeffaf PNG'yi `varliklar/` klasörüne koyup
  `KARAKTERLER` sözlüğüne ekle
- Damalı arka planlı görselleri şeffaflaştırmak için:
  `python varliklar/hazirla.py`

## 📋 Gereksinimler

- Python 3.12+  →  `pip install PySide6`
- Windows 10/11 (şeffaf, her zaman üstte pencere)

Ayarlar `ayarlar.json` dosyasına kaydedilir.
