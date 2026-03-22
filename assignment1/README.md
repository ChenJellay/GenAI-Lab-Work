# Qwen3.5 Prompt Experimentation

Experimentation on **Qwen3.5** (via MLX 4-bit) for three tasks, each with **5 prompt levels** that vary in structure, specificity, and style.

## Tasks

1. **Lyric translation** — Translate song lyrics with rhythm/rhyme adaptability.
2. **Art evaluation** — Evaluate popular poems with semantics and emotion breakdown.
3. **Art discovery** — Recommend music, movies, art, and artists from a text prompt.

## Setup

### 1. Environment

```bash
cd /path/to/GENAI
python -m venv .venv
source .venv/bin/activate   # or: .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**Important:** Qwen3.5 (`model_type` `qwen3_5`) is only supported in **mlx-lm >= 0.30**. If you see `Model type qwen3_5 not supported`, upgrade:

```bash
pip install -U "mlx-lm>=0.31.0"
```

### 2. Download the model (one-time)

From the project root, install the Hugging Face CLI (one-time):

```bash
pip install "huggingface_hub[cli]"
```

Then download the MLX 4-bit model to a local directory:

```bash
hf download mlx-community/Qwen3.5-9B-MLX-4bit --local-dir Qwen3.5-9B-MLX-4bit
```

This creates a folder `Qwen3.5-9B-MLX-4bit` in the current directory. The scripts load from this path by default.

### 3. Run experiments

```bash
python experiment_qwen.py
```

By default the script uses the model in `./Qwen3.5-9B-MLX-4bit`. To use another path:

```bash
export QWEN_MODEL_PATH=/path/to/Qwen3.5-9B-MLX-4bit
python experiment_qwen.py
```

Outputs are written to `experiment_outputs/`:

- `results_YYYYMMDD_HHMMSS.json` — full prompts and model outputs.
- `report_YYYYMMDD_HHMMSS.md` — readable report of all 15 runs.

## Prompt design

See **`PROMPT_DESIGN.md`** for:

- All 15 prompts (5 levels × 3 tasks).
- Design reasoning for each (structure, specificity, style).
- Placeholders and how to plug in your own lyric, poem, or discovery prompt.

## Token limit and thinking mode

- **`MAX_TOKENS`** (default `2048`) caps the length of each response. Increase it in `experiment_qwen.py` if outputs are cut off.
- **`ENABLE_THINKING`** (default `False`) controls Qwen3.5’s “thinking” (reasoning) tokens. When `False`, the chat template sends an empty `<think></think>` block so the model answers directly instead of emitting long reasoning first. That keeps more of the token budget for the actual answer. Set to `True` if you want chain-of-thought style output.

## Customizing inputs

Edit these in `experiment_qwen.py`:

- `SAMPLE_LYRIC` — lyric to translate (default: Spanish stanza).
- `SAMPLE_POEM` — poem to evaluate (default: Frost, “The Road Not Taken”).
- `SAMPLE_DISCOVERY_PROMPT` — text for art discovery (default: “rainy Sunday afternoon, a bit melancholic but hopeful”).

You can also add CLI arguments or a config file to switch inputs without editing the script.

## Requirements

- **Apple Silicon** (M1/M2/M3) for MLX.
- Sufficient RAM for the 4-bit 9B model (typically ~6GB+).
- Python 3.10+.
