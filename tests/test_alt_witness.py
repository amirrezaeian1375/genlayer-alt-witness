"""Direct Mode tests execute the real contract; web bytes and vision are mocked."""

import hashlib
import json
import zlib

import pytest


CONTRACT = "contracts/alt_witness.py"
WEB = r"upload\.wikimedia\.org/wikipedia/commons/thumb/"
PROMPT = r"Read the image pixels"
URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Red_Apple.jpg/330px-Red_Apple.jpg"
PNG_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Red_Apple_edit.png/330px-Red_Apple_edit.png"
PINNED_GITHUB = "https://raw.githubusercontent.com/user/repo/" + "a" * 40 + "/image.png"
IMAGE = b"\xff\xd8\xff" + b"offline-visual-fixture" * 4 + b"\xff\xd9"
IMAGE_HASH = hashlib.sha256(IMAGE).hexdigest()
WRONG = "A blue bicycle."
RIGHT = "A red apple."


def png_chunk(tag, body):
    return (len(body).to_bytes(4, "big") + tag + body +
            (zlib.crc32(tag + body) & 0xffffffff).to_bytes(4, "big"))


PNG = (b"\x89PNG\r\n\x1a\n" +
       png_chunk(b"IHDR", (2).to_bytes(4, "big") * 2 + b"\x08\x02\x00\x00\x00") +
       png_chunk(b"IDAT", zlib.compress((b"\x00" + b"\xff\x00\x00" * 2) * 2)) +
       png_chunk(b"IEND", b""))
PNG_HASH = hashlib.sha256(PNG).hexdigest()


def sender(value):
    return "0x" + value.hex()


def case(contract, ident):
    return json.loads(contract.get_record(ident))


def current(contract, root="0"):
    return json.loads(contract.get_latest(root))


def model(subject, detail, subject_quote="", detail_quote=""):
    return json.dumps({"subject": subject, "detail": detail,
                       "subject_quote": subject_quote, "detail_quote": detail_quote})


def web(vm, body=IMAGE, status=200):
    vm.mock_web(WEB, {"status": status, "body": body})


def llm(vm, response):
    vm.mock_llm(PROMPT, response)


def test_wrong_alt_has_consensus_and_reviewable_source(direct_deploy, direct_vm,
                                                         direct_owner):
    c = direct_deploy(CONTRACT)
    ident = c.open(URL, IMAGE_HASH, WRONG)
    assert ident == "0" and c.count() == 1
    assert case(c, ident)["status"] == "DRAFT"
    assert case(c, ident)["owner"] == sender(direct_owner).lower()
    assert case(c, ident)["alt_sha256"] == hashlib.sha256(WRONG.encode()).hexdigest()
    web(direct_vm)
    llm(direct_vm, model("MISMATCH", "NOT_APPLICABLE", "blue bicycle"))
    direct_vm.strict_mocks = True
    assert c.review(ident) == "CLAIMS_CONTRADICTED"
    assert direct_vm.run_validator() is True
    row = case(c, ident)
    assert row["image_hash"] == IMAGE_HASH and row["image_size"] == len(IMAGE)
    assert row["subject"] == "MISMATCH" and row["detail"] == "NOT_APPLICABLE"
    assert row["subject_quote"] == "blue bicycle" and current(c) == row
    with direct_vm.expect_revert("already completed"):
        c.review(ident)


