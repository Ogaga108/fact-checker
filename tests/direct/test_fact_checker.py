import json

CONTRACT = "contracts/fact_checker.py"


def _mock_verdict(direct_vm, verdict="supported", confidence=85):
    direct_vm.mock_llm(
        r"Fact-check the following claim",
        json.dumps({"verdict": verdict, "confidence": confidence, "explanation": "sources agree"}),
    )


def test_check_claim_without_source(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    _mock_verdict(direct_vm, "supported")

    result = contract.check_claim("The Earth orbits the Sun once per year")

    assert result["verdict"] == "supported"
    assert result["confidence"] == 85
    assert result["source_url"] == ""


def test_check_claim_with_source_url(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    direct_vm.mock_web(
        r"example\.com/water",
        {"status": 200, "body": "Boiling point of water at sea level is 100C."},
    )
    _mock_verdict(direct_vm, "refuted")

    result = contract.check_claim(
        "Water boils at 50 degrees Celsius at sea level",
        source_url="https://example.com/water",
    )

    assert result["verdict"] == "refuted"
    assert result["source_url"] == "https://example.com/water"


def test_unverifiable_verdict(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    _mock_verdict(direct_vm, "unverifiable")

    result = contract.check_claim("Aliens visited my backyard last night")

    assert result["verdict"] == "unverifiable"


def test_check_is_persisted(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    claim = "Gold is denser than aluminum"
    _mock_verdict(direct_vm, "supported")

    contract.check_claim(claim)
    stored = contract.get_check(claim.upper())

    assert stored["exists"] is True
    assert stored["verdict"] == "supported"


def test_stats_counts_checks(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    _mock_verdict(direct_vm)

    contract.check_claim("Statement one about physics")
    contract.check_claim("Statement two about history")

    assert contract.stats()["total_checks"] == 2


def test_rejects_short_claim(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice

    with direct_vm.expect_revert("claim too short"):
        contract.check_claim("hi")


def test_rejects_oversized_claim(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice

    with direct_vm.expect_revert("claim too long"):
        contract.check_claim("c" * 2001)
