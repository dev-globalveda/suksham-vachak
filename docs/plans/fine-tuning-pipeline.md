# Cricket Commentary Fine-Tuning Pipeline

> **Document Version**: 1.0
> **Created**: January 8, 2025
> **Status**: Planning

---

## Overview

This document outlines the pipeline for fine-tuning LLMs on cricket commentary data and deploying them to Raspberry Pi 5 for edge inference.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FINE-TUNING PIPELINE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │ 1. DATA     │───▶│ 2. TRAIN    │───▶│ 3. MERGE    │───▶│ 4. DEPLOY   │  │
│  │             │    │             │    │             │    │             │  │
│  │ Collect &   │    │ QLoRA on    │    │ Merge +     │    │ Ollama on   │  │
│  │ Prepare     │    │ Cloud GPU   │    │ Quantize    │    │ Pi 5        │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Data Collection & Preparation

### Data Sources

| Source             | Type                | Size (est) | Format    |
| ------------------ | ------------------- | ---------- | --------- |
| **Cricsheet**      | Ball-by-ball events | ~200MB     | JSON      |
| **ESPNcricinfo**   | Text commentary     | ~100MB     | HTML/Text |
| **Wisden**         | Match reports       | ~50MB      | Text      |
| **Iconic moments** | Curated examples    | ~10MB      | Text      |

### Data Schema

```json
{
  "instruction": "Generate cricket commentary in the style of Richie Benaud.",
  "input": {
    "event": {
      "type": "boundary_four",
      "batter": "V Kohli",
      "bowler": "JM Anderson",
      "runs": 4,
      "is_boundary": true
    },
    "context": {
      "score": "245/3",
      "overs": 45.3,
      "phase": "death_overs",
      "pressure": "high",
      "target": 320
    },
    "persona": "benaud"
  },
  "output": "Four. Kohli's timing there. Exquisite."
}
```

### Data Preparation Script

```python
# scripts/prepare_training_data.py

from pathlib import Path
import json
from suksham_vachak.parser import CricsheetParser
from suksham_vachak.context import ContextBuilder
from suksham_vachak.personas import BENAUD, GREIG, DOSHI

def prepare_cricsheet_data(data_dir: Path, output_path: Path):
    """Convert Cricsheet JSON to training format."""
    training_examples = []

    for json_file in data_dir.glob("*.json"):
        parser = CricsheetParser(json_file)
        context_builder = ContextBuilder(parser.match_info)

        for event in parser.parse_all_innings():
            rich_context = context_builder.build(event)

            # Generate training examples for each persona
            for persona in [BENAUD, GREIG, DOSHI]:
                example = {
                    "instruction": f"Generate cricket commentary in the style of {persona.name}.",
                    "input": {
                        "event": {
                            "type": event.event_type.value,
                            "batter": event.batter,
                            "bowler": event.bowler,
                            "runs": event.runs_total,
                            "is_wicket": event.is_wicket,
                            "is_boundary": event.is_boundary,
                        },
                        "context": {
                            "score": rich_context.match.score_string,
                            "phase": rich_context.match.phase.value,
                            "pressure": rich_context.pressure.value,
                        },
                        "persona": persona.name.lower().replace(" ", "_"),
                    },
                    # Output will be filled by human annotation or LLM generation
                    "output": ""
                }
                training_examples.append(example)

    # Save to JSONL format
    with output_path.open("w") as f:
        for example in training_examples:
            f.write(json.dumps(example) + "\n")

    return len(training_examples)
```

### Data Augmentation

```python
# Use Claude to generate training data (supervised fine-tuning bootstrap)

async def generate_training_outputs(examples: list[dict]) -> list[dict]:
    """Use Claude to generate initial training outputs."""
    from anthropic import Anthropic

    client = Anthropic()

    for example in examples:
        persona = example["input"]["persona"]
        event = example["input"]["event"]

        prompt = f"""
        You are {persona}. Generate brief cricket commentary for:
        Event: {event['type']}
        Batter: {event['batter']} vs Bowler: {event['bowler']}

        {"ONE WORD OR SHORT PHRASE ONLY." if "benaud" in persona else "Be dramatic but concise."}
        """

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )

        example["output"] = response.content[0].text.strip()

    return examples
```

---

## Phase 2: Training (Cloud GPU)

### Recommended Setup

| Platform             | GPU         | Cost      | Training Time (7B) |
| -------------------- | ----------- | --------- | ------------------ |
| **Google Colab Pro** | T4/A100     | $10/mo    | 4-8 hours          |
| **Lambda Labs**      | A100 (40GB) | $1.10/hr  | 2-4 hours          |
| **RunPod**           | A100        | $0.79/hr  | 2-4 hours          |
| **Vast.ai**          | Various     | ~$0.50/hr | 3-6 hours          |

