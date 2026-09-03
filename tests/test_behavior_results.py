import hashlib
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "tests" / "behavior" / "scenarios.md"
RESULTS = ROOT / "tests" / "behavior" / "skill-results.md"

FINAL_RUN_IDS = {
    "S1": "/root/green_eval_s1_rerun",
    "S2": "/root/green_eval_s2",
    "S3": "/root/green_eval_s3",
    "S4": "/root/green_eval_s4",
    "S5": "/root/green_eval_s5",
    "S6": "/root/green_eval_s6",
}

EXPECTED_CHECKS = {"S1": 4, "S2": 3, "S3": 4, "S4": 1, "S5": 4, "S6": 2}

EXPECTED_CHECK_IDS = {
    scenario_id: tuple(f"{scenario_id}-C{index}" for index in range(1, count + 1))
    for scenario_id, count in EXPECTED_CHECKS.items()
}

# Controller-owned constants from the frozen evaluator artifacts. These values are
# intentionally not generated from skill-results.md at test time. Hash input uses
# UTF-8 after CRLF/CR -> LF normalization. Response blocks retain every captured
# leading/trailing byte; prompt blocks use the documented blockquote extraction in
# _raw_prompt. Acceptance hashes bind the IDs above to the frozen hidden targets.
EXPECTED_PROMPT_SHA256 = {
    "S1": "0cf69d0010d9f57cc05d800ab227d7691c1156cc5d8dc5463ab1cecdaa92eb71",
    "S2": "4675756b4ce389fcef536425a176c9d973335b302307fce83ce70703362ee67e",
    "S3": "6c943aaf40ef54a3e19cb59cc3c3ff1f8c55cdf858063f815406d5e5f320ca50",
    "S4": "dcc4c87115c2c04dd80c1b0b64a579138c2cafa9edcd54cb2b6c611666905556",
    "S5": "948541538fe93bf6acb01eba930556760bbd8e151a819795ffb3da20dcce456d",
    "S6": "8a39274bc9df689cc1028f3420a4d4b3ed1d527053675a550d58669d82040a93",
}

EXPECTED_RESPONSE_SHA256 = {
    "S1": "de2c717342b07bb9f4b169514f71a76ea88169c0c4960b73d8d6120de3fad6e9",
    "S2": "37c244ea070e77b65c3e3d60ac6b3317352927b4146b895bd3fce166b2c2abfa",
    "S3": "8a21d3e4ae471065a8318a1f49b618133675c78c190d7b63c249a11e9646bc08",
    "S4": "a820e9a012b47f5d6a127bc1f7bd6e316e76d64c52ca250e28e1eef22aca1d5e",
    "S5": "602b6213cfd491c86aec572613becc6643440331405524315fec92778f3ef2b5",
    "S6": "73185b35b164719dd3d9aaffa6e4161963138c1364ddbce1665588216f20cee8",
}

EXPECTED_S1_INITIAL_RESPONSE_SHA256 = (
    "fdb8af51e81593b898223c4ada26000724826199c926b831d5faeccebe6d6d5a"
)

EXPECTED_ACCEPTANCE_SHA256 = {
    "S1": "28e84a73fff206d6d3bab0be1e9cd0fbf75346e7c6fa2aa001c5755732da7b54",
    "S2": "28356bb69b7b9a31a2a691c5cc5bff0f2c093ee0fc129d1efcc2a15d532183cb",
    "S3": "2b77c0fa75b83b70df6f33e3f5baef1df62356833f3add340ecd0bb8a552f098",
    "S4": "32d625823ef922be4f628f8bcc59e196f3a464608afaecfcb560f9f5d21286c1",
    "S5": "56d5ce099cbbeb69a9290dc2306d1afb415fc12fe4a1ab78d9ba9aece98017ac",
    "S6": "1a45cc6b4cf1cab78a7504a66568f225aeddf4f2a08c59b51dd674fbae931654",
}

