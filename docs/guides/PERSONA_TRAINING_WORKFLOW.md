# Persona Training Workflow Guide

> **The Heart of Suksham Vachak** - This guide covers the complete workflow for creating AI commentators that capture both the voice and style of legendary cricket commentators.

## Overview

Creating a virtual commentator persona requires training **two separate models**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PERSONA = VOICE + STYLE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────────────────┐      ┌─────────────────────────┐          │
│   │      VOICE MODEL        │      │      STYLE MODEL        │          │
│   │    (TTS Cloning)        │      │    (LLM Fine-tuning)    │          │
│   ├─────────────────────────┤      ├─────────────────────────┤          │
│   │ Input: Audio samples    │      │ Input: Text transcripts │          │
│   │ Output: Cloned voice    │      │ Output: Writing style   │          │
│   │ Tool: ElevenLabs/Coqui  │      │ Tool: QLoRA + Ollama    │          │
│   └─────────────────────────┘      └─────────────────────────┘          │
│                                                                          │
│   "Sounds like Benaud"             "Writes like Benaud"                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Target Personas

| Persona           | Style Characteristics                      | Voice Characteristics               |
| ----------------- | ------------------------------------------ | ----------------------------------- |
| **Richie Benaud** | Minimalist, understated, "marvelous"       | Australian accent, measured pace    |
| **Tony Greig**    | Energetic, dramatic, "absolutely massive!" | South African-English, enthusiastic |
| **Susheel Doshi** | Hindi-English mix, emotional, "shabash!"   | Indian accent, rapid-fire delivery  |
| **Harsha Bhogle** | Analytical, poetic, storytelling           | Indian-English, warm tone           |

---

## Phase 1: Data Collection

### 1.1 Text Data (for LLM Style Training)

**Sources for commentary transcripts:**

| Source                | Type               | How to Obtain             |
| --------------------- | ------------------ | ------------------------- |
| YouTube auto-captions | Raw transcripts    | `yt-dlp --write-auto-sub` |
| Cricinfo ball-by-ball | Written commentary | Web scraping              |
| Commentary books      | Curated quotes     | Manual transcription      |
| Podcast transcripts   | Long-form          | Whisper transcription     |
| Twitter/X archives    | Short snippets     | API or manual             |

**Minimum data requirements:**

| Quality        | Samples | Estimated Words |
| -------------- | ------- | --------------- |
| Minimum viable | 500     | ~25,000         |
| Good quality   | 2,000   | ~100,000        |
| Excellent      | 5,000+  | ~250,000+       |

**Directory structure:**

```
data/personas/
├── benaud/
│   ├── raw/
│   │   ├── youtube_transcripts/
│   │   ├── cricinfo_commentary/
│   │   └── book_quotes/
│   ├── processed/
│   │   └── training_data.jsonl
│   └── metadata.yaml
├── greig/
│   └── ...
└── doshi/
    └── ...
```

**Data format (JSONL):**

```json
{"event": "Boundary through covers", "commentary": "Marvelous shot.", "persona": "benaud", "source": "1999_wcf"}
{"event": "Wicket falls", "commentary": "And he's gone. Bowled him.", "persona": "benaud", "source": "ashes_2005"}
```

### 1.2 Audio Data (for Voice Cloning)

**Requirements by provider:**

| Provider   | Min Duration | Ideal Duration | Audio Quality   |
| ---------- | ------------ | -------------- | --------------- |
| ElevenLabs | 1 minute     | 10-30 minutes  | Clean, no music |
| Coqui XTTS | 6 seconds    | 5-10 minutes   | 22kHz+ mono     |
| OpenVoice  | 10 seconds   | 1-5 minutes    | Clear speech    |

**Audio preparation checklist:**

- [ ] Remove background music/crowd noise
- [ ] Remove co-commentator voices
- [ ] Normalize volume levels
- [ ] Split into 10-30 second clips
- [ ] Export as WAV (22kHz or higher)

**Directory structure:**

```
data/voices/
├── benaud/
│   ├── raw/
│   │   ├── ashes_2005_clip1.mp3
│   │   └── wcf_1999_clip2.mp3
│   ├── cleaned/
│   │   ├── clip_001.wav
│   │   └── clip_002.wav
│   └── voice_profile.json
└── greig/
    └── ...
```

