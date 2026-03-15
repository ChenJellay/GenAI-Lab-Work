#!/usr/bin/env python3
"""
Experiment 2: Few-shot prompting with Qwen3.5-MLX-4bit.

For each of the 3 tasks (lyric translation EN→ZH, art evaluation, art discovery),
runs 6 prompt variants:
  1. baseline             — no examples
  2. one_example          — 1 example
  3. three_examples       — 2 positive, 1 negative
  4. five_examples        — 3 positive, 2 negative
  5. five_with_rationale  — same 5 examples + rationale for each
  6. five_comparison_pairs — 5 positive-negative direct comparison pairs

Lyric translation uses samples from data/ (official/creative = positive, literal = negative).
Task: English → Chinese translation with rhythm/rhyme adaptability.
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL_PATH = os.environ.get("QWEN_MODEL_PATH", "Qwen3.5-9B-MLX-4bit")
DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent / "experiment_outputs"
MAX_TOKENS = 2048
TEMPERATURE = 0.7
TOP_P = 0.9
ENABLE_THINKING = False

# ---------------------------------------------------------------------------
# Sample inputs (test items for the model)
# ---------------------------------------------------------------------------
SAMPLE_LYRIC_EN = """\
Somewhere over the rainbow, way up high
There's a land that I heard of once in a lullaby
Somewhere over the rainbow, skies are blue
And the dreams that you dare to dream really do come true."""

SAMPLE_POEM = """\
The Road Not Taken
Robert Frost

Two roads diverged in a yellow wood,
And sorry I could not travel both
And be one traveler, long I stood
And looked down one as far as I could
To where it bent in the undergrowth;

Then took the other, as just as fair,
And having perhaps the better claim,
Because it was grassy and wanted wear;
Though as for that the passing there
Had worn them really about the same."""

SAMPLE_DISCOVERY_PROMPT = "rainy Sunday afternoon, a bit melancholic but hopeful"

# ---------------------------------------------------------------------------
# Data loading: lyric translation examples from data/
# ---------------------------------------------------------------------------
def _parse_lyric_csv(filepath: Path) -> list[tuple[str, str]]:
    """Parse a lyric CSV into (English_line, Chinese_line) pairs. Strips pinyin in parens from Chinese."""
    pairs = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("Chinese Title"):
                continue
            if "," not in line:
                continue
            first_comma = line.index(",")
            eng = line[:first_comma].strip()
            chn = line[first_comma + 1 :].strip()
            chn = re.sub(r"\s*\([^)]*\)\s*", " ", chn).strip()
            if eng and chn and _has_latin(eng) and _has_cjk(chn):
                pairs.append((eng, chn))
    return pairs


def _has_latin(s: str) -> bool:
    return bool(re.search(r"[a-zA-Z]", s))


def _has_cjk(s: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", s))


def load_lyric_examples() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Load positive (official/creative) and negative (literal) lyric pairs from data/."""
    positive_dir = DATA_DIR / "positive: official_translation"
    creative_dir = DATA_DIR / "positive: creative_translation"
    negative_dir = DATA_DIR / "negative examples"

    positive_pairs: list[tuple[str, str]] = []
    for d in (positive_dir, creative_dir):
        if not d.exists():
            continue
        for p in d.glob("*.csv"):
            positive_pairs.extend(_parse_lyric_csv(p))

    negative_pairs: list[tuple[str, str]] = []
    if negative_dir.exists():
        for p in negative_dir.glob("*.csv"):
            negative_pairs.extend(_parse_lyric_csv(p))

    return positive_pairs, negative_pairs


