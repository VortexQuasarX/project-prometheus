import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    peft_type: "LORA",
    base_model_name_or_path: "meta-llama/Meta-Llama-3-8B-Instruct",
    r: 16,
    lora_alpha: 32,
    lora_dropout: 0.05,
    target_modules: [
      "q_proj",
      "k_proj",
      "v_proj",
      "o_proj",
      "gate_proj",
      "up_proj",
      "down_proj",
    ],
    quantization_config: {
      load_in_4bit: true,
      bnb_4bit_quant_type: "nf4",
      bnb_4bit_use_double_quant: true,
      bnb_4bit_compute_dtype: "bfloat16",
    },
    training_args: {
      per_device_train_batch_size: 4,
      gradient_accumulation_steps: 2,
      learning_rate: 0.0002,
      num_train_epochs: 3,
      warmup_ratio: 0.03,
      lr_scheduler_type: "cosine",
      optim: "paged_adamw_8bit",
      fp16: false,
      bf16: true,
      logging_steps: 10,
    },
  });
}
