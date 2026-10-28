# Studionet deployment and vision record

Observed 2026-10-27 on GenLayer **stable Studionet** (chain ID `61999`, RPC `https://studio.genlayer.com/api`). This document distinguishes the failed v1 JPEG experiment from v2's two successful full-consensus PNG reviews. It is not a WCAG certification, proof of image ownership, or assurance that validators will interpret every image correctly.

- Deployer, v2 case owner and writer: `0x3d9E39265d74511065f88C987f898c1d02892f3e`.
- Current v2 contract: [`0x5a65684b773E104656aA0696A41C7f7D7F8B48eC`](https://explorer-studio.genlayer.com/address/0x5a65684b773E104656aA0696A41C7f7D7F8B48eC).
- No constructor inputs and no GEN value transferred in any of the recorded transactions.
- The first source line pins `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`.

## v1: finalized failure, not a vision verdict

| Action | Transaction | What it established |
| --- | --- | --- |
| Deploy v1 | [`0x602abb97...3770a608`](https://explorer-studio.genlayer.com/tx/0x602abb9786a00f16d66833b7fae454d4d249e59d0b09385c5c3c9f5b3770a608) | `FINALIZED`, GenVM `SUCCESS`; separate contract [`0xa81e063D7b235682A33aC3A4172e1e1ea8209EB2`](https://explorer-studio.genlayer.com/address/0xa81e063D7b235682A33aC3A4172e1e1ea8209EB2). |
| Open v1 | [`0x4132ebc3...0b4d8624`](https://explorer-studio.genlayer.com/tx/0x4132ebc3f16a00ef2b751420bda736bfbdd9c9ae838cfd699b673bb30b4d8624) | `FINALIZED`, `SUCCESS`; draft ID `0` pointing at a JPEG with `A blue bicycle.` |
| Review v1 | [`0x82cb925e...94eb4b61`](https://explorer-studio.genlayer.com/tx/0x82cb925eb3e848a2cb03b6eb9b4cb006bfb964717dc104a59344e3eb94eb4b61) | **`FINALIZED` does not mean success**: consensus **Undetermined**, GenVM **ERROR** with `INVALID_IMAGE` while calling `exec_prompt(images=[body])`, three leader rotations. No successful visual verdict is claimed. |

A local JPEG decoder accepts that image and the contract reached the model call only after its exact image hash matched. That is not proof that GenVM's vision decoder could use the JPEG: the onchain error says the opposite. The old JPEG began with `ff d8 ff db`; the deployed v1 check accepted the broader `ff d8 ff` prefix. The precise pinned-runtime decoder rule was not independently proven. The v1 source is retained in [GitHub history](https://github.com/amirrezaeian1375/genlayer-alt-witness/blob/281db8c3a7ae0dcb9ea17a16930a071e02c2664c/contracts/alt_witness.py), and its onchain source matched that historical text after line-ending normalization. Do not repeat this transaction or count it as a failed caption judgment.

## v2: two contrasting full-consensus observations

v2 adds `VISION_UNAVAILABLE` as a separate, non-positive result when exact media bytes can be fetched but a vision invocation fails and validators independently agree. Malformed model assessments still abort. This **error-handling branch has local coverage only**, not its own live successful transaction; the live v2 reviews below used a PNG and returned vision judgments.

| Action | Explorer transaction | Observed result |
| --- | --- | --- |
| Deploy v2 | [`0x152321ed...4aca2365`](https://explorer-studio.genlayer.com/tx/0x152321ed7de60f5a7c26db39e7bfb9df75d627e67be08261498e44204aca2365) | New contract at the address above. |
| `open(PNG, sha256, "A blue bicycle.")` | [`0x5642bdd0...622deb88`](https://explorer-studio.genlayer.com/tx/0x5642bdd08d99e873e924c2f6369b04bbc4df521d3d1c42cfa8dfb4bd622deb88) | Stored draft `id="0"`, `root="0"`. |
| `review("0")` | [`0xd9c8b9d9...11ee9145`](https://explorer-studio.genlayer.com/tx/0xd9c8b9d943ecb707816b5c5ce5e67cc82d50ea8a55417958e76ccfe011ee9145) | **`CLAIMS_CONTRADICTED`**: subject `MISMATCH`, literal alt-text span `blue bicycle`, detail `NOT_APPLICABLE`. |
| `revise("0", "A red apple.")` | [`0xf2f40afe...0aafe8bc`](https://explorer-studio.genlayer.com/tx/0xf2f40afe81c6cb75c7e62feb16e86a51bad0ccc0a63afadc3394d3ef0aafe8bc) | Same owner appended draft `id="1"`, `root="0"`, `parent="0"`; image commitment was not changed. |
| `review("1")` | [`0xbd700509...b48d330e`](https://explorer-studio.genlayer.com/tx/0xbd700509f9de1a446ed1c7c6b479957fd3511c5832a829bed164e404b48d330e) | **`CLAIMS_SUPPORTED`**: subject `MATCH` / `apple`, detail `MATCH` / `red`. |

The v2 contract Explorer lists **five transactions**. Each is `FINALIZED` with GenVM `SUCCESS` and accepted consensus. Both `review` calls used Normal (Full Consensus), five initial validators and **one leader rotation each**. Do not call that unanimous or zero-rotation consensus.

Both v2 reviews independently acquired the same PNG body, `129,907` bytes, SHA-256 `d35f121064e43255730fe9361a504421bbbeb8770e929a542b798cc4a9450c43`, and their equivalence outputs include that digest. The publicly accessible 330px thumbnail is [Red Apple edit.png](https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Red_Apple_edit.png/330px-Red_Apple_edit.png) on [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Red_Apple_edit.png): original photograph by Abhijit Tembhekar, background edit by Afanasovich, licensed CC BY 2.0. The media is referenced, not committed as a binary file in this repository. A local hash check alone was not used as proof of vision; the two network receipts above are the evidence.

## Finalized state reads

The user selected **Finalized** in Studio Read Methods, then reported:

- `get_record("0")` after the revision still has `alt_text="A blue bicycle."`, `alt_sha256=1907dbad472edf10a9df34ea68d81f2d94c35efeadaa3adc9e9e7c5cea81f6df`, `root="0"`, `parent=""`, `revision=0`, `status=CLAIMS_CONTRADICTED`, `subject=MISMATCH`, and the pinned/observed PNG digest above. This shows the earlier result was not overwritten.
- `get_latest("0")` returned `id="1"`, `root="0"`, `parent="0"`, `revision=1`, `alt_text="A red apple."`, `alt_sha256=8cf0a1fb835d6c720d970e99749cb226ac55a32b0ff95e6cd6139ce0e088a2e9`, `status=CLAIMS_SUPPORTED`, subject/detail `MATCH` with quotes `apple` and `red`, and the same image digest. Both alt hashes were independently recomputed from the exact texts.

These are summarized Finalized state reads, not a published byte-exact JSON transcript. The transaction receipts independently show the two review statuses, source digest and decisive classification fields. No physical accessibility outcome, webpage use or real screen-reader user experience was tested.

## Deployed-source identity and testing limits

- Current GitHub `contracts/alt_witness.py` (v2): **12,960 bytes**, LF with final newline; SHA-256 `244815039fad6058f6caddfd93a21fae931843456dd5aa4931cc61f01bc36198`.
- `gen_getContractCode` from v2 on Studionet: **13,259 bytes**, CRLF without final LF; raw SHA-256 `0ec1c104c8188422950c40fe214a88e32378e871f0df3e2347954b8d136b234b`.
- Raw byte equality: **false**. Normalized text equality: **true**. Replacing only onchain CRLF with LF and appending its missing final LF yields the exact GitHub source. No code-token differences were found; do not call the raw hashes equal.

To reproduce source comparison, POST JSON-RPC `gen_getContractCode` to `https://studio.genlayer.com/api` with `params` containing the address **as a string**, base64-decode `result`, and make only those line-ending adjustments. On v1, raw bytes likewise differ from its [historical GitHub source](https://github.com/amirrezaeian1375/genlayer-alt-witness/blob/281db8c3a7ae0dcb9ea17a16930a071e02c2664c/contracts/alt_witness.py) but normalize to the same text. Studio deployments can reset; verify an address still exists before relying on it.

The v2 source passed `genvm-lint check contracts/alt_witness.py`, `genvm-lint typecheck contracts/alt_witness.py`, and **54 Direct Mode tests** using real contract storage with mocked web/LLM boundaries. The read-only Studionet source schema preflight returned all six public methods. Direct Mode alone does **not** test real model/image decoders or distributed consensus. Aside from the two documented v2 PNG outcomes, `NEEDS_REVIEW`, `IMAGE_CHANGED`, `SOURCE_UNAVAILABLE`, `VISION_UNAVAILABLE`, forged leader packets, invalid quotes and revision limits were tested locally only. Use `requirements-dev.txt` and `scripts/prepare_test_sdk.py` to reproduce the local checks.

Scope is deliberately narrow. A model may miss a detail or share another model's mistake; a literal alt-text span shows what claim was assessed, not whether it is visibly true. `CLAIMS_SUPPORTED` is not a complete alt-text quality score, full WCAG check, license clearance, image-authenticity proof or guarantee of future URL availability.
