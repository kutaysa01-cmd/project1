# T3000 Problem Finder

T3000 Bina Otomasyon Sistemi (BAS) için **offline AI asistanı**. Geçmiş
ticket'lardan ve sistem manuellerinden öğrenir, sorularını doğal dilde
cevaplar. İnternet gerektirmez — tüm veriler ve model senin bilgisayarında
kalır.

> **Mimari:** PyQt6 arayüz • Ollama (yerel LLM) • ChromaDB (vektör DB) •
> sentence-transformers (embedding) • RAG (Retrieval-Augmented Generation)

---

## Özellikler

- **Tamamen offline** — hiçbir veri dışarı çıkmaz
- **Türkçe + İngilizce** destek
- **HTML ticket parser** — esnek, farklı formatları destekler
- **PDF manuel desteği** — sistem dokümantasyonunu da indeksler
- **Streaming cevap** — token token akar, beklemezsin
- **Kaynak gösterme** — her cevap hangi ticket/sayfadan geldi belli
- **Tek dosya veritabanı** — ChromaDB, kolay yedekle/taşı

---

## Donanım gereksinimleri

| Senaryo | RAM | GPU | Model | Hız |
|---|---|---|---|---|
| Minimum | 16 GB | yok | phi3.5:3.8b | 10-15 tok/sn |
| Önerilen | 32 GB | yok | qwen2.5:7b | 4-7 tok/sn |
| Hızlı | 16 GB | 8 GB VRAM | qwen2.5:7b | 30-50 tok/sn |
| Kaliteli | 32 GB | 16 GB VRAM | qwen2.5:14b | 20-30 tok/sn |

---

## Kurulum (Windows)

### 1. Önce bunları kur:
- **Python 3.10+** → [python.org](https://www.python.org/downloads/) — kurulumda **"Add Python to PATH"** işaretle
- **Ollama** → [ollama.com](https://ollama.com) — çift tık `.exe` kur

### 2. Bu repoyu klonla veya indir:
```powershell
git clone https://github.com/kutaysa01-cmd/project1.git C:\Projects\problem-finder
cd C:\Projects\problem-finder
```

### 3. Setup script'ini çalıştır:
```powershell
setup.bat
```
Bu şunları yapar:
- Python sanal ortamı (venv) oluşturur
- Gerekli paketleri kurar (`pip install -r requirements.txt`)
- Ollama kurulu değilse uyarır
- Qwen2.5 7B modelini indirir (~4.5 GB, tek seferlik)

### 4. Veri hazırla:
- HTML ticket dosyalarını `data\tickets\` içine kopyala
- PDF manuelleri `data\manuals\` içine kopyala (opsiyonel)

### 5. Veritabanını oluştur:
```powershell
ingest.bat
```

### 6. Uygulamayı aç:
```powershell
run.bat
```

---

## Kullanım

Uygulama açıldığında:
1. **SORU** kutusuna problemini Türkçe yaz
2. **Sor** butonu veya `Ctrl+Enter`
3. **CEVAP** bölümünde LLM'in cevabı akar
4. **KAYNAKLAR** bölümünde hangi ticket/manuelden geldiği görünür

### Örnek sorular:
- "Zone 3 sıcaklık sensörü -40°C okuyor, ne yapmalıyım?"
- "Chiller'ın COP değeri düştü, sebepleri neler olabilir?"
- "BACnet cihazı offline görünüyor, nasıl debug ederim?"
- "VAV damper kontrolsüz, hangi parametreleri kontrol etmeliyim?"

---

## Konfigürasyon

Tüm ayarlar `config.yaml` içinde:

```yaml
llm:
  model: "qwen2.5:7b"        # Hangi Ollama modelini kullanacak
  temperature: 0.2            # Düşük = tutarlı, yüksek = yaratıcı
  num_ctx: 8192              # Context window

embedding:
  model: "intfloat/multilingual-e5-base"  # Türkçe destekli

retrieval:
  top_k: 5                   # Kaç kaynak chunk kullansın
  min_score: 0.3            # Minimum benzerlik eşiği

ui:
  language: "tr"            # tr veya en
  theme: "dark"             # dark veya light
```

### Daha güçlü modele geçmek
GPU'lu makineye geçtiğinde:
```powershell
ollama pull qwen2.5:14b
```
Sonra `config.yaml`'de `model: "qwen2.5:14b"` yap. Hepsi bu.

---

## HTML Ticket Format Uyarlama

Varsayılan parser yaygın class isimlerini dener (`.ticket-title`, `.problem`,
`.solution`, vb.). Senin HTML format'ın farklıysa `src/parser.py` içindeki
`TICKET_FIELD_SELECTORS` sözlüğünü güncelle:

```python
TICKET_FIELD_SELECTORS = {
    "ticket_id": [".my-ticket-id-class"],
    "problem": ["#description", ".desc"],
    "solution": [".fix-steps"],
    # ...
}
```

Hiçbir alan match etmezse parser dosyanın tüm metnini problem alanı olarak
kullanır — hiçbir veri kaybolmaz.

---

## Proje yapısı

```
project1/
├── README.md                # Bu dosya
├── config.yaml              # Tüm ayarlar
├── requirements.txt         # Python bağımlılıkları
├── setup.bat                # Windows kurulum
├── ingest.bat               # Veritabanı oluştur
├── run.bat                  # Uygulamayı aç
├── src/
│   ├── parser.py           # HTML/PDF parser
│   ├── ingest.py           # Vektör DB oluşturucu
│   ├── rag.py              # Retrieval (benzerlik araması)
│   ├── llm.py              # Ollama wrapper + prompt
│   └── app.py              # PyQt6 GUI
├── data/
│   ├── tickets/            # Senin HTML ticket'ların (git'e dahil değil)
│   └── manuals/            # PDF manueller (git'e dahil değil)
└── chroma_db/              # Vektör DB (otomatik oluşur, git'te değil)
```

---

## Sorun giderme

**"Ollama bağlanılamadı"**
Terminal aç: `ollama serve` — Ollama servisini manuel başlat.

**"Model bulunamadı"**
```powershell
ollama pull qwen2.5:7b
```

**Çok yavaş cevaplar**
- `config.yaml`'de daha küçük modele geç: `phi3.5:3.8b` veya `qwen2.5:3b`
- Veya `num_ctx`'i düşür (4096)

**Türkçe cevap gelmiyor**
- `config.yaml`'de `language: "tr"` olduğundan emin ol
- `qwen2.5` modelleri Türkçe'de `llama3`'ten çok daha iyi

**Vektör DB bozuldu**
```powershell
rmdir /s /q chroma_db
ingest.bat
```

**OneDrive klasöründe çalışırken yavaş**
OneDrive sync dosya kilitlerine yol açar. `C:\Projects\problem-finder\` gibi
yerel bir klasöre taşı.

---

## Veri gizliliği

- **Hiçbir ticket, soru, cevap internete gitmez.**
- Ollama ve ChromaDB tamamen yerel.
- `.gitignore` gerçek veri klasörlerini git'ten dışarıda tutar.
- Modelleri Ollama ilk indirmede alır (bu internet gerektirir, bir kerelik).

Kurumsal ortamda kullanıyorsan `data/tickets/` içindeki dosyaları şirket
policy'sine göre anonimleştirmen yerinde olur.

---

## Lisans

Internal / proprietary (Siemens Energy kullanımı için).