def load_lyric_comparison_pairs(
    n_lines_per_snippet: int = 4,
    max_pairs: int = 5,
) -> list[tuple[str, str, str]]:
    """
    Load same-English (good_cn, bad_cn) pairs by matching official vs literal files.
    Returns list of (eng_block, good_chinese_block, bad_chinese_block).
    """
    official_dir = DATA_DIR / "positive: official_translation"
    negative_dir = DATA_DIR / "negative examples"
    if not official_dir.exists() or not negative_dir.exists():
        return []

    # Match by base name: disney_let_it_go_official.csv <-> disney_let_it_go_literal.csv
    literal_files = {p.name.replace("_literal.csv", ""): p for p in negative_dir.glob("*_literal.csv")}
    results = []
    for off_path in official_dir.glob("*.csv"):
        base = off_path.name.replace("_official.csv", "").replace(".csv", "")
        lit_path = literal_files.get(base + "_literal") or literal_files.get(base)
        if not lit_path or not lit_path.exists():
            continue
        off_pairs = _parse_lyric_csv(off_path)
        lit_pairs = _parse_lyric_csv(lit_path)
        # Align by English line (same order in both files)
        n = min(n_lines_per_snippet, len(off_pairs), len(lit_pairs))
        if n < 2:
            continue
        eng_lines = []
        good_lines = []
        bad_lines = []
        for i in range(n):
            if i < len(off_pairs) and i < len(lit_pairs):
                e_off, c_off = off_pairs[i]
                e_lit, c_lit = lit_pairs[i]
                if e_off.strip().lower() == e_lit.strip().lower():
                    eng_lines.append(e_off)
                    good_lines.append(c_off)
                    bad_lines.append(c_lit)
        if eng_lines:
            eng_block = "\n".join(eng_lines)
            good_block = "\n".join(good_lines)
            bad_block = "\n".join(bad_lines)
            results.append((eng_block, good_block, bad_block))
        if len(results) >= max_pairs:
            break
    return results


def format_lyric_example(eng_lines: list[str], chn_lines: list[str], label: str = "") -> str:
    """Format one lyric example (multiple lines) for the prompt."""
    eng_block = "\n".join(eng_lines)
    chn_block = "\n".join(chn_lines)
    if label:
        return f"English:\n{eng_block}\n\nChinese ({label}):\n{chn_block}"
    return f"English:\n{eng_block}\n\nChinese:\n{chn_block}"


def build_lyric_example_sets(
    positive_pairs: list[tuple[str, str]],
    negative_pairs: list[tuple[str, str]],
) -> tuple[
    list[str],
    list[str],
    list[tuple[str, str, str]],
]:
    """
    Build example sets for few-shot prompts.
    Returns:
      one_example: list of 1 formatted example (positive)
      three_examples: list of 3 formatted strings (2 pos, 1 neg)
      five_with_rationale: list of (formatted_example, "positive"|"negative", rationale)
    """
    def to_snippet(pairs: list[tuple[str, str]], n_lines: int = 4) -> tuple[list[str], list[str]]:
        eng, chn = [], []
        for e, c in pairs[:n_lines]:
            eng.append(e)
            chn.append(c)
        return eng, chn

    one_ex: list[str] = []
    if len(positive_pairs) >= 4:
        eng, chn = to_snippet(positive_pairs, 4)
        one_ex.append(format_lyric_example(eng, chn))

    three_ex: list[str] = []
    if len(positive_pairs) >= 8 and len(negative_pairs) >= 4:
        eng1, chn1 = to_snippet(positive_pairs[0:4], 4)
        eng2, chn2 = to_snippet(positive_pairs[4:8], 4)
        eng3, chn3 = to_snippet(negative_pairs[0:4], 4)
        three_ex.append(format_lyric_example(eng1, chn1, "good translation"))
        three_ex.append(format_lyric_example(eng2, chn2, "good translation"))
        three_ex.append(format_lyric_example(eng3, chn3, "bad translation (literal, not singable)"))

    five_with_rationale: list[tuple[str, str, str]] = []
    if len(positive_pairs) >= 12 and len(negative_pairs) >= 8:
        for i in range(3):
            eng, chn = to_snippet(positive_pairs[i * 4 : (i + 1) * 4], 4)
            five_with_rationale.append(
                (
                    format_lyric_example(eng, chn),
                    "positive",
                    "Adapts meaning for rhythm and rhyme; natural Chinese; singable.",
                )
            )
        for i in range(2):
            eng, chn = to_snippet(negative_pairs[i * 4 : (i + 1) * 4], 4)
            five_with_rationale.append(
                (
                    format_lyric_example(eng, chn),
                    "negative",
                    "Word-for-word literal; awkward or unidiomatic; not singable.",
                )
            )

    return one_ex, three_ex, five_with_rationale


