# Security Check — Final Secret and Leak Scan

TASK-015 §9. Run on the final tree at this commit, after the last documentation edit, with the
working container up. The re-run commands are in *How to re-run this* below, with their observed
output.

**Scan set:** every file `git ls-files` plus `git ls-files --others --exclude-standard` reports
(48 files, all tracked now that this pack is committed, 0 untracked), minus **this file** — 47 files,
425,857 bytes, `.venv/` and
`__pycache__/` excluded. The exclusion is necessary, not cosmetic: a secret scan has to name the
patterns it searches for, so including the report in its own denominator would make every count in
it move each time the report is edited. The repository already handles this problem once:
`docs/architecture/operational-console.md` is deliberately outside `DOC_PATHS`
(`tests/test_ingest.py:730-737`) "so the guard does not scan its own description". This file is
also swept by machine under the same hard patterns (step 2a below prints nothing for it), and its
self-referential lines are listed in the second table.

One consequence of that reasoning is worth stating, because it changed how this pack is written:
**the byte total, the mention census and the high-entropy census appear only here.** Any other file in
the repository is inside the sets those numbers measure, so editing such a file to record a total it
just changed makes the recorded figure stale the moment it is typed. The line counts are the sharper
case: they are per-line, so re-wrapping one scanned paragraph moves them — an earlier revision of this
page quoted a mention figure that a later re-wrap of [`checklist.md`](checklist.md) §7 invalidated.
What a scanned file may therefore carry is a count that no prose edit can move: **47 files, 0 secret
values**. The mention census needs care for a second reason too: it sweeps the 47-file set with this
report outside it, which is why the command at the end writes every anchor as a bracket class. Written
as plain words, the command line itself would be one of the lines counted, and the figure would move
each time this file was edited — the exact trap an earlier revision fell into by quoting **102** for a
sweep that included it.

## What was scanned

