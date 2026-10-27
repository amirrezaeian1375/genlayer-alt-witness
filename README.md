# AltWitness

A standalone GenLayer Intelligent Contract for checking whether a short **alt-text description makes claims supported by one pinned public image**. A caption can be syntactically valid and still call an apple a bicycle. A hash can identify the image bytes, but cannot judge the meaning of the text. AltWitness records a bounded, validator-reviewed image/text observation and keeps corrections as separate immutable revisions.

**Status:** local prototype only. GenVM lint, semantic validation and type checking passed; **52 Direct Mode tests** passed with mocked web and vision responses. Studionet's read-only source preflight recognized six public methods. There is **no deployment or live full-consensus receipt yet**. Direct Mode is not evidence that real image validators agreed.

## Decision boundary

The creator fixes a public direct JPEG/PNG URL, its expected lowercase SHA-256 digest, and a 10–180-character alt text. The contract recognizes only small images served from `upload.wikimedia.org` or a full-commit path on `raw.githubusercontent.com`. It accepts no local paths, mutable GitHub branch references, HTTP URLs, credentials, query strings, or caller-chosen model output. Anyone may trigger a review after the record is opened.

| Status | Meaning |
| --- | --- |
| `CLAIMS_SUPPORTED` | The principal subject described in the alt text matches the image and no asserted visible detail was found unsupported. **Not** a claim that the alt text is complete or WCAG-compliant. |
| `CLAIMS_CONTRADICTED` | The named subject or an asserted visible detail disagrees with the image. |
| `NEEDS_REVIEW` | The subject or an asserted detail could not be judged reliably. Silence is not confirmation. |
| `IMAGE_CHANGED` | The retrieved image differs from the creator's expected SHA-256. No visual judgment is trusted. |
| `SOURCE_UNAVAILABLE` | The image was unreachable, too large, or not a bounded JPEG/PNG. This is not treated as `CLAIMS_CONTRADICTED`. |

A model error or malformed output **reverts** rather than becoming `SOURCE_UNAVAILABLE` or a verdict. Revisions cannot overwrite a prior assessment: the original creator can append at most three new alt texts under the same image URL and expected hash. The latest pointer follows the newest version, including an unreviewed draft; older receipts remain readable.

## GenLayer consensus, not an image-caption bot

`review` copies the frozen URL, hash and alt text from storage into plain Python values. Inside a single non-deterministic block, the leader fetches the image and verifies its HTTP result, length, JPEG/PNG signature and exact SHA-256 **before** asking a vision-capable model to assess two closed axes: principal subject and additional visible claims (such as color or action). Its JSON result is checked for exact fields and bounded, literal alt-text spans. Those spans show *what text was judged*, not proof that the pixels support it.

Each validator independently fetches the image and re-runs the vision assessment. The custom equivalence check requires the **same source state, entire image digest, byte size and main-subject classification**. For details, it must agree on the action-bearing family: contradiction, uncertainty, or no contradiction. `MATCH` and `NOT_CLAIMED` are equivalent **only** when both are nonblocking; disagreement that would change the final outcome is rejected. The code, not the model, derives the stored status. A wrong hash, false quote, omitted field or forged positive cannot pass the full packet check merely by looking like valid JSON.

The two live paths planned for demonstration use the *same* publicly hosted image, with a plainly wrong alt text followed by an owner-authored correction. No image pixels are persisted onchain. A positive verdict is a consensus-backed reading of public pixels under this narrow rubric, not objective or legal proof of accessibility.

## State and public methods

Lifecycle: `DRAFT -> CLAIMS_SUPPORTED | CLAIMS_CONTRADICTED | NEEDS_REVIEW | IMAGE_CHANGED | SOURCE_UNAVAILABLE`. From a reviewed latest version, its creator can append a new `DRAFT` child with corrected alt text; no prior result is edited. A failed or undecided GenLayer transaction stores no result.

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

Keep the environment activated for the helper script; it works around an upstream GenVM release-asset name mismatch, and does not patch contract code. Direct Mode tests execute the actual contract with **mocked** web bytes and vision answers. They cover owner-only revisions, append-only history, hash/source failures, invalid model outputs, prompt fields, forged leaders, harmless validator variation and verdict-changing disagreement. Synthetic JPEG-like test bytes are not a live image-decoding or model-quality benchmark.

## Worked image for a future live run

The proposed public demonstration asset is the [330-pixel thumbnail of **Red Apple.jpg**](https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Red_Apple.jpg/330px-Red_Apple.jpg), from [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Red_Apple.jpg), by Abhijit Tembhekar (CC BY 2.0). A local HTTP check on 2026-10-27, with an explicit User-Agent, returned a 23,473-byte JPEG with SHA-256 `220d5828c8b2d5af9a9182cf1a2f061090afde12c9dc3bfcb54c5f58b5fc405a`. Candidate inputs: `A blue bicycle.` then `A red apple.`. This local check is **not** a Studionet verdict; verify the same bytes are still served before submitting them. If the image or CDN changes, fail closed rather than quietly accepting a new hash.

## Related work and limits

[AltCheck](https://github.com/huzyow155/alt-check-genlayer) audits a web page's HTML accessibility signals and alt-text clarity, and states it does **not** inspect image pixels. [Multimodal Acceptance Matrix](https://github.com/halihalibt/multimodal-acceptance-matrix-genlayer) judges visual deliverables against a general frozen brief. AltWitness is narrower: **claim alignment between a pinned image and its alt text**, with an append-only correction history. It does not copy either project's code or claim this is the first image-caption checker.

An alt text can be factually aligned but still unhelpful in context. This contract does not assess the image's purpose in a page, screen-reader experience, missing essential information, visual bias, ownership, licensing, deepfakes, safety, or WCAG conformance. Validators can agree on a mistaken visual reading; prompt injection and source/decoder differences remain risks. The allowlist is a limited egress policy, not proof that every DNS answer or redirect stays public. See [docs/DESIGN.md](docs/DESIGN.md) for the exact trust boundary and test matrix.

License: MIT. See [LICENSE](LICENSE).
