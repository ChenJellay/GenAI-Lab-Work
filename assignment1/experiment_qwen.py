#!/usr/bin/env python3
"""
Qwen3.5-MLX-4bit prompt experimentation.
Runs 5 prompt levels × 3 tasks (lyric translation, art evaluation, art discovery),
saves outputs and a simple report.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL_PATH = os.environ.get("QWEN_MODEL_PATH", "Qwen3.5-9B-MLX-4bit")
OUTPUT_DIR = Path(__file__).resolve().parent / "experiment_outputs"
MAX_TOKENS = 2048
TEMPERATURE = 0.7
TOP_P = 0.9
# Set to False to disable Qwen3.5 "thinking" (reasoning) tokens so the model
# goes straight to the answer and uses the token budget for the actual response.
# The chat template emits an empty <think></think> block when False.
ENABLE_THINKING = False

# ---------------------------------------------------------------------------
# Sample inputs (placeholders for the prompts)
# ---------------------------------------------------------------------------
SAMPLE_LYRIC = """\
Despacito, quiero respirar tu cuello despacito
Deja que te diga cosas al oído
Para que te acuerdes si no estás conmigo."""

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
# Task 1: Lyric translation — 5 levels
# ---------------------------------------------------------------------------
LYRIC_PROMPTS = {
    "level_1_minimal": """Translate this song lyric to English. Keep it singable.

Lyric:
{lyric}""",

    "level_2_structured": """Translate the following lyric to English.

Requirements:
- Preserve the emotional tone
- Aim for similar syllable count per line where possible
- Prefer natural phrasing over word-for-word accuracy

Lyric to translate:
{lyric}""",

    "level_3_specific": """You are a lyric translator. Translate the lyric below from Spanish to English.

Constraints:
- Target rhyme scheme: AABB or match original where possible
- Preserve or adapt the original meter (e.g., 4 beats per line)
- Keep each line under 12 syllables for singability
- Retain key emotional words and imagery even if you need to rephrase

Output format: provide the translation first, then 2–3 lines on choices you made for rhythm/rhyme.

Lyric:
{lyric}""",

    "level_4_styled": """You are a bilingual songwriter who specializes in translating pop and rock lyrics for international releases. Your translations are known for feeling native in the target language while keeping the song performable—same energy, similar punch on rhyming words, and lines that fit the melody.

Translate this lyric to English in that spirit: prioritize how it would sound when sung, then meaning, then literal fidelity. If the original rhymes, your translation should rhyme in equivalent positions; if it doesn't, you may add subtle rhyme for catchiness. Keep the register (formal/slang/poetic) consistent.

Lyric:
{lyric}""",

    "level_5_expert": """Task: Lyric translation with full rhythm and rhyme adaptability.

Role: Expert lyric translator for music localization (subtitles, dubbed songs, and cover versions).

Input: A song lyric in Spanish. Original meter and rhyme scheme will be provided if known.

Output format:
1. **Translation** — Full English translation, one stanza per block.
2. **Meter note** — Original meter (e.g., 8-6-8-6) and how you adapted it (e.g., "kept 8-6; line 3 extended to 9 for stress").
3. **Rhyme note** — Original pattern (e.g., AABB) and your pattern; list any lines where rhyme was sacrificed for meaning and why.
4. **Key choices** — Up to 3 specific word or phrase decisions (source → target) and rationale (rhythm, rhyme, or cultural nuance).

Constraints:
- Max 14 syllables per line unless the original clearly exceeds it.
- No forced rhyme that distorts meaning; prefer half-rhyme or assonance over nonsense.
- Preserve emotional climax and key imagery; reorder or paraphrase as needed for singability.

Lyric:
{lyric}""",
}

# ---------------------------------------------------------------------------
# Task 2: Art evaluation (poems) — 5 levels
# ---------------------------------------------------------------------------
EVALUATION_PROMPTS = {
    "level_1_minimal": """Evaluate this poem. Talk about what it means and how it makes you feel.

Poem:
{poem}""",

    "level_2_structured": """Evaluate the following poem. Structure your response as follows:

1. Summary — What the poem is about in 2–3 sentences.
2. Main themes — List 2–4 themes or ideas.
3. Emotional effect — How the poem might make a reader feel and why.
4. One standout line or image — Quote it and briefly explain.

Poem:
{poem}""",

    "level_3_specific": """Analyze the poem below along two dimensions: semantics and emotion.

