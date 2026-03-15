# Qwen3.5 Prompt Experimentation: Design Document

Three tasks with five prompt levels each, varying in **structure**, **specificity**, and **style**. Levels progress from minimal/open-ended to highly specified/expert-style prompts to test how the model responds to different prompt engineering approaches.

---

## Task 1: Lyric Translation (with rhythm/rhyme adaptability)

**Goal:** Translate song lyrics while preserving or adapting rhythm, rhyme, and singability in the target language.

---

### Level 1 — Minimal / Open-ended

**Prompt:**
```
Translate this song lyric to English. Keep it singable.
```

**Design reasoning:**
- **Structure:** Single imperative sentence; no sections or formatting requirements.
- **Specificity:** Low — no source language, no rhyme/meter constraints, “singable” is vague.
- **Style:** Casual, directive. Tests baseline behavior when the model must infer all translation priorities.
- **Hypothesis:** Model may default to literal translation and ignore rhythm; useful as control.

---

### Level 2 — Structured

**Prompt:**
```
Translate the following lyric to English.

Requirements:
- Preserve the emotional tone
- Aim for similar syllable count per line where possible
- Prefer natural phrasing over word-for-word accuracy

Lyric to translate:
[LYRIC_PLACEHOLDER]
```

**Design reasoning:**
- **Structure:** Bullet-point requirements + placeholder; clear sections.
- **Specificity:** Medium — “syllable count” and “natural phrasing” give direction but no exact metrics.
- **Style:** Instructional. Gives the model a checklist without prescribing format of output.
- **Hypothesis:** Should improve rhythm awareness and readability over Level 1.

---

### Level 3 — Specific

**Prompt:**
```
You are a lyric translator. Translate the lyric below from [SOURCE_LANG] to English.

Constraints:
- Target rhyme scheme: [e.g., AABB or match original]
- Preserve or adapt the original meter (e.g., 4 beats per line)
- Keep each line under 12 syllables for singability
- Retain key emotional words and imagery even if you need to rephrase

Output format: provide the translation first, then 2–3 lines on choices you made for rhythm/rhyme.

Lyric:
[LYRIC_PLACEHOLDER]
```

**Design reasoning:**
- **Structure:** Role + constraints + output format (translation + short rationale).
- **Specificity:** High — explicit rhyme scheme, meter, syllable cap, and rationale request.
- **Style:** Professional, constraint-driven. Tests whether the model can follow concrete specs and explain tradeoffs.
- **Hypothesis:** Should yield more controllable, comparable outputs and expose reasoning.

---

### Level 4 — Styled / Persona

**Prompt:**
```
You are a bilingual songwriter who specializes in translating pop and rock lyrics for international releases. Your translations are known for feeling native in the target language while keeping the song performable—same energy, similar punch on rhyming words, and lines that fit the melody.

Translate this lyric to English in that spirit: prioritize how it would sound when sung, then meaning, then literal fidelity. If the original rhymes, your translation should rhyme in equivalent positions; if it doesn’t, you may add subtle rhyme for catchiness. Keep the register (formal/slang/poetic) consistent.

Lyric:
[LYRIC_PLACEHOLDER]
```

**Design reasoning:**
- **Structure:** Persona + implicit priorities (sung first, meaning, fidelity) + optional rhyme rule.
- **Specificity:** Medium–high via prioritization and “equivalent positions,” but no numeric constraints.
- **Style:** Narrative, expert persona. Appeals to identity and “how it would sound when sung.”
- **Hypothesis:** Persona may improve naturalness and rhythm over Level 2 without hard constraints.

---

### Level 5 — Expert / Full specification

