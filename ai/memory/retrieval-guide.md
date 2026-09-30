# Retrieval guide

## Default: local, summary first

Spend effort when saving information so future questions can be answered from short,
connected notes. Granola supplies imports and explicit refreshes; it is not required to
recall already imported details. Both outlines and full transcripts live in this vault.

1. Search canonical notes and meeting abstractions. Start with a gist and quick answers.
2. Read the relevant discussion, decision, Q&A, or dated update section.
3. Expand to the complete original outline only if more detail is needed.
4. Read local transcript passages for exact wording, ambiguity, omissions, or verification.
5. Stop once the answer is supported. Cite the note and precise section or source paragraph.

Do not read every linked note or load a whole transcript to answer a summary question.
If summaries lack evidence, search local sources before concluding something is unknown.
If a source is absent, say so. Fetch from Granola only to repair that absence or refresh
an explicitly requested scope, and archive the result before relying on it next time.

## Local tools

Read `~/.config/life-memory/config.json` for `python` and `runtime`; `recall.py` is beside
`memory.py`. The commands below use those values, not the shell's arbitrary Python.

```sh
<python> <runtime-directory>/recall.py search "question or keywords"
<python> <runtime-directory>/recall.py read "Wiki/Projects/Job search.md"
<python> <runtime-directory>/recall.py context "Wiki/Projects/Job search.md"
<python> <runtime-directory>/recall.py read "Meetings/<meeting>.md" --section "Quick answers"
<python> <runtime-directory>/recall.py search "specific phrase" --scope outline
<python> <runtime-directory>/recall.py search "exact words" --scope transcript
<python> <runtime-directory>/recall.py read "Sources/Granola/<id>/<revision>/Transcript.md" --layer transcript --section Transcript --offset 0 --limit 4000
```

Search is section-sized SQLite full-text retrieval with word stemming, title/alias/heading
weighting, and one result per note. Default scope is `summary`; `session`, `outline`,
`transcript`, and `all` are explicit opt-ins. The index refreshes changed notes on search;
it is a disposable local cache. `read` defaults to gist/quick answers plus a section menu.
Use `next_offset` to continue a bounded passage. A search snippet is a candidate, not an answer.

For paraphrases or low keyword recall, use Basic Memory semantic/hybrid search with
`metadata_filters={"retrieval_layer":"canonical"}` or `{"retrieval_layer":"meeting"}`.
Read the exact matching path locally. Broaden to source/session search when appropriate.
Never interpret an empty keyword result as proof that no relevant evidence exists.

Local `context` resolves an exact path, unique title, or stored permalink. It returns the
requested summary and bounded linked summaries, plus evidence paths without source bodies.
It refuses ambiguous identities. Basic Memory's context tool previously returned an
unrelated primary for Job search; after metadata/index refresh it resolved correctly in
the verification run. Still validate its returned primary path before trusting it.
Do not rely on a successful tool response alone as proof of correct resolution.

## Writing for retrieval

- Canonical notes: descriptive title, useful aliases, `retrieval_layer: canonical`, concise
  gist, quick answers, dated changes, explicit unknowns, and explained links to evidence.
- Meetings: `retrieval_layer: meeting`, gist, key decisions/follow-ups/Q&A, date and source ID,
  full original outline in the Markdown body, and a full locally archived transcript link.
- Preserve original outline wording, heading hierarchy, nested bullets, and private notes.
  Embeds and external URLs alone do not satisfy local completeness.
- Keep corrections, interpretations, and later outcomes outside original source blocks.
- Prefer exact source paragraphs when available. Preserve supplied speaker labels; a
  microphone channel is not proof of identity. Never invent timestamps.
- Topic and entity notes should answer useful questions rather than only list related files.
  Do not infer employment, attendance, preference, or completed work from a mere mention.
- Keep current state dated. A proposed interview, service plan, or deployment is not completion.
  Draft answers are not confirmed biographical facts or messages that were actually sent.
- Reuse existing entities; add cross-topic connections when supported, not merely because
  they share words. Update both the relevant overview and the source-linked meeting.
- Managed outline/evidence sections have conflict detection. Preserve human edits and
  source revisions. Changed sources require synthesis review, not silent summary replacement.

## Verification

Run representative local questions with expected sources, including paraphrases, comparisons,
exact evidence, changed decisions, and unanswerable questions. Check both retrieval ranking
and answer support. Record gaps honestly. Local text equality establishes source completeness,
not truth of every statement in the source. See [[System/Granola import]] and
[[System/Memory status]] for coverage and pending synthesis.

## Relations

- implements [[System/Memory rules]] — source-grounded recall and preservation.
- implements [[System/Linking rules]] — meaningful connected retrieval.
- supports [[Wiki/Projects/Connected memory setup]] — operational lookup protocol.