---

## Phase 2: LLM Style Training (QLoRA)

### 2.1 Data Preparation

**Script: `scripts/prepare_persona_data.py`**

```python
#!/usr/bin/env python3
"""Prepare persona training data from raw transcripts."""

import json
from pathlib import Path
from dataclasses import dataclass

@dataclass
class TrainingExample:
    """Single training example for persona fine-tuning."""
    system: str
    user: str
    assistant: str

def create_training_example(
    event: str,
    commentary: str,
    persona_name: str,
    persona_style: str,
) -> TrainingExample:
    """Create a single training example."""
    return TrainingExample(
        system=f"You are {persona_name}, the legendary cricket commentator. {persona_style}",
        user=f"Commentate on this cricket event: {event}",
        assistant=commentary,
    )

def prepare_dataset(
    persona: str,
    input_dir: Path,
    output_file: Path,
) -> int:
    """Prepare training dataset for a persona."""

    # Persona style definitions
    PERSONA_STYLES = {
        "benaud": "Respond in 1-5 words maximum. Be understated and elegant. Never use exclamation marks.",
        "greig": "Be dramatic and enthusiastic. Use vivid descriptions. Exclamations are encouraged!",
        "doshi": "Mix Hindi and English naturally. Be emotional and passionate. Use 'shabash' and 'kya baat hai'.",
        "bhogle": "Be analytical yet poetic. Tell the story behind the numbers. Use cricket metaphors.",
    }

    examples = []

    # Load raw data
    for jsonl_file in input_dir.glob("*.jsonl"):
        with open(jsonl_file) as f:
            for line in f:
                data = json.loads(line)
                example = create_training_example(
                    event=data["event"],
                    commentary=data["commentary"],
                    persona_name=persona.title(),
                    persona_style=PERSONA_STYLES.get(persona, ""),
                )
                examples.append({
                    "messages": [
                        {"role": "system", "content": example.system},
                        {"role": "user", "content": example.user},
                        {"role": "assistant", "content": example.assistant},
                    ]
                })

    # Write training file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    return len(examples)

if __name__ == "__main__":
    import sys
    persona = sys.argv[1] if len(sys.argv) > 1 else "benaud"

    count = prepare_dataset(
        persona=persona,
        input_dir=Path(f"data/personas/{persona}/raw"),
        output_file=Path(f"data/personas/{persona}/processed/training_data.jsonl"),
    )
    print(f"Prepared {count} training examples for {persona}")
```

### 2.2 Cloud Training (Google Colab / Lambda Labs)

**Training script: `scripts/train_persona_qlora.py`**

```python
#!/usr/bin/env python3
"""QLoRA fine-tuning script for persona training.

Run on cloud GPU (Colab Pro, Lambda Labs, RunPod).
Requires: torch, transformers, peft, bitsandbytes, datasets
"""

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer

# Configuration
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
PERSONA = "benaud"  # Change for each persona
OUTPUT_DIR = f"./outputs/{PERSONA}-qlora"
DATA_FILE = f"data/personas/{PERSONA}/processed/training_data.jsonl"

# QLoRA configuration
QLORA_CONFIG = LoraConfig(
    r=64,                      # LoRA rank
    lora_alpha=16,             # LoRA alpha
    target_modules=[           # Layers to fine-tune
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

# 4-bit quantization config
BNB_CONFIG = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

def train():
    """Run QLoRA fine-tuning."""

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Load model with 4-bit quantization
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=BNB_CONFIG,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, QLORA_CONFIG)

    # Print trainable parameters
    model.print_trainable_parameters()

    # Load dataset
    dataset = load_dataset("json", data_files=DATA_FILE, split="train")

    # Format function for chat template
    def format_chat(example):
        return tokenizer.apply_chat_template(
            example["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )

    # Training arguments
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        weight_decay=0.01,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        logging_steps=10,
        save_steps=100,
        save_total_limit=3,
        bf16=True,
        optim="paged_adamw_8bit",
        report_to="none",
    )

    # Initialize trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        formatting_func=format_chat,
        max_seq_length=512,
        packing=True,
    )

    # Train
    trainer.train()

    # Save LoRA adapter
    trainer.save_model(OUTPUT_DIR)
    print(f"LoRA adapter saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    train()
```

