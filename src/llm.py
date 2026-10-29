"""Thin wrapper around the local Ollama server."""
from __future__ import annotations

from typing import Iterator

import ollama


SYSTEM_PROMPT_TR = """Sen T3000 Bina Otomasyon Sistemi (BAS) uzmanısın. Görevin:

1. Kullanıcının sorduğu problemi anlamak
2. Sana verilen BAĞLAM (geçmiş ticket'lar ve sistem manuelleri) içinde cevabı aramak
3. Türkçe, net, teknik ve kısa cevap vermek
4. Her iddiayı bağlamdaki kaynağa dayandırmak (örn: "[Ticket #1234'e göre...]")
5. Çözüm adımlarını numaralı liste olarak sunmak
6. Bağlamda cevap YOKSA uydurma! Açıkça şöyle de:
   "Verilen bilgi tabanında bu probleme dair bir kayıt bulamadım.
    Şunları kontrol etmeni öneririm: ..."

ÖNEMLİ KURALLAR:
- Sadece verilen bağlama dayanarak cevap ver
- Emin değilsen "emin değilim" de
- Teknik terimleri olduğu gibi bırak (sensor, valve, PID, setpoint vs.)
- Güvenlik uyarıları varsa mutlaka belirt
"""

SYSTEM_PROMPT_EN = """You are a T3000 Building Automation System (BAS) expert. Your job:

1. Understand the user's problem
2. Search the provided CONTEXT (past tickets and system manuals) for answers
3. Give a clear, technical, concise answer
4. Ground every claim in a context source (e.g. "[According to Ticket #1234...]")
5. Present solution steps as a numbered list
6. If the context does NOT contain the answer, do NOT fabricate! Say explicitly:
   "I could not find a record of this problem in the knowledge base.
    I suggest checking: ..."

CRITICAL RULES:
- Answer ONLY based on provided context
- Say "I'm not sure" when uncertain
- Keep technical terms as-is (sensor, valve, PID, setpoint, etc.)
- Always flag any safety warnings from the manual
"""


def _build_prompt(question: str, context_chunks: list[dict], lang: str) -> list[dict]:
    """Build the messages array sent to Ollama."""
    sys_prompt = SYSTEM_PROMPT_TR if lang == "tr" else SYSTEM_PROMPT_EN

    # Format retrieved chunks as a numbered context block
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        meta = chunk.get("metadata", {})
        src_label = meta.get("ticket_id") or meta.get("title") or meta.get("source", "?")
        kind = meta.get("type", "doc")
        context_parts.append(
            f"[{i}] ({kind} - {src_label})\n{chunk['document']}\n"
        )
    context_block = "\n---\n".join(context_parts) if context_parts else "(No context found)"

    header = "BAĞLAM" if lang == "tr" else "CONTEXT"
    question_header = "SORU" if lang == "tr" else "QUESTION"
    user_msg = f"{header}:\n{context_block}\n\n{question_header}: {question}"

    return [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_msg},
    ]


class LLMClient:
    def __init__(self, model: str, host: str, temperature: float = 0.2,
                 num_ctx: int = 8192):
        self.model = model
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.client = ollama.Client(host=host)

    def check_connection(self) -> tuple[bool, str]:
        """Returns (is_ok, message)."""
        try:
            models = self.client.list()
            names = [m.get("name") or m.get("model", "") for m in models.get("models", [])]
            if not any(self.model in n for n in names):
                return False, (
                    f"Model '{self.model}' bulunamadı. Kurmak için:\n"
                    f"   ollama pull {self.model}"
                )
            return True, f"OK ({len(names)} model yüklü)"
        except Exception as e:
            return False, f"Ollama'ya bağlanılamadı: {e}\nOllama çalışıyor mu? (ollama serve)"

    def ask(self, question: str, context_chunks: list[dict], lang: str = "tr") -> str:
        """Non-streaming call. Returns the full answer string."""
        messages = _build_prompt(question, context_chunks, lang)
        resp = self.client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
            },
        )
        return resp["message"]["content"]

    def ask_stream(self, question: str, context_chunks: list[dict],
                   lang: str = "tr") -> Iterator[str]:
        """Streaming call. Yields response chunks as they arrive."""
        messages = _build_prompt(question, context_chunks, lang)
        stream = self.client.chat(
            model=self.model,
            messages=messages,
            stream=True,
            options={
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
            },
        )
        for part in stream:
            content = part.get("message", {}).get("content", "")
            if content:
                yield content
