---
name: discourse-lm
description: Fetch a Discourse topic, convert the thread to markdown, and create a new NotebookLM notebook from that content. Use when the user wants to send a Discourse thread into NotebookLM, archive a topic as markdown first, or reuse the fetch and markdown conversion pipeline separately.
---

# Discourse to NotebookLM

Use this skill when the user wants a Discourse topic turned into a NotebookLM notebook, or when they want the intermediate fetch and markdown outputs.

## Preconditions

- `notebooklm login` has already been completed on the machine if NotebookLM creation is required.
- `discourse-lm` is installed, or this repository checkout is present so the bundled wrapper can run the project from source.
- Network access is available when fetching live Discourse topics.

## Primary Workflow

For the normal end-to-end case, run:

```bash
./skills/discourse-lm/scripts/run_discourse_lm.sh run "<TOPIC_URL>" --output-dir ./runs
```

This will:

1. Fetch the full Discourse topic as JSON.
2. Convert it to NotebookLM-friendly markdown.
3. Create a new NotebookLM notebook.
4. Upload the markdown file or files as notebook sources.
5. Write `manifest.json` with the resulting notebook and source IDs.

## Component Workflows

Fetch only:

```bash
./skills/discourse-lm/scripts/run_discourse_lm.sh fetch "<TOPIC_URL>" -o ./topic.json
```

Convert only:

```bash
./skills/discourse-lm/scripts/run_discourse_lm.sh convert ./topic.json -o ./topic
```

Notebook creation from existing markdown:

```bash
./skills/discourse-lm/scripts/run_discourse_lm.sh notebook ./topic.md --title "Notebook Title"
```

## Operational Guidance

- Default to `run` unless the user explicitly wants only fetch/convert.
- Keep the local run directory and manifest unless the user asks to delete outputs.
- For large topics, use `--chunk-size` so NotebookLM receives multiple markdown sources instead of one oversized file.
- If the user only wants a dry run, use `--skip-notebook`.
- If source ingestion time is not important, use `--no-wait` to return sooner after upload.

## Verification

After a successful end-to-end run, inspect the JSON response for:

- `json_path`
- `markdown_paths`
- `notebook.notebook_id`
- `notebook.sources[*].id`

If NotebookLM creation fails but fetch/convert succeeds, return the saved markdown paths so the user can retry the upload step separately.