### 2.3 Merge and Convert to GGUF

**Script: `scripts/merge_and_convert.py`**

```python
#!/usr/bin/env python3
"""Merge LoRA adapter and convert to GGUF for Ollama."""

import subprocess
from pathlib import Path

# Configuration
PERSONA = "benaud"
BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
LORA_PATH = f"./outputs/{PERSONA}-qlora"
MERGED_PATH = f"./outputs/{PERSONA}-merged"
GGUF_PATH = f"./outputs/{PERSONA}.gguf"
QUANTIZATION = "Q4_K_M"  # Best for Pi 5

def merge_lora():
    """Merge LoRA weights into base model."""
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print("Loading base model...")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype="auto",
        device_map="auto",
    )

    print("Loading LoRA adapter...")
    model = PeftModel.from_pretrained(base_model, LORA_PATH)

    print("Merging weights...")
    merged_model = model.merge_and_unload()

    print(f"Saving merged model to {MERGED_PATH}...")
    merged_model.save_pretrained(MERGED_PATH)

    # Save tokenizer too
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.save_pretrained(MERGED_PATH)

    print("Merge complete!")

def convert_to_gguf():
    """Convert merged model to GGUF format."""
    print("Converting to GGUF...")

    # Requires llama.cpp to be installed
    cmd = [
        "python", "llama.cpp/convert_hf_to_gguf.py",
        MERGED_PATH,
        "--outfile", GGUF_PATH.replace(".gguf", "-f16.gguf"),
        "--outtype", "f16",
    ]
    subprocess.run(cmd, check=True)

    print(f"Quantizing to {QUANTIZATION}...")
    cmd = [
        "./llama.cpp/llama-quantize",
        GGUF_PATH.replace(".gguf", "-f16.gguf"),
        GGUF_PATH,
        QUANTIZATION,
    ]
    subprocess.run(cmd, check=True)

    print(f"GGUF model saved to {GGUF_PATH}")

if __name__ == "__main__":
    merge_lora()
    convert_to_gguf()
```

### 2.4 Deploy to Ollama

**Create Modelfile:**

```dockerfile
# Modelfile.benaud
FROM ./benaud-q4_k_m.gguf

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 2048

SYSTEM """You are Richie Benaud, the legendary Australian cricket commentator.

Style guidelines:
- Maximum 5 words per response
- Never use exclamation marks
- Understated elegance
- Signature phrases: "marvelous", "remarkable", "simply extraordinary"
- Let the cricket speak for itself
"""
```

**Deploy commands:**

```bash
# Create Ollama model from Modelfile
ollama create suksham-benaud -f Modelfile.benaud

# Test the model
ollama run suksham-benaud "Commentate: Kohli hits a boundary through covers"

# List all persona models
ollama list | grep suksham
```

---

## Phase 3: Voice Cloning (TTS)

### 3.1 Audio Preparation

**Script: `scripts/prepare_voice_samples.py`**

```python
#!/usr/bin/env python3
"""Prepare audio samples for voice cloning."""

import subprocess
from pathlib import Path

def clean_audio(input_file: Path, output_file: Path) -> None:
    """Clean and normalize audio for voice cloning."""
    cmd = [
        "ffmpeg", "-i", str(input_file),
        "-af", "highpass=f=80,lowpass=f=8000,afftdn=nf=-25,loudnorm=I=-16:LRA=11:TP=-1.5",
        "-ar", "22050",
        "-ac", "1",
        "-y", str(output_file),
    ]
    subprocess.run(cmd, check=True)

def split_into_clips(input_file: Path, output_dir: Path, clip_duration: int = 30) -> int:
    """Split audio into clips of specified duration."""
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-i", str(input_file),
        "-f", "segment",
        "-segment_time", str(clip_duration),
        "-c", "copy",
        str(output_dir / "clip_%03d.wav"),
    ]
    subprocess.run(cmd, check=True)

    return len(list(output_dir.glob("*.wav")))

def prepare_persona_voice(persona: str) -> None:
    """Prepare all voice samples for a persona."""
    raw_dir = Path(f"data/voices/{persona}/raw")
    cleaned_dir = Path(f"data/voices/{persona}/cleaned")
    cleaned_dir.mkdir(parents=True, exist_ok=True)

    for audio_file in raw_dir.glob("*.*"):
        if audio_file.suffix.lower() in [".mp3", ".wav", ".m4a", ".flac"]:
            output_file = cleaned_dir / f"{audio_file.stem}.wav"
            print(f"Processing: {audio_file.name}")
            clean_audio(audio_file, output_file)

    print(f"Cleaned audio saved to {cleaned_dir}")

if __name__ == "__main__":
    import sys
    persona = sys.argv[1] if len(sys.argv) > 1 else "benaud"
    prepare_persona_voice(persona)
```

