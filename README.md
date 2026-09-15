# 🔥 Project Prometheus: Autonomous AI Governance & FinOps Control Plane

<div align="center">

[![AWS ap-south-1](https://img.shields.io/badge/AWS-ap--south--1%20(Mumbai)-FF9900?logo=amazon-aws&logoColor=white)](https://4oyzp80sy9.execute-api.ap-south-1.amazonaws.com)
[![Status](https://img.shields.io/badge/Status-100%25%20Live%20%26%20Verified-00C853?style=flat-square)](#-live-cloud-deployments)
[![Compute](https://img.shields.io/badge/Compute-Serverless%20Lambda%20Adapter-FF9900?style=flat-square)](#-zero-idle-cost-cloud-native-infrastructure)
[![Database](https://img.shields.io/badge/Database-Amazon%20RDS%20PostgreSQL%20%2B%20pgvector-336791?logo=postgresql&logoColor=white)](#-data-plane--persistence)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14%20Standalone-black?logo=next.js&logoColor=white)](https://nextjs.org)

**An enterprise-grade, real-time AI governance gateway and FinOps control plane that enforces deterministic policy budgets, semantic caching, PII masking, circuit-breaker kill-switches, and autonomous agent orchestration across 44+ foundation models with $0.00 idle compute costs.**

[Live Dashboard](https://4oyzp80sy9.execute-api.ap-south-1.amazonaws.com) • [Live API Gateway](https://w6qubbix87.execute-api.ap-south-1.amazonaws.com) • [Architecture](#-system-architecture) • [12-Stage Pipeline](#-the-12-stage-governance-pipeline) • [Model Catalog](#-universal-model-catalog-zero-credit-card) • [Quickstart](#-local-quickstart)

</div>

---

## 🌐 Live Cloud Deployments

Prometheus is fully deployed to AWS in the **`ap-south-1` (Mumbai)** region using **44 Terraform resources**. Every layer of the stack is 100% live and runs on real cloud services.

| Interface / Component | Production Endpoint | Architecture & Service |
|---|---|---|
| **Web Dashboard** | [`https://4oyzp80sy9.execute-api.ap-south-1.amazonaws.com`](https://4oyzp80sy9.execute-api.ap-south-1.amazonaws.com) | Next.js 14 Standalone via AWS Lambda Web Adapter |
| **API Gateway (HTTP API)** | [`https://w6qubbix87.execute-api.ap-south-1.amazonaws.com`](https://w6qubbix87.execute-api.ap-south-1.amazonaws.com) | Amazon API Gateway HTTP API v2 (CORS enabled) |
| **Direct Lambda URL** | [`https://n4cmh77bmu7i5ave64bo2bpyqm0gaajy.lambda-url.ap-south-1.on.aws`](https://n4cmh77bmu7i5ave64bo2bpyqm0gaajy.lambda-url.ap-south-1.on.aws) | Container-based Lambda (`prometheus-api`) |
| **Relational & Vector Store** | `prometheus-db.cf2ie46cw46t.ap-south-1.rds.amazonaws.com:5432` | Amazon RDS PostgreSQL 15.13 + `pgvector` |
| **Observability** | AWS CloudWatch Real-Time Dashboard | CloudWatch metrics, traces, latency percentiles |

> **Authentication**: API calls require header `x-api-key: prometheus-admin` (default admin credential).

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Client["Client Tier & Edge"]
        User["Client Application / Next.js Web UI"]
        APIGW["Amazon API Gateway HTTP API v2<br/>(CORS, Routing, TLS Termination)"]
    end

    subgraph ServerlessCompute["Zero-Idle Compute (VPC Private Subnets)"]
        LambdaAPI["prometheus-api (AWS Lambda + Web Adapter)<br/>FastAPI 12-Stage Governance Engine"]
        LambdaFinOps["prometheus-finops (AWS Lambda)<br/>EventBridge Scheduled Daily FinOps Agent"]
    end

    subgraph GovernanceLoop["12-Stage Deterministic Governance Pipeline"]
        Auth["1. Auth & API Key Validation (SHA-256)"]
        Rate["2. Sliding-Window Rate Limiter"]
        Budget["3. Dynamic FinOps Budget & Kill-Switch"]
        Guard["4. PII Masking & Injection Detection"]
        Router["5. Intelligent Tier Cost Router"]
        Cache["6. pgvector Semantic Cache Check (Cosine >= 0.82)"]
        RAG["7. RAG Knowledge Retrieval (pgvector)"]
        LLM["8. Universal Bedrock Converse Invocation"]
        Eval["9. LLM-as-a-Judge Evaluation"]
        CacheWrite["10. Semantic Cache Write"]
        CostLog["11. Microsecond Cost & Token Accounting"]
        AuditLog["12. Canonical Trace & Audit Persistence"]
    end

    subgraph Persistence["Amazon RDS PostgreSQL 15.13 + pgvector"]
        VectorDB[("pgvector Embeddings & Semantic Cache<br/>(Amazon Titan Text Embeddings v2)")]
        RelationalDB[("Traces, Policies, Audit Logs,<br/>Dead-Letter Queue, API Keys")]
    end

    subgraph AIServices["AWS Bedrock Universal Model Engine"]
        Bedrock["AWS Bedrock Converse API<br/>(44+ Verified Zero-Credit Card Foundation Models)"]
        Nova["Amazon Nova (Micro, Lite, Pro, 2 Lite)"]
        Llama["Meta Llama 3 (8B, 70B)"]
        Gemma["Google Gemma 3 (4B, 12B, 27B)"]
        Mistral["Mistral AI (7B, Mixtral 8x7B, Large, Ministral)"]
        Qwen["Qwen (32B, Coder 30B/480B, 235B)"]
        Others["DeepSeek V3, NVIDIA Nemotron, Z.AI GLM"]
    end

    User --> APIGW
    APIGW --> LambdaAPI
    LambdaAPI --> Auth
    Auth --> Rate --> Budget --> Guard --> Router --> Cache
    Cache -- Cache Hit (0 Cost, <30ms) --> CostLog
    Cache -- Cache Miss --> RAG --> LLM --> Eval --> CacheWrite --> CostLog --> AuditLog
    RAG <--> VectorDB
    Cache <--> VectorDB
    LLM <--> Bedrock
    Bedrock --> Nova
    Bedrock --> Llama
    Bedrock --> Gemma
    Bedrock --> Mistral
    Bedrock --> Qwen
    Bedrock --> Others
    CostLog --> RelationalDB
    AuditLog --> RelationalDB
    LambdaFinOps --> RelationalDB
```

---

## ⚡ The 12-Stage Governance Pipeline

Every request to `POST /api/v1/chat` executes through a strictly synchronous, deterministic 12-stage pipeline. Synchronous execution guarantees that audit trails, cost metering, guardrail enforcement, and budget checks remain 100% auditable and reproducible without out-of-order race conditions.

```
Request ➡️ [Auth] ➡️ [Rate Limit] ➡️ [Budget & Kill-Switch] ➡️ [Guardrails] ➡️ [Router]
               ⬇️
        [Semantic Cache Check] ──(Hit)──> [Cost & Audit Log] ──> Response
               ⬇️ (Miss)
        [RAG Retrieval] ➡️ [Universal Bedrock Invocation] ➡️ [Evaluation] ➡️ [Cache Store] ➡️ [Trace Persist]
```

1. **Request Ingestion**: Request ID assigned or replayed with cryptographic idempotency.
2. **Auth & Identity Validation**: `X-API-Key` hashed via SHA-256 and verified using timing-safe `hmac.compare_digest`.
3. **Sliding-Window Rate Limiting**: Per-key token and request rate enforcement.
4. **Pre-flight Budget Gating & Kill-Switch**: Real-time evaluation against project budgets, team daily allocations, and kill-switch states (`off`, `degrade_to_cheap`, `read_only_cache`, `full_shutdown`).
5. **Security Guardrails**: Regex and heuristic detectors identify prompt injection, jailbreaks, and PII (SSN, credit cards, emails, phone numbers) with automated zero-leak masking.
6. **Cost-Aware Model Routing**: Classifies task complexity (reasoning, coding, factual, simple chat) and selects the cheapest capable model tier (`cheap`, `strong`, `premium`).
7. **Semantic Caching**: Performs high-speed cosine similarity (`>= 0.82`) search over vector embeddings. Cache hits return in **< 30ms** at **\$0.00 model cost**.
8. **RAG Context Grounding**: Context retrieval via pgvector embeddings using Amazon Titan Text Embeddings v2 (1024 dimensions) with cosine distance search.
9. **Universal LLM Execution**: Executes via AWS Bedrock Converse API with automated backoff retry logic and unified token metrics.
10. **LLM Evaluation & Verification**: Real-time evaluation score for answer correctness, hallucination detection, and context adherence.
11. **Granular Cost Accounting**: Calculates precise micro-dollar costs using token pricing tables for prompt tokens, completion tokens, and cache write tokens.
12. **Canonical Audit Trail**: Emits structured audit and trace events into PostgreSQL for compliance, observability, and FinOps reporting.

---

## 🤖 Universal Model Catalog (Zero Credit Card Required)

Prometheus features a multi-vendor engine built on AWS Bedrock's unified **Converse API**. While third-party AWS Marketplace offerings typically enforce commercial payment instruments, **Prometheus unlocks 44 verified foundation models across 8 major AI labs that operate natively in your AWS account without requiring a credit card or marketplace subscription**:

| Provider | Models Supported | Latency Benchmark | Ideal Use Case |
|---|---|---|---|
| **Google** | `google.gemma-3-4b-it`<br/>`google.gemma-3-12b-it`<br/>`google.gemma-3-27b-it` | ⚡ **167ms – 967ms** | High-speed classification, summarization, multilingual |
| **DeepSeek** | `deepseek.v3-v1:0`<br/>`deepseek.v3.2` | ⚡ **317ms – 1,142ms** | Complex logical reasoning, math, code generation |
| **Qwen (Alibaba)** | `qwen.qwen3-32b-v1:0`<br/>`qwen.qwen3-coder-30b-a3b-v1:0`<br/>`qwen.qwen3-coder-480b-a35b-v1:0`<br/>`qwen.qwen3-235b-a22b-2507-v1:0`<br/>`qwen.qwen3-next-80b-a3b`<br/>`qwen.qwen3-vl-235b-a22b` | ⚡ **211ms – 1,007ms** | Polyglot coding, large context reasoning, vision-language |
| **Meta** | `meta.llama3-8b-instruct-v1:0`<br/>`meta.llama3-70b-instruct-v1:0` | ⚡ **548ms – 1,270ms** | General chat, instruction following, agentic workflows |
| **Mistral AI** | `mistral.mistral-7b-instruct-v0:2`<br/>`mistral.mixtral-8x7b-instruct-v0:1`<br/>`mistral.mistral-large-2402-v1:0`<br/>`mistral.mistral-large-3-675b-instruct`<br/>`mistral.ministral-3-3b-instruct`<br/>`mistral.ministral-3-8b-instruct`<br/>`mistral.ministral-3-14b-instruct`<br/>`mistral.voxtral-mini-3b-2507`<br/>`mistral.voxtral-small-24b-2507`<br/>`mistral.magistral-small-2509`<br/>`mistral.devstral-2-123b` | ⚡ **252ms – 716ms** | Low-latency inference, code analysis, agent reasoning |
| **Amazon** | `apac.amazon.nova-micro-v1:0`<br/>`apac.amazon.nova-lite-v1:0`<br/>`apac.amazon.nova-pro-v1:0`<br/>`global.amazon.nova-2-lite-v1:0` | ⚡ **465ms – 1,912ms** | Cost-minimized enterprise routing, multimodal tasks |
| **NVIDIA** | `nvidia.nemotron-nano-9b-v2`<br/>`nvidia.nemotron-nano-12b-v2`<br/>`nvidia.nemotron-nano-3-30b` | ⚡ **427ms** | On-device alignment, synthetic data evaluation |
| **Z.AI / Moonshot** | `zai.glm-4.7-flash`, `zai.glm-4.7`, `zai.glm-5`<br/>`moonshotai.kimi-k2.5` | ⚡ **231ms** | Extreme-speed lightweight tasks, high-concurrency |
| **Embeddings** | `amazon.titan-embed-text-v2:0`<br/>`amazon.titan-embed-image-v1` | ⚡ **150ms** | 1024-dim dense RAG vectors & multimodal embeddings |

---

## 💰 FinOps & Autonomous Governance Agents

Prometheus is not just a gateway; it is an **active FinOps management loop** designed to eliminate wasted AI spend:

* **Dynamic Policy Engine**: Multi-versioned policies (`v1` through `v5`) stored in PostgreSQL. Updating a policy automatically invalidates stale semantic cache entries and applies new budget constraints instantly across all nodes.
* **Autonomous FinOps Agent**: Runs via AWS EventBridge on a recurring schedule. Scans token telemetry, flags anomalous cost spikes, identifies budget overruns, and drafts optimization proposals (e.g., routing downgrades, cache TTL extensions).
* **Human-in-the-Loop (HITL) Gate**: Governance changes (budget changes, model bans, kill-switch triggers) can be configured to require explicit human approval via the web UI before activation.
* **Granular Micro-Cost Tracking**: Calculates spend per team, per user, per API key, and per request down to \$0.000001 precision.

```mermaid
sequenceDiagram
    autonumber
    actor User as Client
    participant GW as Prometheus API
    participant Cache as pgvector Cache
    participant LLM as Bedrock (Nova / Llama / Gemma)
    participant DB as RDS PostgreSQL

    User->>GW: POST /api/v1/chat {"query": "Explain quantum computing"}
    GW->>GW: 1. Auth & Rate Limit Validation
    GW->>GW: 2. PII Masking & Injection Check
    GW->>GW: 3. Router selects model tier
    GW->>Cache: 4. Check semantic similarity
    alt Semantic Cache Hit (Cosine >= 0.82)
        Cache-->>GW: Cached response + 100% cost reduction
        GW->>DB: Log trace (cost = $0.00, cache_hit = true)
        GW-->>User: ⚡ Return cached answer in <30ms ($0.00)
    else Cache Miss
        GW->>LLM: 5. Invoke selected foundation model
        LLM-->>GW: Generated response + token usage
        GW->>GW: 6. Run LLM evaluation judge
        GW->>Cache: 7. Store query embedding & response
        GW->>DB: 8. Persist canonical trace & financial audit
        GW-->>User: Return answer with citations & trace URL
    end
```

---

## 📊 Live Verification Benchmarks

Measurements taken from the live production infrastructure in `ap-south-1`:

```
┌──────────────────────────────────────┬────────────┬─────────────┬───────────┐
│ Scenario / Model                     │ Latency    │ Cost / Call │ Cache Hit │
├──────────────────────────────────────┼────────────┼─────────────┼───────────┤
│ Semantic Cache Hit (PostgreSQL)      │ 28 ms      │ $0.000000   │ TRUE      │
│ Google Gemma 3 4B                    │ 167 ms     │ $0.000034   │ FALSE     │
│ Z.AI GLM 4.7 Flash                   │ 231 ms     │ $0.000050   │ FALSE     │
│ Mistral 7B Instruct                  │ 252 ms     │ $0.000150   │ FALSE     │
│ DeepSeek V3.1                        │ 317 ms     │ $0.000218   │ FALSE     │
│ Qwen3 32B                            │ 237 ms     │ $0.000173   │ FALSE     │
│ Amazon Nova Micro (Cold Execution)   │ 465 ms     │ $0.000035   │ FALSE     │
│ Meta Llama 3 8B                      │ 548 ms     │ $0.000123   │ FALSE     │
│ Amazon Nova Lite (Strong Tier)       │ 1,340 ms   │ $0.000060   │ FALSE     │
│ Meta Llama 3 70B (Complex Reasoning) │ 1,270 ms   │ $0.002650   │ FALSE     │
│ Amazon Nova Pro (Premium Tier)       │ 1,883 ms   │ $0.001062   │ FALSE     │
└──────────────────────────────────────┴────────────┴─────────────┴───────────┘
```

---

## 🚀 Local Quickstart

### Prerequisites
* Python 3.11+
* Docker Desktop & Docker Compose
* Node.js 18+ (for Web UI)
* AWS CLI configured (optional, for real Bedrock integration)

### 1. Clone & Setup
```bash
git clone https://github.com/VortexQuasarX/project-prometheus.git
cd project-prometheus

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r app/requirements.txt
```

### 2. Environment Configuration
```bash
cp .env.example .env
```
Key configuration variables in `.env`:
```ini
# Provider: 'bedrock' for real AWS models, 'mock' for local offline testing
LLM_PROVIDER=bedrock
BEDROCK_REGION=ap-south-1

# Database: Local Docker PostgreSQL or AWS RDS
DATABASE_URL=postgresql://prometheus:prometheus@localhost:5432/prometheus

# Governance & FinOps
DEFAULT_DAILY_BUDGET_USD=5.0
REQUIRE_CACHE_CHECK=true
REQUIRE_RAG=true
```

### 3. Run with Docker Compose
```bash
docker compose up -d
```
This launches:
* **API Service**: `http://localhost:8000`
* **PostgreSQL + pgvector**: `localhost:5432`
* **Redis 7**: `localhost:6379`
* **Next.js Web Dashboard**: `http://localhost:3000`

---

## 📡 API Reference

### 1. Send Chat Request (`POST /api/v1/chat`)
```bash
curl -X POST "https://4oyzp80sy9.execute-api.ap-south-1.amazonaws.com/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: prometheus-admin" \
  -d '{
    "query": "Explain our cloud FinOps governance policy",
    "model": "apac.amazon.nova-micro-v1:0"
  }'
```

### 2. Update Governance Policy (`PUT /api/v1/policies`)
```bash
curl -X PUT "https://4oyzp80sy9.execute-api.ap-south-1.amazonaws.com/api/v1/policies" \
  -H "Content-Type: application/json" \
  -H "x-api-key: prometheus-admin" \
  -d '{
    "policy": {
      "daily_budget_usd": 10.0,
      "request_budget_usd": 0.05,
      "kill_switch_mode": "off",
      "allowed_models": ["google.gemma-3-4b-it", "deepseek.v3-v1:0", "apac.amazon.nova-micro-v1:0"]
    },
    "reason": "Expand model allowlist for Q3"
  }'
```

### 3. Ingest RAG Knowledge Documents (`POST /api/v1/ingest`)
```bash
curl -X POST "https://4oyzp80sy9.execute-api.ap-south-1.amazonaws.com/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -H "x-api-key: prometheus-admin" \
  -d '{
    "document_id": "finops-handbook",
    "title": "Enterprise Cloud FinOps Guide",
    "content": "All production AI workloads must adhere to unit cost metrics..."
  }'
```

### 4. Fetch Trace & Audit Trail (`GET /api/v1/traces/{request_id}`)
```bash
curl -X GET "https://4oyzp80sy9.execute-api.ap-south-1.amazonaws.com/api/v1/traces/req_6c3c34ad9c4c4902" \
  -H "x-api-key: prometheus-admin"
```

---

## 📂 Repository Structure

```
project-prometheus/
├── app/                        # Core backend FastAPI application
│   ├── api/v1/                 # REST endpoints (chat, policies, ingest, traces, agents)
│   ├── core/                   # Security, settings, logging, telemetry
│   ├── cost/                   # Token pricing matrix & FinOps estimators
│   ├── guardrails/             # PII masking, regex rules, injection filters
│   ├── providers/              # Universal Bedrock Converse, Titan, & Mock providers
│   ├── cache/                  # pgvector semantic cache implementation
│   ├── rag/                    # Vector chunking, indexing, & retrieval engine
│   └── agents/                 # FinOps & Reliability autonomous agents
├── web/                        # Next.js 14 Web UI Dashboard
│   ├── app/                    # App router (Playground, Policies, Budget, Traces, Audits)
│   ├── components/             # Tailwind & Radix UI visual components
│   └── lib/                    # API clients and state hooks
├── infra/                      # Terraform AWS Cloud Infrastructure
│   ├── main.tf                 # VPC, Lambda, API Gateway, RDS, Secrets Manager
│   ├── variables.tf            # Region, instance sizing, environment inputs
│   └── outputs.tf              # Live endpoints and resource identifiers
├── docs/                       # Architecture specs, system design, runbooks
├── tests/                      # Pytest suite (unit, integration, load, security)
├── Dockerfile.api              # Multi-stage production container with Lambda Web Adapter
├── Dockerfile.web              # Standalone Next.js production container
└── docker-compose.yml          # Local development stack (App + PG + Redis)
```

---

## 🔒 Security & Compliance

* **Timing-Safe Authentication**: API keys are hashed with SHA-256 and evaluated using constant-time comparisons to prevent timing side-channel attacks.
* **Zero PII Leakage**: Automated masking filters sanitize credit card numbers, social security numbers, email addresses, and phone numbers before queries reach foundation models.
* **Network Isolation**: All database and cache compute resources reside within private VPC subnets with AWS VPC Endpoints for S3, Secrets Manager, and Bedrock.
* **Audit Immutability**: Every transaction, policy update, agent action, and circuit breaker trip is immutably logged with microsecond timestamps.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
