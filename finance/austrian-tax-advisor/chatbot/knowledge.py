"""Knowledge base loader — reads all references/*.md as system context."""

from pathlib import Path
from typing import Optional

from config import REFERENCES_DIR


SYSTEM_PROMPT_PREFIX = """Du bist ein österreichischer Steuer-Assistent für das Steuerjahr 2026.
Du beantwortest Fragen zum österreichischen Steuerrecht basierend auf dem "1x1 der Steuern 2026" von TPA Steuerberatung.

WICHTIGE REGELN:
- Antworte auf Deutsch, klar und verständlich
- Verwende die bereitgestellten Tools für Berechnungen — rate niemals bei Zahlen
- Nenne immer die relevanten Regelungen und Paragraphen
- Weise bei komplexen Fällen auf die Notwendigkeit professioneller Beratung hin
- Formatiere Zahlen mit Tausendertrennzeichen und 2 Dezimalstellen
- Verwende Tabellen für Vergleiche

DISCLAIMER: Du bist ein KI-Assistent und kein Steuerberater. Deine Antworten sind informativ, aber keine Steuerberatung. Für verbindliche Auskünfte soll sich der User an einen Steuerberater wenden.

STEUERWISSEN 2026:
"""


def load_knowledge_base() -> str:
    """Load all reference markdown files and build the system prompt."""
    knowledge_parts: list[str] = []

    if not REFERENCES_DIR.exists():
        return SYSTEM_PROMPT_PREFIX + "\n(Keine Wissensbasis gefunden.)"

    for md_file in sorted(REFERENCES_DIR.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
            # Truncate very long files to keep context manageable
            if len(content) > 8000:
                content = content[:8000] + "\n\n[... gekürzt ...]"
            knowledge_parts.append(f"\n### {md_file.stem}\n{content}")
        except Exception:
            continue

    full_knowledge = "\n".join(knowledge_parts)

    # Keep system prompt under ~30k chars to leave room for conversation
    if len(full_knowledge) > 30000:
        full_knowledge = full_knowledge[:30000] + "\n\n[... weitere Inhalte gekürzt ...]"

    return SYSTEM_PROMPT_PREFIX + full_knowledge


# Cache the system prompt at module load
SYSTEM_PROMPT: Optional[str] = None


def get_system_prompt() -> str:
    """Get the cached system prompt."""
    global SYSTEM_PROMPT
    if SYSTEM_PROMPT is None:
        SYSTEM_PROMPT = load_knowledge_base()
    return SYSTEM_PROMPT
