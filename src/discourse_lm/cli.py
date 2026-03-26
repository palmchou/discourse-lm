from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .discourse import fetch_topic, save_topic_json
from .markdown import load_topic_payload, write_markdown_files
from .notebooklm_adapter import NotebookLMService
from .pipeline import run_topic_to_notebook


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="discourse-lm",
        description="Fetch Discourse topics, convert them to Markdown, and create NotebookLM notebooks.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Fetch a topic and create a NotebookLM notebook")
    run_parser.add_argument("url", help="Discourse topic URL")
    run_parser.add_argument(
        "--output-dir",
        default="runs",
        help="Directory used for JSON, markdown, and manifest outputs",
    )
    run_parser.add_argument("--title", help="Notebook title override")
    run_parser.add_argument("--chunk-size", type=int, default=2000, help="Posts per markdown file; 0 disables chunking")
    run_parser.add_argument("--num-chunks", type=int, default=0, help="Maximum number of markdown chunks to emit")
    run_parser.add_argument("--storage-path", help="Path to NotebookLM storage_state.json")
    run_parser.add_argument("--skip-notebook", action="store_true", help="Only fetch and convert; do not create a notebook")
    run_parser.add_argument("--no-wait", action="store_true", help="Do not wait for NotebookLM source ingestion to finish")
    run_parser.add_argument(
        "--source-wait-timeout",
        type=float,
        default=180.0,
        help="Seconds to wait for each uploaded source to become ready",
    )

    fetch_parser = subparsers.add_parser("fetch", help="Fetch a topic into a JSON file")
    fetch_parser.add_argument("url", help="Discourse topic URL")
    fetch_parser.add_argument("-o", "--output", required=True, help="Output JSON path")

    convert_parser = subparsers.add_parser("convert", help="Convert a fetched topic JSON file to markdown")
    convert_parser.add_argument("input", help="Input topic JSON file")
    convert_parser.add_argument("-o", "--output-base", required=True, help="Output base path for markdown file(s)")
    convert_parser.add_argument("--chunk-size", type=int, default=2000, help="Posts per markdown file; 0 disables chunking")
    convert_parser.add_argument("--num-chunks", type=int, default=0, help="Maximum number of markdown chunks to emit")

    notebook_parser = subparsers.add_parser("notebook", help="Create a NotebookLM notebook from markdown file(s)")
    notebook_parser.add_argument("files", nargs="+", help="Markdown files to upload")
    notebook_parser.add_argument("--title", required=True, help="Notebook title")
    notebook_parser.add_argument("--storage-path", help="Path to NotebookLM storage_state.json")
    notebook_parser.add_argument("--no-wait", action="store_true", help="Do not wait for NotebookLM source ingestion to finish")
    notebook_parser.add_argument(
        "--source-wait-timeout",
        type=float,
        default=180.0,
        help="Seconds to wait for each uploaded source to become ready",
    )

    return parser


async def _run_async(args: argparse.Namespace) -> int:
    if args.command == "run":
        result = await run_topic_to_notebook(
            topic_url=args.url,
            output_dir=args.output_dir,
            notebook_title=args.title,
            chunk_size=args.chunk_size,
            num_chunks=args.num_chunks,
            create_notebook=not args.skip_notebook,
            storage_path=args.storage_path,
            wait_for_sources=not args.no_wait,
            source_wait_timeout=args.source_wait_timeout,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "notebook":
        service = NotebookLMService(storage_path=args.storage_path)
        result = await service.create_notebook_from_files(
            title=args.title,
            files=[Path(path) for path in args.files],
            wait_for_sources=not args.no_wait,
            source_wait_timeout=args.source_wait_timeout,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0

    raise ValueError(f"Unsupported async command: {args.command}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "fetch":
        payload = fetch_topic(args.url)
        output = save_topic_json(payload, args.output)
        print(output)
        return

    if args.command == "convert":
        payload = load_topic_payload(args.input)
        outputs = write_markdown_files(
            payload,
            args.output_base,
            chunk_size=args.chunk_size,
            num_chunks=args.num_chunks,
        )
        print(json.dumps([str(path) for path in outputs], indent=2))
        return

    asyncio.run(_run_async(args))


if __name__ == "__main__":
    main()
