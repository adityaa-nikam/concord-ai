from app.agents.understand import CustomerComplaintUnderstandEngine


def test_understand_extraction_with_utr(db_session):
    text = "₹2,400 was deducted from my account for UTR 426189012345, but the receiver didn't get it."
    parsed = CustomerComplaintUnderstandEngine.parse_complaint(text, case_id="case-001", db=db_session)

    assert parsed["issue_type"] == "DEBITED_BENEFICIARY_NOT_CREDITED"
    assert parsed["extracted_amount"] == 2400.0
    assert parsed["extracted_utr"] == "426189012345"
    assert parsed["is_utr_ambiguous"] is False


def test_understand_missing_utr_candidate_lookup(db_session):
    # Complaint text without explicit UTR
    text = "₹2,400 was debited but the beneficiary didn't receive the money."
    parsed = CustomerComplaintUnderstandEngine.parse_complaint(text, case_id="case-001", db=db_session)

    assert parsed["extracted_amount"] == 2400.0
    # Candidate lookup from case-001 should resolve UTR 426189012345 without hallucinating
    assert parsed["extracted_utr"] == "426189012345"
    assert parsed["is_utr_ambiguous"] is False