### QLoRA Training Script

```python
# scripts/train_qlora.py

"""
QLoRA Fine-tuning for Cricket Commentary

Usage:
    python scripts/train_qlora.py \
        --base_model Qwen/Qwen2.5-7B \
        --train_data data/training/cricket_commentary.jsonl \
        --output_dir ./models/cricket-qwen-7b-lora \
        --epochs 3
"""

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
import torch

def train_qlora(
    base_model: str = "Qwen/Qwen2.5-7B",
    train_data: str = "data/training/cricket_commentary.jsonl",
    output_dir: str = "./models/cricket-qwen-7b-lora",
    epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-4,
    lora_r: int = 64,
    lora_alpha: int = 16,
):
    """Fine-tune a model with QLoRA."""

    # 4-bit quantization config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    # Load base model
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    # Prepare model for training
    model = prepare_model_for_kbit_training(model)

    # LoRA config
    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=learning_rate,
        bf16=True,
        logging_steps=10,
        save_strategy="epoch",
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
    )

    # Load dataset
    from datasets import load_dataset
    dataset = load_dataset("json", data_files=train_data, split="train")

    # Format prompts
    def format_prompt(example):
        return f"""### Instruction: {example['instruction']}

### Input:
{json.dumps(example['input'], indent=2)}

### Response:
{example['output']}"""

    # Train
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        tokenizer=tokenizer,
        args=training_args,
        formatting_func=format_prompt,
        max_seq_length=512,
    )

    trainer.train()

    # Save adapter
    trainer.save_model(output_dir)
    print(f"LoRA adapter saved to: {output_dir}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", default="Qwen/Qwen2.5-7B")
    parser.add_argument("--train_data", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--epochs", type=int, default=3)
    args = parser.parse_args()

    train_qlora(
        base_model=args.base_model,
        train_data=args.train_data,
        output_dir=args.output_dir,
        epochs=args.epochs,
    )
```

### Google Colab Notebook

```python
# Fine_Tune_Cricket_Commentary.ipynb

# Cell 1: Install dependencies
!pip install transformers peft trl bitsandbytes accelerate datasets

# Cell 2: Mount drive and upload data
from google.colab import drive
drive.mount('/content/drive')

# Cell 3: Upload training data
!mkdir -p data/training
# Upload cricket_commentary.jsonl to data/training/

# Cell 4: Run training
!python train_qlora.py \
    --base_model Qwen/Qwen2.5-7B \
    --train_data data/training/cricket_commentary.jsonl \
    --output_dir /content/drive/MyDrive/models/cricket-qwen-7b-lora \
    --epochs 3

# Cell 5: Test the model
from peft import AutoPeftModelForCausalLM

model = AutoPeftModelForCausalLM.from_pretrained(
    "/content/drive/MyDrive/models/cricket-qwen-7b-lora",
    device_map="auto"
)

prompt = """### Instruction: Generate cricket commentary in the style of Richie Benaud.

### Input:
{"event": {"type": "boundary_four", "batter": "V Kohli", "bowler": "JM Anderson"}}

### Response:
"""

inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
outputs = model.generate(**inputs, max_new_tokens=50)
print(tokenizer.decode(outputs[0]))
```

---

## Phase 3: Merge & Quantize

### Merge LoRA Adapter

```python
# scripts/merge_lora.py

from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer

def merge_lora_weights(
    adapter_path: str,
    output_path: str,
):
    """Merge LoRA weights into base model."""

    # Load model with adapter
    model = AutoPeftModelForCausalLM.from_pretrained(
        adapter_path,
        device_map="cpu",
        torch_dtype="auto",
    )

    # Merge weights
    merged_model = model.merge_and_unload()

    # Save merged model
    merged_model.save_pretrained(output_path)

    # Save tokenizer
    tokenizer = AutoTokenizer.from_pretrained(adapter_path)
    tokenizer.save_pretrained(output_path)

    print(f"Merged model saved to: {output_path}")
```

### Convert to GGUF (for Ollama)

```bash
# On your local machine (not Pi)

# Clone llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

# Install requirements
pip install -r requirements.txt

# Convert to GGUF
python convert_hf_to_gguf.py \
    /path/to/merged_model \
    --outfile cricket-qwen-7b-f16.gguf \
    --outtype f16

# Quantize to Q4_K_M (recommended for Pi 5)
./llama-quantize \
    cricket-qwen-7b-f16.gguf \
    cricket-qwen-7b-q4_k_m.gguf \
    Q4_K_M

# Result: ~5GB model file
```

### Quantization Options

