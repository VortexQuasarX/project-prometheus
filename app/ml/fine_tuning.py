"""LoRA / QLoRA Parameter-Efficient Fine-Tuning (PEFT) Pipeline.

Curates high-scoring golden traces from the Prometheus governance ledger and compiles
them into Alpaca, ChatML, and ShareGPT formats for fine-tuning smaller, cheaper models.
Generates PEFT LoRA adapter configurations and ready-to-run Hugging Face SFTTrainer scripts.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "curate_golden_dataset",
    "export_dataset_jsonl",
    "generate_lora_config",
    "generate_sft_training_script",
    "get_finetuning_stats",
]

_SEED_FINE_TUNING_PAIRS = [
    {
        "query": "Explain how Prometheus semantic caching eliminates cloud model spend.",
        "answer": "Prometheus semantic caching computes high-dimensional vector embeddings of incoming prompts and queries an indexed vector database (e.g. pgvector) using cosine similarity. If an incoming query has a similarity score >= 0.82 with an existing cached query, Prometheus returns the stored answer immediately in under 350ms for $0.00 cost, completely bypassing foundation model invocation.",
        "eval_score": 0.98,
    },
    {
        "query": "What happens when an employee sends credit card numbers or PII into an LLM prompt?",
        "answer": "Prometheus guardrails intercept the request during Stage 4 before any external model call. Regex and entity recognition filters detect the credit card or PII and either masks them (e.g. [REDACTED_CARD]) or safely rejects the prompt with zero cost incurred, logging the incident to the immutable audit ledger for compliance review.",
        "eval_score": 0.96,
    },
    {
        "query": "How does the Prometheus budget kill-switch prevent surprise AWS bills?",
        "answer": "Prometheus tracks cumulative micro-dollar spending in real time. If a department or key reaches its configured warning ratio (70%), alerts fire to Slack and Discord. If spending hits the critical quota (90-100%), the automated circuit-breaker trips, cutting non-critical traffic or forcing fallback to zero-cost models to guarantee budget caps.",
        "eval_score": 0.95,
    },
    {
        "query": "Compare dense vector search against BM25 sparse lexical search in RAG pipelines.",
        "answer": "Dense vector search embeds text into continuous semantic vector space, excelling at conceptual and thematic matching. BM25 sparse lexical search evaluates exact token frequencies and inverse document frequencies, excelling at rare keywords, acronyms, and product IDs. Prometheus Hybrid Search combines both using Reciprocal Rank Fusion (RRF) and Cross-Encoder re-ranking for optimal retrieval precision.",
        "eval_score": 0.97,
    },
]


def curate_golden_dataset(
    session: Any = None,
    min_score: float = 0.85,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Fetch completed requests with high evaluation scores and clean guardrail status."""
    pairs: list[dict[str, Any]] = list(_SEED_FINE_TUNING_PAIRS)

    if session is not None:
        try:
            from app.db.models import Request

            rows = (
                session.query(Request)
                .filter(Request.evaluation_score >= min_score)
                .filter(Request.guardrail_status == "passed")
                .order_by(Request.evaluation_score.desc())
                .limit(limit)
                .all()
            )
            for r in rows:
                if r.query and r.answer:
                    pairs.append(
                        {
                            "query": r.query,
                            "answer": r.answer,
                            "eval_score": round(float(r.evaluation_score or 0.9), 4),
                            "model": r.model or "unknown",
                            "request_id": r.request_id,
                        }
                    )
        except Exception as e:
            logger.debug("Could not query DB requests for fine-tuning: %s", e)

    return pairs


def export_dataset_jsonl(
    pairs: list[dict[str, Any]],
    output_format: str = "chatml",
) -> str:
    """Format pairs into Alpaca, ChatML, or ShareGPT JSONL string."""
    lines: list[str] = []
    fmt = output_format.lower()

    for item in pairs:
        q = item.get("query", "")
        a = item.get("answer", "")
        if not q or not a:
            continue

        if fmt == "alpaca":
            record = {
                "instruction": q,
                "input": "",
                "output": a,
            }
        elif fmt == "sharegpt":
            record = {
                "conversations": [
                    {"from": "human", "value": q},
                    {"from": "gpt", "value": a},
                ]
            }
        else:  # Default ChatML
            record = {
                "messages": [
                    {"role": "system", "content": "You are Prometheus AI, a specialized enterprise assistant."},
                    {"role": "user", "content": q},
                    {"role": "assistant", "content": a},
                ]
            }
        lines.append(json.dumps(record, ensure_ascii=False))

    return "\n".join(lines)


