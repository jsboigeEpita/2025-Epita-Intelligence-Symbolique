# Rules for sub-agents

Repository root: the checkout you are working in (GitHub `jsboigeEpita/2025-Epita-Intelligence-Symbolique`).
All paths below are relative to that root. Read `CLAUDE.md` (§ Dataset Privacy Discipline, § Cleanup Gate)
and `AGENTS.md` first if you have not.

1. **Privacy (hard).**
   - GitHub-indexed surfaces (commit messages, PR and issue titles, bodies, comments) and tracked files never carry a
     document identifier: no source name, author, speech title or date, and no 8-hex document id. Write "doc_A",
     "the panel's longest document".
   - Never copy dataset text (fields `full_text`, `raw_text`, `full_text_segment`, `raw_text_snippet`, quotes of the
     documents) into a tracked file or a GitHub text.
   - Recorded states and panel files live under `argumentation_analysis/evaluation/results/` (gitignored). Read them in
     place. Never copy them elsewhere.
   - When you print tool output that may contain ids, pipe it through `sed -E 's/[0-9a-f]{8}(_ext[0-9]+)?/<id>/g'`.
   - Every text bound for GitHub passes `python scripts/coordination/post_tracker.py scan <file>` (prints "all clean").
     The posting commands (`new`, `comment`, `title`, `body`, `close`) run the same scan themselves and refuse before
     any `gh` call. Commits pass `python scripts/security/scan_indexed_surfaces.py --commits origin/main..HEAD` (run
     with `git -C <worktree>` context: from the worktree root).
2. **No spend.** No LLM or network model call, no paid run, no cassette re-record. The checkout's `.env` holds live keys
   and the loaders read it: before running repository code that could build an LLM client, read that code. If a measure
   cannot be had for free, stop and report.
3. **Shell.** Never `cd <path>` and never `rm` inside a compound command. Use `git -C <absolute path>` and absolute paths.
   Delete only files you created, by name, one command each. Never `git checkout -- <file>`. Never force-push.
   Never `git checkout` / `git switch` / `git pull` in the main clone: a paid pipeline may run from it and the
   coordinator moves it. Code or doc changes go in a worktree under `.tmp/wt/`, created by an isolated
   `git worktree add .tmp/wt/<name> -b <branch> origin/main` command (after `git fetch origin`).
4. **GitHub writes.** `gh auth switch -u jsboigeEpita` immediately before every gh or git write. Push with an explicit
   refspec. Never merge. Never close or edit an issue or PR unless your brief says so. Prefer one bulk gh call to a
   per-item loop. For tracker posts, `scripts/coordination/post_tracker.py` does not switch anything globally: pass
   `--user <account>` and it injects that account's token into the environment of that single `gh` call, without
   displaying it.
5. **Python.** Run inside the most recent conda environment available on your seat — check `conda env list`, and see
   `docs/guides/DEV_ENV_SEATS.md` for what each seat holds. From the repository root:
   `conda run -n <env> --no-capture-output python ...`. Tests: `-m "not slow and not requires_api"`, at most `-n 4`,
   and read the `LLM egress (#1787)` line of the output before the pass count.
6. **Commits** are conventional, in English, and end with the `Co-Authored-By:` line required by the seat's harness.
   PR bodies end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
7. **Scratch** under `.tmp/` only.
8. **Figures.** Every figure you write was produced by a command you ran in this task, and the command is beside it.
   A figure you could not re-derive is written "reported, not re-verified", with its source.
9. **Prose for GitHub.** Plain sentences, one idea each. No arrows or symbols as connectors, no labels coined in your
   working notes, no emphasis words. Say what was measured, on what, with which command.
10. **Final message.** It is read by a coordinator short on tokens: at most 25 lines. What was done, what was not, file
    paths and URLs, and anything that needs a decision. No narrative of how you got there.