# ---------------------------------------------------------------------------
# Task 1: Lyric translation (EN→ZH) — 6 few-shot variants
# ---------------------------------------------------------------------------
def build_lyric_prompts(
    one_example: list[str],
    three_examples: list[str],
    five_with_rationale: list[tuple[str, str, str]],
    comparison_pairs: list[tuple[str, str, str]],
) -> dict[str, str]:
    """Build the 6 lyric translation prompts (EN→Chinese) with optional examples."""
    base_instruction = """You are a lyric translator. Translate the following English song lyric into Chinese.

Requirements:
- Preserve emotional tone and key imagery.
- Aim for rhythm and singability in Chinese (adapt rhyme where needed).
- Prefer natural, idiomatic Chinese over word-for-word literal translation.
- Keep lines concise so they can be sung to the same melody."""

    baseline = f"""{base_instruction}

Translate this lyric to Chinese:

{SAMPLE_LYRIC_EN}"""

    prompts = {"baseline": baseline}

    if one_example:
        prompts["one_example"] = f"""{base_instruction}

Example of a good translation:

{one_example[0]}

---
Now translate this lyric to Chinese:

{SAMPLE_LYRIC_EN}"""

    if len(three_examples) >= 3:
        ex_block = "\n\n---\n\n".join(three_examples)
        prompts["three_examples"] = f"""{base_instruction}

Examples (first two are good translations, third is a bad literal translation to avoid):

{ex_block}

---
Now translate this lyric to Chinese:

{SAMPLE_LYRIC_EN}"""

    if len(five_with_rationale) >= 5:
        ex_only = "\n\n---\n\n".join([t[0] for t in five_with_rationale])
        prompts["five_examples"] = f"""{base_instruction}

Examples:

{ex_only}

---
Now translate this lyric to Chinese:

{SAMPLE_LYRIC_EN}"""

        rationale_block = "\n\n".join(
            f"Example:\n{t[0]}\nRationale: {t[2]}" for t in five_with_rationale
        )
        prompts["five_with_rationale"] = f"""{base_instruction}

Examples with rationale (what makes a translation good or bad):

{rationale_block}

---
Now translate this lyric to Chinese:

{SAMPLE_LYRIC_EN}"""

        if comparison_pairs:
            comp_blocks = []
            for eng_block, good_cn, bad_cn in comparison_pairs[:5]:
                comp_blocks.append(
                    f"Same English:\n{eng_block}\n\n"
                    f"Bad (literal, avoid):\n{bad_cn}\n\n"
                    f"Good (adapt rhythm/meaning):\n{good_cn}"
                )
            comparison_block_str = "\n\n---\n\n".join(comp_blocks)
            prompts["five_comparison_pairs"] = f"""{base_instruction}

Below are 5 direct comparison pairs (same English lyric): bad literal translation vs good singable translation. Learn from the contrast.

{comparison_block_str}

---
Now translate this lyric to Chinese:

{SAMPLE_LYRIC_EN}"""
        else:
            comp_parts = []
            for formatted, label, _ in five_with_rationale:
                if label == "positive":
                    comp_parts.append(f"Good translation example:\n{formatted}")
                else:
                    comp_parts.append(f"Bad translation example (avoid):\n{formatted}")
            comparison_block_str = "\n\n---\n\n".join(comp_parts)
            prompts["five_comparison_pairs"] = f"""{base_instruction}

Below are 5 examples: 3 good translations and 2 bad (literal) translations. Learn from the contrast.

{comparison_block_str}

---
Now translate this lyric to Chinese:

{SAMPLE_LYRIC_EN}"""

    return prompts


# ---------------------------------------------------------------------------
# Task 2: Art evaluation — 6 few-shot variants
# ---------------------------------------------------------------------------
EVAL_GOOD_1 = """Poem (excerpt): "Two roads diverged in a yellow wood..."
Good evaluation: The poem presents a literal choice between two paths in a wood, but the central metaphor is life decisions and the impossibility of revisiting the road not taken. The speaker's tone shifts from hesitation ("long I stood") to retrospective certainty ("I took the one less traveled by"), yet the closing line—"And that has made all the difference"—is famously ambiguous: it may suggest pride or quiet irony. Emotionally, the poem moves from contemplation to resolution, with an undertone of wistfulness."""