**Prompt:**
```
Task: Lyric translation with full rhythm and rhyme adaptability.

Role: Expert lyric translator for music localization (subtitles, dubbed songs, and cover versions).

Input: A song lyric in [SOURCE_LANG]. Original meter and rhyme scheme will be provided if known.

Output format:
1. **Translation** — Full English translation, one stanza per block.
2. **Meter note** — Original meter (e.g., 8-6-8-6) and how you adapted it (e.g., “kept 8-6; line 3 extended to 9 for stress”).
3. **Rhyme note** — Original pattern (e.g., AABB) and your pattern; list any lines where rhyme was sacrificed for meaning and why.
4. **Key choices** — Up to 3 specific word or phrase decisions (source → target) and rationale (rhythm, rhyme, or cultural nuance).

Constraints:
- Max 14 syllables per line unless the original clearly exceeds it.
- No forced rhyme that distorts meaning; prefer half-rhyme or assonance over nonsense.
- Preserve emotional climax and key imagery; reorder or paraphrase as needed for singability.

Lyric:
[LYRIC_PLACEHOLDER]

(Optional: Original meter: [METER]. Original rhyme: [SCHEME].)
```

**Design reasoning:**
- **Structure:** Task + role + input/output spec + constraints + optional metadata.
- **Specificity:** Very high — numbered output sections, syllable cap, rules for rhyme vs meaning, optional meter/scheme.
- **Style:** Specification document. Suitable for evaluation (consistent sections) and real localization workflows.
- **Hypothesis:** Maximizes consistency and interpretability; may stress the model on very long instructions.

---

## Task 2: Art Evaluation (popular poems — semantics and emotion)

**Goal:** Evaluate poems with explicit breakdown of semantic content and emotional arc.

---

### Level 1 — Minimal / Open-ended

**Prompt:**
```
Evaluate this poem. Talk about what it means and how it makes you feel.
```

**Design reasoning:**
- **Structure:** One sentence; no format.
- **Specificity:** Low — “evaluate,” “means,” and “makes you feel” are broad.
- **Style:** Conversational. Baseline for how much structure the model adds on its own.
- **Hypothesis:** Output may be short and generic or inconsistently structured.

---

### Level 2 — Structured

**Prompt:**
```
Evaluate the following poem. Structure your response as follows:

1. Summary — What the poem is about in 2–3 sentences.
2. Main themes — List 2–4 themes or ideas.
3. Emotional effect — How the poem might make a reader feel and why.
4. One standout line or image — Quote it and briefly explain.

Poem:
[POEM_PLACEHOLDER]
```

**Design reasoning:**
- **Structure:** Numbered sections (summary, themes, emotion, standout moment).
- **Specificity:** Medium — sections defined but not deeply specified (e.g., no rubric).
- **Style:** Essay-like. Encourages coverage of semantics and emotion without heavy jargon.
- **Hypothesis:** More comparable responses and clearer semantics/emotion split than Level 1.

---

### Level 3 — Specific

**Prompt:**
```
Analyze the poem below along two dimensions: semantics and emotion.

**Semantics:**
- Literal meaning: What literally happens or is described (setting, speaker, events).
- Figurative meaning: Metaphors, symbols, or deeper ideas (list with brief explanation).
- Diction: 2–3 word choices that carry extra weight and why.

**Emotion:**
- Dominant emotion(s): Name them and point to lines or images that create them.
- Emotional arc: How the feeling shifts from start to end (e.g., calm → unease → resolve).
- Tone: Describe the speaker’s attitude (e.g., nostalgic, ironic, solemn).

Keep each subsection to 2–4 sentences. End with one sentence on how semantics and emotion work together in the poem.

Poem:
[POEM_PLACEHOLDER]
```

**Design reasoning:**
- **Structure:** Two main dimensions with sub-bullets and a closing synthesis.
- **Specificity:** High — defined terms (literal/figurative, diction, arc, tone) and length guidance.
- **Style:** Analytical. Mirrors classroom or review formats.
- **Hypothesis:** Should yield consistent, comparable analyses and explicit semantics/emotion breakdown.

---

### Level 4 — Styled / Persona

**Prompt:**
```
You are a critic who writes for a general audience—thoughtful but not academic. Your reviews help readers decide what to read and why it might matter to them.

Review this poem. Write in a warm, precise voice. Cover what the poem is “doing” (its ideas and craft) and what it “does” to the reader (emotional impact). Use one or two short quotes. Avoid jargon; if you use a term like “meter” or “imagery,” briefly explain it. End with who might especially enjoy this poem and why.

Poem:
[POEM_PLACEHOLDER]
```