### 3.2 ElevenLabs Voice Cloning

**Script: `scripts/create_elevenlabs_voice.py`**

```python
#!/usr/bin/env python3
"""Create ElevenLabs voice clone from audio samples."""

import os
from pathlib import Path
from elevenlabs import ElevenLabs, Voice, VoiceSettings

def create_voice_clone(
    persona: str,
    name: str,
    description: str,
) -> str:
    """Create a cloned voice on ElevenLabs."""
    client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

    # Collect audio files
    audio_dir = Path(f"data/voices/{persona}/cleaned")
    audio_files = list(audio_dir.glob("*.wav"))[:25]  # Max 25 files

    if not audio_files:
        raise ValueError(f"No audio files found in {audio_dir}")

    print(f"Uploading {len(audio_files)} audio samples...")

    # Create voice clone
    voice = client.clone(
        name=name,
        description=description,
        files=[str(f) for f in audio_files],
    )

    print(f"Voice created: {voice.voice_id}")

    # Save voice ID for later use
    config_file = Path(f"data/voices/{persona}/voice_profile.json")
    import json
    with open(config_file, "w") as f:
        json.dump({
            "provider": "elevenlabs",
            "voice_id": voice.voice_id,
            "name": name,
            "persona": persona,
        }, f, indent=2)

    return voice.voice_id

# Persona voice configurations
PERSONA_VOICES = {
    "benaud": {
        "name": "Richie Benaud",
        "description": "Australian cricket commentator. Measured, elegant, understated delivery.",
    },
    "greig": {
        "name": "Tony Greig",
        "description": "Energetic cricket commentator. South African-English accent, enthusiastic.",
    },
    "doshi": {
        "name": "Susheel Doshi",
        "description": "Hindi cricket commentator. Passionate, rapid delivery, Hindi-English mix.",
    },
}

if __name__ == "__main__":
    import sys
    persona = sys.argv[1] if len(sys.argv) > 1 else "benaud"
    config = PERSONA_VOICES[persona]

    voice_id = create_voice_clone(
        persona=persona,
        name=config["name"],
        description=config["description"],
    )
    print(f"Voice clone created: {voice_id}")
```

### 3.3 Update TTS Provider Configuration

**File: `config/personas.yaml`**

```yaml
# Persona configurations for Suksham Vachak
personas:
  benaud:
    display_name: "Richie Benaud"
    language: "en-AU"
    style:
      is_minimalist: true
      max_words: 5
      signature_phrases:
        - "marvelous"
        - "remarkable"
        - "simply extraordinary"
      avoid_phrases:
        - "!"
        - "incredible"
        - "amazing"
    voice:
      provider: "elevenlabs"
      voice_id: "${ELEVENLABS_BENAUD_VOICE_ID}"
      settings:
        stability: 0.75
        similarity_boost: 0.85
        style: 0.3
    llm:
      model: "suksham-benaud" # Custom Ollama model
      temperature: 0.7
      max_tokens: 20

  greig:
    display_name: "Tony Greig"
    language: "en-GB"
    style:
      is_minimalist: false
      max_words: 30
      signature_phrases:
        - "absolutely massive"
        - "gone!"
        - "what a shot"
    voice:
      provider: "elevenlabs"
      voice_id: "${ELEVENLABS_GREIG_VOICE_ID}"
      settings:
        stability: 0.6
        similarity_boost: 0.8
        style: 0.7
    llm:
      model: "suksham-greig"
      temperature: 0.8
      max_tokens: 50

  doshi:
    display_name: "Susheel Doshi"
    language: "hi-IN"
    style:
      is_minimalist: false
      max_words: 25
      signature_phrases:
        - "shabash"
        - "kya baat hai"
        - "arre wah"
      code_switching: true # Hindi-English mix
    voice:
      provider: "elevenlabs"
      voice_id: "${ELEVENLABS_DOSHI_VOICE_ID}"
      settings:
        stability: 0.5
        similarity_boost: 0.9
        style: 0.8
    llm:
      model: "suksham-doshi"
      temperature: 0.85
      max_tokens: 40
```