EVAL_BAD_1 = """Poem (excerpt): "Two roads diverged in a yellow wood..."
Bad evaluation: This poem is about someone walking in the woods and choosing a path. It's thoughtful. The poet seems to like nature."""

EVAL_GOOD_2 = """Poem (excerpt): "I wandered lonely as a cloud..."
Good evaluation: Literally, the speaker describes walking and seeing daffodils; figuratively, solitude is contrasted with the sudden joy of connection to nature. The emotional arc moves from loneliness to remembered bliss ("and then my heart with pleasure fills"). Diction such as "lonely as a cloud" and "host of golden daffodils" creates a clear semantic and emotional layer."""

EVAL_BAD_2 = """Poem (excerpt): "I wandered lonely as a cloud..."
Bad evaluation: It's a nice poem about flowers. Makes you feel good."""

EVAL_GOOD_3 = """Poem (excerpt): "Because I could not stop for Death..."
Good evaluation: Semantically, Death is personified as a courteous driver; the journey is literal (carriage ride) and figurative (life to eternity). The emotional tone is calm and accepting rather than fearful. The poem's syntax and repeated "We passed" create a steady, inevitable rhythm that reinforces the theme."""

EVAL_BAD_3 = """Poem (excerpt): "Because I could not stop for Death..."
Bad evaluation: The poet talks about death. It's a bit sad but also peaceful."""

EVAL_GOOD_4 = """Good evaluation: Identifies literal vs figurative meaning; names dominant emotions and ties them to specific lines; describes emotional arc; uses brief quotes."""
EVAL_BAD_4 = """Bad evaluation: Only summarizes plot in one sentence; no semantic or emotional breakdown; no quotes."""
EVAL_GOOD_5 = """Good evaluation: Discusses diction and tone; explains how semantics and emotion reinforce each other; accessible but precise."""
EVAL_BAD_5 = """Bad evaluation: Vague praise ("beautiful", "deep"); no structure; no analysis of how meaning or feeling is achieved."""

EVAL_ONE = EVAL_GOOD_1
EVAL_THREE = [EVAL_GOOD_1, EVAL_GOOD_2, EVAL_BAD_1]
EVAL_FIVE = [
    (EVAL_GOOD_1, "positive", "Breaks down semantics and emotion; uses quotes; notes tone and ambiguity."),
    (EVAL_GOOD_2, "positive", "Separates literal/figurative; traces emotional arc; cites diction."),
    (EVAL_GOOD_3, "positive", "Analyzes metaphor and syntax; ties form to theme."),
    (EVAL_BAD_1, "negative", "Only plot summary; no semantic or emotional analysis; no structure."),
    (EVAL_BAD_2, "negative", "Vague; no literal/figurative distinction; no quotes or detail."),
]
EVAL_COMPARISON_PAIRS = [
    (EVAL_BAD_1, EVAL_GOOD_1),
    (EVAL_BAD_2, EVAL_GOOD_2),
    (EVAL_BAD_3, EVAL_GOOD_3),
    (EVAL_BAD_4, EVAL_GOOD_4),
    (EVAL_BAD_5, EVAL_GOOD_5),
]