**Design reasoning:**
- **Structure:** Persona + implicit sections (doing / does to reader / audience).
- **Specificity:** Medium — “ideas and craft” and “emotional impact” without rigid subsections.
- **Style:** Accessible critic. Tone and audience constrain style more than structure.
- **Hypothesis:** May improve readability and engagement; semantics and emotion still present but less templated.

---

### Level 5 — Expert / Full specification

**Prompt:**
```
Task: Poem evaluation with semantics and emotion breakdown.

Role: Literary analyst producing evaluations for an anthology or textbook (student and general reader audience).

Output format (use these headings):

**1. Overview**
- 2–3 sentence summary of the poem’s subject and situation.
- Identification of form (e.g., sonnet, free verse, ballad) if relevant.

**2. Semantic analysis**
- Literal layer: Setting, speaker, narrative or descriptive content.
- Figurative layer: Central metaphor(s), symbol(s), or conceit; how they extend through the poem.
- Diction and syntax: 2–3 specific choices (quote + line number) and their effect on meaning.

**3. Emotional analysis**
- Dominant emotions: Name and tie each to specific lines or images.
- Emotional progression: Beginning → middle → end (describe the shift).
- Tone: Speaker’s attitude and how it is achieved (word choice, rhythm, punctuation).

**4. Synthesis**
- In 2–4 sentences, explain how the poem’s semantic and emotional layers reinforce each other.
- One sentence on the poem’s lasting effect or why it might resonate with readers.

Constraints: Quote sparingly (3–5 short quotes total). No plot-only summary; focus on how meaning and feeling are made. Be precise but accessible.

Poem:
[POEM_PLACEHOLDER]
```

**Design reasoning:**
- **Structure:** Task + role + numbered sections with sub-bullets and a synthesis.
- **Specificity:** Very high — headings, quote count, “no plot-only” constraint, audience.
- **Style:** Formal specification. Enables grading or comparison across many poems.
- **Hypothesis:** Most consistent and complete semantics/emotion breakdown; useful for benchmarking.

---

## Task 3: Art Discovery (music / movie / art / artists from prompt)

**Goal:** Recommend music, films, visual art, or artists based on a user’s textual prompt (mood, theme, style).

---

### Level 1 — Minimal / Open-ended

**Prompt:**
```
I want something that feels like [PROMPT]. What do you recommend?
```

**Design reasoning:**
- **Structure:** Single sentence with a single placeholder.
- **Specificity:** Low — no media type, no count, “feels like” is vague.
- **Style:** Conversational, user-like. Tests default breadth (e.g., does model mix music and film?).
- **Hypothesis:** Recommendations may be generic or biased toward one medium.

---

### Level 2 — Structured

**Prompt:**
```
Based on this description, suggest some recommendations:

Description: [PROMPT]

Give me:
- 2–3 songs or musicians
- 2–3 movies or directors
- 2–3 artworks or artists (any medium: painting, sculpture, etc.)

For each item, write one short sentence on why it fits.
```

**Design reasoning:**
- **Structure:** Description + three categories with counts and “why it fits.”
- **Specificity:** Medium — multi-modal (music, film, visual art) and brief justification.
- **Style:** Request list. Ensures coverage across domains.
- **Hypothesis:** More balanced and comparable than Level 1; reasoning may be shallow.

---

### Level 3 — Specific

**Prompt:**
```
Art discovery task: recommend works and creators that match the user’s prompt.

User prompt: “[PROMPT]”

Requirements:
- Recommend exactly 2 items per category: Music (song or artist), Film (movie or director), Visual art (artwork or artist).
- For each item provide: title/name, creator (if applicable), and 1–2 sentences explaining the match (theme, mood, or style).
- If the prompt is very narrow (e.g., one genre), you may interpret “match” as adjacent or complementary rather than literal.
- Prefer specific titles/names over vague descriptions.

Output format: Use headings “Music,” “Film,” “Visual art.” Under each, list the 2 items with the requested details.
```

**Design reasoning:**
- **Structure:** Task + user prompt + requirements + output format.
- **Specificity:** High — exact counts, categories, and fields (title, creator, explanation).
- **Style:** Brief spec. Good for evaluation (fixed format) and real discovery UIs.
- **Hypothesis:** Consistent structure and reasoning; may favor well-known works.