**Semantics:**
- Literal meaning: What literally happens or is described (setting, speaker, events).
- Figurative meaning: Metaphors, symbols, or deeper ideas (list with brief explanation).
- Diction: 2–3 word choices that carry extra weight and why.

**Emotion:**
- Dominant emotion(s): Name them and point to lines or images that create them.
- Emotional arc: How the feeling shifts from start to end (e.g., calm → unease → resolve).
- Tone: Describe the speaker's attitude (e.g., nostalgic, ironic, solemn).

Keep each subsection to 2–4 sentences. End with one sentence on how semantics and emotion work together in the poem.

Poem:
{poem}""",

    "level_4_styled": """You are a critic who writes for a general audience—thoughtful but not academic. Your reviews help readers decide what to read and why it might matter to them.

Review this poem. Write in a warm, precise voice. Cover what the poem is "doing" (its ideas and craft) and what it "does" to the reader (emotional impact). Use one or two short quotes. Avoid jargon; if you use a term like "meter" or "imagery," briefly explain it. End with who might especially enjoy this poem and why.

Poem:
{poem}""",

    "level_5_expert": """Task: Poem evaluation with semantics and emotion breakdown.

Role: Literary analyst producing evaluations for an anthology or textbook (student and general reader audience).

Output format (use these headings):

**1. Overview**
- 2–3 sentence summary of the poem's subject and situation.
- Identification of form (e.g., sonnet, free verse, ballad) if relevant.

**2. Semantic analysis**
- Literal layer: Setting, speaker, narrative or descriptive content.
- Figurative layer: Central metaphor(s), symbol(s), or conceit; how they extend through the poem.
- Diction and syntax: 2–3 specific choices (quote + line number) and their effect on meaning.

**3. Emotional analysis**
- Dominant emotions: Name and tie each to specific lines or images.
- Emotional progression: Beginning → middle → end (describe the shift).
- Tone: Speaker's attitude and how it is achieved (word choice, rhythm, punctuation).

**4. Synthesis**
- In 2–4 sentences, explain how the poem's semantic and emotional layers reinforce each other.
- One sentence on the poem's lasting effect or why it might resonate with readers.

Constraints: Quote sparingly (3–5 short quotes total). No plot-only summary; focus on how meaning and feeling are made. Be precise but accessible.

Poem:
{poem}""",
}

# ---------------------------------------------------------------------------
# Task 3: Art discovery — 5 levels
# ---------------------------------------------------------------------------
DISCOVERY_PROMPTS = {
    "level_1_minimal": """I want something that feels like {prompt}. What do you recommend?""",

    "level_2_structured": """Based on this description, suggest some recommendations:

Description: {prompt}

Give me:
- 2–3 songs or musicians
- 2–3 movies or directors
- 2–3 artworks or artists (any medium: painting, sculpture, etc.)

For each item, write one short sentence on why it fits.""",

    "level_3_specific": """Art discovery task: recommend works and creators that match the user's prompt.

User prompt: "{prompt}"

Requirements:
- Recommend exactly 2 items per category: Music (song or artist), Film (movie or director), Visual art (artwork or artist).
- For each item provide: title/name, creator (if applicable), and 1–2 sentences explaining the match (theme, mood, or style).
- If the prompt is very narrow (e.g., one genre), you may interpret "match" as adjacent or complementary rather than literal.
- Prefer specific titles/names over vague descriptions.

Output format: Use headings "Music," "Film," "Visual art." Under each, list the 2 items with the requested details.""",

    "level_4_styled": """You are a curator and tastemaker. Someone comes to you and says: "{prompt}"

Respond as if you're reading their vibe and pulling from a deep, cross-genre knowledge. Suggest a few things across music, film, and visual art (or other arts if they fit better). For each suggestion, say why it fits—not just theme but mood, energy, or the "world" it creates. Write in a warm, confident tone. It's okay to be opinionated ("If you like X, you have to try Y"). Aim for 4–6 recommendations total, with at least two different media.""",

    "level_5_expert": """Task: Multi-modal art discovery from a natural-language prompt.

Role: Expert curator for a platform that suggests music, film, and visual art based on mood, theme, or style. Your recommendations are used by real users to discover new work.

Input: User prompt (free text describing what they want to find or how they want to feel).

Output format:

**1. Interpretation**
- In 1–2 sentences, summarize how you interpreted the prompt (key themes, mood, style, or constraints).
- Note any ambiguity and how you resolved it (e.g., "Focused on 'lonely' as emotional tone rather than literal solitude").

**2. Recommendations**
For each of the three categories, provide exactly 2 recommendations (6 total).