---

## Phase 4: Evaluation

### 4.1 Style Evaluation

Test that the fine-tuned model captures the persona's style:

```bash
# Evaluate persona model quality
python scripts/evaluate_models.py --model suksham-benaud --quality --output eval/benaud_quality.json

# Compare against base model
python scripts/evaluate_models.py --compare suksham-benaud qwen2.5:7b --quality
```

**Persona-specific test cases:**

```python
# Add to suksham_vachak/eval/quality.py
PERSONA_TEST_CASES = {
    "benaud": [
        {
            "event": "Kohli hits a cover drive for four",
            "expected_traits": ["under 5 words", "no exclamation", "understated"],
            "bad_responses": ["What an incredible shot!", "Kohli smashes it!"],
        },
        {
            "event": "Wicket! Clean bowled!",
            "expected_traits": ["calm", "descriptive", "not hyperbolic"],
            "bad_responses": ["GONE!", "Unbelievable!", "Sensational!"],
        },
    ],
    "greig": [
        {
            "event": "Six over long-on",
            "expected_traits": ["enthusiastic", "exclamation allowed", "dramatic"],
            "good_markers": ["!", "massive", "tremendous"],
        },
    ],
}
```

### 4.2 Voice Evaluation

**Script: `scripts/evaluate_voice.py`**

```python
#!/usr/bin/env python3
"""Evaluate voice clone quality."""

from pathlib import Path
from suksham_vachak.tts import TTSEngine
from suksham_vachak.personas import load_persona

def evaluate_voice(persona: str, test_texts: list[str]) -> dict:
    """Generate samples and evaluate voice quality."""
    persona_config = load_persona(persona)
    tts = TTSEngine()

    results = []
    output_dir = Path(f"eval/voice_samples/{persona}")
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, text in enumerate(test_texts):
        output_path = output_dir / f"sample_{i:03d}.mp3"

        # Generate audio
        result = tts.synthesize(
            text=text,
            voice_id=persona_config.voice.voice_id,
            output_path=output_path,
        )

        results.append({
            "text": text,
            "audio_path": str(output_path),
            "duration_ms": result.duration_ms,
            "characters": len(text),
        })

    return {
        "persona": persona,
        "samples": results,
        "avg_duration_per_char": sum(r["duration_ms"] / r["characters"] for r in results) / len(results),
    }

# Test texts for evaluation
TEST_TEXTS = [
    "Marvelous shot through the covers.",
    "And that's the end of the innings.",
    "What a remarkable display of batting.",
    "The ball races away to the boundary.",
    "Simply extraordinary cricket.",
]

if __name__ == "__main__":
    import sys
    persona = sys.argv[1] if len(sys.argv) > 1 else "benaud"
    results = evaluate_voice(persona, TEST_TEXTS)
    print(f"Generated {len(results['samples'])} voice samples")
    print(f"Average pace: {results['avg_duration_per_char']:.1f}ms per character")
```

### 4.3 End-to-End Evaluation

```bash
# Run full pipeline evaluation
python scripts/evaluate_e2e.py --persona benaud --matches 5 --output eval/e2e_benaud.json
```

---

## Phase 5: Inference Deployment

### 5.1 Pi 5 Setup