def build_evaluation_prompts() -> dict[str, str]:
    """Build 6 art evaluation prompts (poem analysis with semantics and emotion)."""
    base = """You are evaluating a popular poem. Provide a structured analysis that covers both semantics (literal and figurative meaning, diction) and emotion (dominant emotions, emotional arc, tone). Be specific and quote where relevant."""

    baseline = f"""{base}

Poem to evaluate:

{SAMPLE_POEM}"""

    prompts = {"baseline": baseline}

    prompts["one_example"] = f"""{base}

Example of a good evaluation:

{EVAL_ONE}

---
Now evaluate this poem in the same style (semantics + emotion breakdown):

{SAMPLE_POEM}"""

    ex_block = "\n\n---\n\n".join(EVAL_THREE)
    prompts["three_examples"] = f"""{base}

Examples (first two are good evaluations, third is a bad one to avoid):

{ex_block}

---
Now evaluate this poem:

{SAMPLE_POEM}"""

    ex_only = "\n\n---\n\n".join([t[0] for t in EVAL_FIVE])
    prompts["five_examples"] = f"""{base}

Examples:

{ex_only}

---
Now evaluate this poem:

{SAMPLE_POEM}"""

    rationale_block = "\n\n".join(
        f"Example:\n{t[0]}\nRationale: {t[2]}" for t in EVAL_FIVE
    )
    prompts["five_with_rationale"] = f"""{base}

Examples with rationale (what makes an evaluation good or bad):

{rationale_block}

---
Now evaluate this poem:

{SAMPLE_POEM}"""

    comp_blocks = [
        f"Bad:\n{bad}\n\nGood:\n{good}" for bad, good in EVAL_COMPARISON_PAIRS
    ]
    comparison_block_str = "\n\n---\n\n".join(comp_blocks)
    prompts["five_comparison_pairs"] = f"""{base}

Below are 5 direct comparison pairs: bad evaluation vs good evaluation (same poem or same criteria). Learn from the contrast.

{comparison_block_str}

---
Now evaluate this poem:

{SAMPLE_POEM}"""

    return prompts


# ---------------------------------------------------------------------------
# Task 3: Art discovery — 6 few-shot variants
# ---------------------------------------------------------------------------
DISC_GOOD_1 = """User prompt: "rainy Sunday afternoon, a bit melancholic but hopeful"
Good recommendations: Music: Nick Drake - "Pink Moon" (quiet, introspective, fits the mood). Film: "Lost in Translation" (melancholic but warm). Visual art: Hopper's "Nighthawks" or Monet's "Woman with a Parasol" for a softer take. Each ties to the mood and is specific."""

DISC_BAD_1 = """User prompt: "rainy Sunday afternoon, a bit melancholic but hopeful"
Bad recommendations: You could listen to some music or watch a movie. Maybe try something relaxing. Art is subjective."""

DISC_GOOD_2 = """User prompt: "something that feels like rebellion and youth"
Good recommendations: Music: The Clash - "London Calling"; Film: "The 400 Blows" (Truffaut); Visual art: Basquiat. Each captures rebellion and youth with concrete titles and creators."""

DISC_BAD_2 = """User prompt: "something that feels like rebellion and youth"
Bad recommendations: Rock music, indie films, street art. Lots of options out there."""

DISC_GOOD_3 = """User prompt: "cosy winter evening by the fire"
Good recommendations: Music: "Chocolate" by The 1975 or Vince Guaraldi's "Christmas Time Is Here"; Film: "The Holiday"; Visual art: Norman Rockwell's domestic scenes. Specific and mood-matched."""

DISC_BAD_3 = """User prompt: "cosy winter evening by the fire"
Bad recommendations: Something warm and nice. Maybe jazz or a romance movie."""

DISC_GOOD_4 = """Good recommendations: Include 2+ items per category (music, film, visual art); give title and creator; 1–2 sentences why it matches theme/mood. Prefer specific titles over genres."""
DISC_BAD_4 = """Bad recommendations: Generic ("listen to jazz"); no titles or creators; no explanation of why it fits the prompt."""
DISC_GOOD_5 = """Good recommendations: Interpret the prompt (mood/theme); suggest concrete works; note cross-connections between picks when relevant."""
DISC_BAD_5 = """Bad recommendations: Ignore nuance in the prompt; list only famous items without reasoning; no variety across media."""

DISC_ONE = DISC_GOOD_1
DISC_THREE = [DISC_GOOD_1, DISC_GOOD_2, DISC_BAD_1]
DISC_FIVE = [
    (DISC_GOOD_1, "positive", "Specific titles and creators; explains why each matches mood; covers music, film, art."),
    (DISC_GOOD_2, "positive", "Concrete names; theme and mood clearly linked."),
    (DISC_GOOD_3, "positive", "Mood-matched; specific works across media."),
    (DISC_BAD_1, "negative", "No specific recommendations; generic; no reasoning."),
    (DISC_BAD_2, "negative", "Only genres, no titles or creators; no explanation."),
]
DISC_COMPARISON_PAIRS = [
    (DISC_BAD_1, DISC_GOOD_1),
    (DISC_BAD_2, DISC_GOOD_2),
    (DISC_BAD_3, DISC_GOOD_3),
    (DISC_BAD_4, DISC_GOOD_4),
    (DISC_BAD_5, DISC_GOOD_5),
]


