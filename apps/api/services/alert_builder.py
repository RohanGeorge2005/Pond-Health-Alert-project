import json
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_TEMPLATES_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "alert_templates.json"


class AlertTemplateBuilder:
    """Bilingual alert message builder using reviewed templates (no hallucinated free-text LLM)."""

    def __init__(self, templates_path: Optional[str] = None):
        path = Path(templates_path) if templates_path else DEFAULT_TEMPLATES_PATH
        if not path.exists():
            path = Path("config/alert_templates.json")
        with open(path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.templates = self.data.get("templates", {})

    def render(self, code: str, **variables) -> Dict[str, str]:
        """Renders bilingual message given a reason code and variables."""
        tpl = self.templates.get(code)
        if not tpl:
            # Fallback
            tpl = self.templates.get("CANT_TELL")
            variables.setdefault("reason_en", code)
            variables.setdefault("reason_kn", code)

        en_text = tpl.get("en", "")
        kn_text = tpl.get("kn", "")

        # Format variables safely
        for k, v in variables.items():
            en_text = en_text.replace(f"{{{k}}}", str(v))
            kn_text = kn_text.replace(f"{{{k}}}", str(v))

        return {
            "code": code,
            "message_en": en_text,
            "message_kn": kn_text,
            "action_en": tpl.get("action_en", ""),
            "action_kn": tpl.get("action_kn", ""),
            "priority": tpl.get("priority", "MEDIUM"),
            "needs_review": self.data.get("metadata", {}).get("needs_review", True),
        }
