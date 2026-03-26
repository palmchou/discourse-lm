from __future__ import annotations

import importlib
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


class NotebookLMAdapterError(RuntimeError):
    """Raised when notebooklm-py cannot be imported or used."""


@dataclass
class UploadedSource:
    id: str
    title: str
    status: int | None


@dataclass
class NotebookCreationResult:
    notebook_id: str
    title: str
    sources: list[UploadedSource]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _discover_site_packages() -> Path | None:
    candidate_roots: list[Path] = []

    env_path = os.environ.get("DISCOURSE_LM_NOTEBOOKLM_SITE_PACKAGES")
    if env_path:
        candidate_roots.append(Path(env_path))

    notebooklm_bin = shutil.which("notebooklm")
    if notebooklm_bin:
        try:
            first_line = Path(notebooklm_bin).read_text(encoding="utf-8").splitlines()[0]
        except (OSError, UnicodeDecodeError, IndexError):
            first_line = ""
        if first_line.startswith("#!") and "python" in first_line:
            interpreter = Path(first_line[2:].strip())
            lib_root = interpreter.parent.parent / "lib"
            if lib_root.exists():
                candidate_roots.append(lib_root)

    for root in candidate_roots:
        if root.name == "site-packages" and root.exists():
            return root
        matches = sorted(root.glob("python*/site-packages"))
        if matches:
            return matches[-1]
    return None


def load_notebooklm_client_class():
    try:
        from notebooklm import NotebookLMClient  # type: ignore

        return NotebookLMClient
    except ImportError:
        site_packages = _discover_site_packages()
        if site_packages and str(site_packages) not in sys.path:
            sys.path.insert(0, str(site_packages))
        try:
            module = importlib.import_module("notebooklm")
            return module.NotebookLMClient
        except Exception as exc:
            raise NotebookLMAdapterError(
                "Unable to import notebooklm-py. Install it into the active environment "
                "or make it discoverable via the `notebooklm` CLI or "
                "`DISCOURSE_LM_NOTEBOOKLM_SITE_PACKAGES`."
            ) from exc


class NotebookLMService:
    def __init__(self, storage_path: str | None = None) -> None:
        self.storage_path = storage_path
        self._client_class = load_notebooklm_client_class()

    async def create_notebook_from_files(
        self,
        title: str,
        files: list[Path],
        wait_for_sources: bool = True,
        source_wait_timeout: float = 180.0,
    ) -> NotebookCreationResult:
        if not files:
            raise NotebookLMAdapterError("No markdown files provided for upload")

        client = await self._client_class.from_storage(self.storage_path)
        async with client:
            notebook = await client.notebooks.create(title)
            uploaded = []
            for file_path in files:
                source = await client.sources.add_file(
                    notebook.id,
                    file_path,
                    wait=wait_for_sources,
                    wait_timeout=source_wait_timeout,
                )
                uploaded.append(
                    UploadedSource(
                        id=source.id,
                        title=source.title,
                        status=getattr(source, "status", None),
                    )
                )
            return NotebookCreationResult(
                notebook_id=notebook.id,
                title=notebook.title,
                sources=uploaded,
            )
