from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .discourse import fetch_topic, parse_discourse_topic_url, save_topic_json
from .markdown import extract_topic_metadata, slugify, write_markdown_files
from .notebooklm_adapter import NotebookCreationResult, NotebookLMService


@dataclass
class WorkflowResult:
    topic_url: str
    topic_id: str
    topic_title: str
    json_path: str
    markdown_paths: list[str]
    notebook: dict[str, object] | None
    run_dir: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_run_directory(base_dir: str | Path, topic_url: str, title_hint: str | None = None) -> Path:
    topic_ref = parse_discourse_topic_url(topic_url)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = slugify(title_hint or topic_ref.slug or f"topic-{topic_ref.topic_id}")
    return Path(base_dir) / f"{timestamp}-{topic_ref.topic_id}-{suffix}"


async def run_topic_to_notebook(
    topic_url: str,
    output_dir: str | Path,
    notebook_title: str | None = None,
    chunk_size: int = 2000,
    num_chunks: int = 0,
    create_notebook: bool = True,
    storage_path: str | None = None,
    wait_for_sources: bool = True,
    source_wait_timeout: float = 180.0,
) -> WorkflowResult:
    run_dir = build_run_directory(output_dir, topic_url)
    run_dir.mkdir(parents=True, exist_ok=True)

    topic_payload = fetch_topic(topic_url)
    topic = extract_topic_metadata(topic_payload)
    topic_slug = slugify(topic["title"])

    json_path = save_topic_json(topic_payload, run_dir / f"{topic_slug}.json")
    markdown_paths = write_markdown_files(
        topic_payload,
        run_dir / topic_slug,
        chunk_size=chunk_size,
        num_chunks=num_chunks,
    )

    notebook_result: NotebookCreationResult | None = None
    if create_notebook:
        service = NotebookLMService(storage_path=storage_path)
        notebook_result = await service.create_notebook_from_files(
            title=notebook_title or topic["title"],
            files=markdown_paths,
            wait_for_sources=wait_for_sources,
            source_wait_timeout=source_wait_timeout,
        )

    result = WorkflowResult(
        topic_url=topic_url,
        topic_id=str(topic["id"]),
        topic_title=topic["title"],
        json_path=str(json_path),
        markdown_paths=[str(path) for path in markdown_paths],
        notebook=notebook_result.to_dict() if notebook_result else None,
        run_dir=str(run_dir),
    )

    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return result