EXPECTED_EVIDENCE_SHA256 = {
    "S1-C1": "182557d86b1e36b6a3ad5e05c9e050c03b4bd467b3d9e78db42e86cbac5c4b9c",
    "S1-C2": "c5f2650f4440f11e25f09f25e40c2c106f0d9d2dfa5d4f5f0c83d205bcc0591a",
    "S1-C3": "7705413e9bbb7e2a1d1ad75315a7f78779538b054dd0e12437d0b360cfacb198",
    "S1-C4": "9a9625526148e0c827422cbc03e22a9ae53af1c632758eccd92d1489bae921d5",
    "S2-C1": "e804793c9a3d46a500ee1c30bf8e235a520356089c5aaa21758458e9c331fb70",
    "S2-C2": "a9d0d1ca9725b56d1bdc657c2f3d5642407ed3be4b9c6650bdd28f53bc94a839",
    "S2-C3": "451e94f4e476a9617d5a0dce9a6c244592291dbd7e1acc17220efd0719757f97",
    "S3-C1": "2a4dc7d771b93e8610c0e296650a52f0314ca65ab68d3477965c30f3e1c4e606",
    "S3-C2": "23d9df9f9e0cec54ec21de4d996b65c547e369b9ab6420f9bde4ba193caf85b7",
    "S3-C3": "2ec2b6e5743d91c520381b89e38ef2c9c692ac8bf74fff1fcb115184eaf45656",
    "S3-C4": "5602d51dd05dae45db7a8de83bd28f83ae5b198f406680dea213f149f1e082d2",
    "S4-C1": "6ca31ebe67d2bcc502b59df7558a5df750013686688ee30d3d779c1339eb7f09",
    "S5-C1": "cca1ba6c42e2449a74d1b384538f312c5fbd30dacef05222ca73986203a684c8",
    "S5-C2": "51de0eba7ea7ddbda02f96f73dd4ab3a5da2ba63a0fa0d0d9449f056ef7a43c6",
    "S5-C3": "822737060c5127133343d35d5f345013e72a15c9796019b628cecdb52133ed2d",
    "S5-C4": "2e437766f12eb2049db1c34ee1c6207205aff1cc06cfabb78c4ce6c3853d8798",
    "S6-C1": "e3b19853b011b8739b000efe5b122e74cd706fe736a307c3392ce2dc1c162baf",
    "S6-C2": "4ca74015737478a7f78b1667c08447098b625bbdfb399fe65952e83676ebd86d",
}

SELF_REPORT_SCENARIOS = {"S1", "S2", "S3", "S5"}
SELF_REPORT_DISCLAIMER = (
    "Evaluator statements about file reads, command exit codes, tool use, or "
    "non-use are self-reports, remain unverified, and are excluded from acceptance evidence."
)