def build_discovery_prompts() -> dict[str, str]:
    """Build 6 art discovery prompts (recommend music/film/art from user prompt)."""
    base = """You are a curator. Given a user prompt describing a mood, theme, or vibe, recommend specific music (songs or artists), films (or directors), and visual art (artworks or artists). For each recommendation give the title/name, creator if relevant, and a short explanation of why it matches the prompt. Prefer concrete titles over vague genres."""

    baseline = f"""{base}

User prompt: "{SAMPLE_DISCOVERY_PROMPT}"

Provide your recommendations."""

    prompts = {"baseline": baseline}

    prompts["one_example"] = f"""{base}

Example of good recommendations:

{DISC_ONE}

---
Now provide recommendations for this user prompt: "{SAMPLE_DISCOVERY_PROMPT}" """

    ex_block = "\n\n---\n\n".join(DISC_THREE)
    prompts["three_examples"] = f"""{base}

Examples (first two are good, third is bad):

{ex_block}

---
User prompt: "{SAMPLE_DISCOVERY_PROMPT}"

Provide your recommendations."""

    ex_only = "\n\n---\n\n".join([t[0] for t in DISC_FIVE])
    prompts["five_examples"] = f"""{base}

Examples:

{ex_only}

---
User prompt: "{SAMPLE_DISCOVERY_PROMPT}"

Provide your recommendations."""

    rationale_block = "\n\n".join(
        f"Example:\n{t[0]}\nRationale: {t[2]}" for t in DISC_FIVE
    )
    prompts["five_with_rationale"] = f"""{base}

Examples with rationale (what makes recommendations good or bad):

{rationale_block}

---
User prompt: "{SAMPLE_DISCOVERY_PROMPT}"

Provide your recommendations."""

    comp_blocks = [
        f"Bad:\n{bad}\n\nGood:\n{good}" for bad, good in DISC_COMPARISON_PAIRS
    ]
    comparison_block_str = "\n\n---\n\n".join(comp_blocks)
    prompts["five_comparison_pairs"] = f"""{base}

Below are 5 direct comparison pairs: bad vs good recommendations for similar prompts. Learn from the contrast.

{comparison_block_str}

---
User prompt: "{SAMPLE_DISCOVERY_PROMPT}"

Provide your recommendations."""

    return prompts


# ---------------------------------------------------------------------------
# Model loading and generation (same as experiment 1)
# ---------------------------------------------------------------------------
def load_model_and_tokenizer():
    """Load Qwen3.5 MLX model and tokenizer."""
    try:
        from mlx_lm import load
    except ImportError:
        print("Install mlx-lm: pip install mlx mlx-lm")
        sys.exit(1)
    try:
        import mlx_lm.models.qwen3_5  # noqa: F401
    except ImportError:
        print(
            "Your mlx-lm version does not support Qwen3.5.\n"
            "Upgrade with: pip install -U 'mlx-lm>=0.31.0'"
        )
        sys.exit(1)

    model_path = Path(MODEL_PATH)
    if not model_path.exists():
        model_path = Path(__file__).resolve().parent / MODEL_PATH
    path_str = str(model_path) if model_path.exists() else MODEL_PATH
    print(f"Loading model from: {path_str}")
    model, tokenizer = load(path_str)
    return model, tokenizer


def run_generation(model, tokenizer, user_content: str) -> str:
    """Run one generation with chat template."""
    from mlx_lm import generate
    from mlx_lm.sample_utils import make_sampler

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": user_content},
    ]
    try:
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=ENABLE_THINKING,
        )
    except TypeError:
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    except Exception:
        text = f"<|im_start|>user\n{user_content}<|im_end|>\n<|im_start|>assistant\n"

    sampler = make_sampler(temp=TEMPERATURE, top_p=TOP_P)
    response = generate(
        model,
        tokenizer,
        prompt=text,
        max_tokens=MAX_TOKENS,
        sampler=sampler,
        verbose=False,
    )
    return response


