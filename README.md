# AltWitness

A standalone GenLayer Intelligent Contract for checking whether a short **alt-text description makes claims supported by one pinned public image**. A caption can be syntactically valid and still call an apple a bicycle. A hash can identify the image bytes, but cannot judge the meaning of the text. AltWitness records a bounded, validator-reviewed image/text observation and keeps corrections as separate immutable revisions.

**Status:** v2 deployed and exercised on GenLayer Studionet (chain `61999`). Five transactions finalized with successful GenVM execution, including two full-consensus reviews of the same PNG: `CLAIMS_CONTRADICTED` for a false caption and `CLAIMS_SUPPORTED` after a creator revision. A prior v1 JPEG attempt failed with `INVALID_IMAGE` and an undetermined transaction; it was **not** a visual verdict. GenVM lint, semantic validation, type checking and **54 Direct Mode tests** with mocked web/vision responses passed locally. Direct Mode tests are separate from the live receipts below.

## Decision boundary

The creator fixes a public direct JPEG/PNG URL, its expected lowercase SHA-256 digest, and a 10–180-character alt text. The contract recognizes only small images served from `upload.wikimedia.org` or a full-commit path on `raw.githubusercontent.com`. It accepts no local paths, mutable GitHub branch references, HTTP URLs, credentials, query strings, or caller-chosen model output. Anyone may trigger a review after the record is opened.

| Status | Meaning |
| --- | --- |
| `CLAIMS_SUPPORTED` | The principal subject described in the alt text matches the image and no asserted visible detail was found unsupported. **Not** a claim that the alt text is complete or WCAG-compliant. |
| `CLAIMS_CONTRADICTED` | The named subject or an asserted visible detail disagrees with the image. |
| `NEEDS_REVIEW` | The subject or an asserted detail could not be judged reliably. Silence is not confirmation. |
| `IMAGE_CHANGED` | The retrieved image differs from the creator's expected SHA-256. No visual judgment is trusted. |
| `SOURCE_UNAVAILABLE` | The image was unreachable, too large, or not a bounded JPEG/PNG. This is not treated as `CLAIMS_CONTRADICTED`. |
| `VISION_UNAVAILABLE` | Exact image bytes were fetched, but the vision decoder or model could not run. The digest and size are retained; no alt-text verdict is inferred. |

A vision invocation failure produces `VISION_UNAVAILABLE` only if validators agree on the same bytes and failure state. A malformed model response **reverts** rather than becoming a source error or a positive verdict. Revisions cannot overwrite a prior assessment: the original creator can append at most three new alt texts under the same image URL and expected hash. The latest pointer follows the newest version, including an unreviewed draft; older receipts remain readable.

## GenLayer consensus, not an image-caption bot

`review` copies the frozen URL, hash and alt text from storage into plain Python values. Inside a single non-deterministic block, the leader fetches the image and verifies its HTTP result, length, JPEG/PNG signature and exact SHA-256 **before** asking a vision-capable model to assess two closed axes: principal subject and additional visible claims (such as color or action). Its JSON result is checked for exact fields and bounded, literal alt-text spans. Those spans show *what text was judged*, not proof that the pixels support it.

Each validator independently fetches the image and re-runs the vision assessment. The custom equivalence check requires the **same source state, entire image digest, byte size and main-subject classification**. For details, it must agree on the action-bearing family: contradiction, uncertainty, or no contradiction. `MATCH` and `NOT_CLAIMED` are equivalent **only** when both are nonblocking; disagreement that would change the final outcome is rejected. The code, not the model, derives the stored status. A wrong hash, false quote, omitted field or forged positive cannot pass the full packet check merely by looking like valid JSON.

The two linked Studionet reviews use the *same* publicly hosted PNG, with a plainly wrong alt text followed by an owner-authored correction. No image pixels are persisted onchain. A positive verdict is a consensus-backed reading of public pixels under this narrow rubric, not objective or legal proof of accessibility.

## State and public methods

Lifecycle: `DRAFT -> CLAIMS_SUPPORTED | CLAIMS_CONTRADICTED | NEEDS_REVIEW | IMAGE_CHANGED | SOURCE_UNAVAILABLE | VISION_UNAVAILABLE`. From a reviewed latest version, its creator can append a new `DRAFT` child with corrected alt text; no prior result is edited. A failed or undecided GenLayer transaction stores no result.

| Method | Function |
| --- | --- |
| `open(image_url, expected_sha256, alt_text)` | Create the first immutable draft; caller becomes owner. |
| `review(record_id)` | Permissionlessly collect independent image/vision observations and finalize one draft. |
| `revise(record_id, new_alt_text)` | Owner appends one version after reviewing the current head; original image URL and digest remain frozen. |
| `get_record(record_id)` | Read a numbered version as JSON or return an empty string. |
| `get_latest(root_id)` | Read the most recent version, including an unreviewed correction. |
| `count()` | Number of versioned records. |

All record text and URLs are **public**. Do not use private images, confidential alt text or secret credentials.

## Local verification

From this repository root (Python 3.12+):

1. `python3 -m venv .venv`
2. `source .venv/bin/activate` (PowerShell: `.venv\Scripts\Activate.ps1`)
3. `python -m pip install -r requirements-dev.txt`
4. `python scripts/prepare_test_sdk.py`
5. `genvm-lint check contracts/alt_witness.py`
6. `genvm-lint typecheck contracts/alt_witness.py`
7. `python -m pytest tests -q`