| Quantization | Size (7B) | Quality   | Pi 5 Speed  | Recommended    |
| ------------ | --------- | --------- | ----------- | -------------- |
| Q8_0         | ~8GB      | Best      | 3-5 tok/s   | No (too slow)  |
| Q6_K         | ~6GB      | Very Good | 4-6 tok/s   | Memory OK      |
| **Q4_K_M**   | ~5GB      | Good      | 6-8 tok/s   | **Yes**        |
| Q4_0         | ~4GB      | Decent    | 8-10 tok/s  | Speed priority |
| Q3_K_M       | ~3.5GB    | OK        | 10-12 tok/s | Testing only   |

---

## Phase 4: Deploy to Pi 5

### Create Ollama Modelfile

```dockerfile
# Modelfile
FROM ./cricket-qwen-7b-q4_k_m.gguf

TEMPLATE """{{ if .System }}{{ .System }}
{{ end }}{{ if .Prompt }}### Input:
{{ .Prompt }}

### Response:
{{ end }}"""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
PARAMETER stop "### Input:"
PARAMETER stop "### Response:"

SYSTEM """You are a cricket commentary assistant trained on decades of cricket knowledge.
Generate brief, authentic commentary in the requested persona's style."""
```

### Deploy Script

```bash
#!/bin/bash
# scripts/deploy_to_pi.sh

PI_HOST="pi5.local"
MODEL_FILE="cricket-qwen-7b-q4_k_m.gguf"
MODELFILE="Modelfile"

# Copy model to Pi
echo "Copying model to Pi 5..."
scp $MODEL_FILE $PI_HOST:~/models/
scp $MODELFILE $PI_HOST:~/models/

# Create Ollama model on Pi
ssh $PI_HOST << 'EOF'
cd ~/models
ollama create cricket-qwen -f Modelfile
ollama list
EOF

echo "Model deployed! Test with:"
echo "  ssh $PI_HOST 'ollama run cricket-qwen \"Kohli hits a four\"'"
```

### Test Deployment

```bash
# On Pi 5

# List models
ollama list

# Test inference
ollama run cricket-qwen "Generate Benaud-style commentary: Kohli hits a boundary"

# Benchmark
curl -X POST http://localhost:11434/api/generate \
  -d '{
    "model": "cricket-qwen",
    "prompt": "Kohli hits a four",
    "stream": false
  }'
```

---

## Evaluation Workflow

### A/B Testing Script

```python
# scripts/ab_test_models.py

from suksham_vachak.eval import ModelBenchmark, QualityEvaluator, EvaluationReport

def run_ab_test(
    baseline_model: str = "qwen2.5:7b",
    fine_tuned_model: str = "cricket-qwen:latest",
):
    """Compare baseline vs fine-tuned model."""

    benchmark = ModelBenchmark()
    evaluator = QualityEvaluator()
    report = EvaluationReport()

    models = [baseline_model, fine_tuned_model]

    for model in models:
        print(f"\nEvaluating: {model}")

        # Speed test
        speed = benchmark.run_speed_test(model, num_samples=50)

        # Quality test
        quality = evaluator.evaluate_model(model)

        report.add_result(model, speed, quality)

    # Print comparison
    report.print_summary()

    # Save report
    report.save(f"ab_test_{baseline_model.replace(':', '_')}_vs_{fine_tuned_model.replace(':', '_')}.json")

if __name__ == "__main__":
    run_ab_test()
```

---

## Cost Estimation

| Phase            | Resource                  | Cost     |
| ---------------- | ------------------------- | -------- |
| **Data Prep**    | Claude API (10K examples) | ~$20     |
| **Training**     | A100 (4 hours)            | ~$5-10   |
| **Quantization** | Local (Mac/PC)            | Free     |
| **Deployment**   | Pi 5 (owned)              | Free     |
| **Total**        |                           | **~$30** |

---

## Timeline

| Phase            | Duration      | Deliverable             |
| ---------------- | ------------- | ----------------------- |
| Data Collection  | 2 days        | 10K+ training examples  |
| Data Preparation | 1 day         | Formatted JSONL dataset |
| Training         | 4-8 hours     | LoRA adapter            |
| Merge & Quantize | 2 hours       | GGUF model file         |
| Deployment       | 1 hour        | Running on Pi 5         |
| Evaluation       | 1 day         | A/B test report         |
| **Total**        | **~4-5 days** |                         |

---

## Next Steps

1. [ ] Prepare training data from existing Cricsheet matches
2. [ ] Generate initial training outputs using Claude
3. [ ] Set up Google Colab training notebook
4. [ ] Train first model iteration
5. [ ] Quantize and deploy to Pi 5
6. [ ] Run evaluation harness
7. [ ] Iterate based on results

---

_"A well-trained model, like a well-coached batsman, knows when to play and when to leave."_
