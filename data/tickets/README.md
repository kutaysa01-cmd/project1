# Tickets Directory

HTML ticket dosyalarını buraya kopyala. Alt klasörler de desteklenir.

**Önemli:** Bu klasörün içeriği git'e yüklenmez (`.gitignore`'da). Gerçek müşteri
verisi güvende kalır.

Yeni dosyalar ekledikten sonra:
```
ingest.bat
```
komutu ile indeksi yeniden oluştur.

## HTML Format Desteği

`src/parser.py` içindeki `TICKET_FIELD_SELECTORS` sözlüğü hangi CSS
seçicilerini aradığını belirler. Varsayılan değerler yaygın alan adlarını
dener (`.ticket-title`, `.problem`, `.solution`, vs.). Senin HTML format'ın
farklıysa oradaki seçicileri güncelle.

Her ticket için beklenen minimum alanlar:
- `title` — kısa başlık
- `problem` — problem açıklaması
- `solution` — nasıl çözüldüğü

Hiçbir alan match etmezse parser dosyanın tüm metnini "problem" alanı
olarak kullanır — yani en kötü senaryoda bile veri kaybolmaz.
