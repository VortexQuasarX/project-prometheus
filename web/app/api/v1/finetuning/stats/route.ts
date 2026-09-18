import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    curated_samples: 142,
    average_eval_score: 0.968,
    estimated_token_count: 58400,
    available_formats: ["chatml", "alpaca", "sharegpt"],
    recommended_base_model: "meta-llama/Meta-Llama-3-8B-Instruct",
    peft_method: "QLoRA (4-bit NF4)",
  });
}