| Category   | Title/Name      | Creator       | Why it matches (1–2 sentences) |
|-----------|------------------|---------------|---------------------------------|
| Music     | …                | …             | …                               |
| Film      | …                | …             | …                               |
| Visual art| …                | …             | …                               |

**3. Cross-connections**
- In 2–3 sentences, note any theme or mood that appears across your picks (e.g., "Several recommendations share a sense of quiet rebellion").
- Optional: one "wild card" suggestion from any medium that stretches the prompt in an interesting way, with one sentence justification.

Constraints: Prefer concrete titles and names. If the prompt is very broad, narrow to one coherent reading. Balance familiarity (recognizable) with discovery (at least one less obvious pick per category when possible).

User prompt: "{prompt}" """,
}


def load_model_and_tokenizer():
    """Load Qwen3.5 MLX model and tokenizer from local path or HuggingFace."""
    try:
        from mlx_lm import load, generate
    except ImportError:
        print("Install mlx-lm: pip install mlx mlx-lm")
        sys.exit(1)
    # Qwen3.5 (model_type qwen3_5) requires mlx-lm >= 0.30; older versions lack mlx_lm.models.qwen3_5
    try:
        import mlx_lm.models.qwen3_5  # noqa: F401
    except ImportError:
        print(
            "Your mlx-lm version does not support Qwen3.5 (model_type qwen3_5).\n"
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
        # Qwen3.5: enable_thinking=False makes the chat template emit an empty
        # <think></think> block so the model skips reasoning and goes straight to the answer.
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=ENABLE_THINKING,
        )
    except TypeError:
        # Tokenizer doesn't forward enable_thinking (e.g. some wrappers)
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
    """Run all 15 prompts and collect results."""
    results = {
        "meta": {
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

    # Task 1: Lyric translation
    print("Task 1: Lyric translation (5 levels)...")
    for level_key, template in LYRIC_PROMPTS.items():
        prompt_text = template.format(lyric=SAMPLE_LYRIC)
        print(f"  Running {level_key}...")
        out = run_generation(model, tokenizer, prompt_text)
        results["task_1_lyric_translation"][level_key] = {
            "prompt_preview": prompt_text[:300] + "..." if len(prompt_text) > 300 else prompt_text,
            "output": out,
        }
        print(f"\n  [{level_key}] Model output:\n{out}{SEP}")

    # Task 2: Art evaluation
    print("Task 2: Art evaluation (5 levels)...")
    for level_key, template in EVALUATION_PROMPTS.items():
        prompt_text = template.format(poem=SAMPLE_POEM)
        print(f"  Running {level_key}...")
        out = run_generation(model, tokenizer, prompt_text)
        results["task_2_art_evaluation"][level_key] = {
            "prompt_preview": prompt_text[:300] + "..." if len(prompt_text) > 300 else prompt_text,
            "output": out,
        }
        print(f"\n  [{level_key}] Model output:\n{out}{SEP}")

    # Task 3: Art discovery
    print("Task 3: Art discovery (5 levels)...")
    for level_key, template in DISCOVERY_PROMPTS.items():
        prompt_text = template.format(prompt=SAMPLE_DISCOVERY_PROMPT)
        print(f"  Running {level_key}...")
        out = run_generation(model, tokenizer, prompt_text)
        results["task_3_art_discovery"][level_key] = {
            "prompt_preview": prompt_text[:300] + "..." if len(prompt_text) > 300 else prompt_text,
            "output": out,
        }
        print(f"\n  [{level_key}] Model output:\n{out}{SEP}")

    return results


def save_results(results: dict):
    """Write results to OUTPUT_DIR as JSON and a readable report."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = OUTPUT_DIR / f"results_{ts}.json"
    report_path = OUTPUT_DIR / f"report_{ts}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Simple markdown report
    lines = [
        "# Qwen3.5 Prompt Experiment Report",
        "",
        f"**Model:** {results['meta']['model_path']}  \n**Time:** {results['meta']['timestamp']}  \n**Max tokens:** {results['meta']['max_tokens']}",
        "",
        "---",
        "",
    ]
    for task_name, task_key in [
        ("Task 1: Lyric translation", "task_1_lyric_translation"),
        ("Task 2: Art evaluation", "task_2_art_evaluation"),
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
    print("Loading model (this may take a moment)...")
    model, tokenizer = load_model_and_tokenizer()
    print("Running all 15 experiments...")
    results = run_experiments(model, tokenizer)
    save_results(results)
    print("Done.")


if __name__ == "__main__":
    main()
