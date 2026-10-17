import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "bands.yaml"


def load_bands_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        # Fallback to local config directory if in another path
        fallback = Path("config/bands.yaml")
        if fallback.exists():
            path = fallback
        else:
            raise FileNotFoundError(f"Bands config not found at {path} or {fallback}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