Keep the environment activated for the helper script; it works around an upstream GenVM release-asset name mismatch, and does not patch contract code. Direct Mode tests execute the actual contract with **mocked** web bytes and vision answers. They cover owner-only revisions, append-only history, separate web/vision/hash failures, a generated CRC-correct PNG, malformed model outputs, forged leaders, harmless validator variation and verdict-changing disagreement. A mocked vision answer is **not** proof that a live image decoder or model will work; the actual full-consensus reviews are linked below.

## Live Studionet evidence

The v2 contract is [`0x5a65684b773E104656aA0696A41C7f7D7F8B48eC`](https://explorer-studio.genlayer.com/address/0x5a65684b773E104656aA0696A41C7f7D7F8B48eC), chain `61999`. All five v2 transactions below reached **FINALIZED**, GenVM **SUCCESS**, accepted consensus and `0 GEN` transferred. Both visual reviews ran in Normal (Full Consensus) mode with five initial validators and **one leader rotation each**; this does not mean five unanimous votes.

| Action | Explorer transaction | Observed result |
| --- | --- | --- |
| Deploy v2 | [`0x152321ed...4aca2365`](https://explorer-studio.genlayer.com/tx/0x152321ed7de60f5a7c26db39e7bfb9df75d627e67be08261498e44204aca2365) | New contract, no constructor inputs. |
| Open wrong text | [`0x5642bdd0...622deb88`](https://explorer-studio.genlayer.com/tx/0x5642bdd08d99e873e924c2f6369b04bbc4df521d3d1c42cfa8dfb4bd622deb88) | Pinned public PNG and `A blue bicycle.`; record `0`. |
| Review record `0` | [`0xd9c8b9d9...11ee9145`](https://explorer-studio.genlayer.com/tx/0xd9c8b9d943ecb707816b5c5ce5e67cc82d50ea8a55417958e76ccfe011ee9145) | `CLAIMS_CONTRADICTED`; subject `MISMATCH`, literal span `blue bicycle`. |
| Owner revises | [`0xf2f40afe...0aafe8bc`](https://explorer-studio.genlayer.com/tx/0xf2f40afe81c6cb75c7e62feb16e86a51bad0ccc0a63afadc3394d3ef0aafe8bc) | Corrected text `A red apple.`; child record `1` under root `0`. |
| Review record `1` | [`0xbd700509...b48d330e`](https://explorer-studio.genlayer.com/tx/0xbd700509f9de1a446ed1c7c6b479957fd3511c5832a829bed164e404b48d330e) | `CLAIMS_SUPPORTED`; subject `MATCH` (`apple`), detail `MATCH` (`red`). |

Both visual receipts bind the same fetched PNG: **129,907 bytes**, SHA-256 `d35f121064e43255730fe9361a504421bbbeb8770e929a542b798cc4a9450c43`. Studio **Finalized** reads confirmed `get_latest("0")` points to the supported revision `1` while `get_record("0")` still returns the original `CLAIMS_CONTRADICTED` record. The asset is the [330-pixel Red Apple edit.png thumbnail](https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Red_Apple_edit.png/330px-Red_Apple_edit.png) on [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Red_Apple_edit.png); photograph by Abhijit Tembhekar, background edit by Afanasovich (CC BY 2.0). We reference the public image; no binary is included in this repository.

**Earlier failed attempt, not a successful review:** the separate [v1 contract](https://explorer-studio.genlayer.com/address/0xa81e063D7b235682A33aC3A4172e1e1ea8209EB2) tried a different JPEG thumbnail. Its [`review("0")`](https://explorer-studio.genlayer.com/tx/0x82cb925eb3e848a2cb03b6eb9b4cb006bfb964717dc104a59344e3eb94eb4b61) transaction was FINALIZED but consensus **Undetermined** and GenVM **ERROR / INVALID_IMAGE**; it stored **no visual verdict**. The v2 source handles a failed vision invocation separately from HTTP failure; v2's `VISION_UNAVAILABLE` branch has **local tests only**, not a live receipt. Do not cite v1 as a passing image review.

Studio stored v2 source with CRLF and no final newline. It is **not raw-byte-equal** to the GitHub source; after normalizing only those line endings, the source texts match exactly. See [docs/DEPLOY.md](docs/DEPLOY.md) for both generations, full transaction hashes, source hashes, tests and limitations.

## Related work and limits

[AltCheck](https://github.com/huzyow155/alt-check-genlayer) audits a web page's HTML accessibility signals and alt-text clarity, and states it does **not** inspect image pixels. [Multimodal Acceptance Matrix](https://github.com/halihalibt/multimodal-acceptance-matrix-genlayer) judges visual deliverables against a general frozen brief. AltWitness is narrower: **claim alignment between a pinned image and its alt text**, with an append-only correction history. It does not copy either project's code or claim this is the first image-caption checker.

An alt text can be factually aligned but still unhelpful in context. This contract does not assess the image's purpose in a page, screen-reader experience, missing essential information, visual bias, ownership, licensing, deepfakes, safety, or WCAG conformance. Validators can agree on a mistaken visual reading; prompt injection and source/decoder differences remain risks. The allowlist is a limited egress policy, not proof that every DNS answer or redirect stays public. See [docs/DESIGN.md](docs/DESIGN.md) for the exact trust boundary and test matrix.

License: MIT. See [LICENSE](LICENSE).
