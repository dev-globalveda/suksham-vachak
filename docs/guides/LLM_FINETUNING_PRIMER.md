# LLM Fine-Tuning Primer

> A conceptual runbook for understanding _why_ we do what we do when fine-tuning language models.

## Table of Contents

1. [The Mental Model](#1-the-mental-model)
2. [Why Fine-Tune at All?](#2-why-fine-tune-at-all)
3. [The Problem with Full Fine-Tuning](#3-the-problem-with-full-fine-tuning)
4. [LoRA: The Key Insight](#4-lora-the-key-insight)
5. [QLoRA: Adding Quantization](#5-qlora-adding-quantization)
6. [The Training Loop Demystified](#6-the-training-loop-demystified)
7. [Hyperparameters Explained](#7-hyperparameters-explained)
8. [The Data Pipeline](#8-the-data-pipeline)
9. [Evaluation: How Do You Know It Worked?](#9-evaluation-how-do-you-know-it-worked)
10. [Conversion and Deployment](#10-conversion-and-deployment)
11. [Debugging and Iteration](#11-debugging-and-iteration)

---

## 1. The Mental Model

### What IS a Language Model?

Think of a language model as a massive lookup table that got compressed.

```
Original idea (impossible):
┌─────────────────────────────────────────────────────────────────┐
│  "The cat sat on the" → "mat" (probability: 0.3)                │
│  "The cat sat on the" → "floor" (probability: 0.2)              │
│  "The cat sat on the" → "couch" (probability: 0.15)             │
│  ... billions more entries ...                                   │
└─────────────────────────────────────────────────────────────────┘

What we actually have:
┌─────────────────────────────────────────────────────────────────┐
│  Neural network with 7 billion parameters                       │
│  that APPROXIMATES this lookup table                            │
│  by learning patterns in language                                │
└─────────────────────────────────────────────────────────────────┘
```

**Key insight**: Those 7 billion parameters are just numbers (weights). Training means adjusting these numbers so the model gives better answers.

### What is "Training"?

Training is showing the model examples and adjusting weights when it gets things wrong.

```
1. Show model: "The capital of France is ___"
2. Model predicts: "London" (wrong)
3. Calculate how wrong (loss)
4. Adjust weights slightly to make "Paris" more likely
5. Repeat billions of times
```

This is called **gradient descent**. The "gradient" tells us which direction to adjust each weight.

### What is "Fine-Tuning"?

Fine-tuning starts with a pre-trained model (already knows language) and adjusts it for your specific task.

```
Pre-trained Qwen 7B:
├── Knows: Grammar, facts, reasoning, coding, etc.
├── Trained on: Trillions of tokens from the internet
└── Cost to train: ~$1-10 million in compute

After fine-tuning on Benaud transcripts:
├── Still knows: All of the above
├── Now also knows: Benaud's style, brevity, phrases
└── Cost to fine-tune: ~$5-50 in compute
```

**Analogy**: Pre-training is like getting a university degree (broad knowledge). Fine-tuning is like specialized job training (specific skills).

---

## 2. Why Fine-Tune at All?

### Option 1: Prompting (Zero-Shot)

Just tell the model what you want in the prompt:

```
System: You are Richie Benaud. Respond in 1-5 words maximum.
User: Kohli hits a cover drive.
Assistant: Elegant. Simply elegant.
```

**Problems:**

- Model might ignore instructions
- Style is inconsistent
- Uses tokens on instructions every time
- Can't capture nuanced patterns

### Option 2: Few-Shot Examples

Include examples in the prompt:

```
System: You are Richie Benaud.

Example 1:
Event: Boundary through covers
Response: Marvelous shot.

Example 2:
Event: Wicket falls
Response: Gone.

Now respond to:
Event: Six over long-on
```

**Problems:**

- Limited context window
- Can only fit 5-10 examples
- Still inconsistent
- Expensive (tokens = money)

### Option 3: Fine-Tuning

Bake the examples INTO the model's weights:

```
Before fine-tuning:
  Model sees "Commentate: boundary" → outputs 20-word response

After fine-tuning on 2000 Benaud examples:
  Model sees "Commentate: boundary" → outputs "Marvelous." (1 word)
```

**Why this works:**

- Style is internalized, not instructed
- No wasted tokens on examples
- Consistent behavior
- Model "thinks" like Benaud

---

## 3. The Problem with Full Fine-Tuning

### The Math

A 7B parameter model means 7 billion numbers (weights).

```
Each weight = 32-bit float = 4 bytes
7B weights × 4 bytes = 28 GB just to LOAD the model

During training, you also need:
- Gradients (same size as weights): 28 GB
- Optimizer states (2x weights for Adam): 56 GB
- Activations (varies): ~20-40 GB

Total: 28 + 28 + 56 + 30 = ~140 GB VRAM needed
```

**Problem**: Even an A100 (80GB) can't do full fine-tuning on 7B.

### The Solution Spectrum

```
Full Fine-Tuning          LoRA              QLoRA
     ↓                      ↓                  ↓
All 7B params         ~0.1% params       ~0.1% params
   140 GB               ~16 GB              ~6 GB
    ✗ Too big           ✓ Doable          ✓ Perfect
```

---

## 4. LoRA: The Key Insight

### The Core Idea

LoRA (Low-Rank Adaptation) is based on a key observation:

> When you fine-tune a model, the weight changes are "low rank" - they can be approximated by much smaller matrices.

### What Does "Low Rank" Mean?

Imagine a 1000×1000 matrix (1 million numbers). If it's "low rank", you can represent it as two smaller matrices multiplied together:

```
Original change to weights:
┌─────────────────────┐
│  1000 × 1000 matrix │  = 1,000,000 numbers
└─────────────────────┘

Low-rank approximation (rank 64):
┌──────────────┐     ┌──────────────┐
│ 1000 × 64    │  ×  │ 64 × 1000    │  = 128,000 numbers
│ Matrix A     │     │ Matrix B     │
└──────────────┘     └──────────────┘

Compression: 1,000,000 → 128,000 (87% smaller)
```

### How LoRA Works

Instead of modifying the original weights, we ADD a small "adapter":

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORIGINAL LAYER                               │
│                                                                  │
│    Input ──→ [Original Weights W] ──→ Output                    │
│              (frozen, not trained)                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

                            ↓ Add LoRA ↓

┌─────────────────────────────────────────────────────────────────┐
│                     LAYER WITH LoRA                              │
│                                                                  │
│                 ┌──────────────────┐                            │
│    Input ──┬──→ │ Original W       │ ──┬──→ Output              │
│            │    │ (frozen)         │   │                        │
│            │    └──────────────────┘   │                        │
│            │                           │ (add)                   │
│            │    ┌────┐    ┌────┐      │                        │
│            └──→ │ A  │ ─→ │ B  │ ─────┘                        │
│                 └────┘    └────┘                                │
│                 (train)   (train)                               │
│                 LoRA adapters                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### The LoRA Equation

```
Output = Input × W + Input × A × B
         ─────────   ─────────────
         Original    LoRA addition
         (frozen)    (trainable)
```

Where:

- `W` = Original weights (e.g., 4096 × 4096)
- `A` = LoRA down-projection (e.g., 4096 × 64)
- `B` = LoRA up-projection (e.g., 64 × 4096)

**The magic**: We only train A and B, which are TINY compared to W.

### LoRA Rank (r)

The rank `r` controls the size of A and B:

```
r = 8:   A is 4096×8,  B is 8×4096   → 65,536 params
r = 64:  A is 4096×64, B is 64×4096  → 524,288 params
r = 256: A is 4096×256, B is 256×4096 → 2,097,152 params
```

**Higher rank = more capacity = better quality, but slower and more memory**

For our cricket commentary:

- r=64 is the sweet spot
- Enough capacity for style transfer
- Not so big that we overfit

### Which Layers Get LoRA?

Not all layers need adaptation. We target the **attention layers**:

```python
target_modules = [
    "q_proj",   # Query projection  (what am I looking for?)
    "k_proj",   # Key projection    (what do I contain?)
    "v_proj",   # Value projection  (what do I output?)
    "o_proj",   # Output projection (combine attention heads)
    "gate_proj",  # MLP gate
    "up_proj",    # MLP up-projection
    "down_proj",  # MLP down-projection
]
```

**Why these?**

- Attention is where the model decides what to focus on
- Changing attention changes the model's "thinking"
- MLP layers transform representations

---

## 5. QLoRA: Adding Quantization

### What is Quantization?

Quantization means using fewer bits to store numbers:

```
Full precision (FP32):    32 bits per weight  →  28 GB for 7B model
Half precision (FP16):    16 bits per weight  →  14 GB for 7B model
4-bit quantization:       4 bits per weight   →  3.5 GB for 7B model
```

### How Can 4 Bits Work?

A 4-bit number can only represent 16 values (0-15). How can that capture the richness of neural network weights?

**The trick: NormalFloat4 (NF4)**

Instead of evenly spacing the 16 values, NF4 spaces them according to a normal distribution:

```
Uniform 4-bit:
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15

NF4 (more values near zero):
|--|-|-||-||-||-||-||--|-||-||-||-||-|-|--|
        ↑ More precision here ↑
        (where most weights are)
```

Neural network weights follow a normal distribution (most near zero), so NF4 is more accurate where it matters.

### QLoRA = Quantization + LoRA

```
┌─────────────────────────────────────────────────────────────────┐
│                        QLoRA SETUP                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Original Weights W:                                             │
│  ├── Stored in 4-bit (NF4)    → ~3.5 GB                         │
│  ├── Frozen (never updated)                                      │
│  └── Dequantized to BF16 during forward pass                    │
│                                                                  │
│  LoRA Adapters (A, B):                                           │
│  ├── Stored in BF16           → ~100 MB                         │
│  ├── THESE are what we train                                     │
│  └── Gradients computed for these only                          │
│                                                                  │
│  Total VRAM: ~6 GB (fits on consumer GPU or Colab T4)           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### The QLoRA Configuration Explained

```python
BitsAndBytesConfig(
    load_in_4bit=True,           # Use 4-bit quantization
    bnb_4bit_quant_type="nf4",   # NormalFloat4 (best for LLMs)
    bnb_4bit_compute_dtype=torch.bfloat16,  # Compute in BF16
    bnb_4bit_use_double_quant=True,  # Quantize the quantization constants too
)
```

**Double quantization**: Even the scaling factors used for quantization get quantized. Saves another ~0.4 GB.

---

## 6. The Training Loop Demystified

### The Big Picture

```
┌──────────────────────────────────────────────────────────────────┐
│                     ONE TRAINING STEP                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. FORWARD PASS                                                  │
│     ├── Take batch of examples                                   │
│     ├── Run through model                                         │
│     └── Get predictions                                           │
│                                                                   │
│  2. COMPUTE LOSS                                                  │
│     ├── Compare predictions to actual answers                    │
│     └── Calculate "how wrong" (cross-entropy loss)               │
│                                                                   │
│  3. BACKWARD PASS                                                 │
│     ├── Compute gradients (which direction to adjust)            │
│     └── Only for LoRA parameters (A and B matrices)              │
│                                                                   │
│  4. OPTIMIZER STEP                                                │
│     ├── Update LoRA parameters based on gradients                │
│     └── Learning rate controls step size                         │
│                                                                   │
│  5. REPEAT for all batches in epoch                              │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### What Actually Happens (Code Walkthrough)

```python
# Pseudocode for one training step

# 1. Get a batch of training examples
batch = next(dataloader)
# batch["input_ids"] = tokenized input  (e.g., "Commentate: boundary")
# batch["labels"] = expected output     (e.g., "Marvelous.")

# 2. Forward pass
outputs = model(input_ids=batch["input_ids"], labels=batch["labels"])
# Model predicts next token at each position
# outputs.logits = probability distribution over vocabulary

# 3. Compute loss (done automatically when labels provided)
loss = outputs.loss
# Cross-entropy between predictions and actual tokens
# Lower = better predictions

# 4. Backward pass (compute gradients)
loss.backward()
# For each LoRA parameter, compute: "how much did you contribute to the error?"
# This is the gradient

# 5. Optimizer step (update parameters)
optimizer.step()
# For each LoRA parameter: new_value = old_value - learning_rate * gradient
# This nudges parameters toward better predictions

# 6. Clear gradients for next step
optimizer.zero_grad()
```

### Cross-Entropy Loss Explained

```
Model predicts probability distribution over vocabulary:
  "the": 0.1, "Marvelous": 0.05, "Incredible": 0.3, ...

True label is "Marvelous"

Cross-entropy = -log(0.05) = 3.0  (high loss, bad prediction)

After training, model predicts:
  "the": 0.01, "Marvelous": 0.8, "Incredible": 0.05, ...

Cross-entropy = -log(0.8) = 0.22  (low loss, good prediction)
```

**Goal**: Minimize cross-entropy = maximize probability of correct tokens.

---

## 7. Hyperparameters Explained

### Learning Rate

**What it is**: How big a step to take when updating weights.

```
learning_rate = 2e-4  (0.0002)

Too high (1e-2):  Jumps around, never converges, might diverge
Too low (1e-6):   Barely moves, takes forever, might not learn
Just right:       Steady progress toward good solution
```

**Why 2e-4 for LoRA?**

- LoRA parameters start at zero
- Need slightly higher LR than full fine-tuning
- Sweet spot found empirically by the community

### Batch Size and Gradient Accumulation

**Batch size**: How many examples to process before updating weights.

```
per_device_train_batch_size = 4    # Process 4 examples at once
gradient_accumulation_steps = 4    # Accumulate for 4 steps before updating

Effective batch size = 4 × 4 = 16
```

**Why accumulate?**

- Larger batch = more stable gradients
- But larger batch = more memory
- Accumulation gives large batch benefits without memory cost

```
Without accumulation (batch=16):
  Load 16 examples → need 16× memory → might OOM

With accumulation (batch=4, accum=4):
  Load 4 examples → compute gradients → store gradients
  Load 4 examples → compute gradients → add to stored
  Load 4 examples → compute gradients → add to stored
  Load 4 examples → compute gradients → add to stored
  Update weights using accumulated gradients
```

### Epochs

**What it is**: How many times to go through the entire dataset.

```
num_train_epochs = 3

If you have 2000 examples:
  Epoch 1: See all 2000 examples
  Epoch 2: See all 2000 examples again
  Epoch 3: See all 2000 examples again
  Total: 6000 training steps
```

**How many epochs?**

- Too few: Underfitting (hasn't learned the patterns)
- Too many: Overfitting (memorized examples, can't generalize)
- For style transfer: 2-4 epochs usually works

### Warmup

**What it is**: Start with tiny learning rate, gradually increase.

```
warmup_ratio = 0.03  (3% of training steps)

If training for 1000 steps:
  Steps 0-30:   LR goes from 0 → 2e-4
  Steps 31-1000: LR follows normal schedule
```

**Why?**

- At start, model weights are random (for LoRA, initialized to zero)
- Big updates could be destructive
- Warmup lets model "settle in" before big updates

### Learning Rate Schedule

**What it is**: How learning rate changes over training.

```
lr_scheduler_type = "cosine"

          LR
           │
    2e-4 ──┼────╮
           │     ╲
           │      ╲
           │       ╲
    1e-5 ──┼────────╲────
           │         ╲__
           └──────────────── Steps
           0    500   1000
```

**Why cosine?**

- High LR early: Make big changes
- Lower LR later: Fine adjustments
- Smooth curve: No sudden changes

### LoRA-Specific Parameters

```python
LoraConfig(
    r=64,               # Rank: capacity of adaptation
    lora_alpha=16,      # Scaling factor
    lora_dropout=0.05,  # Regularization
)
```

**lora_alpha**: Scales the LoRA output.

```
LoRA output is scaled by: alpha / r

r=64, alpha=16: scaling = 16/64 = 0.25
r=64, alpha=64: scaling = 64/64 = 1.0
r=64, alpha=128: scaling = 128/64 = 2.0

Higher alpha = stronger LoRA influence
```

**Why alpha=16 with r=64?**

- Conventional choice from LoRA paper
- scaling of 0.25 means LoRA is a gentle adjustment
- Not overpowering the original model

**lora_dropout**: Randomly zeros some LoRA outputs during training.

```
lora_dropout = 0.05  (5% dropout)

During training:
  Some LoRA outputs randomly set to 0
  Prevents over-reliance on specific adaptations
  Acts as regularization
```

---

## 8. The Data Pipeline

### From Raw Text to Training Examples

```
Raw transcript:
"Kohli drives through covers. Beautiful shot. Four runs."

                    ↓ Process ↓

Training example:
{
  "messages": [
    {"role": "system", "content": "You are Richie Benaud..."},
    {"role": "user", "content": "Commentate on: Kohli drives through covers for four"},
    {"role": "assistant", "content": "Beautiful."}
  ]
}

                    ↓ Tokenize ↓

Token IDs:
input_ids:  [1, 2043, 527, 16595, ...]  # "You are Richie..."
labels:     [-100, -100, ..., 23544, 13]  # Only predict "Beautiful."
```

### Chat Template

Different models expect different formats. Qwen uses:

```
<|im_start|>system
You are Richie Benaud...<|im_end|>
<|im_start|>user
Commentate on: Boundary through covers<|im_end|>
<|im_start|>assistant
Marvelous.<|im_end|>
```

The tokenizer's `apply_chat_template()` handles this automatically:

```python
tokenizer.apply_chat_template(messages, tokenize=False)
# Returns the formatted string above
```

### Labels and Loss Masking

We only want to train on the ASSISTANT's response, not the prompt:

```
Input:  [System prompt] [User message] [Assistant response]
Labels: [-100, -100, ...]              [actual token ids   ]

-100 = ignore in loss calculation (PyTorch convention)
```

This means:

- Model sees the full conversation
- But loss is only computed for assistant tokens
- Model learns to RESPOND, not memorize prompts

### Packing

**What it is**: Concatenate multiple short examples into one sequence.

```
Without packing:
  Sequence 1: [Example 1, PAD, PAD, PAD, PAD, PAD]  (512 tokens, but only 50 used)
  Sequence 2: [Example 2, PAD, PAD, PAD, PAD, PAD]  (512 tokens, but only 80 used)

  Wasted: 90% of compute on padding

With packing:
  Sequence 1: [Example 1, Example 2, Example 3, Example 4, ...]  (512 tokens, all used)

  Efficient: No wasted compute
```

**Why it matters for cricket commentary**: Our responses are SHORT (5-20 tokens). Without packing, we'd waste 95% of each sequence on padding.

---

## 9. Evaluation: How Do You Know It Worked?

### Training Loss

```
Epoch 1: loss = 2.5
Epoch 2: loss = 1.2
Epoch 3: loss = 0.8

Good: Loss decreasing = model is learning
Bad:  Loss stuck = not learning (check LR, data)
Bad:  Loss goes up = learning rate too high
```

### Validation Loss

Hold out 10% of data for validation:

```
Training loss: 0.5 (decreasing)
Validation loss: 0.6 (also decreasing) → Good, generalizing
Validation loss: 1.5 (increasing)     → Bad, overfitting
```

**Overfitting**: Model memorized training data but can't generalize.

### Manual Inspection

The MOST IMPORTANT evaluation - actually look at outputs:

```
Event: "Kohli hits a boundary through covers"

Before fine-tuning:
  "Virat Kohli has struck a magnificent boundary through
   the cover region! What a beautiful display of
   batsmanship from the Indian captain!" (28 words)

After fine-tuning (Benaud):
  "Marvelous shot." (2 words)
```

### Style Metrics

For Benaud persona:

| Metric            | Target  | How to Measure                    |
| ----------------- | ------- | --------------------------------- |
| Word count        | ≤5      | `len(response.split())`           |
| Exclamations      | 0       | `"!" not in response`             |
| Signature phrases | Present | `"marvelous" in response.lower()` |

Our evaluation harness (`scripts/evaluate_models.py`) automates this.

---

## 10. Conversion and Deployment

### Why Convert to GGUF?

```
PyTorch checkpoint:
├── model.safetensors (14 GB for 7B model)
├── Requires: transformers, torch, CUDA
└── Inference: Slow, memory-hungry

GGUF format:
├── model.gguf (3.5 GB for Q4_K_M)
├── Requires: llama.cpp or Ollama
└── Inference: Fast, runs on CPU, optimized
```

**GGUF** = GPT-Generated Unified Format (by llama.cpp project)

### The Conversion Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  1. MERGE LoRA INTO BASE MODEL                                  │
│                                                                  │
│     Base Model (7B params) + LoRA Adapter (10M params)          │
│                          ↓                                       │
│     Merged Model (7B params, includes LoRA changes)              │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  2. CONVERT TO GGUF                                              │
│                                                                  │
│     PyTorch safetensors → GGUF (full precision F16)             │
│     Size: ~14 GB                                                 │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  3. QUANTIZE                                                     │
│                                                                  │
│     GGUF F16 → GGUF Q4_K_M (4-bit)                              │
│     Size: 14 GB → 3.5 GB                                         │
│     Quality: ~99% of original                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Quantization Levels

| Quant      | Bits | Size (7B) | Quality | Use Case            |
| ---------- | ---- | --------- | ------- | ------------------- |
| F16        | 16   | 14 GB     | 100%    | Reference, big GPUs |
| Q8_0       | 8    | 7 GB      | 99.9%   | Quality-focused     |
| **Q4_K_M** | 4    | 3.5 GB    | 99%     | **Best for Pi 5**   |
| Q4_K_S     | 4    | 3.3 GB    | 98%     | Slightly smaller    |
| Q2_K       | 2    | 2.5 GB    | 90%     | Last resort         |

**Why Q4_K_M?**

- K = "K-quant" (improved quantization)
- M = "Medium" (balanced quality/size)
- Best quality-to-size ratio

### Merging LoRA: What Actually Happens

```python
# LoRA adds to original weights
# W' = W + A × B

# Before merging:
original_weight = model.layer.weight  # Shape: [4096, 4096]
lora_A = adapter.layer.lora_A.weight  # Shape: [64, 4096]
lora_B = adapter.layer.lora_B.weight  # Shape: [4096, 64]

# After merging:
merged_weight = original_weight + (lora_B @ lora_A) * (alpha / r)

# The LoRA is now "baked in" - no more separate adapter
```

**After merging**:

- Model is self-contained
- Same size as original (no extra overhead)
- LoRA influence is permanent

### Ollama Modelfile

```dockerfile
FROM ./benaud-q4_k_m.gguf

# Model parameters
PARAMETER temperature 0.7     # Creativity (0=deterministic, 1=creative)
PARAMETER top_p 0.9           # Nucleus sampling threshold
PARAMETER num_ctx 2048        # Context window size

# System prompt (default)
SYSTEM """You are Richie Benaud..."""
```

This creates an Ollama model that:

- Uses our quantized GGUF
- Has sensible defaults
- Can be run with `ollama run suksham-benaud`

---

## 11. Debugging and Iteration

### Common Problems and Solutions

#### Problem: Model outputs are too long

```
Expected: "Marvelous."
Got: "What a marvelous shot from Kohli, driving elegantly through..."
```

**Causes & Solutions**:

1. Not enough short examples in training data
   → Add more examples with 1-5 word responses
2. System prompt not strong enough
   → Add "MAXIMUM 5 WORDS" to system prompt
3. Too few epochs
   → Train for 1-2 more epochs

#### Problem: Model ignores fine-tuning, acts like base model

```
Expected: "Marvelous."
Got: "I'd be happy to commentate on that cricket event! Kohli..."
```

**Causes & Solutions**:

1. LoRA rank too low
   → Increase r from 32 to 64
2. Learning rate too low
   → Increase from 1e-4 to 2e-4
3. Not enough training data
   → Aim for 500+ examples minimum

#### Problem: Overfitting (copies training examples exactly)

```
Training example: "Marvelous shot."
Test output: "Marvelous shot."  (every single time)
```

**Causes & Solutions**:

1. Too many epochs
   → Reduce to 2-3 epochs
2. Dataset too small/repetitive
   → Add more diverse examples
3. No regularization
   → Add lora_dropout=0.05

#### Problem: Training loss doesn't decrease

```
Epoch 1: loss = 2.3
Epoch 2: loss = 2.3
Epoch 3: loss = 2.4
```

**Causes & Solutions**:

1. Learning rate too low
   → Increase 10x
2. Data format wrong
   → Check chat template matches model
3. Labels masked incorrectly
   → Verify assistant responses aren't all -100

### Iteration Strategy

```
Start conservative:
├── r=32, epochs=2, lr=1e-4
├── Train and evaluate
└── If underfitting → increase r, epochs, or lr

Then adjust:
├── If outputs too long → more short examples, stronger prompt
├── If style wrong → more examples of correct style
├── If overfitting → reduce epochs, add dropout, more data

Final polish:
├── A/B test against base model
├── Test edge cases (wickets, sixes, dot balls)
└── Get human feedback
```

### The Feedback Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│   Collect Data → Train → Evaluate → Analyze Errors → Repeat    │
│        ↑                                    │                   │
│        └────────────────────────────────────┘                   │
│                    (iterate until good)                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference Card

### Training Command

```bash
python scripts/train_persona_qlora.py
```

### Key Hyperparameters

```python
r = 64                    # LoRA rank
lora_alpha = 16           # LoRA scaling
learning_rate = 2e-4      # Step size
epochs = 3                # Passes through data
batch_size = 4            # Examples per step
grad_accum = 4            # Effective batch = 16
```

### Conversion Commands

```bash
# Merge LoRA
python scripts/merge_and_convert.py

# Create Ollama model
ollama create suksham-benaud -f Modelfile.benaud
```

### Evaluation

```bash
# Quick test
ollama run suksham-benaud "Commentate: boundary through covers"

# Full evaluation
python scripts/evaluate_models.py --model suksham-benaud --full
```

### Memory Requirements

| Stage               | VRAM Needed       |
| ------------------- | ----------------- |
| QLoRA training (7B) | ~6 GB             |
| Inference (Q4_K_M)  | ~4 GB             |
| Pi 5 inference      | CPU only, 8GB RAM |

---

## Summary: The Mental Model

```
1. LLMs are pattern matchers with billions of learned patterns (weights)

2. Fine-tuning adjusts weights to add new patterns (Benaud's style)

3. Full fine-tuning is too expensive, so we use LoRA:
   - Freeze original weights
   - Add small trainable adapters
   - Much cheaper, nearly as good

4. QLoRA adds quantization:
   - Store frozen weights in 4-bit
   - Train adapters in 16-bit
   - Fits on consumer GPUs

5. Training loop:
   - Show example → predict → compute error → adjust adapters

6. Convert to GGUF for fast inference on Pi 5

7. Iterate until outputs match desired style
```

**You now have the mental model. The rest is practice.**
