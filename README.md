# CONCORD-AI

[![Deploy with Vercel](https://img.shields.io/badge/Vercel-Frontend%20Live-black?style=for-the-badge&logo=vercel)](https://concord-ai-six.vercel.app)
[![Deploy on Railway](https://img.shields.io/badge/Railway-Backend%20Live-0B0D0E?style=for-the-badge&logo=railway)](https://concord-ai-production.up.railway.app/docs)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14.2-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![Mistral AI](https://img.shields.io/badge/Mistral_AI-Enabled-FF7000?style=for-the-badge)](https://mistral.ai)
[![Tests](https://img.shields.io/badge/Tests-65%20Passed-emerald?style=for-the-badge)](https://github.com/adityaa-nikam/concord-ai)

> **Paytm Build for India AI Hackathon — Track 3: Autonomous AI Teammates**  
> **Product Name:** Concord-AI (Autonomous Exception Resolution Teammate for UPI Payment Failures)  
> **Live Demo**: [https://concord-ai-six.vercel.app](https://concord-ai-six.vercel.app) | **API Docs**: [https://concord-ai-production.up.railway.app/docs](https://concord-ai-production.up.railway.app/docs)

Concord-AI is an **Autonomous Payment Operations Workstation & AI Teammate** designed to resolve ambiguous UPI payment exceptions (e.g. *"₹2,400 was debited from my account, but the beneficiary didn't receive the money"*).

Instead of relying solely on static status checking or unconstrained LLMs, Concord-AI combines **LLM natural language & multi-system evidence interpretation** with **deterministic RBI Policy Gates and Action Idempotency Guardrails**.

---

## Core Product Principle

> **"Reason Broadly. Act Narrowly. Verify Everything Consequential."**

- **LLM Reasoning**: Parses complaint intent, interprets conflicting multi-system telemetry, flags state uncertainties, recommends missing evidence tools, and proposes resolution paths (`ACT`, `WAIT`, `ESCALATE`).
- **Deterministic Controls**: Validates Policy & RBI circular rules (`RBI/2019-20/67`), enforces action allowlists, verifies dispute amount caps (₹50,000 threshold), prevents duplicate payouts via idempotency keys (`REVERSAL:{transaction_id}`), and executes post-action multi-source verification.

---

## Architecture Pipeline

```
CUSTOMER COMPLAINT
       │
       ▼
AI UNDERSTANDING (NLU Intent & UTR Extraction)
       │
       ▼
MULTI-SYSTEM INVESTIGATION (Gateway, Ledger, Beneficiary Telemetry)
       │
       ▼
EVIDENCE NORMALIZATION & CONFLICT DETECTION
       │
       ▼
AI EVIDENCE INTERPRETATION (Uncertainty Identification & Dynamic Tool Selection)
       │
       ▼
POLICY & TAT RULES ENGINE (RBI Circular RBI/2019-20/67 Grounding)
       │
       ▼
AI RESOLUTION PROPOSAL (Structured Output: ACT / WAIT / ESCALATE)
       │
       ▼
DETERMINISTIC POLICY GATE & ACTION GATEWAY (Allowlist, Idempotency & Cap Check)
       │
       ▼
CONTROLLED ACTION & MULTI-SOURCE VERIFICATION
       │
       ▼
RESOLVED  OR  ESCALATED (With Structured Evidence Packet)
```

---

## Quick Start & Local Execution

### 1. Environment Setup

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Environment Modes:
- **MOCK LLM MODE (Default for testing & offline execution)**:
  `LLM_PROVIDER=mock`
- **LIVE LLM MODE (OpenAI / Gemini API completion)**:
  `LLM_PROVIDER=openai`  
  `OPENAI_API_KEY=your_key_here`  
  `LLM_MODEL=gpt-4o-mini`

---

### 2. Backend & Test Suite Execution

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/
```
*(All 65 Pytest unit and integration test cases will run and pass).*

Start FastAPI Backend Server:
```bash
python -m uvicorn app.main:app --reload --port 8000
```

- **Interactive API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Demo Readiness Health Check**: [http://localhost:8000/api/v1/demo/health](http://localhost:8000/api/v1/demo/health)

---

### 3. Frontend Operations Dashboard & Presentation Mode

```bash
cd frontend
npm install
npm run dev
```

Open in Browser:
- **Judge Presentation Mode**: [http://localhost:3000/demo](http://localhost:3000/demo)
- **Demo Scenario Orchestrator**: [http://localhost:3000/scenarios](http://localhost:3000/scenarios)
- **Cases Queue**: [http://localhost:3000/cases](http://localhost:3000/cases)

---

## Supported Pre-Configured Demo Scenarios

1. **HERO: CONFLICTING PAYMENT (`case-001`)**: Gateway reports `SUCCESS`, Ledger `DEBITED`, Beneficiary `NOT CREDITED`. Proposes auto-reversal, passes Policy Gate, executes reversal, and verifies outcome.
2. **ALREADY RESOLVED (`case-002`)**: Detects prior completed reversal, avoids duplicate financial mutation, notifies customer, and closes case.
3. **PENDING WITHIN TAT (`case-003`)**: Gateway and Ledger report `PENDING`. Verifies transaction is within RBI T+1 clearing window and schedules monitoring.
4. **VERIFICATION FAILURE (`case-005`)**: Reversal API call succeeds, but post-action core ledger debit check remains unverified. Safely escalates to human ops.
5. **HIGH VALUE ESCALATION (`case-004`)**: CBS Administrative Hold or dispute amount > ₹50,000 threshold. Policy Gate blocks automated payout and generates structured evidence packet for Tier 2 Ops.

---

## Documentation Index

- [Release Status & System Health](docs/release-status.md)
- [Judge Presentation & Demo Script](docs/demo-script.md)
- [Judge Q&A & Architecture Defense](docs/judge-questions.md)
- [Candidate Release Checklist](docs/release-checklist.md)
- [System Architecture Specification](docs/architecture.md)
- [REST API Reference](docs/api.md)
- [Agent Workflow Specification](docs/agent-workflow.md)
