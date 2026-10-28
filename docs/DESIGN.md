# AltWitness design boundary

Status: v2 deployed on Studionet with two finalized full-consensus vision reviews and separate Finalized state reads, documented in [DEPLOY.md](DEPLOY.md). Local lint, typecheck and 54 Direct Mode tests passed with mocked inputs. The earlier v1 JPEG review failed `INVALID_IMAGE` and was Undetermined; do not count it as a successful review. Portal submission and acceptance are not claimed.

## Why an image caption is a consensus question

An informative image may be accompanied by alt text that is grammatically fine but contradicts its pixels. An exact SHA-256 shows which *bytes* were reviewed, not whether `A blue bicycle.` describes a photographed apple. One publisher or off-chain classifier can write the wrong label without an independent check. AltWitness asks GenLayer validators to inspect the same public image, independently judge a small closed vector, and accept a receipt only when those decision-bearing fields agree. It checks asserted visual claims, **not** whether the alt text is sufficient for a particular user or page.

## Roles and immutable inputs

- The wallet opening a case becomes its owner. It fixes an allowlisted direct public JPEG/PNG URL, the exact expected 64-hex SHA-256, and a short public alt text. This does not attest that the opener owns the image, chose an ethical depiction, or obtained a valid license.
- `open` stores a `DRAFT` record under a monotonically increasing string ID and a root ID. No model or web call is made here, so a caller's digest is not trusted as proof of available media.
- Anyone may call `review` for the current draft. Before nondeterminism, code copies the relevant plain strings from storage. Each validator independently fetches and checks actual image bytes during the review.
- After assessment, only the creator can append a corrected alt text under that root. `revise` copies the exact URL and expected image hash, fixes the new parent, increments the revision and moves the root's latest pointer to the new `DRAFT`. It never edits an old result. At most three revisions are allowed. A different asset needs a new root.
- All submitted alt texts and source URLs are public. Do not insert private customer data or secrets.

## Vision/equivalence boundary

A bounded HTTP 200 JPEG/PNG body of no more than 160,000 bytes is hashed in code. On mismatch with the frozen expectation, `IMAGE_CHANGED` is a distinct terminal result; no image-model call is used. Fetch failure, oversized/invalid image container or malformed response returns `SOURCE_UNAVAILABLE`. Neither implies the alt text was wrong. If the vision invocation or decoder fails *after* matching bytes are fetched, v2 returns `VISION_UNAVAILABLE` with their digest and size when validators agree on the failure; it does not mislabel this as an HTTP outage. A malformed model assessment still aborts rather than writing a verdict. Not every valid JPEG accepted by the contract's minimal magic check is accepted by GenVM's image decoder: the v1 JPEG `INVALID_IMAGE` receipt demonstrates this limitation.

For matching source bytes, the vision prompt treats JSON-encoded alt text as **untrusted data** and asks for only these decision fields:

- `subject`: `MATCH`, `MISMATCH` or `UNKNOWN` — does the main named subject match the pixels?
- `detail`: `MATCH`, `MISMATCH`, `NOT_CLAIMED`, `UNKNOWN`, or `NOT_APPLICABLE` — are additional visually checkable asserted details supported? If subject is not `MATCH`, detail must be `NOT_APPLICABLE`.
- `subject_quote`, `detail_quote`: bounded exact spans *in the recorded alt text*. Positive/negative classifications require a nonempty span; unknown/not-claimed/not-applicable require empty spans. Text inclusion is checked by code, but **cannot** establish visual truth on its own.

The accepted packet includes source status, image digest, byte size and the axis vector. Validators independently re-fetch, hash and run their own vision inference, then reject a leader's bad source status, missing field, inconsistent hash/size, invented span, changed subject class, contradictory detail or uncertainty crossing. For an otherwise matching subject, `detail=MATCH` and `detail=NOT_CLAIMED` belong to one **nonblocking consequence family**. Their wording/quotes can differ; neither permits a contradiction or turns uncertainty into approval. Deterministic code separately recomputes the final status from the leader's valid accepted vector, never from a model-supplied verdict.

Outcome priority: unavailable source → `SOURCE_UNAVAILABLE`; changed image → `IMAGE_CHANGED`; failed vision invocation → `VISION_UNAVAILABLE`; otherwise any `MISMATCH` → `CLAIMS_CONTRADICTED`, any `UNKNOWN` → `NEEDS_REVIEW`, else `CLAIMS_SUPPORTED`. No reward, NFT mint, content publication or machine action is executed by this contract. A consumer must wait for a **finalized, successful** review before using its observation, bind to the exact root/revision/digest and apply its own purpose-specific accessibility requirements.

## Tests, nearby work and limitations

The 54 Direct Mode tests cover image/alt bounds, HTTPS egress allowlist, unchanged immutable root data across revisions, owner guard, max revisions, source/vision/image-hash failure states, a CRC-correct synthetic PNG, positive/negative and uncertain model answers, invalid model shapes, quote forgery, a lying leader, independently changed validator image bytes, and permitted nonblocking variance versus forbidden outcome-changing disagreement. They execute the real contract with mocked web and model calls, not a distributed committee. Two real PNG vision reviews and a separate v1 JPEG failure are linked in [DEPLOY.md](DEPLOY.md); those receipts are distinct from the tests.

Compared with [AltCheck](https://github.com/huzyow155/alt-check-genlayer), this primitive actually presents image bytes to the models rather than grading HTML alt attributes without vision. Compared with the generic [Multimodal Acceptance Matrix](https://github.com/halihalibt/multimodal-acceptance-matrix-genlayer), this contract fixes one alt-text claim rubric, image-byte identity, and an owner-linked correction journal. There is no global originality claim or borrowed source code.

Limitations: the two allowed hosts are not an SSRF guarantee for redirects or DNS rebinding; image hash binds observed bytes, not authorship or licensing. Models can share the same visual mistake; a quote is an alt-text span, not a pixel proof. A valid `CLAIMS_SUPPORTED` result does not certify usefulness for blind readers, full image context, WCAG conformance, image authenticity or that the URL will remain reachable later. The live claims are limited to two successful full-consensus reviews of one pinned PNG. The v1 JPEG failure shows that fetching valid bytes and matching their hash does not prove the runtime's vision path accepts every JPEG. Later model upgrades, unavailable media and validator disagreement can still prevent consensus; do not extrapolate the two receipts to all images.