```bash
# 1. Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Copy GGUF model to Pi
scp outputs/benaud-q4_k_m.gguf pi@raspberrypi:~/models/

# 3. Create Ollama model on Pi
ssh pi@raspberrypi
cd ~/models
ollama create suksham-benaud -f Modelfile.benaud

# 4. Verify model works
ollama run suksham-benaud "Commentate: Boundary through covers"
```

### 5.2 Service Configuration

**File: `/etc/systemd/system/suksham-vachak.service`**

```ini
[Unit]
Description=Suksham Vachak Commentary Service
After=network.target ollama.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/suksham-vachak
ExecStart=/home/pi/.local/bin/poetry run uvicorn suksham_vachak.api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
Environment=OLLAMA_HOST=http://localhost:11434

[Install]
WantedBy=multi-user.target
```

### 5.3 API Usage

```python
# Client code
import requests

response = requests.post(
    "http://pi.local:8000/api/commentary",
    json={
        "event": {
            "type": "boundary",
            "runs": 4,
            "batter": "V Kohli",
            "bowler": "JM Anderson",
            "shot_type": "cover_drive",
        },
        "persona": "benaud",
        "include_audio": True,
    },
)

result = response.json()
print(f"Commentary: {result['text']}")
print(f"Audio URL: {result['audio_url']}")
```

---

## Quick Reference: Complete Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PERSONA CREATION WORKFLOW                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. COLLECT DATA                                                         │
│     ├── Text transcripts (YouTube, Cricinfo, books)                     │
│     └── Audio samples (10-30 min clean audio)                           │
│                                                                          │
│  2. PREPARE DATA                                                         │
│     ├── python scripts/prepare_persona_data.py benaud                   │
│     └── python scripts/prepare_voice_samples.py benaud                  │
│                                                                          │
│  3. TRAIN MODELS                                                         │
│     ├── [Cloud GPU] python scripts/train_persona_qlora.py               │
│     └── [ElevenLabs] python scripts/create_elevenlabs_voice.py benaud   │
│                                                                          │
│  4. CONVERT & DEPLOY                                                     │
│     ├── python scripts/merge_and_convert.py                             │
│     ├── scp benaud-q4_k_m.gguf pi@raspberrypi:~/models/                 │
│     └── ollama create suksham-benaud -f Modelfile.benaud                │
│                                                                          │
│  5. EVALUATE                                                             │
│     ├── python scripts/evaluate_models.py --model suksham-benaud        │
│     └── python scripts/evaluate_voice.py benaud                         │
│                                                                          │
│  6. DEPLOY                                                               │
│     └── sudo systemctl start suksham-vachak                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix: Data Sources

### Commentary Transcript Sources

| Commentator | Source   | URL                               | Notes                    |
| ----------- | -------- | --------------------------------- | ------------------------ |
| Benaud      | YouTube  | Search "Richie Benaud commentary" | Use yt-dlp for subtitles |
| Benaud      | Books    | "Anything But...An Autobiography" | Manual transcription     |
| Greig       | YouTube  | "Tony Greig best commentary"      | Channel 9 archives       |
| Doshi       | YouTube  | "Susheel Doshi commentary Hindi"  | Star Sports archives     |
| Bhogle      | Podcasts | Cricbuzz, ESPNcricinfo            | Whisper transcription    |

### Audio Sample Sources

| Commentator | Source                     | Quality   | Duration Available |
| ----------- | -------------------------- | --------- | ------------------ |
| Benaud      | YouTube compilation videos | Variable  | 2+ hours           |
| Greig       | Channel 9 archives         | Good      | 5+ hours           |
| Doshi       | Star Sports Hindi          | Good      | 10+ hours          |
| Bhogle      | Podcasts (Cricbuzz)        | Excellent | 50+ hours          |

---

## Troubleshooting

### Common Issues

| Issue                  | Cause                       | Solution                               |
| ---------------------- | --------------------------- | -------------------------------------- |
| Model outputs too long | Insufficient style training | Add more examples with short responses |
| Wrong accent in TTS    | Mixed audio samples         | Use only single-commentator audio      |
| Slow inference on Pi   | Model too large             | Use Q4_K_M quantization                |
| Voice sounds robotic   | Low similarity_boost        | Increase to 0.85-0.95                  |
| Style inconsistent     | Low training epochs         | Train for 3-5 epochs                   |
