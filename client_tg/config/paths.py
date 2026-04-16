# client_tg/config/paths.py
# Автоматически сгенерировано для сервиса: client_tg

from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass
class ProjectPaths:
    """Управление путями проекта"""

    data: Path

    @classmethod
    def from_base(cls, base_dir: Path = None) -> "ProjectPaths":
        """Создаёт пути относительно base_dir (корень сервиса)"""
        if base_dir is None:
            base_dir = Path(__file__).parent.parent
        paths = cls(
            data="data",
        )
        paths.create_directories()
        return paths

    def create_directories(self) -> None:
        for field_name in self.__dataclass_fields__:
            path = getattr(self, field_name)
            if isinstance(path, Path):
                path.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Path]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    def __str__(self) -> str:
        lines = []
        for name, path in self.to_dict().items():
            status = "✓" if path.exists() else "✗"
            try:
                rel = path.relative_to(Path.cwd())
            except ValueError:
                rel = path
            lines.append(f"  {name}: {rel} {status}")
        return "Project Paths:\n" + "\n".join(lines)
