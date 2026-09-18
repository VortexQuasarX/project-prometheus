"""Fine-Tuning & LoRA REST API endpoints.

Provides endpoints to query golden trace statistics, export fine-tuning datasets
in ChatML/Alpaca/ShareGPT formats, and retrieve generated QLoRA SFT training scripts.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import require_api_key
from app.db.session import get_db
from app.ml.fine_tuning import (
    curate_golden_dataset,
    export_dataset_jsonl,
    generate_lora_config,
    generate_sft_training_script,
    get_finetuning_stats,
)

router = APIRouter(prefix="/finetuning", tags=["finetuning"])


class ExportRequest(BaseModel):
    format: str = "chatml"
    min_score: float = 0.85
    limit: int = 500


@router.get("/stats")
def finetuning_stats(
    db: Session = Depends(get_db),
    _: Any = Depends(require_api_key),
) -> dict[str, Any]:
    """Retrieve counts and statistics of available golden traces eligible for fine-tuning."""
    return get_finetuning_stats(session=db)


@router.get("/config")
def finetuning_config(
    base_model: str = Query(default="meta-llama/Meta-Llama-3-8B-Instruct"),
    r: int = Query(default=16),
    lora_alpha: int = Query(default=32),
    quantization: str = Query(default="4bit"),
    _: Any = Depends(require_api_key),
) -> dict[str, Any]:
    """Generate production HuggingFace PEFT / LoRA adapter configuration."""
    return generate_lora_config(
        base_model=base_model,
        r=r,
        lora_alpha=lora_alpha,
        quantization=quantization,
    )


@router.get("/training-script")
def finetuning_script(
    base_model: str = Query(default="meta-llama/Meta-Llama-3-8B-Instruct"),
    _: Any = Depends(require_api_key),
) -> dict[str, str]:
    """Generate ready-to-run Hugging Face TRL SFTTrainer Python script."""
    script = generate_sft_training_script(base_model=base_model)
    return {"script": script, "framework": "Hugging Face TRL + PEFT + BitsAndBytes"}


@router.post("/export")
def finetuning_export(
    req: ExportRequest,
    db: Session = Depends(get_db),
    _: Any = Depends(require_api_key),
) -> Response:
    """Export curated golden traces into a downloadable JSONL file for model fine-tuning."""
    pairs = curate_golden_dataset(session=db, min_score=req.min_score, limit=req.limit)
    jsonl_content = export_dataset_jsonl(pairs, output_format=req.format)

    filename = f"prometheus_lora_{req.format}.jsonl"
    return Response(
        content=jsonl_content,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