def generate_lora_config(
    base_model: str = "meta-llama/Meta-Llama-3-8B-Instruct",
    r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    quantization: str = "4bit",
) -> dict[str, Any]:
    """Generate production HuggingFace PEFT / LoRA adapter configuration."""
    return {
        "peft_type": "LORA",
        "base_model_name_or_path": base_model,
        "r": r,
        "lora_alpha": lora_alpha,
        "lora_dropout": lora_dropout,
        "target_modules": [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        "bias": "none",
        "task_type": "CAUSAL_LM",
        "quantization_config": {
            "load_in_4bit": quantization == "4bit",
            "load_in_8bit": quantization == "8bit",
            "bnb_4bit_quant_type": "nf4",
            "bnb_4bit_use_double_quant": True,
            "bnb_4bit_compute_dtype": "bfloat16",
        },
        "training_args": {
            "per_device_train_batch_size": 4,
            "gradient_accumulation_steps": 4,
            "learning_rate": 2e-4,
            "num_train_epochs": 3,
            "warmup_ratio": 0.03,
            "lr_scheduler_type": "cosine",
            "optim": "paged_adamw_8bit" if quantization == "4bit" else "adamw_torch",
            "fp16": False,
            "bf16": True,
            "logging_steps": 10,
        },
    }


def generate_sft_training_script(
    base_model: str = "meta-llama/Meta-Llama-3-8B-Instruct",
    dataset_path: str = "prometheus_golden_traces.jsonl",
    output_dir: str = "./prometheus-lora-adapter",
) -> str:
    """Generate a ready-to-run Supervised Fine-Tuning script using Hugging Face TRL."""
    return f'''# Auto-generated by Project Prometheus LoRA/QLoRA Pipeline
import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from trl import SFTTrainer

# 1. 4-Bit NormalFloat (NF4) QLoRA Configuration
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)

# 2. Load Base Model and Tokenizer
model_id = "{base_model}"
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.bfloat16,
)
model = prepare_model_for_kbit_training(model)

# 3. LoRA Adapter Hyperparameters (Rank=16, Alpha=32)
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
)

# 4. Load Curated Prometheus Golden Dataset
dataset = load_dataset("json", data_files="{dataset_path}")

# 5. Training Arguments
training_args = TrainingArguments(
    output_dir="{output_dir}",
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    num_train_epochs=3,
    bf16=True,
    logging_steps=10,
    save_strategy="epoch",
    optim="paged_adamw_8bit",
)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset["train"],
    peft_config=peft_config,
    max_seq_length=2048,
    tokenizer=tokenizer,
    args=training_args,
)

print("Starting Prometheus QLoRA fine-tuning...")
trainer.train()
trainer.model.save_pretrained("{output_dir}")
tokenizer.save_pretrained("{output_dir}")
print("Fine-tuning complete! LoRA adapter saved to {output_dir}")
'''


def get_finetuning_stats(session: Any = None) -> dict[str, Any]:
    """Compute aggregate statistics for available golden training data."""
    dataset = curate_golden_dataset(session=session)
    count = len(dataset)
    avg_score = sum(d.get("eval_score", 0.0) for d in dataset) / count if count > 0 else 0.0
    estimated_tokens = sum((len(d.get("query", "")) + len(d.get("answer", ""))) // 4 for d in dataset)

    return {
        "curated_samples": count,
        "average_eval_score": round(avg_score, 4),
        "estimated_token_count": estimated_tokens,
        "available_formats": ["chatml", "alpaca", "sharegpt"],
        "recommended_base_model": "meta-llama/Meta-Llama-3-8B-Instruct",
        "peft_method": "QLoRA (4-bit NF4)",
    }