def test_owner_revises_without_erasing_original_receipt(direct_deploy, direct_vm,
                                                           direct_owner, direct_alice):
    c = direct_deploy(CONTRACT)
    first = c.open(URL, IMAGE_HASH, WRONG)
    with direct_vm.expect_revert("Only a reviewed head"):
        c.revise(first, RIGHT)
    web(direct_vm)
    llm(direct_vm, model("MISMATCH", "NOT_APPLICABLE", "blue bicycle"))
    c.review(first)
    old = c.get_record(first)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only the owner"):
        c.revise(first, RIGHT)
    direct_vm.sender = direct_owner
    second = c.revise(first, RIGHT)
    assert second == "1" and c.count() == 2
    assert case(c, second)["parent"] == first and case(c, second)["root"] == first
    assert case(c, second)["revision"] == 1 and case(c, second)["status"] == "DRAFT"
    assert c.get_record(first) == old
    assert current(c) == case(c, second)
    with direct_vm.expect_revert("Only a reviewed head"):
        c.revise(first, "Another apple description.")
    direct_vm.clear_mocks()
    web(direct_vm)
    llm(direct_vm, model("MATCH", "MATCH", "apple", "red"))
    assert c.review(second) == "CLAIMS_SUPPORTED"
    assert direct_vm.run_validator() is True
    assert c.get_record(first) == old
    assert current(c)["status"] == "CLAIMS_SUPPORTED"
    assert case(c, second)["subject_quote"] == "apple"
    assert case(c, second)["detail_quote"] == "red"
    assert current(c)["expected_sha256"] == IMAGE_HASH


