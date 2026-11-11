from pathlib import Path

from .models import Corpus

DATA_PATH = Path(__file__).parent / "data" / "sample.json"


def load(path: Path) -> Corpus:
    return Corpus.model_validate_json(path.read_text(encoding="utf-8"))
