# anything2explainer-lite

**English** | [简体中文](README_zh.md)

> **Topic in, narrated explainer video out.** A black-canvas motion-graphics explainer with TTS voiceover, word-aligned subtitles and a chapter progress bar, in Chinese or English — every frame drawn in code with Remotion / React.
>
> This is the **low-cost tier** of [`anything2explainer`](https://github.com/Vincentwei1021/anything2explainer): **−76% read-list cost, −99.8% image-replay cost**. All of those savings come from "the same image being re-read over and over", and the side effect is that aesthetic feedback becomes **open-loop** — so the tier pays it back with **four zero-image machine gates**.

> [!IMPORTANT]
> **This repository is an unofficial derivative of `anything2explainer` and is not endorsed by its author.**
> Upstream is licensed under **PolyForm Noncommercial 1.0.0**: free for noncommercial use; **commercial use of the toolkit itself requires prior authorization from the upstream author**. Relicensing, resale and sublicensing are not permitted. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Videos you produce with the toolkit belong to you.

---

## 1. What this is

**What it does**: give it a topic, get a finished MP4. Every intermediate artifact is on disk too — research brief → storyboard → per-shot TSX source → TTS voiceover → subtitles → a four-axis gate report.

**How it fits in**: upstream `anything2explainer` is a high-quality toolkit, but **every build group has to read 39,478 tokens** of protocol files per dispatch, and the genuinely expensive part is **image replay**: 15 shots, 6 full-size stills per shot, read while coding — **8,295,750 tokens** in total.

**What this tier does**: cut both of those bills, without leaving quality to chance — replacing the discarded human eye with machine gates.

**It is also a Windows-friendly port**: upstream's five shell scripts are `#!/bin/zsh` (depending on `rsync`, BSD `sed` and zsh arrays); here they are equivalent Python implementations, with the `.sh` names kept as thin compatibility entries. See [`WINDOWS-PORT.md`](WINDOWS-PORT.md).

**What it is not**:

- Not an official slim build — every change is itemised in [NOTICE](NOTICE) §1;
- Not a stripped-down everything: the gates only **grow** (4 axes vs upstream's 3);
- Not good at vertical 9:16 (the whole tier assumes 1280×720 landscape);
- Does not guarantee aesthetic parity with upstream (see [§8 Known limits](#8-known-limits-must-be-told-to-the-user)).

---

## 2. Where the savings come from (three levers)

| # | Lever | Upstream C0 | This tier | Mechanism |
|---|---|---|---|---|
| **A** | **Dispatch read list** | 5 reference docs + the **whole** `ui.tsx` + `fx.tsx` + **the whole project**<br>**39,478 tok / group** | `build-contract-lite.md` + `api-index` + `common-api` + `types.ts` + **3 slices for this group**<br>**8,833–9,412 tok / group** | Instead of "read everything, then start", read the **contract plus your own slices**. A build group does not need to know what the other groups are drawing |
| **B** | **Looking at images (stills)** | scale 1.0 (1280×720) · **6 per shot** (≥10 for hero shots) · **read while coding** | scale 0.25 (320×180) · **2 per shot** · **read once, at the tail of the lifecycle** | In ledger B the expensive thing is **not image area, it is "how many turns remain after you read it"**. C0 is 75 turns (each image is re-billed across the following 75 turns); this tier is 8 turns → **appending an image at the tail is 9.4× cheaper than at the start** |
| **C** | **Buying quality back** | — | **Four zero-image gates** + three hard rules | What got cut was the human eye, so: **turn the geometric facts that only an image could reveal into numbers readable in the source** |

Lever C deserves its own line:

> **Occlusion should not be solved by "seeing it clearly" — it should be solved by "computing it".** And computing it is a **text** cost, two to three orders of magnitude cheaper than images.

---

## 3. Measured results (instrumented by `measure.py`)

> **Sample caveat**: every number below comes from the same control film, *"Why does the HTTPS (TLS 1.3) handshake need only one round trip?"* (**15 shots · 1280×720 / 30 fps · 3 build groups**), with both tiers measured over the same files by the same `measure.py`. **This is not a general benchmark you can assume for any topic**, though group slicing is linear, so the order of magnitude extrapolates.

### Ledger A — protocol read list (tokens per dispatch, once per group)

| | G1 | G2 | G3 | Whole film | vs C0 |
|---|---|---|---|---|---|
| Upstream C0 | 39,478 | 39,478 | 39,478 | **118,434** | — |
| This tier, as measured (C2F) | 8,833 | 9,412 | 9,301 | **27,546** | **−77%** |
| + gate rules (criterion 260 + ruler 60 + audit report 170) | 490 | 490 | 490 | 1,470 | — |
| **This tier + optimisation** | 9,323 | 9,902 | 9,791 | **29,016** | **−76%** |

Budget is 11,500/group → all three groups pass (headroom 2,088 / 2,199 / 2,667), and the cost is **close to linearly additive** (all three running the tier at once does not degrade through cross-group coupling).

### Ledger B — image replay cost (15 shots, whole film)

| Accounting | Raw image tok | Replay turns | Total tok | vs C0 |
|---|---|---|---|---|
| Upstream C0 (6 full-size stills/shot, read while coding) | 110,610 | 75 | **8,295,750** | — |
| **This tier (2 × 0.25 stills/shot, read at the tail)** | 2,310 | 8 | **18,480** | **−99.8%** |

**Both ledgers together**: read list **−76%**, image replay **−99.8%**. And turning occlusion back into a defect the gate can catch cost only **+5.3%** of ledger A and **zero** of ledger B.

### Quality side — nothing caved in

| Metric | Upstream C0 | This tier (C2F) |
|---|---|---|
| Sustained motion (mean still ratio / longest still) | 14.3% / 0.9 s | **6.7% / 0.5 s** (better) |
| `frame_metrics` high/med/low | 1 / 0 / 13 | **1 / 0 / 10** (3 fewer low) |
| Per-shot improved / regressed / unchanged | — | **5 / 3 / 7** (net improvement) |
| Reused C0 frames | — | **14.6% (shell layers only)** → independently produced |
| `zorder_audit` (15 shots) | axis does not exist upstream | **2 true positives (both "high") / 14 shots clean** |

---

## 4. How quality is protected: four zero-image gates

| Gate | What it catches | Cost |
|---|---|---|
| `zorder_audit.py` | **Inverted layer order** (a later-entering element covered by an earlier opaque block), text overlap within a frame, and **auditable coverage** | zero image tokens, seconds |
| `selfcheck.py` | frame coverage holes, flicker-whitelist overflow, on-screen literals contradicting the facts, storyboard drifting from source | zero image tokens |
| `frame_metrics.py` | pixel readings for hero ink / glow / stray purple fragments | zero image tokens |
| `lite_gate.py` | **runs all four axes in one command and returns one exit code**, making it structurally impossible to skip an axis | zero image tokens |

Plus three new hard rules (`reference/build-contract-lite.md` §12–§14):

1. **Layer-order discipline** — enter order = draw order (source order is screen stacking order; no `z-index` in this tier);
2. **Coordinates must be literals** — no `x={fn()}` / `cx={MAP[i].cx}`; this is the **precondition for auditability**;
3. **Delivery must report** — hero ink box / max overlap / Z1·Z2 hits go into `BUILD_NOTES.md`.

**Worked example (a real hit)**: at 23.0 s of SC06, the later-entering hero "TLS 1.3" is covered by the earlier-entering paper card — 39×150 px = 5,850 px² of ink overlap. Pixel verification: ink in that band drops from 54.3% to 1.3% (−53 pp, while a control band inside the glyphs differs by only 1.2 pp). The auditor not only reports it — it tells you **how many pixels to move**.

**Honest gate design**: `lite_gate.py` treats rc=1 (fail) and **unknown** alike as failure; `zorder_audit` reports "insufficient coverage" instead of a fake pass when coverage < 90%. "Not run" is a **distinct state**, not a pass.

---

## 5. Quick start

```bash
# 0) verify the install (no external dependencies; should print "独立性自检通过 ✓")
python scripts/lite_bootstrap.py --check

# 1) scaffold a project (copy engine → npm install → tsc)
python scripts/lite_bootstrap.py D:/a2e/my-video myvideo

# 2) follow the five-stage flow in SKILL.md (main session orchestrates, build groups run in parallel)
#    a dispatch hands over only 6 files (see reference/prompts-lite.md §0)

# 3) run the gate before closing every group (zero image cost, a few seconds)
python scripts/zorder_audit.py src/shots --gate

# 4) after the final render, run the four-axis gate (rc=1 must not be delivered)
python scripts/lite_gate.py --require-final
```

**Environment notes**

- On Windows **do not use `python3`** (it may resolve to the Microsoft Store stub); point at your venv interpreter, or set `A2E_PYTHON`;
- Keep the project on a **short path** (e.g. `D:/a2e/xxx`) — `node_modules` will hit the 260-character `MAX_PATH`;
- Leave **≥5 GB** of disk;
- `npm install` pulls Remotion (see [License & credits](#9-license--credits)).

**Fully standalone**: download and use — no other skill required. The engine (a 17.6 MB Remotion project), example assets (the full reference-film paper trail plus counter-examples), reference docs and gate scripts are all bundled.

---

## 6. Repository layout

```
anything2explainer-lite/
├── SKILL.md                    ← entry point: five-stage flow, gates, rollback criteria, residual risks
├── scripts/
│   └── lite_bootstrap.py       ← scaffold + standalone self-check (the only command you run by hand)
├── reference/
│   ├── build-contract-lite.md  ← mandatory for build groups (full hard-constraint set + §12–§14)
│   ├── qc-lite.md              ← four-axis gate / rollback criteria / coverage matrix / human review list
│   ├── prompts-lite.md         ← dispatch templates for build / fix / final check
│   ├── lessons-lite.md         ← must-read lessons, occlusion-first
│   ├── ENGINE.md               ← bundled-file manifest / self-check / maintainer sync notes
│   └── style-guide.md · motion-vocabulary.md · composition-and-light.md
│       narration-storyboard.md · research-brief.md · common-api.md
│       prompts.md · lessons.md ← stage 1–4 general specs + the full lesson log
├── template/                   ← bundled engine (Remotion 4 project)
│   ├── src/                    ← primitives / lighting / overlay / common / shots (only shots change)
│   ├── scripts/                ← 22 tools, including zorder_audit.py and lite_gate.py
│   └── public/fonts/           ← four fonts + their OFL license (do not delete: the ruler needs real fonts)
├── examples/
│   ├── rag/                    ← the reference film's full paper trail (shots_src · frames · storyboard · QC)
│   └── contrast/               ← 6 bad/good frame pairs (the aesthetic yardstick)
├── LICENSE · NOTICE · CITATION.cff
│                               ← upstream license / redistribution notice + change log (do not delete)
├── WINDOWS-PORT.md             ← Windows port notes (upstream is zsh/rsync; this tier uses .py)
└── UPSTREAM_README*.md         ← upstream READMEs, archived verbatim (they describe the full tier)
```

---

## 7. How it relates to the full tier

| | Full tier `anything2explainer` | This tier (lite) |
|---|---|---|
| Read list per group | 39,478 tok | **8,833–9,412 tok (−76%)** |
| Stills per shot | 6 full-size (≥10 for hero) | **2 at scale 0.25** |
| When images are read | while coding (closed loop) | **at the tail of the lifecycle (open loop)** |
| Gates | 3 axes | **4 axes** (adds `zorder_audit`) |
| Engine | bundled | bundled (inside this package) |
| License | PolyForm NC 1.0.0 | same (derivative) |

**When to switch to the full tier**: quality first, cost no object · extremely high visual complexity that needs heavy aesthetic iteration (this tier's aesthetic feedback is open-loop).

`reference/ENGINE.md §5` holds the maintainer **sync script** (pulls the upstream engine / examples / general docs without overwriting this tier's `*-lite.md`).

---

## 8. Known limits (**must be told to the user**)

1. **Aesthetic feedback is open-loop** — build groups never see full-size stills, so **prior-driven** defects like "the detail is not refined enough" survive more often than in the full tier.
2. **Pixel-level occlusion is invisible to the gate** — `zorder_audit` reasons about **geometric intersection**; pixel-level problems such as "a soft glow washing out a neighbouring element" (e.g. a large purple glow forming a solid ring on an object's edge) are **unverified**.
3. **Coverage depends on code style** — measured auditable coverage is **74.0%** (37 resolved / 50 content objects); the blind spots are non-literal coordinates such as object property access, which is exactly the disease §13 ("coordinates must be literals") exists to cure. When coverage is short the gate **errors out** rather than passing (by design).
4. **Subtitle wrapping / pacing / A-V sync** have no machine axis and must be reviewed by a human (checklist: `reference/qc-lite.md` §6).

---

## 9. License & credits

**Upstream license: PolyForm Noncommercial 1.0.0** (full text in [`LICENSE`](LICENSE)).

| Question | Answer |
|---|---|
| Noncommercial use (individual / teaching / research / non-profit) | ✅ free |
| **Copying and redistributing** (including modified versions) | ✅ allowed, **must ship** `LICENSE` and the `Required Notice` line |
| Videos you produce with the toolkit | ✅ yours |
| Commercial use of the **toolkit itself** | ⚠️ requires prior authorization from the upstream author |
| Relicensing (e.g. to MIT) / resale / sublicensing | ❌ not permitted (no sublicense right) |

So: **this repository may be public and may be redistributed**, provided `LICENSE`, `NOTICE`, `CITATION.cff` and `template/public/fonts/LICENSE.md` are kept unmodified and undeleted, and the repo does not claim MIT or any other license. The itemised list of changes is in [`NOTICE`](NOTICE) §1.

- Upstream: <https://github.com/Vincentwei1021/anything2explainer> (**unofficial derivative, not endorsed**)
- **Remotion is not redistributed here**: `node_modules/` is excluded by `.gitignore` and installed by the user at bootstrap time. Remotion carries its own license (free for individuals, non-profits and for-profit organisations with up to 3 employees; larger for-profit organisations need a Company License — see <https://www.remotion.dev/license>), which each user must comply with themselves.
- The four bundled fonts (Noto Sans SC / Orbitron / Exo 2 / Audiowide) are **SIL OFL 1.1** (see `template/public/fonts/LICENSE.md`, do not delete); they may be redistributed with this package, may not be sold on their own, and modified versions may not use the Reserved Font Names.
- Frame images under `examples/` are stills from the upstream reference film; they may travel with this package but must **not** be reused as stock footage or as an asset pack.
- The visual language is inspired by the Douyin creator @图灵宇宙; the **style is a homage, every frame is drawn in code**, and no frames or clips from any existing video are used.
