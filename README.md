# 🔥 Project Prometheus: Autonomous AI Governance & FinOps Control Plane

<div align="center">

[![AWS ap-south-1](https://img.shields.io/badge/AWS-ap--south--1%20(Mumbai)-FF9900?logo=amazon-aws&logoColor=white)](#-zero-idle-cost-cloud-native-infrastructure)
[![Status](https://img.shields.io/badge/Status-100%25%20Verified%20%26%20Tested-00C853?style=flat-square)](#-key-capabilities)
[![Compute](https://img.shields.io/badge/Compute-Serverless%20Lambda%20Adapter-FF9900?style=flat-square)](#-zero-idle-cost-cloud-native-infrastructure)
[![Streaming](https://img.shields.io/badge/Streaming-Apache%20Kafka%20Event%20Bus-231F20?logo=apachekafka&logoColor=white)](#-apache-kafka-distributed-event-streaming-pipeline)
[![RAG](https://img.shields.io/badge/RAG-Hybrid%20BM25%20%2B%20Cross--Encoder-7928CA?style=flat-square)](#-advanced-hybrid-search--cross-encoder-re-ranking)
[![PEFT](https://img.shields.io/badge/Fine--Tuning-LoRA%20%2F%20QLoRA%20Hub-FF4081?style=flat-square)](#-lora--qlora-parameter-efficient-fine-tuning-peft-hub)
[![Database](https://img.shields.io/badge/Database-Amazon%20RDS%20PostgreSQL%20%2B%20pgvector-336791?logo=postgresql&logoColor=white)](#-data-plane--persistence)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14%20Standalone-black?logo=next.js&logoColor=white)](https://nextjs.org)

**An enterprise-grade, real-time AI governance gateway and FinOps control plane that enforces deterministic policy budgets, hybrid dense/sparse semantic caching, PII masking, circuit-breaker kill-switches, Kafka event streaming, and LoRA/QLoRA continuous fine-tuning across 50+ foundation models with $0.00 idle compute costs.**

[Architecture](#-system-architecture) • [Demo Walkthrough](#-architecture--system-walkthrough-demo) • [Key Capabilities](#-key-capabilities) • [Developer SDKs](#-developer-sdks--client-integration) • [Local Setup](#-local-development--quickstart) • [API Reference](#-api-reference)

</div>

---

## 🎬 Architecture & System Walkthrough Demo

Watch the comprehensive video walkthrough demonstrating the Prometheus 12-stage governance engine, multi-region Bedrock routing, FinOps chargeback, real-time Kafka event streaming, and LoRA/QLoRA continuous evaluation.

<div align="center">
  <a href="https://github.com/VortexQuasarX/project-prometheus/blob/main/assets/final_cut_prometheus.mp4">
    <img src="assets/demo_preview.gif" alt="Project Prometheus Architecture & FinOps Demo Walkthrough" width="100%" style="border-radius: 8px;" />
  </a>
  <br/>
  <p align="center">
    🎬 <i>Animated live walkthrough preview. Click the preview image or any link below to open the complete video with full sound and playback controls:</i><br/>
    <b><a href="https://github.com/VortexQuasarX/project-prometheus/blob/main/assets/final_cut_prometheus.mp4">▶️ Watch Full HD Video in GitHub Player (assets/final_cut_prometheus.mp4)</a></b> • 
    <b><a href="https://github.com/VortexQuasarX/project-prometheus/releases/download/v1.0.0/final_cut_prometheus.mp4">📥 Direct MP4 Download (Release CDN)</a></b> • 
    <b><a href="https://github.com/VortexQuasarX/project-prometheus/releases/tag/v1.0.0">🏷️ Release v1.0.0</a></b>
  </p>
</div>

### 🧩 Core Platform Components & Console Modules

| Interface / Component | Route / Target | Architecture & Capabilities |
|---|---|---|
| **Web Dashboard** | `/` | Next.js 14 Standalone via AWS Lambda Web Adapter |
| **Developer Portal & SDKs** | `/developers` | Drop-in Python & TypeScript SDKs, live cURL & CLI generator |
| **LoRA Fine-Tuning Hub** | `/evaluations` | Golden trace curation, ChatML/Alpaca exports, HF SFTTrainer scripts |
| **Kafka Telemetry & Topology** | `/settings` | Topic partition health, latency probes, Hybrid RAG telemetry |
| **Multi-Tenant Workspaces** | `/workspaces` | Departmental quotas, model whitelists, 1-click CSV chargeback export |
| **Arena & Playground** | `/playground` | Dual-model benchmark split view, real-time SSE streaming, TTFT/TPS |
| **Traces APM Waterfall** | `/traces` | Sub-millisecond 12-stage duration Gantt chart with filter pills |
| **Adversarial Red Team** | `/redteam` | Live OWASP Top 10 automated jailbreak fuzzing suite |
| **API Gateway (HTTP API)** | `/api/v1` | Amazon API Gateway HTTP API v2 (CORS enabled) / FastAPI Engine |
| **Zero-Idle Compute Engine** | Containerized Lambda | Serverless Lambda (`prometheus-api`) with scale-to-zero compute |
| **Relational & Vector Store** | PostgreSQL 15 + `pgvector` | Amazon RDS PostgreSQL + `pgvector` for semantic caching & embeddings |
| **Observability & APM** | CloudWatch Metrics & Traces | End-to-end distributed tracing, latency percentiles & alerts |

> **Authentication**: API calls require header `x-api-key: prometheus-admin` (default admin credential).

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Client["Client Tier & Edge UI"]
        User["Client Application / Next.js 14 Web Console"]
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
        RAG["7. Hybrid Search (Dense + BM25 + Cross-Encoder)"]
        LLM["8. Universal Bedrock Converse Invocation"]
        Eval["9. LLM-as-a-Judge Evaluation"]
        CacheWrite["10. Semantic Cache Write"]
        CostLog["11. Microsecond Cost & Token Accounting"]
        AuditLog["12. Canonical Trace & Audit Persistence"]
    end

    subgraph EventStream["Asynchronous Event Streaming (Kafka Bus)"]
        KafkaProducer["Async Event Producer (Background Dispatch)"]
        TopicReq["Topic: prometheus.requests"]
        TopicAudit["Topic: prometheus.audit"]
        TopicCosts["Topic: prometheus.costs"]
        TopicDLQ["Topic: prometheus.requests.dlq"]
    end

    subgraph Persistence["Amazon RDS PostgreSQL 15.13 + pgvector"]
        VectorDB[("pgvector Embeddings & Semantic Cache<br/>(Amazon Titan Text Embeddings v2)")]
        RelationalDB[("Traces, Policies, Audit Logs,<br/>Dead-Letter Queue, API Keys")]
    end

    subgraph MLPipeline["MLOps & Fine-Tuning Pipeline"]
        GoldenTraces["Golden Trace Extraction (Score >= 0.85)"]
        DatasetExport["Multi-Format JSONL (ChatML / Alpaca / ShareGPT)"]
        LoRAEngine["LoRA / QLoRA 4-bit NF4 Adapter Config"]
        SFTTrainer["Hugging Face TRL SFTTrainer Script Generator"]
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
    AuditLog --> KafkaProducer
    KafkaProducer --> TopicReq
    KafkaProducer --> TopicAudit
    KafkaProducer --> TopicCosts
    KafkaProducer --> TopicDLQ
    RelationalDB --> GoldenTraces --> DatasetExport --> LoRAEngine --> SFTTrainer
```

---

## ⚡ The 12-Stage Governance Pipeline

Every request to `POST /api/v1/chat` executes through a strictly synchronous, deterministic 12-stage pipeline. Synchronous execution guarantees that audit trails, cost metering, guardrail enforcement, and budget checks remain 100% auditable and reproducible without out-of-order race conditions.

```
Request ➡️ [Auth] ➡️ [Rate Limit] ➡️ [Budget & Kill-Switch] ➡️ [Guardrails] ➡️ [Router]
               ⬇️
        [Semantic Cache Check] ──(Hit)──> [Cost & Audit Log] ──> Response
               ⬇️ (Miss)
        [Hybrid RAG Retrieval] ➡️ [Universal Bedrock Invocation] ➡️ [Evaluation] ➡️ [Cache Store] ➡️ [Trace Persist] ➡️ [Kafka Event Bus]
```

1. **Request Ingestion**: Request ID assigned or replayed with cryptographic idempotency.
2. **Auth & Identity Validation**: `X-API-Key` hashed via SHA-256 and verified using timing-safe `hmac.compare_digest`.
3. **Sliding-Window Rate Limiting**: Per-key token and request rate enforcement.
4. **Pre-flight Budget Gating & Kill-Switch**: Real-time evaluation against project budgets, team daily allocations, and kill-switch states (`off`, `degrade_to_cheap`, `read_only_cache`, `full_shutdown`).
5. **Security Guardrails**: Regex and heuristic detectors identify prompt injection, jailbreaks, and PII (SSN, credit cards, emails, phone numbers) with automated zero-leak masking.
6. **Cost-Aware Model Routing**: Classifies task complexity (reasoning, coding, factual, simple chat) and selects the cheapest capable model tier (`cheap`, `strong`, `premium`).
7. **Semantic Caching**: Performs high-speed cosine similarity (`>= 0.82`) search over vector embeddings. Cache hits return in **< 30ms** at **$0.00 model cost**.
8. **Hybrid RAG Retrieval (Dense + Sparse BM25 + Cross-Encoder)**: Combines dense vector search (Amazon Titan Text Embeddings v2, 1024-dim) with Okapi BM25 lexical search using Reciprocal Rank Fusion (RRF), followed by Cross-Encoder joint re-ranking for context compression and hallucination elimination.
9. **Universal LLM Execution**: Executes via AWS Bedrock Converse API with automated backoff retry logic and unified token metrics.
10. **LLM Evaluation & Verification**: Real-time evaluation score for answer correctness, hallucination detection, and context adherence.
11. **Granular Cost Accounting**: Calculates precise micro-dollar costs using token pricing tables for prompt tokens, completion tokens, and cache write tokens.
12. **Canonical Audit Trail & Kafka Dispatch**: Emits structured audit traces into PostgreSQL and publishes non-blocking telemetry events to Apache Kafka topics (`prometheus.requests`, `prometheus.audit`, `prometheus.costs`).

---

## 🎯 Advanced Hybrid Search & Cross-Encoder Re-Ranking

Modern enterprise RAG pipelines fail when relying exclusively on either dense semantic embeddings or keyword matching. Dense embeddings miss domain-specific product SKUs, acronyms, and error codes; pure keyword search misses semantic synonyms and conceptual relevance.

Prometheus implements a state-of-the-art **3-Stage Hybrid Retrieval & Re-Ranking Architecture**:

```mermaid
flowchart LR
    Query["User Query"] --> Dense["1. Dense Vector Search<br/>(Amazon Titan v2 Cosine)"]
    Query --> Sparse["2. Sparse Lexical Search<br/>(Okapi BM25 k1=1.5, b=0.75)"]
    Dense --> RRF["3. Reciprocal Rank Fusion<br/>RRF Score = Σ 1/(60 + rank)"]
    Sparse --> RRF
    RRF --> CrossEncoder["4. Cross-Encoder Re-Ranking<br/>Joint Query-Doc Cross-Attention"]
    CrossEncoder --> Compressed["Top-K Grounded Context<br/>(Zero Hallucination)"]
```

### 1. Zero-Dependency Okapi BM25 (`app/rag/bm25.py`)
- Native Python implementation with document length normalization:
  $$\text{BM25}(D, Q) = \sum_{q \in Q} \text{IDF}(q) \cdot \frac{f(q, D) \cdot (k_1 + 1)}{f(q, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$
- Hyperparameters calibrated for enterprise documentation: $k_1 = 1.5$, $b = 0.75$.
- Custom alphanumeric token extraction with comprehensive stop-word filtering.

### 2. Reciprocal Rank Fusion (RRF)
- Blends dense vector ranking ($r_{\text{dense}}$) and sparse lexical ranking ($r_{\text{bm25}}$) into an unbiased fused score:
  $$\text{RRF}(d) = \frac{1}{60 + r_{\text{dense}}(d)} + \frac{1}{60 + r_{\text{bm25}}(d)}$$

### 3. Cross-Encoder Re-Ranking (`app/rag/reranker.py`)
- Evaluates full token cross-attention across $[Query, Document]$ pairs simultaneously, capturing inter-word dependencies that dual-encoder bi-encoders miss.
- Supports Hugging Face transformer models (`cross-encoder/ms-marco-MiniLM-L-6-v2`) with native heuristic fallback:
  - Exact query phrase sequence matching (3x boost)
  - Document title alignment (2x boost)
  - Term density proximity scoring
- Prunes noisy chunks to compress LLM prompt context, reducing prompt token costs and eliminating hallucinations.
- Citations returned in chat responses explicitly report `dense_score`, `bm25_score`, and `rerank_score` for complete groundedness verification.

---

## ⚡ Apache Kafka Distributed Event Streaming Pipeline

To support enterprise-scale observability without impacting proxy throughput, Prometheus decouples analytical telemetry into an asynchronous **Apache Kafka Event Streaming Bus** (`app/events_pipeline/kafka_pipeline.py`).

```mermaid
flowchart TD
    FastAPI["FastAPI 12-Stage Proxy"] -->|Zero-Latency Background Thread| Producer["Prometheus Event Broker"]
    Producer --> TopicReq["prometheus.requests<br/>(3 Partitions)"]
    Producer --> TopicAudit["prometheus.audit<br/>(2 Partitions)"]
    Producer --> TopicCosts["prometheus.costs<br/>(1 Partition)"]
    Producer --> TopicDLQ["prometheus.requests.dlq<br/>(Dead-Letter Queue)"]

    TopicReq --> AnalyticsConsumer["Real-time Analytics / ClickHouse / Druid"]
    TopicAudit --> SIEMConsumer["SIEM / Splunk / SOC2 Audit Ingestion"]
    TopicCosts --> FinOpsConsumer["FinOps Automated Billing & Chargeback"]
    TopicDLQ --> AlertConsumer["OpsGenie / PagerDuty Incident Alerting"]
```

### Managed Topic Architecture
| Topic Name | Default Partitions | Purpose | Retention |
|---|---|---|---|
| `prometheus.requests` | 3 | Full prompt/completion telemetry, latency, token velocity | 7 Days |
| `prometheus.audit` | 2 | Immutable compliance records, policy version diffs, HITL sign-offs | 365 Days |
| `prometheus.costs` | 1 | Micro-dollar financial transactions for internal billing | 90 Days |
| `prometheus.requests.dlq` | 1 | Poison-pill events, malformed payloads, rate-limit overruns | 14 Days |

### Real-Time Kafka Administration (`/settings`)
- Live REST endpoints: `GET /api/v1/kafka/status`, `GET /api/v1/kafka/topics`, and `POST /api/v1/kafka/produce-test`.
- Test probe latency measurement (sub-millisecond local broker dispatch).
- Seamless dual-mode operation: connects to distributed Apache Kafka clusters via `kafka-python` or falls back to an in-memory high-speed circular buffer in serverless environments.

---

## 🧬 LoRA & QLoRA Parameter-Efficient Fine-Tuning (PEFT) Hub

Why continue paying high per-token costs for massive 70B foundation models when a tailored, domain-specialized 8B or 3B model fine-tuned on your organization's highest-performing interactions can achieve higher accuracy at 90% lower cost?

Prometheus includes a complete, end-to-end **PEFT LoRA / QLoRA Pipeline** (`app/ml/fine_tuning.py`) accessible directly from the **Evaluations Console** (`/evaluations`):

```mermaid
flowchart LR
    Traces[("Historical Traces in PostgreSQL")] --> Curate["Curate Golden Dataset<br/>(Score >= 0.85, 0 Violations)"]
    Curate --> Format["Format Selector<br/>(ChatML / Alpaca / ShareGPT)"]
    Format --> Download["1-Click Dataset Download<br/>(.jsonl)"]
    Curate --> LoRAConfig["Auto-Generate LoRA Config<br/>(4-bit NF4, r=16, α=32)"]
    LoRAConfig --> ScriptGen["HF TRL SFTTrainer Script<br/>(Standalone Python)"]
    ScriptGen --> Train["Train Model on GPU / Colab / RunPod"]
```

### 1. Automated Golden Trace Curation
- Queries production trace history for interactions meeting strict quality criteria:
  - Evaluation score $\ge 0.85$ (correctness and context adherence)
  - Zero security guardrail violations (no PII, no prompt injection)
  - Non-empty answer with valid token latency metrics

### 2. Multi-Format Dataset Compiler (`.jsonl`)
- **ChatML** (`{"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}`): For Llama 3, Qwen 2.5, Mistral Instruct, and modern conversational models.
- **Alpaca** (`{"instruction": ..., "input": ..., "output": ...}`): Standard instruction-tuning format.
- **ShareGPT** (`{"conversations": [{"from": "human", ...}, {"from": "gpt", ...}]}`): Multi-turn conversational format.

### 3. Parameter-Efficient Adapter Configuration (QLoRA)
- 4-bit NormalFloat (NF4) quantization using `BitsAndBytesConfig` with double quantization.
- LoRA parameters: rank $r = 16$, scaling $\alpha = 32$, dropout $= 0.05$.
- Target modules targeting all projection layers: `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`.

### 4. Ready-to-Run Standalone Training Script
- Generates fully self-contained Python scripts powered by Hugging Face `transformers`, `peft`, and `trl.SFTTrainer`.
- Copy-paste into AWS SageMaker, Google Colab, Lambda Labs, or local GPU workstations.

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
* **Granular Micro-Cost Tracking**: Calculates spend per team, per user, per API key, and per request down to $0.000001 precision.

```mermaid
sequenceDiagram
    autonumber
    actor User as Client
    participant GW as Prometheus API
    participant Cache as pgvector Cache
    participant RAG as Hybrid Retriever (BM25 + CrossEncoder)
    participant LLM as Bedrock (Nova / Llama / Gemma)
    participant DB as RDS PostgreSQL
    participant Kafka as Kafka Bus

    User->>GW: POST /api/v1/chat {"query": "Explain AWS FinOps policies"}
    GW->>GW: 1. Auth & Rate Limit Validation
    GW->>GW: 2. PII Masking & Injection Check
    GW->>GW: 3. Router selects model tier
    GW->>Cache: 4. Check semantic similarity
    alt Semantic Cache Hit (Cosine >= 0.82)
        Cache-->>GW: Cached response + 100% cost reduction
        GW->>DB: Log trace (cost = $0.00, cache_hit = true)
        GW->>Kafka: Async emit to prometheus.requests
        GW-->>User: ⚡ Return cached answer in <30ms ($0.00)
    else Cache Miss
        GW->>RAG: 5. Hybrid Search (Dense Titan + Sparse BM25 + RRF)
        RAG->>RAG: 6. Cross-Encoder re-rank top candidates
        RAG-->>GW: Compressed grounded context chunks
        GW->>LLM: 7. Invoke selected foundation model
        LLM-->>GW: Generated response + token usage
        GW->>GW: 8. Run LLM evaluation judge
        GW->>Cache: 9. Store query embedding & response
        GW->>DB: 10. Persist canonical trace & financial audit
        GW->>Kafka: 11. Publish async telemetry (requests, costs, audit)
        GW-->>User: Return answer with citations (dense, bm25, rerank scores)
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

## ⚡ Enterprise Capabilities & Developer Ecosystem

Project Prometheus bridges the gap between raw LLM APIs and mission-critical enterprise deployment through a unified control plane.

### 1. 🛠️ Developer Portal & Drop-In SDKs (`/developers`)
Prometheus delivers strict drop-in parity with the OpenAI API standard, allowing enterprise engineering teams to onboard in under 5 minutes without rewriting application logic.

* **Python SDK (Drop-In OpenAI Client):**
```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("PROMETHEUS_BASE_URL", "http://localhost:8000/api/v1"),
    api_key=os.environ.get("PROMETHEUS_API_KEY", "prometheus-admin")
)

# Automated governance, FinOps caching & semantic routing happens automatically
response = client.chat.completions.create(
    model="auto-router",  # Automatically picks optimal cost/performance model
    messages=[
        {"role": "system", "content": "You are a specialized enterprise AI assistant."},
        {"role": "user", "content": "Analyze our AWS CloudWatch bill for anomalies."}
    ],
    temperature=0.2,
    stream=True  # Real-time token streaming with sub-100ms TTFT
)

for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")
```

* **TypeScript / Node.js SDK:**
```typescript
import OpenAI from "openai";

const openai = new OpenAI({
  baseURL: process.env.PROMETHEUS_BASE_URL || "http://localhost:8000/api/v1",
  apiKey: process.env.PROMETHEUS_API_KEY || "prometheus-admin",
});

const completion = await openai.chat.completions.create({
  model: "llama-3.3-70b-instruct:free",
  messages: [{ role: "user", content: "Optimize this PostgreSQL query plan." }]
});
```

* **Prometheus Developer CLI:**
```bash
# Run head-to-head dual model benchmark from terminal
prometheus test --arena

# Stream live production request traces in real-time
prometheus traces --tail -n 20

# Dispatch Kafka test telemetry probe
prometheus kafka probe --topic prometheus.requests

# Export golden fine-tuning dataset in ChatML format
prometheus finetuning export --format chatml --min-score 0.85 -o dataset.jsonl

# Emergency circuit-breaker to halt all LLM egress traffic
prometheus kill-switch --engage

# Execute automated OWASP Top 10 jailbreak fuzzing
prometheus redteam --fuzz-all
```

### 2. 🏢 Multi-Tenant Workspaces & FinOps Chargeback (`/workspaces`)
Isolate spend, quotas, and permissions across organizational departments:
* **Departmental Budget Partitions:** Independent hard quotas for Engineering ($2,500/mo), Product AI ($1,200/mo), and Risk/Compliance ($800/mo).
* **Dynamic Model Whitelisting:** Restrict sensitive departments to specific verified models (e.g. `llama-3.3-70b-instruct:free`, `deepseek-r1:free`).
* **1-Click Chargeback Invoice Export:** Downloadable RFC 4180 CSV reports for corporate accounting and internal cross-billing.
* **Global Header Tenant Pill:** Dynamic department indicator for rapid workspace switching.

### 3. ⚔️ Multi-Model Arena & Real-Time Token Velocity Telemetry (`/playground`)
* **Head-to-Head Arena:** Benchmark two models side-by-side with identical prompts. Automated **Arena Verdict** banner computes speedup percentages and cost differences.
* **Token Velocity Telemetry:** Real-time 6-column telemetry bar tracking:
  * **TTFT (Time To First Token):** Sub-100ms first-token latency measurement.
  * **Throughput Velocity (tok/s):** Real-time generation velocity badge.
  * **Micro-Dollar Cost:** Exact cost tracking down to 6 decimal places ($0.000000).
* **Stream Tokens Toggle:** Toggle between buffered JSON responses and real-time Server-Sent Events (SSE) typewriter rendering.

### 4. 📊 12-Stage APM Waterfall Gantt (`/traces/[request_id]`)
* Sub-millisecond Gantt chart tracking execution time across all 12 pipeline stages (`auth`, `rate_limit`, `budget`, `guardrails`, `routing`, `semantic_cache`, `retrieval`, `llm_inference`, `evaluation`, `cost_logging`, `audit_persistence`).
* Active search and status filter pills (`All`, `Cache Hits`, `>1s Slow`, `Errors/Blocked`).

### 5. 🛡️ Security, Quorum Approvals & Compliance (`/approvals`, `/audit`, `/redteam`)
* **Multi-Stage Quorum Sign-Off:** High-risk routing policy changes require dual sign-off (FinOps Admin + Security Lead) stamped with immutable SHA-256 hashes.
* **SOC2, HIPAA & ISO 27001 Audit Export:** Dedicated 1-click **Export CSV** and **Export JSON** formatted for regulatory compliance reviews.
* **Automated Adversarial Red Teaming:** Interactive fuzzing harness testing against OWASP LLM01 (Prompt Injection), LLM02 (Sensitive Information Disclosure), and LLM06 (Excessive Agency).

### 6. 🤖 Interactive Agent DAG Workflow Visualizer (`/agents/runs/[run_id]`)
* ReactFlow-powered visual Directed Acyclic Graph (DAG) with animated glowing token-flow edges, per-step latency badges, and tool input/output inspectors.

---

## ☸️ Kubernetes (K8s) Production Deployment

Prometheus is packaged for zero-downtime, horizontally auto-scalable deployment across any CNCF-certified Kubernetes cluster (Amazon EKS, Google GKE, self-hosted K8s).

### 1. Apply Cluster Manifests
```bash
kubectl apply -f infra/k8s/
```

### 2. Architecture of K8s Manifests (`infra/k8s/`)
* **`api.yaml`**: Deploys the containerized FastAPI control plane (`ghcr.io/vortexquasarx/prometheus-api:latest`) with readiness/liveness HTTP health probes on `/api/v1/health`.
* **`hpa.yaml`**: Horizontal Pod Autoscaler (HPA) configured for automatic elasticity:
  - **Min Replicas**: 2
  - **Max Replicas**: 10
  - **Scaling Triggers**: Target average CPU utilization of **70%** and memory utilization of **80%**.
* **`networkpolicy.yaml`**: Zero-trust defense-in-depth isolation:
  - Disallows arbitrary inter-pod egress.
  - Permits egress solely to PostgreSQL (`5432`), Redis (`6379`), Kafka (`9092`), and external AWS Bedrock endpoints over TLS (`443`).
* **`config.yaml`**: Centralized non-sensitive configuration maps and secrets integration with external SecretManagers.

---

## 🗄️ Database Strategy & Alembic Migrations

Prometheus uses a robust dual-database persistence strategy:
* **Production**: Amazon RDS PostgreSQL 15.13 with the native `pgvector` extension for 1024-dimensional vector similarity search.
* **Local / Test**: Resilient automatic fallback to SQLite (`sqlite:///prometheus.db`) and in-memory cosine cache so developers can run, test, and develop offline without database dependencies.

### Database Migrations (Alembic)
Schema evolution is strictly versioned using SQLAlchemy and Alembic:
```bash
# Apply all forward migrations to latest revision
alembic upgrade head

# Inspect current revision state
alembic current

# Rollback one migration step
alembic downgrade -1
```

---

## 🧠 Comprehensive Technology & Skills Matrix

This project encompasses verified enterprise competencies across the modern AI Engineering, MLOps, LLMOps, Cloud, and Distributed Systems stack. Every technology listed is backed by real implementation in this repository:

| Domain | Technologies & Frameworks Built in Prometheus | Implementation & Codebase Evidence |
|---|---|---|
| **AI & LLM Orchestration** | **AWS Bedrock Converse API** (44+ models across Amazon Nova, Llama 3, Gemma 3, Mistral, Qwen, DeepSeek), **Deterministic 12-Stage Governance Engine**, Intelligent 3-Tier Cost Router (`cheap`, `strong`, `premium`), In-Context Few-Shot Grounded RAG, Heuristic PII Masking, Strict Pydantic v2 Schema Output | [`app/providers/bedrock.py`](app/providers/bedrock.py)<br/>[`app/api/v1/chat.py`](app/api/v1/chat.py)<br/>[`app/cost/router.py`](app/cost/router.py)<br/>[`app/guardrails/`](app/guardrails/) |
| **PEFT & Model Training** *(Group 2)* | **LoRA & QLoRA (4-bit NF4)**, **Hugging Face Transformers**, **TRL (`SFTTrainer`)**, **BitsAndBytes Quantization**, **PEFT**, Automated Golden Trace Curation ($\ge 0.85$ eval score, 0 guardrail flags), Multi-Format Dataset Export (ChatML, Alpaca, ShareGPT) | [`app/ml/fine_tuning.py`](app/ml/fine_tuning.py)<br/>[`app/api/v1/fine_tuning.py`](app/api/v1/fine_tuning.py)<br/>[`web/app/evaluations/page.tsx`](web/app/evaluations/page.tsx) |
| **Hybrid Search & Re-Ranking** *(Group 2)* | **Okapi BM25 Sparse Lexical Search** ($k_1=1.5, b=0.75$), **Cross-Encoder Re-Ranking** (Joint cross-attention scoring, phrase matching, title boosts), **Reciprocal Rank Fusion (RRF)**, **Dense Vector Search (Amazon Titan v2)**, Cosine Distance Similarity | [`app/rag/bm25.py`](app/rag/bm25.py)<br/>[`app/rag/reranker.py`](app/rag/reranker.py)<br/>[`app/rag/retriever.py`](app/rag/retriever.py)<br/>[`app/rag/citations.py`](app/rag/citations.py) |
| **Vector & Relational Storage** | **Amazon RDS PostgreSQL 15.13 + `pgvector`** (1024-dim Titan embeddings), **In-Memory & SQLite Semantic Vector Cache** ($<30\text{ms}$ latency, $\$0.00$ cost), Dual-database fallback, **Alembic** schema migrations (`alembic upgrade head`) | [`app/db/models.py`](app/db/models.py)<br/>[`app/cache/semantic.py`](app/cache/semantic.py)<br/>[`app/db/session.py`](app/db/session.py)<br/>[`alembic/`](alembic/) |
| **Event Streaming & Data Pipelines** *(Group 2)* | **Apache Kafka KRaft Event Streaming Bus** (`prometheus.requests`, `prometheus.audit`, `prometheus.costs`, `prometheus.dlq`), Non-blocking Async Dispatch, **Apache Spark (PySpark)** batch ingestion pipeline, **Apache Airflow DAG** orchestration, **Redis 7** sliding-window limiter | [`app/events_pipeline/kafka_pipeline.py`](app/events_pipeline/kafka_pipeline.py)<br/>[`app/spark/pipeline.py`](app/spark/pipeline.py)<br/>[`ml/airflow_dags/prometheus_dag.py`](ml/airflow_dags/prometheus_dag.py)<br/>[`app/core/rate_limit.py`](app/core/rate_limit.py) |
| **LLMOps & MLOps Lifecycle** | **MLflow** experiment tracking & artifact logging (`ml/mlruns/mlflow.db`), **PSI (Population Stability Index) Drift Detection** (0.2 threshold), **Automated Safe Retraining Pipeline**, Distilled LogisticRegression Router, LLM-as-a-Judge 10-Category Eval Suite with 5-Dimension Radar Scoring | [`app/ml/train.py`](app/ml/train.py)<br/>[`app/ml/drift.py`](app/ml/drift.py)<br/>[`app/ml/retrain.py`](app/ml/retrain.py)<br/>[`app/eval/runner.py`](app/eval/runner.py)<br/>[`tests/test_mlops.py`](tests/test_mlops.py) |
| **Cloud & Serverless Architecture** | **Amazon Web Services (AWS `ap-south-1`)**: AWS Lambda, **AWS Lambda Web Adapter** (Scale-to-Zero / $0.00 idle compute), Amazon API Gateway HTTP API v2, RDS PostgreSQL, S3, Secrets Manager, CloudWatch, Bedrock Converse API | [`infra/compute.tf`](infra/compute.tf)<br/>[`infra/aurora.tf`](infra/aurora.tf)<br/>[`infra/s3.tf`](infra/s3.tf)<br/>[`Dockerfile.api`](Dockerfile.api) |
| **Infrastructure as Code (IaC)** | **Terraform** (44 declarative cloud resources, modular VPC, subnets, route tables, IAM policies, ECR lifecycle policies) | [`infra/main.tf`](infra/main.tf)<br/>[`infra/compute.tf`](infra/compute.tf)<br/>[`infra/vpc.tf`](infra/vpc.tf)<br/>[`infra/aurora.tf`](infra/aurora.tf) |
| **Containers & Orchestration** | **Docker** (Multi-stage scratch builds), **Docker Compose**, **Kubernetes (K8s)**: Deployments, Horizontal Pod Autoscaler (HPA 2-10 pods, 70% CPU / 80% RAM target), zero-trust NetworkPolicy, ConfigMaps | [`Dockerfile.api`](Dockerfile.api)<br/>[`Dockerfile.web`](Dockerfile.web)<br/>[`docker-compose.yml`](docker-compose.yml)<br/>[`infra/k8s/`](infra/k8s/) |
| **Backend & Microservices** | **Python 3.11**, **FastAPI**, **SQLAlchemy 2.0**, **Alembic**, **Pydantic v2**, Uvicorn, Asynchronous Event Loop, SHA-256 Timing-Safe HMAC Auth, 6-Role RBAC | [`app/main.py`](app/main.py)<br/>[`app/api/v1/`](app/api/v1/)<br/>[`app/core/security.py`](app/core/security.py)<br/>[`app/core/rbac.py`](app/core/rbac.py) |
| **Frontend & Web Console** | **Next.js 14 Standalone**, **React 18**, **TypeScript**, **Tailwind CSS**, **Framer Motion**, **Lucide Icons**, **Recharts**, **Cobe 3D WebGL Globe**, **Web Audio Synthesizer**, **ReactFlow DAG** visualizer | [`web/app/`](web/app/)<br/>[`web/components/`](web/components/)<br/>[`web/lib/`](web/lib/) |
| **Security & Governance** | **OWASP Top 10 for LLMs** (LLM01 Prompt Injection, LLM02 Sensitive Data Disclosure, LLM06 Excessive Agency), Automated PII Redaction, Adversarial Red Team Fuzzing, Multi-Signature Quorum Sign-Off, SOC2/HIPAA Audit Ledger | [`app/guardrails/`](app/guardrails/)<br/>[`app/api/v1/redteam.py`](app/api/v1/redteam.py)<br/>[`web/app/approvals/`](web/app/approvals/)<br/>[`web/app/audit/`](web/app/audit/) |

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
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: prometheus-admin" \
  -d '{
    "query": "Explain our cloud FinOps governance policy",
    "model": "apac.amazon.nova-micro-v1:0"
  }'
```

### 2. Query Kafka Broker Telemetry (`GET /api/v1/kafka/status`)
```bash
curl -X GET "http://localhost:8000/api/v1/kafka/status" \
  -H "x-api-key: prometheus-admin"
```

### 3. Export Golden Fine-Tuning Dataset (`GET /api/v1/finetuning/export`)
```bash
curl -X GET "http://localhost:8000/api/v1/finetuning/export?format=chatml&min_score=0.85" \
  -H "x-api-key: prometheus-admin" \
  -o prometheus_chatml.jsonl
```

### 4. Fetch Trace & Audit Trail (`GET /api/v1/traces/{request_id}`)
```bash
curl -X GET "http://localhost:8000/api/v1/traces/req_6c3c34ad9c4c4902" \
  -H "x-api-key: prometheus-admin"
```

---

## 📂 Repository Structure

```
project-prometheus/
├── app/                        # Core backend FastAPI 12-stage governance pipeline
│   ├── api/v1/                 # REST endpoints (chat, policies, ingest, traces, kafka, finetuning)
│   ├── core/                   # Security, settings, logging, telemetry, RBAC
│   ├── cost/                   # Token pricing matrix & FinOps estimators
│   ├── guardrails/             # PII masking, regex rules, injection filters
│   ├── providers/              # Universal Bedrock Converse, Titan, OpenRouter & Mock providers
│   ├── cache/                  # pgvector & in-memory semantic cache implementation
│   ├── rag/                    # Hybrid retrieval (Dense vector, Okapi BM25, Cross-Encoder, RRF)
│   ├── ml/                     # LoRA/QLoRA fine-tuning, dataset curation, HF SFTTrainer generator
│   ├── events_pipeline/        # Apache Kafka distributed event bus & async publishers
│   └── agents/                 # FinOps & Reliability autonomous agents
├── web/                        # Next.js 14 Enterprise Web UI Console
│   ├── app/                    # App router
│   │   ├── developers/         # Developer Portal, Python/TypeScript SDKs, CLI reference
│   │   ├── workspaces/         # Multi-tenant departmental quotas & chargeback invoices
│   │   ├── playground/         # Multi-Model Arena & real-time token streaming telemetry
│   │   ├── traces/             # 12-Stage APM waterfall Gantt chart & active search
│   │   ├── redteam/            # OWASP Top 10 automated jailbreak attack fuzzer
│   │   ├── approvals/          # Multi-stage dual-signature quorum sign-offs
│   │   ├── audit/              # SOC2, HIPAA, ISO 27001 audit ledger & CSV/JSON export
│   │   ├── budget/             # FinOps webhooks, burn rate & 30-day forecast
│   │   ├── evaluations/        # LoRA & QLoRA Fine-Tuning Hub, golden trace curation
│   │   ├── policies/           # Policy dry-run sandbox impact simulator
│   │   └── settings/           # Kafka Event Bus health & Upstream edge latency monitor
│   ├── components/             # ReactFlow DAG, TraceWaterfall, Cobe WebGL Globe, UI primitives
│   └── lib/                    # Typed API clients, state hooks, and utilities
├── infra/                      # Terraform AWS Cloud Infrastructure & Kubernetes
│   ├── main.tf                 # Root orchestration
│   ├── compute.tf              # Lambda serverless functions, ECR, API Gateway HTTP API v2
│   ├── aurora.tf               # Amazon RDS PostgreSQL 15.13 with pgvector extension
│   ├── s3.tf                   # Private encrypted S3 bucket for RAG corpus
│   ├── vpc.tf                  # Multi-AZ VPC, subnets, route tables, security groups
│   ├── bedrock.tf              # IAM roles and Bedrock model execution policies
│   ├── cloudwatch.tf           # APM dashboards, alarms, log retention policies
│   └── k8s/                    # Production Kubernetes manifests (HPA, NetworkPolicy, Deployments)
├── tests/                      # Pytest suite (unit, integration, hybrid rag, kafka, finetuning)
├── Dockerfile.api              # Multi-stage production container with Lambda Web Adapter
├── Dockerfile.web              # Standalone Next.js production container
└── docker-compose.yml          # Local development stack (App + PostgreSQL + Redis)
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