---

### Level 4 — Styled / Persona

**Prompt:**
```
You are a curator and tastemaker. Someone comes to you and says: “[PROMPT]”

Respond as if you’re reading their vibe and pulling from a deep, cross-genre knowledge. Suggest a few things across music, film, and visual art (or other arts if they fit better). For each suggestion, say why it fits—not just theme but mood, energy, or the “world” it creates. Write in a warm, confident tone. It’s okay to be opinionated (“If you like X, you have to try Y”). Aim for 4–6 recommendations total, with at least two different media.
```

**Design reasoning:**
- **Structure:** Persona + user quote + implicit categories and tone.
- **Specificity:** Medium — “4–6,” “at least two media,” “why it fits” (mood/energy/world).
- **Style:** Curator voice, “vibe” and “world” framing. Encourages associative, cross-art reasoning.
- **Hypothesis:** May produce more surprising or nuanced matches; structure less rigid.

---

### Level 5 — Expert / Full specification

**Prompt:**
```
Task: Multi-modal art discovery from a natural-language prompt.

Role: Expert curator for a platform that suggests music, film, and visual art based on mood, theme, or style. Your recommendations are used by real users to discover new work.

Input: User prompt (free text describing what they want to find or how they want to feel).

Output format:

**1. Interpretation**
- In 1–2 sentences, summarize how you interpreted the prompt (key themes, mood, style, or constraints).
- Note any ambiguity and how you resolved it (e.g., “Focused on ‘lonely’ as emotional tone rather than literal solitude”).

**2. Recommendations**
For each of the three categories, provide exactly 2 recommendations (6 total).

| Category   | Title/Name      | Creator       | Why it matches (1–2 sentences) |
|-----------|------------------|---------------|---------------------------------|
| Music     | …                | …             | …                               |
| Film      | …                | …             | …                               |
| Visual art| …                | …             | …                               |

**3. Cross-connections**
- In 2–3 sentences, note any theme or mood that appears across your picks (e.g., “Several recommendations share a sense of quiet rebellion”).
- Optional: one “wild card” suggestion from any medium that stretches the prompt in an interesting way, with one sentence justification.

Constraints: Prefer concrete titles and names. If the prompt is very broad, narrow to one coherent reading. Balance familiarity (recognizable) with discovery (at least one less obvious pick per category when possible).

User prompt: “[PROMPT]”
```

**Design reasoning:**
- **Structure:** Task + role + input/output + interpretation section + table + cross-connections + constraints.
- **Specificity:** Very high — interpretation step, table format, cross-cutting analysis, optional wild card.
- **Style:** Product-style spec. Supports UX (interpretation) and evaluation (fixed schema).
- **Hypothesis:** Best for consistency and reasoning visibility; table may need post-processing if model output is markdown.

---

## Summary table

| Task              | Level 1       | Level 2      | Level 3       | Level 4        | Level 5         |
|-------------------|---------------|--------------|---------------|----------------|-----------------|
| **Structure**     | Minimal       | Sectioned    | Role + format | Persona-led    | Full spec       |
| **Specificity**   | Low           | Medium       | High          | Medium–high    | Very high       |
| **Style**         | Casual        | Instructional| Analytical    | Narrative/voice| Formal spec     |
| **Primary use**   | Baseline      | Consistency  | Evaluation    | Engagement     | Benchmarking    |

---

## Placeholders for experimentation

- **Task 1:** Replace `[LYRIC_PLACEHOLDER]` (and optionally `[SOURCE_LANG]`, `[METER]`, `[SCHEME]`) with real lyrics.
- **Task 2:** Replace `[POEM_PLACEHOLDER]` with a public-domain or popular poem (e.g., Frost, Dickinson, Hughes).
- **Task 3:** Replace `[PROMPT]` with user-style queries (e.g., “rainy Sunday afternoon, a bit melancholic but hopeful,” “post-apocalyptic hope,” “something that feels like a warm hug”).

These placeholders are used in the experiment script to run each prompt level with concrete inputs.
