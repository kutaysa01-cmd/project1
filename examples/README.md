# Sample Tickets

Buradaki HTML dosyaları **test/demo** amaçlıdır — parser'ın nasıl çalıştığını
gösterir ve kurulumdan hemen sonra bir şeyin çalıştığını görmen için.

**Hızlı başlangıç için:**
```powershell
copy examples\sample_tickets\*.html data\tickets\
ingest.bat
run.bat
```

Sonra uygulamada şunu sor:
> "Sıcaklık sensörü eksi değer okuyorsa ne yapmalıyım?"

Veya:
> "Chiller COP değeri düşerse hangi noktalar kontrol edilmeli?"

Gerçek verilerinle çalışmaya başladığında bu klasörü yok sayabilir veya
silebilirsin.

## Dosya format örnekleri

- `sample_ticket_001.html` — Yapılandırılmış: `.ticket-id`, `.problem`, `.solution` CSS class'ları
- `sample_ticket_002.html` — Aynı yapı, farklı içerik
- `sample_ticket_003.html` — Yapısız: `<h1>` title, `<h2>` section header, `<p>` içerik
  (parser bu durumda tüm metni "problem" olarak alır — hiçbir şey kaybolmaz)