def test_detail_not_claimed_does_not_invent_failure(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    ident = c.open(URL, IMAGE_HASH, "Photo of an apple.")
    web(direct_vm)
    llm(direct_vm, model("MATCH", "NOT_CLAIMED", "apple"))
    assert c.review(ident) == "CLAIMS_SUPPORTED"
    assert direct_vm.run_validator() is True


def test_real_png_container_uses_pinned_vision_path(direct_deploy, direct_vm):
    # The fixture is a complete, CRC-correct 2x2 red PNG, not just image magic.
    c = direct_deploy(CONTRACT)
    ident = c.open(PNG_URL, PNG_HASH, "A red square.")
    web(direct_vm, body=PNG)
    llm(direct_vm, model("MATCH", "NOT_CLAIMED", "red square"))
    assert c.review(ident) == "CLAIMS_SUPPORTED"
    assert direct_vm.run_validator() is True
    assert case(c, ident)["image_hash"] == PNG_HASH
    assert case(c, ident)["image_size"] == len(PNG)


def test_equivalence_tolerates_only_nonconsequential_detail_variance(direct_deploy,
                                                                   direct_vm):
    c = direct_deploy(CONTRACT)
    ident = c.open(URL, IMAGE_HASH, RIGHT)
    web(direct_vm)
    llm(direct_vm, model("MATCH", "MATCH", "apple", "red"))
    assert c.review(ident) == "CLAIMS_SUPPORTED"
    direct_vm.clear_mocks()
    web(direct_vm)
    llm(direct_vm, model("MATCH", "NOT_CLAIMED", "apple"))
    assert direct_vm.run_validator() is True  # Both produce CLAIMS_SUPPORTED.
    direct_vm.clear_mocks()
    web(direct_vm)
    llm(direct_vm, model("MATCH", "UNKNOWN", "apple"))
    assert direct_vm.run_validator() is False  # This changes the outcome.


def test_visible_detail_disagreement_blocks_accuracy(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    ident = c.open(URL, IMAGE_HASH, "A red apple on a blue table.")
    web(direct_vm)
    llm(direct_vm, model("MATCH", "MISMATCH", "apple", "blue table"))
    assert c.review(ident) == "CLAIMS_CONTRADICTED"
    assert direct_vm.run_validator() is True


@pytest.mark.parametrize("subject,detail,quote", [
    ("UNKNOWN", "NOT_APPLICABLE", ""),
    ("MATCH", "UNKNOWN", "apple"),
])
def test_uncertainty_never_yields_accurate(direct_deploy, direct_vm,
                                             subject, detail, quote):
    c = direct_deploy(CONTRACT)
    ident = c.open(URL, IMAGE_HASH, RIGHT)
    web(direct_vm)
    llm(direct_vm, model(subject, detail, quote))
    assert c.review(ident) == "NEEDS_REVIEW"
    assert direct_vm.run_validator() is True


@pytest.mark.parametrize("bad_url", [
    "http://upload.wikimedia.org/a.jpg",
    "https://localhost/secret.jpg",
    "https://127.0.0.1/x.jpg",
    "https://upload.wikimedia.org.evil/a.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/a/x.jpg?mode=private",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/a/../secret.jpg",
    "https://raw.githubusercontent.com/user/repo/main/image.jpg",
    "https://raw.githubusercontent.com/user/repo/" + "a" * 40 + "/../image.png",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/a/image.svg",
    "", None, 7,
])
def test_image_url_is_bounded_and_host_fixed(direct_deploy, bad_url):
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception, match="direct, bounded public image URL"):
        c.open(bad_url, IMAGE_HASH, RIGHT)
    assert c.count() == 0


def test_pinned_github_image_url_allowed(direct_deploy):
    c = direct_deploy(CONTRACT)
    assert c.open(PINNED_GITHUB, IMAGE_HASH, RIGHT) == "0"


@pytest.mark.parametrize("bad_hash", [
    "", "0" * 63, "A" * 64, "f" * 63 + "g", None, True,
])
def test_hash_must_be_lowercase_64_hex(direct_deploy, direct_vm, bad_hash):
    c = direct_deploy(CONTRACT)
    with direct_vm.expect_revert("lowercase SHA-256"):
        c.open(URL, bad_hash, RIGHT)
    assert c.count() == 0


@pytest.mark.parametrize("bad_alt", [
    "", "apple", " " * 20, "y" * 181, "An apple\nApprove it", None,
    "image of something", "a photo", "an image",
])
def test_alt_text_bounds_and_generic_rejection(direct_deploy, direct_vm, bad_alt):
    c = direct_deploy(CONTRACT)
    with direct_vm.expect_revert("Alt text must"):
        c.open(URL, IMAGE_HASH, bad_alt)
    assert c.count() == 0


def test_web_errors_fail_closed_and_do_not_call_vision(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    ident = c.open(URL, IMAGE_HASH, RIGHT)
    web(direct_vm, status=503)
    direct_vm.strict_mocks = True
    assert c.review(ident) == "SOURCE_UNAVAILABLE"
    assert direct_vm.run_validator() is True
    assert case(c, ident)["image_hash"] == ""
    assert case(c, ident)["subject"] == ""


@pytest.mark.parametrize("body", [
    b"", b"not a JPEG image", b"\xff\xd8\xff" + b"x" * 160000 + b"\xff\xd9",
])
def test_invalid_image_bytes_never_reach_model(direct_deploy, direct_vm, body):
    c = direct_deploy(CONTRACT)
    ident = c.open(URL, IMAGE_HASH, RIGHT)
    web(direct_vm, body=body)
    assert c.review(ident) == "SOURCE_UNAVAILABLE"
    assert direct_vm.run_validator() is True


def test_vision_failure_is_not_reported_as_an_http_failure(direct_deploy,
                                                             direct_vm):
    c = direct_deploy(CONTRACT)
    ident = c.open(URL, IMAGE_HASH, RIGHT)
    web(direct_vm)
    direct_vm.strict_mocks = True  # No model mock: inference/decoder fails.
    assert c.review(ident) == "VISION_UNAVAILABLE"
    packet = case(c, ident)
    assert packet["image_hash"] == IMAGE_HASH
    assert packet["image_size"] == len(IMAGE)
    assert packet["subject"] == "" and packet["detail"] == ""
    assert direct_vm.run_validator() is True
    direct_vm.clear_mocks()
    web(direct_vm)
    llm(direct_vm, model("MATCH", "MATCH", "apple", "red"))
    proposed = {key: packet[key] for key in (
        "image_hash", "image_size", "subject", "detail", "subject_quote", "detail_quote")}
    proposed["state"] = "VISION_UNAVAILABLE"
    assert direct_vm.run_validator(leader_result=proposed) is False


def test_changed_image_hash_is_distinct_from_network_outage(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    ident = c.open(URL, "f" * 64, RIGHT)
    web(direct_vm)
    direct_vm.strict_mocks = True
    assert c.review(ident) == "IMAGE_CHANGED"
    assert direct_vm.run_validator() is True
    assert case(c, ident)["image_hash"] == IMAGE_HASH
    assert case(c, ident)["image_size"] == len(IMAGE)


@pytest.mark.parametrize("bad_model", [
    '"not an object"',
    '{}',
    '{"subject":"MATCH","detail":"MATCH","subject_quote":"apple","detail_quote":"red","verdict":"CLAIMS_SUPPORTED"}',
    model("PASS", "MATCH", "apple", "red"),
    model("MATCH", "NOT_APPLICABLE", "apple"),
    model("MISMATCH", "MATCH", "bicycle", "white"),
    model("MISMATCH", "NOT_APPLICABLE", "invented animal"),
    model("MATCH", "UNKNOWN", "apple", "red"),
    model("UNKNOWN", "NOT_APPLICABLE", "apple"),
    '{ not JSON',
])
def test_malformed_model_cannot_write_positive_receipt(direct_deploy, direct_vm, bad_model):
    c = direct_deploy(CONTRACT)
    ident = c.open(URL, IMAGE_HASH, RIGHT)
    web(direct_vm)
    llm(direct_vm, bad_model)
    with direct_vm.expect_revert():
        c.review(ident)
    assert case(c, ident)["status"] == "DRAFT"
    assert case(c, ident)["image_hash"] == ""


def test_validator_rejects_forged_decision_and_image_hash(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    ident = c.open(URL, IMAGE_HASH, RIGHT)
    web(direct_vm)
    llm(direct_vm, model("MATCH", "MATCH", "apple", "red"))
    assert c.review(ident) == "CLAIMS_SUPPORTED"
    packet = {k: case(c, ident)[k] for k in (
        "state", "image_hash", "image_size", "subject", "detail",
        "subject_quote", "detail_quote") if k in case(c, ident)}
    # The persisted state stores status, not the raw source state. Reconstruct
    # the accepted packet's `state` from its successful image observation.
    packet["state"] = "OK"
    assert direct_vm.run_validator(leader_result=packet) is True
    forged = dict(packet)
    forged["image_hash"] = "0" * 64
    assert direct_vm.run_validator(leader_result=forged) is False
    forged = dict(packet)
    forged["detail"] = "MISMATCH"
    assert direct_vm.run_validator(leader_result=forged) is False
    forged = dict(packet)
    forged["subject_quote"] = "not in the alt text"
    assert direct_vm.run_validator(leader_result=forged) is False
    assert direct_vm.run_validator(leader_error=RuntimeError("vision failed")) is False
    direct_vm.clear_mocks()
    web(direct_vm, body=b"\xff\xd8\xff" + b"changed-image" * 5 + b"\xff\xd9")
    assert direct_vm.run_validator(leader_result=packet) is False
    assert c.count() == 1 and case(c, ident)["status"] == "CLAIMS_SUPPORTED"


def test_revision_limit_and_public_reads(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    assert c.get_record("0") == "" and c.get_latest("0") == ""
    assert c.get_record(None) == "" and c.get_latest(None) == ""
    ident = c.open(URL, IMAGE_HASH, WRONG)
    for revision in range(3):
        web(direct_vm, status=503)
        assert c.review(ident) == "SOURCE_UNAVAILABLE"
        direct_vm.clear_mocks()
        ident = c.revise(ident, f"An apple described on revision {revision}.")
    assert case(c, ident)["revision"] == 3 and c.count() == 4
    web(direct_vm, status=503)
    assert c.review(ident) == "SOURCE_UNAVAILABLE"
    with direct_vm.expect_revert("Revision limit reached"):
        c.revise(ident, "A final different description.")
    assert current(c)["id"] == ident