def _sha256_lf(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _acceptance_target(section: str) -> str:
    match = re.search(
        r"### Acceptance target \(not shown to evaluator\)\s+\n(?P<body>.*)",
        section,
        re.DOTALL,
    )
    assert match, "scenario must contain its hidden acceptance target"
    return match.group("body").strip()


def _validate_document(results_text: str, scenarios_text: str) -> None:
    scenarios = _scenario_sections(scenarios_text)
    results = _scenario_sections(results_text)
    assert set(scenarios) == set(FINAL_RUN_IDS)
    assert set(results) == set(FINAL_RUN_IDS)
    assert "single-run qualitative validation" in results_text
    assert "not a reliability estimate" in results_text
    assert "**Overall status:** **6/6 PASS (GREEN)**" in results_text
    assert SELF_REPORT_DISCLAIMER in results_text

    audit = re.search(
        r"^## Run audit trail\s+(?P<body>.*?)\n\*\*Overall status:",
        results_text,
        re.MULTILINE | re.DOTALL,
    )
    assert audit, "missing top-level run audit trail"
    final_line = re.search(
        r"^- Final fresh task/session IDs: (?P<body>.+)$",
        audit.group("body"),
        re.MULTILINE,
    )
    assert final_line, "missing final task/session mapping in audit trail"
    audit_final_ids = dict(re.findall(r"(S[1-6]) `([^`]+)`", final_line.group("body")))
    assert audit_final_ids == FINAL_RUN_IDS
    initial_line = re.search(
        r"^- S1 initially ran as `(?P<initial>[^`]+)`.*fresh task `(?P<rerun>[^`]+)`\.$",
        audit.group("body"),
        re.MULTILINE,
    )
    assert initial_line, "missing S1 initial/fresh-rerun audit binding"
    assert initial_line.group("initial") == "/root/green_eval_s1"
    assert initial_line.group("rerun") == FINAL_RUN_IDS["S1"]

    for scenario_id, run_id in FINAL_RUN_IDS.items():
        scenario = scenarios[scenario_id]
        result = results[scenario_id]
        source_prompt = _raw_prompt(scenario)
        recorded_prompt = _result_block(result, "Raw evaluator prompt transcript")
        response = _result_block(result, "Assistant response transcript")

        assert f"**Final evaluator task/session:** `{run_id}`" in result
        assert recorded_prompt == source_prompt
        assert _sha256_lf(source_prompt) == EXPECTED_PROMPT_SHA256[scenario_id]
        assert _sha256_lf(response) == EXPECTED_RESPONSE_SHA256[scenario_id]
        assert _sha256_lf(_acceptance_target(scenario)) == EXPECTED_ACCEPTANCE_SHA256[
            scenario_id
        ]
        status_count = result.count("**Tool/run self-report status:**")
        if scenario_id in SELF_REPORT_SCENARIOS:
            assert status_count == 1
            status = re.search(
                r"\*\*Tool/run self-report status:\*\* (?P<body>.+)", result
            )
            assert status
            assert "unverified" in status.group("body")
            assert "not used as acceptance evidence" in status.group("body")
        else:
            assert status_count == 0

        observed = re.search(
            r"\*\*Observed acceptance checks \((\d+)/(\d+)\):\*\*(?P<body>.*?)"
            r"\n\*\*Observed omission/over-expansion:\*\*",
            result,
            re.DOTALL,
        )
        assert observed, f"{scenario_id} must record its observed checks"
        passed, total = map(int, observed.group(1, 2))
        entries = re.findall(
            r"^- (?P<id>S\d-C\d+) — (?P<decision>PASS|FAIL) — (?P<evidence>.+)$",
            observed.group("body"),
            re.MULTILINE,
        )
        ids = [entry[0] for entry in entries]
        assert tuple(ids) == EXPECTED_CHECK_IDS[scenario_id]
        assert len(ids) == len(set(ids))
        assert total == len(EXPECTED_CHECK_IDS[scenario_id])
        assert all(decision == "PASS" for _, decision, _ in entries)
        assert all(evidence.strip() for _, _, evidence in entries)
        for check_id, _, evidence in entries:
            assert _sha256_lf(evidence) == EXPECTED_EVIDENCE_SHA256[check_id]
            contains = re.findall(r'transcript_contains="([^"]+)"', evidence)
            excludes = re.findall(r'transcript_excludes="([^"]+)"', evidence)
            assert contains, f"{check_id} must bind evidence to response text"
            assert all(snippet in response for snippet in contains)
            assert all(snippet not in response for snippet in excludes)
        assert passed == len(entries)
        assert "**Final result:** **PASS (GREEN)**" in result

    final_results = re.findall(r"^\*\*Final result:\*\* \*\*(.+?)\*\*\.$", results_text, re.MULTILINE)
    assert final_results == ["PASS (GREEN)"] * len(FINAL_RUN_IDS)


def _scenario_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^## (S[1-6])\b.*$", text, re.MULTILINE))
    return {
        match.group(1): text[match.start() : matches[index + 1].start()]
        if index + 1 < len(matches)
        else text[match.start() :]
        for index, match in enumerate(matches)
    }


def _raw_prompt(section: str) -> str:
    match = re.search(
        r"### Raw evaluator prompt\s+\n(?P<body>(?:>.*(?:\n|$))+?)\n### Acceptance target",
        section,
    )
    assert match, "scenario must contain a raw evaluator prompt"
    lines = []
    for line in match.group("body").splitlines():
        assert line.startswith(">")
        lines.append(line[1:].lstrip())
    return "\n".join(lines).strip()


def _result_block(section: str, label: str) -> str:
    match = re.search(
        rf"\*\*{re.escape(label)} \(verbatim\):\*\*\s+~~~text\n(?P<body>.*?)\n~~~",
        section,
        re.DOTALL,
    )
    assert match, f"missing verbatim {label.lower()} block"
    return match.group("body")


def test_green_results_have_six_fresh_final_runs_and_exact_prompts():
    results_text = RESULTS.read_text(encoding="utf-8")
    _validate_document(results_text, SCENARIOS.read_text(encoding="utf-8"))


def test_each_green_run_records_every_check_and_final_status():
    results_text = RESULTS.read_text(encoding="utf-8")
    _validate_document(results_text, SCENARIOS.read_text(encoding="utf-8"))


def test_s1_failed_first_run_is_preserved_as_an_audit_trail():
    text = RESULTS.read_text(encoding="utf-8")
    s1 = _scenario_sections(text)["S1"]
    assert "**Initial failed evaluator task/session:** `/root/green_eval_s1`" in s1
    initial_response = _result_block(s1, "Initial failed assistant response transcript")
    assert _sha256_lf(initial_response) == EXPECTED_S1_INITIAL_RESPONSE_SHA256
    assert "FAIL" in text
    assert "`/root/green_eval_s1_rerun`" in text
    assert "2–3" in text
    assert "rerun" in text.lower()


@pytest.mark.parametrize("replacement", ["摘要占位", "B"])
def test_response_transcript_mutations_are_rejected(replacement):
    text = RESULTS.read_text(encoding="utf-8")
    s1 = _scenario_sections(text)["S1"]
    original = _result_block(s1, "Assistant response transcript")
    mutated = text.replace(original, replacement, 1)
    with pytest.raises(AssertionError):
        _validate_document(mutated, SCENARIOS.read_text(encoding="utf-8"))


def test_duplicate_and_missing_check_id_mutation_is_rejected():
    text = RESULTS.read_text(encoding="utf-8")
    mutated = text.replace("S1-C2", "S1-C1", 1)
    with pytest.raises(AssertionError):
        _validate_document(mutated, SCENARIOS.read_text(encoding="utf-8"))


def test_missing_check_id_mutation_is_rejected():
    text = RESULTS.read_text(encoding="utf-8")
    mutated = re.sub(r"^- S2-C3 .+\n", "", text, count=1, flags=re.MULTILINE)
    with pytest.raises(AssertionError):
        _validate_document(mutated, SCENARIOS.read_text(encoding="utf-8"))


def test_unknown_check_id_mutation_is_rejected():
    text = RESULTS.read_text(encoding="utf-8")
    mutated = text.replace("S3-C4", "S3-C5", 1)
    with pytest.raises(AssertionError):
        _validate_document(mutated, SCENARIOS.read_text(encoding="utf-8"))


def test_top_audit_task_id_mutation_is_rejected():
    text = RESULTS.read_text(encoding="utf-8")
    mutated = text.replace("S2 `/root/green_eval_s2`", "S2 `/root/forged_s2`", 1)
    with pytest.raises(AssertionError):
        _validate_document(mutated, SCENARIOS.read_text(encoding="utf-8"))


def test_observed_evidence_mutation_is_rejected():
    text = RESULTS.read_text(encoding="utf-8")
    mutated = text.replace("names three distinct candidate paths", "generic summary", 1)
    assert mutated != text
    with pytest.raises(AssertionError):
        _validate_document(mutated, SCENARIOS.read_text(encoding="utf-8"))


def test_scenario_and_overall_result_mutations_are_rejected():
    text = RESULTS.read_text(encoding="utf-8")
    scenario_mutation = text.replace(
        "**Final result:** **PASS (GREEN)**", "**Final result:** **FAIL**", 1
    )
    overall_mutation = text.replace(
        "**Overall status:** **6/6 PASS (GREEN)**",
        "**Overall status:** **5/6 PASS**",
        1,
    )
    scenarios_text = SCENARIOS.read_text(encoding="utf-8")
    with pytest.raises(AssertionError):
        _validate_document(scenario_mutation, scenarios_text)
    with pytest.raises(AssertionError):
        _validate_document(overall_mutation, scenarios_text)


def test_unverified_self_report_disclaimer_is_required():
    text = RESULTS.read_text(encoding="utf-8")
    disclaimer = (
        "Evaluator statements about file reads, command exit codes, tool use, or "
        "non-use are self-reports, remain unverified, and are excluded from acceptance evidence."
    )
    assert disclaimer in text
    mutated = text.replace(disclaimer, "", 1)
    with pytest.raises(AssertionError):
        _validate_document(mutated, SCENARIOS.read_text(encoding="utf-8"))
