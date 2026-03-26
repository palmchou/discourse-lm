# discourse-lm

`discourse-lm` fetches a Discourse topic, converts the full thread into NotebookLM-friendly markdown, and creates a new NotebookLM notebook populated with that markdown.

## What It Does

- Fetches the complete topic through Discourse JSON APIs with chunked post retrieval.
- Converts cooked Discourse HTML into readable markdown with topic metadata and post structure preserved.
- Creates a fresh NotebookLM notebook and uploads the generated markdown file or files as sources.
- Writes a local run directory with the raw JSON, markdown output, and a `manifest.json` describing the run.

## Project Layout

- `src/discourse_lm/discourse.py`: topic URL parsing and Discourse fetching.
- `src/discourse_lm/markdown.py`: topic JSON to markdown conversion and chunked file emission.
- `src/discourse_lm/notebooklm_adapter.py`: `notebooklm-py` import fallback and notebook/source creation.
- `src/discourse_lm/pipeline.py`: end-to-end orchestration.
- `src/discourse_lm/cli.py`: CLI entrypoint.
- `skills/discourse-lm/SKILL.md`: installable OpenClaw/Codex skill definition.
- `skills/discourse-lm/scripts/run_discourse_lm.sh`: skill wrapper for invoking the project CLI.

## Requirements

- Python 3.11+
- NotebookLM authentication already set up through `notebooklm login`
- `notebooklm-py` available either in the current Python environment or in the existing uv tool install at `~/.local/share/uv/tools/notebooklm-py`

## Install

```bash
cd /Users/palm/Projects/discourse-lm
python3 -m pip install -e .[dev]
```

## OpenClaw Skill Install

This repository includes an installable skill at `skills/discourse-lm/`.

To use it with OpenClaw or Codex-style local skills:

```bash
python3 -m pip install -e /Users/palm/Projects/discourse-lm
mkdir -p ~/.codex/skills
ln -s /Users/palm/Projects/discourse-lm/skills/discourse-lm ~/.codex/skills/discourse-lm
```

If your OpenClaw setup uses a different skills directory, copy or symlink `skills/discourse-lm/` there instead.

The skill uses the bundled wrapper at `skills/discourse-lm/scripts/run_discourse_lm.sh`, which prefers the checked-out repository source tree and falls back to the installed `discourse-lm` CLI.

Once installed, the skill can be used to:

- Fetch a Discourse topic.
- Convert it to markdown.
- Create a new NotebookLM notebook from that topic content.
- Reuse the same pipeline in separate fetch, convert, and notebook steps.

## Usage

End-to-end:

```bash
discourse-lm run "https://meta.discourse.org/t/my-topic/12345"
```

Fetch only:

```bash
discourse-lm fetch "https://meta.discourse.org/t/my-topic/12345" -o ./topic.json
```

Convert only:

```bash
discourse-lm convert ./topic.json -o ./topic
```

Create a notebook from markdown:

```bash
discourse-lm notebook ./topic.md --title "My Notebook"
```

## Recommended Features Included

- Chunking large topics into multiple markdown sources for NotebookLM.
- Separate subcommands for fetch, convert, and notebook creation.
- Source ingestion waiting with timeout control.
- Local artifact retention for auditability and reruns.

## Notes

- The end-to-end command creates outputs under `runs/<timestamp>-<topicid>-<slug>/`.
- If `notebooklm-py` is not importable in the active interpreter, the adapter falls back to the existing local uv tool installation.
- For fetch-only or convert-only workflows, use `--skip-notebook` or the dedicated subcommands.