def run_experiments(model, tokenizer):
    """Run all 6×3 = 18 few-shot prompt variants and collect results."""
    positive_pairs, negative_pairs = load_lyric_examples()
    one_ex, three_ex, five_rationale = build_lyric_example_sets(
        positive_pairs, negative_pairs
    )
    comparison_pairs = load_lyric_comparison_pairs(max_pairs=5)

    lyric_prompts = build_lyric_prompts(
        one_ex, three_ex, five_rationale, comparison_pairs
    )
    eval_prompts = build_evaluation_prompts()
    disc_prompts = build_discovery_prompts()

    results = {
        "meta": {
            "experiment": "experiment2_fewshot",
            "model_path": MODEL_PATH,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "enable_thinking": ENABLE_THINKING,
            "timestamp": datetime.now().isoformat(),
        },
        "task_1_lyric_translation": {},
        "task_2_art_evaluation": {},
        "task_3_art_discovery": {},
    }

    SEP = "\n" + "-" * 60 + "\n"

    for level_key, prompt_text in lyric_prompts.items():
        print(f"Task 1 Lyric [{level_key}]...")
        out = run_generation(model, tokenizer, prompt_text)
        results["task_1_lyric_translation"][level_key] = {
            "prompt_preview": prompt_text[:400] + "..." if len(prompt_text) > 400 else prompt_text,
            "output": out,
        }
        print(f"  Output length: {len(out)} chars{SEP}")

    for level_key, prompt_text in eval_prompts.items():
        print(f"Task 2 Evaluation [{level_key}]...")
        out = run_generation(model, tokenizer, prompt_text)
        results["task_2_art_evaluation"][level_key] = {
            "prompt_preview": prompt_text[:400] + "..." if len(prompt_text) > 400 else prompt_text,
            "output": out,
        }
        print(f"  Output length: {len(out)} chars{SEP}")

    for level_key, prompt_text in disc_prompts.items():
        print(f"Task 3 Discovery [{level_key}]...")
        out = run_generation(model, tokenizer, prompt_text)
        results["task_3_art_discovery"][level_key] = {
            "prompt_preview": prompt_text[:400] + "..." if len(prompt_text) > 400 else prompt_text,
            "output": out,
        }
        print(f"  Output length: {len(out)} chars{SEP}")

    return results


def save_results(results: dict):
    """Write results to OUTPUT_DIR as JSON and markdown report."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = OUTPUT_DIR / f"experiment2_results_{ts}.json"
    report_path = OUTPUT_DIR / f"experiment2_report_{ts}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    lines = [
        "# Experiment 2: Few-Shot Prompting Report",
        "",
        f"**Model:** {results['meta']['model_path']}  ",
        f"**Time:** {results['meta']['timestamp']}  ",
        f"**Max tokens:** {results['meta']['max_tokens']}",
        "",
        "## Prompt variants (per task)",
        "- baseline, one_example, three_examples, five_examples, five_with_rationale, five_comparison_pairs",
        "",
        "---",
        "",
    ]
    for task_name, task_key in [
        ("Task 1: Lyric translation (EN→ZH)", "task_1_lyric_translation"),
        ("Task 2: Art evaluation (poems)", "task_2_art_evaluation"),
        ("Task 3: Art discovery", "task_3_art_discovery"),
    ]:
        lines.append(f"## {task_name}\n")
        for level_key, data in results[task_key].items():
            lines.append(f"### {level_key}\n")
            lines.append("**Output:**\n")
            lines.append("```")
            lines.append((data["output"] or "").strip())
            lines.append("```\n")
        lines.append("---\n")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nResults saved to:\n  JSON: {json_path}\n  Report: {report_path}")
    return json_path, report_path


def main():
    print("Experiment 2: Few-shot prompting (6 variants × 3 tasks)")
    print("Loading model...")
    model, tokenizer = load_model_and_tokenizer()
    print("Running 18 experiments...")
    results = run_experiments(model, tokenizer)
    save_results(results)
    print("Done.")


if __name__ == "__main__":
    main()