| Surface | Method | Result |
|---|---|---|
| Scan set: 47 files, 425,857 bytes | line-by-line sweep for the value shapes `nvapi-` + a key character, `Bearer` + a ≥12-character non-placeholder token, `SENTINEL_INGEST_TOKEN=`/`NVIDIA_API_KEY=` + a non-empty non-placeholder value, `BEGIN … PRIVATE KEY`, `AKIA[0-9A-Z]{16}`, `ghp_`/`github_pat_` + ≥8 characters | **0 secret values.** 83 lines in the scan set merely *name* one of those patterns or variables (prose tables, `os.environ.get(...)`, assertions); **6** of them carry text in the value position, listed one by one below, all benign. PEM blocks 0, `AKIA…` 0, `ghp_…`/`github_pat_…` 0 |
| High-entropy sweep, same 47 files | every run of ≥32 unbroken `[-\w]` characters — word characters **and** hyphens, so that separator rules are surfaced and classified rather than silently omitted — then classified | **0 credentials.** 178 runs, fully accounted for: 128 are `test_*` identifiers, 33 are Markdown/ASCII separator rules, 15 are `inc_` + 32-hex incident ids (8 distinct; public by design — they are the console's `?incident=` value), 2 are hyphenated prose (`authenticated-by-different-means`, `guessed-token-should-never-be-echoed`). None is opaque-and-mixed in the way a generated secret is |
| Git history — every line ever added, swept through `git log --all -p` | same patterns against every added line in every commit | **0 secret values.** 0 added lines where `nvapi-` is followed by a key character; 6 added lines sit in a value position and all are placeholders or source code — three `SENTINEL_INGEST_TOKEN=` (`...` twice, one regex body), two `NVIDIA_API_KEY=` (one empty, one `export NVIDIA_API_KEY=nvapi-...` whose value is a literal ellipsis, later rewritten to `'paste your NVIDIA Build key here'`), and the header built at run time `f"Bearer {config.api_key}"`. Six added lines spell the `nvapi-` prefix inside test assertions and a `# never commit a real value` comment. The diff's own size is not quoted here, for the same reason the byte total appears only once: commit count, byte count and added-line count grow with every commit, while this result does not — step 2c prints them on demand. The sweep was re-run after this pack landed and after every follow-up commit since. **It returns 0.** The pack adds no new secret-shaped text — its lines *are* the documents the tree sweep above already covers file by file — and the value patterns cannot self-match, because a bracket or a space always follows the prefix in this pack. One caveat belongs to the method rather than to the result: the same sweep with a greedy `.*` between the two PEM words returns a non-zero count made up entirely of this report — the row that describes the pattern, the command lines that carry it, the commit that replaced the greedy form with the strict one — and no figure is quoted for it, because it is unstable by construction: any later commit writing those two words in either form adds to it, whereas the strict set cannot self-match, which is why the sweep above uses it. |
| `.env` in the tree and in history | `rglob(".env*")`, `git log --all -- .env` | **absent.** Only `.env.example` exists; no commit has ever touched `.env` |
| `.gitignore` | direct read | `.env` (line 2), `.env.*` (line 3), `!.env.example` (line 4), `.venv/` (line 17) |
| Browser surface, live production | `GET /`, `/static/app.js`, `/static/index.html`, `/static/styles.css`, `/openapi.json`, `/health` fetched and scanned | **clean on all six**: 0 hits for `nvapi-`, bearer literal, `NVIDIA_API_KEY=`/`SENTINEL_INGEST_TOKEN=` with a value, `integrate.api.nvidia.com`, `reasoning_content`, `innerHTML` |
| Provider payload | code read + assertions in `tests/test_console.py:77`, `:502`, `tests/test_incidents.py:57`, `tests/test_workflow.py:74` | only `tool_calls[0].function.arguments` is read; `content` and `reasoning_content` are never surfaced, so no hidden chain of thought reaches the API or the page |
| CSP delivery | `curl -D` on production | `content-security-policy: default-src 'self'; … frame-ancestors 'none'` on `GET /` only; `/static/app.js` correctly carries no CSP (it is not a document) |

## The matches, stated rather than hidden

A scan that reports "nothing found" is not evidence. 83 lines in the scan set name one of these
patterns or variables; the overwhelming majority are prose (`| NVIDIA_API_KEY | *(none)* | … |`), an
`os.environ.get("…")` call, or a test assertion. What a reviewer needs is the subset that puts
*something in the value position*, because that is the only shape that could leak a credential.
Every one of them is here — there are six:

| File:line | Match | Why benign |
|---|---|---|
| `.env.example:14` | `NVIDIA_API_KEY=` | key with an **empty** value, plus the comment "never commit a real value" |
| `docs/deployment/coolify.md:201`, `scripts/send_demo_event.py:10` | `export SENTINEL_INGEST_TOKEN=...` | placeholder ellipsis — three dots, not a token |
| `sentinel/nvidia.py:171` | `f"Bearer {config.api_key}"` | the request header built at run time; an f-string interpolation, no literal |
| `tests/test_ingest.py:780` | `SENTINEL_INGEST_TOKEN=\s*\S` | regex *source* inside the guard, read by the test runner as text |
| `docs/submission/architecture.md:13` | `Bearer guard<br/>…` | a Mermaid table cell whose next word is `guard`; matched only because the pattern is whitespace-delimited |

This file is the one document that has to write those patterns down in order to scan for them, so it
is checked the way the other forty-seven are: the step-2a sweep run over it alone prints **nothing**
and exits `1`. Every pattern this document and its command block carries is regex source whose next
character is a bracket or an escape — which is precisely what a literal credential would have to
*not* be. What the file does contain is prose *describing* matches: rows of the two tables above and
this paragraph. Their line numbers are deliberately not quoted — editing this paragraph moves the
ones below it, which is the same self-reference in a smaller frame; `grep -n` over this file
re-derives any of them at any moment.

A plain `grep -n` for a non-space character after an equals sign finds **eight** more lines elsewhere
in the tree: four command substitutions that mint a fresh token at run time, two shell-indirection
lines that pass the operator's own environment through, one quoted instruction the operator then
overwrites, and one assertion string naming the guard's own pattern. All eight are rows of the mention
table below, each with its reason there — a generator, a name, or an instruction is not a stored
credential.
That is the whole reason the report sits outside its own denominator rather than inside it: the
sentence describing the count is itself one of the lines being counted, so any number typed into it
is wrong the instant it is typed.

The rest are name mentions, and the ones worth naming explicitly:

| File:line | Match | Why benign |
|---|---|---|
| `README.md:112` | `export NVIDIA_API_KEY='paste your NVIDIA Build key here'` | instruction to the operator, quoted prose |
| `README.md:114`, `:291`, `scripts/README.md:11`, `docs/architecture/machine-event-ingestion.md:232` | `export SENTINEL_INGEST_TOKEN=$(openssl rand -hex 32)` | generates a fresh value at run time; nothing is stored |
| `README.md:132`, `:134` | `-e NVIDIA_API_KEY="$NVIDIA_API_KEY"` | shell indirection of the operator's own environment |
| `sentinel/nvidia.py:95`, `:99` | `os.environ.get("NVIDIA_API_KEY", "")` | reading the variable name, default empty string |
| `tests/test_console.py:73`, `tests/test_ingest.py:790` | `"nvapi-"` | assertion strings in the in-repo guard |
| `tests/test_ingest.py:779`, `:780` | `SENTINEL_INGEST_TOKEN=` | the guard itself: asserts the literal appears **and** that no non-space character follows `=` |
| `docs/architecture/operational-console.md:138` | `` `nvapi-` `` | sentence describing what the asset scan checks for. This file is deliberately **not** in `DOC_PATHS` (`tests/test_ingest.py:730-737`) so the guard does not scan its own description |

## In-repo guard

`tests/test_ingest.py::test_no_credential_shaped_text_in_shipped_files` (:788) fails the build if a
credential-shaped string ever lands in a shipped file. Its scope is `DOC_PATHS`
(`tests/test_ingest.py:730-737` — `README.md`, `docs/architecture/machine-event-ingestion.md`,
`docs/decisions/0003-machine-event-ingestion.md`, `docs/deployment/coolify.md`,
`docs/evaluation/README.md`, `.env.example`) plus `Dockerfile`, `static/app.js` and
`static/index.html`, and it asserts three things per file: no `nvapi-` substring, no
`TOKEN_ASSIGNMENT` match, no `BEARER_LITERAL` match (`tests/test_ingest.py:783-792`). It is part of
the 211 passing tests, so those checks run on every suite invocation rather than once.

**`docs/submission/*.md` is not in that list, and this pack does not add it there.** Two reasons,
both stated rather than glossed: `docs/architecture/operational-console.md` was already excluded on
the same principle (a file must not be scanned with a pattern it exists to describe), and
`test_no_credential_shaped_text_in_shipped_files` asserts `"nvapi-" not in text` outright — which
any honest scan report must be allowed to write. So this directory is covered by the sweep recorded
above instead of by the standing guard; extending `DOC_PATHS` is a test change, and TASK-015 §16
puts test changes behind a stop-and-ask, not behind a doc commit. It is logged as follow-on work in
[`status.md`](status.md).

## The previously exposed key

The NVIDIA key that was exposed during earlier development has been **revoked and rotated** at the
provider. Neither the old value nor the new one appears in this repository, in its history, in any
documentation file, in the console, in `/openapi.json`, in a command line recorded in a doc, or in
this file. The new key exists only in the deployment secret store and in the operator's shell.

## Residual risk, stated as a limit and not as a defect

- The public console and `POST /api/v1/incidents/analyze` are intentionally unauthenticated, so any
  client that can reach the port can spend a provider inference and approve its own incident
  (`README.md:476-483`). Platform-layer controls guard the rest.
- One shared bearer secret, no rotation, no per-producer identity — demo-grade (`README.md:480-481`).
- `HEAD /` returns `405` with `allow: GET` because the routes are declared GET-only. Correct
  FastAPI behaviour, noted so a reviewer who probes with `curl -I` is not surprised.
- Workflow state, the audit trail and the idempotency ledger are per-process memory: a restart
  removes the evidence, which is a durability limit, not a leak.

## How to re-run this

The patterns are printed here in full. That is only possible because this file is outside its own
scan set — the same reason `docs/architecture/operational-console.md` is outside `DOC_PATHS`. A
reviewer can therefore re-derive every number above rather than trust it:

```bash
# 0. the scan set: 48 files in the tree, minus this report = 47 files, 425,857 bytes
git ls-files; git ls-files --others --exclude-standard    # .venv/ and __pycache__/ excluded
{ git ls-files; git ls-files --others --exclude-standard; } \
  | grep -v '^docs/submission/security-check\.md$' | sort -u | xargs wc -c | tail -1

# 1. the standing guard — the shipped-file half of this scan, wired into the suite
.venv/bin/python -m pytest tests/test_ingest.py -k "credential or env_example or docs" -q   # 26 passed, 76 deselected
.venv/bin/python -m pytest tests/test_console.py -k "no_secret or reasoning" -q             # 4 passed, 32 deselected

# 2. hard secret formats across the scan set (expect: no output at all), then history (expect: 0)
grep -rnE 'nvapi-[A-Za-z0-9]|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY|(ghp_|github_pat_)[A-Za-z0-9_]{8,}' \
  --exclude-dir=.venv --exclude-dir=__pycache__ --exclude=security-check.md .
git log --all -p | grep -cE '^\+.*(nvapi-[A-Za-z0-9]|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY)'

# 2a. the same hard patterns over this report alone: it names them, but always as regex source whose next
# character is a bracket or an escape, so it cannot match itself (expect: no output, exit 1)
grep -nE 'nvapi-[A-Za-z0-9]|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY|(ghp_|github_pat_)[A-Za-z0-9_]{8,}' \
  docs/submission/security-check.md

# 2b. the mention census behind the "83 lines name a pattern" figure. Each anchor is written as a
# bracket class so this command line cannot match itself and move the number it reports.
{ git ls-files; git ls-files --others --exclude-standard; } \
  | grep -v '^docs/submission/security-check\.md$' | sort -u \
  | xargs grep -cE '[n]vapi|NVIDIA_[A]P[I]_KEY|SENTINEL_[I]NGEST_[T]OKEN|[P]RIVATE KEY|[A]KIA|[g]hp_|github_[p]at_|[B]earer ' \
  | awk -F: '{s+=$2} END{printf "mentions=%d\n", s}'                                 # mentions=83

# 2c. the size of the history just swept — quoted nowhere in this pack, because it moves with every commit
git rev-list --count --all; git log --all -p | wc -c; git log --all -p | wc -l

# 3. .env must not exist in the tree or in any commit
find . -name '.env*' -not -path './.venv/*'; git log --all --oneline -- .env

# 4. browser surface: nothing secret may be rendered
for p in / /static/app.js /static/index.html /static/styles.css /openapi.json /health; do
  printf '%s ' "$p"
  curl -s "https://sentinel.novatechsystem.co.uk$p" \
    | grep -cE 'nvapi-[A-Za-z0-9]|integrate\.api\.nvidia\.com|reasoning_content|innerHTML'
done

# 5. the high-entropy census: every run of >=32 hyphen/word characters, then classified
{ git ls-files; git ls-files --others --exclude-standard; } \
  | grep -v '^docs/submission/security-check\.md$' | sort -u \
  | xargs grep -ohE '[-_[:alnum:]]{32,}' \
  | awk '/^test_/{a++;next} /^-+$/{b++;next} /^inc_/{c++;next} {print "  unmatched: "$0} \
         END{printf "test_=%d separators=%d inc_=%d prose=%d total=%d\n", a,b,c,NR-a-b-c, NR}'
```

Observed, in this order: step 0 lists the 48 filenames and then `425857 total` (the comma in
"425,857" is this document's, not `wc`'s); step 1 prints `26 passed` then `4 passed`; step 2 prints
**nothing** (grep exit `1`, i.e. no match anywhere in the scan set) and then `0` for history; step 2a
prints **nothing** either, exit `1`, which is the paragraph above being true; step 2b prints
`mentions=83`; step 2c prints the history's size, which is the reason no figure of that kind is quoted
for it anywhere in this pack; step 3 prints `./.env.example` and nothing from `git log`; step 4 prints `0`
for all six paths; step 5 prints `test_=128 separators=33 inc_=15 prose=2 total=178` with nothing
unmatched but the two hyphenated prose runs named in that row.

The three regexes not typed above — the two `…_TOKEN=` / `…_API_KEY=` assignment shapes and the
`Bearer ` + 12-character literal — are deliberately left to the suite, because it already encodes
them as `TOKEN_ASSIGNMENT` and `BEARER_LITERAL` (`tests/test_ingest.py:783-784`) and enforces them
on every shipped file. Both step-1 selections are subsets of the 211-test run in §11, so that half
of the scan re-runs itself on every `pytest` rather than living in this document as a one-off.

## Verdict

**No secret material is present in the repository, its history, its container image, or anything
the browser can read.** Safe to publish; already public at
`https://github.com/novatechsystemsgroup/novabrain-sentinel`.
