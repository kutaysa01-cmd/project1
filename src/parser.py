"""HTML ticket parser.

Designed to be flexible: tries structured extraction first (common field names),
falls back to raw-text extraction if structure is not recognized.

Edit the TICKET_FIELD_SELECTORS dict below to match your actual HTML format
after you inspect a few sample tickets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup


# ===== CUSTOMIZE THIS AFTER INSPECTING YOUR HTML =====
# Keys are the logical field name; values are CSS selectors to try in order.
# The first selector that returns text wins.
TICKET_FIELD_SELECTORS: dict[str, list[str]] = {
    "ticket_id": [
        "[data-field='ticket-id']", ".ticket-id", "#ticket-id",
        ".ticket-number", "#ticket-number",
    ],
    "title": [
        "[data-field='title']", ".ticket-title", "h1", "h2",
        ".subject", "#subject",
    ],
    "problem": [
        "[data-field='problem']", ".problem", ".description",
        ".issue", "#description",
    ],
    "solution": [
        "[data-field='solution']", ".solution", ".resolution",
        ".fix", "#resolution",
    ],
    "comments": [
        "[data-field='comments']", ".comments", ".comment-thread",
        "#comments",
    ],
    "status": [
        "[data-field='status']", ".status", "#status",
    ],
    "priority": [
        "[data-field='priority']", ".priority", "#priority",
    ],
    "created_at": [
        "[data-field='created']", ".created", ".created-at",
        ".date-created",
    ],
    "resolved_at": [
        "[data-field='resolved']", ".resolved", ".resolved-at",
        ".date-resolved",
    ],
    "assignee": [
        "[data-field='assignee']", ".assignee", ".owner",
    ],
    "category": [
        "[data-field='category']", ".category", ".component",
        ".system",
    ],
}


@dataclass
class Ticket:
    """A parsed ticket."""
    source_file: str
    ticket_id: Optional[str] = None
    title: Optional[str] = None
    problem: Optional[str] = None
    solution: Optional[str] = None
    comments: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None
    assignee: Optional[str] = None
    category: Optional[str] = None
    raw_text: str = ""
    extra: dict = field(default_factory=dict)

    def to_document(self) -> str:
        """Serialize to a single text block for embedding."""
        parts = []
        if self.ticket_id:
            parts.append(f"Ticket ID: {self.ticket_id}")
        if self.title:
            parts.append(f"Başlık / Title: {self.title}")
        if self.category:
            parts.append(f"Kategori / Category: {self.category}")
        if self.status:
            parts.append(f"Durum / Status: {self.status}")
        if self.priority:
            parts.append(f"Öncelik / Priority: {self.priority}")
        if self.created_at:
            parts.append(f"Oluşturma / Created: {self.created_at}")
        if self.resolved_at:
            parts.append(f"Çözüm Tarihi / Resolved: {self.resolved_at}")
        if self.problem:
            parts.append(f"\nPROBLEM:\n{self.problem}")
        if self.solution:
            parts.append(f"\nÇÖZÜM / SOLUTION:\n{self.solution}")
        if self.comments:
            parts.append(f"\nYORUMLAR / COMMENTS:\n{self.comments}")
        if not parts and self.raw_text:
            return self.raw_text
        return "\n".join(parts)

    def metadata(self) -> dict:
        """Metadata attached to vector store entries."""
        return {
            "source": self.source_file,
            "ticket_id": self.ticket_id or "",
            "title": (self.title or "")[:200],
            "category": self.category or "",
            "status": self.status or "",
        }


def _extract_first(soup: BeautifulSoup, selectors: list[str]) -> Optional[str]:
    """Try each selector; return the first non-empty text found."""
    for sel in selectors:
        try:
            el = soup.select_one(sel)
        except Exception:
            continue
        if el:
            text = el.get_text(" ", strip=True)
            if text:
                return text
    return None


def parse_html_ticket(file_path: str | Path) -> Ticket:
    """Parse a single HTML ticket file into a Ticket."""
    path = Path(file_path)
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")

    # Remove script/style noise
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    ticket = Ticket(source_file=str(path))

    for field_name, selectors in TICKET_FIELD_SELECTORS.items():
        value = _extract_first(soup, selectors)
        if value:
            setattr(ticket, field_name, value)

    # Always keep the raw text as a fallback. This ensures nothing is lost
    # even if the structured selectors miss something.
    ticket.raw_text = soup.get_text(" ", strip=True)

    # If problem AND solution are both missing (regardless of title), the structured
    # extraction failed to find the actual content — fall back to raw text.
    if not ticket.problem and not ticket.solution:
        ticket.problem = ticket.raw_text

    return ticket


def parse_tickets_dir(tickets_dir: str | Path) -> list[Ticket]:
    """Parse all *.html and *.htm files in a directory (recursive)."""
    base = Path(tickets_dir)
    if not base.exists():
        return []
    tickets = []
    for pattern in ("**/*.html", "**/*.htm"):
        for p in sorted(base.glob(pattern)):
            try:
                tickets.append(parse_html_ticket(p))
            except Exception as e:
                print(f"[WARN] Failed to parse {p}: {e}")
    return tickets


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Simple character-based chunking with overlap. Good enough for RAG."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Try to break at paragraph or sentence boundary
        if end < len(text):
            for sep in ["\n\n", "\n", ". ", " "]:
                last = text.rfind(sep, start + chunk_size // 2, end)
                if last != -1:
                    end = last + len(sep)
                    break
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [c for c in chunks if c]
