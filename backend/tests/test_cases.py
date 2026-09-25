def test_list_cases(client):
    response = client.get("/api/cases")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["cases"]) == 5


def test_get_case_detail(client):
    response = client.get("/api/cases/case-001")
    assert response.status_code == 200
    data = response.json()
    assert data["case_number"] == "CAS-2026-0001"
    assert data["customer"]["upi_id"] == "rajesh@paytm"
    assert data["transaction"]["amount"] == 2400.0


def test_create_case(client):
    payload = {
        "customer_upi": "newuser@paytm",
        "transaction_utr": "999888777666",
        "issue_description": "₹3,000 deducted, merchant did not receive.",
        "priority": "HIGH"
    }
    response = client.post("/api/cases", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["customer"]["upi_id"] == "newuser@paytm"
    assert data["transaction"]["utr"] == "999888777666"
    assert data["status"] == "NEW"
