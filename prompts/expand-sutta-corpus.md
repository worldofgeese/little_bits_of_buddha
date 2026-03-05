# Task: Expand Sutta Corpus from SuttaCentral Data

## Context

Little Bits of Buddha (LBOB) is a Telegram chatbot that teaches the Dhamma using LLM + semantic sutta search + conversation memory. The sutta corpus currently has 25 hand-written summaries in `sutta_corpus/suttas.json`. We need to expand to ~200-300 curated suttas using real translations from SuttaCentral's open data.

**Repo:** `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`
**Python:** 3.12, trio (NOT asyncio)
**License:** Bhikkhu Sujato's translations are CC0 (public domain)

## Branch

Create and work on branch: `feat/expand-sutta-corpus`
Do NOT work on main.

## What to Do

### Step 1: Write the scraper script

Create `scripts/fetch_sc_suttas.py` — a Python script that:

1. **Clones or shallow-fetches** the `suttacentral/sc-data` GitHub repo (just the translation directory).
   - Path in repo: `sc_bilara_data/translation/en/sujato/sutta/`
   - Use `git clone --depth 1 --filter=blob:none --sparse` then `git sparse-checkout set sc_bilara_data/translation/en/sujato/sutta` to keep it small.
   - Clone into a temp directory, clean up after.

2. **Parses bilara JSON files.** Each file is a JSON dict mapping segment IDs to English text:
   ```json
   {
     "mn10:0.1": "Middle Discourses 10 ",
     "mn10:0.2": "Mindfulness Meditation ",
     "mn10:1.1": "So I have heard. ",
     ...
   }
   ```
   Concatenate all segment values (in segment ID order) to produce the full sutta text. Strip HTML tags if any. Segment IDs sort lexically within a sutta.

3. **Filters to a curated list** of ~200-300 essential suttas (see curation list below).

4. **Extracts metadata** from the file path:
   - Collection: `dn`, `mn`, `sn`, `an`, `kn` (from directory structure)
   - Sutta ID: from filename, e.g. `mn10_translation-en-sujato.json` → `MN10`
   - Title: from the segment with key ending in `:0.2` (or `:0.1` if no `:0.2`)

5. **Assigns themes** using a keyword-based heuristic. Map common Pali/English terms to theme tags:
   - "suffering", "dukkha" → `suffering`
   - "mindfulness", "sati" → `mindfulness`
   - "meditation", "jhana", "samadhi" → `meditation`
   - "impermanent", "anicca" → `impermanence`
   - "not-self", "anatta" → `non-self`
   - "eightfold path" → `eightfold path`
   - "dependent origination", "conditions" → `dependent origination`
   - "ethics", "precepts", "sila" → `ethics`
   - "loving-kindness", "metta" → `loving-kindness`
   - "equanimity", "upekkha" → `equanimity`
   - "craving", "tanha" → `craving`
   - "nibbana", "extinguishment" → `nibbana`
   - "kamma", "karma", "action" → `kamma`
   - "rebirth", "lives" → `rebirth`
   - "lay life", "householder" → `lay life`
   - Add more as you see fit. Each sutta should have 2-5 theme tags.

6. **Outputs** `sutta_corpus/suttas.json` in the existing format:
   ```json
   [
     {
       "id": "MN10",
       "title": "Mindfulness Meditation",
       "collection": "MN",
       "text": "So I have heard. At one time the Buddha was staying...",
       "themes": ["mindfulness", "meditation", "four foundations"]
     }
   ]
   ```

7. **Text length limit:** If a sutta's concatenated text exceeds 4000 characters, truncate to 4000 chars at the nearest sentence boundary and append "[text truncated]". Very long suttas (DN1 is ~15,000 words) need this to keep embedding quality reasonable.

### Step 2: The Curation List

Create `sutta_corpus/curated_ids.txt` — one sutta ID per line. Include these essential categories:

**Core Doctrinal (must include all):**
- SN56.11 (Dhammacakkappavattana — First Sermon)
- SN22.59 (Anattalakkhana — Non-Self)
- MN10 (Satipatthana — Mindfulness)
- DN22 (Mahasatipatthana)
- MN118 (Anapanasati — Breathing)
- SN12.2 (Paticcasamuppada — Dependent Origination)
- MN28 (Mahahatthipadopama — Elephant Footprint)
- MN141 (Saccavibhanga — Analysis of Truths)
- SN45.8 (Magga-vibhanga — Path Factors)
- SN35.28 (Aditta — Fire Sermon)
- MN22 (Alagaddupama — Water Snake Simile — on grasping)

**Ethics & Practice:**
- AN8.54 (Dighajanu — advice to householders)
- AN5.57 (Upajjhatthana — five remembrances)
- AN10.176 (Cunda Sutta)
- MN61 (Ambalatthika-rahulovada — advice to Rahula)
- MN21 (Kakacupama — Simile of the Saw)
- MN8 (Sallekha — Effacement)
- AN3.65 (Kalama Sutta)
- MN2 (Sabbasava — All Taints)
- DN31 (Sigalovada — lay ethics)

**Meditation & Mental Development:**
- MN19 (Dvedhavitakka — Two Kinds of Thought)
- MN20 (Vitakkasanthana — Removing Distracting Thoughts)
- AN4.41 (Samadhi — Concentration)
- SN46.51 (Ahara — Feeding the Factors)
- AN5.28 (Samadhanga — Factors of Concentration)
- MN62 (Maha-Rahulovada — advice on breathing)
- AN11.2 (Cetana — Intention)
- MN131 (Bhaddekaratta — Ideal Lover of Solitude)

**Loving-Kindness & Compassion:**
- SN1.8 (Metta — Karaniya Metta)
- AN4.125 (Mettavihari — Loving-Kindness Dweller)
- AN11.16 (Mettanisamsa — Benefits of Loving-Kindness)
- Snp1.8 (Karaniya Metta Sutta — from Khuddaka Nikaya)
- SN46.54 (Mettasahagata)

**Wisdom & Insight:**
- SN22.95 (Phena — Foam)
- MN1 (Mulapariyaya — Root of All Things)
- MN9 (Sammaditthi — Right View)
- AN4.170 (Yuganaddha — In Tandem)
- SN36.6 (Salla — Arrow)
- MN63 (Culamalunkya — the Poisoned Arrow)
- SN35.85 (Sunyata — Emptiness)
- MN38 (Mahatanhasankhaya — Craving)
- SN12.15 (Kaccayanagotta — Right View on Existence)
- MN72 (Aggivacchagotta — to Vacchagotta on Fire)

**Similes & Stories (great for teaching):**
- SN56.31 (Simsapa — Handful of Leaves)
- SN3.25 (Pabbatupama — Simile of Mountains/aging)
- MN140 (Dhatuvibhanga — Analysis of Elements — the potter's shed)
- SN4.19 (Kassaka — the Farmer)
- MN75 (Magandiya)
- SN35.238 (Asivisopama — Simile of Vipers)
- SN22.87 (Vakkali — the sick monk)

**Daily Life & Relationships:**
- AN4.55 (Samajivina — Living in Tune — good marriage)
- AN4.32 (Sangahavatthu — Bonds of Fellowship)
- AN5.177 (Vanijja — Wrong Livelihood)
- AN8.25 (Mahanama — Lay Practice)
- AN3.61 (Tittha — Sectarians)

**Advanced Topics (for returning practitioners):**
- AN10.48 (Dasadhamma — Ten Themes)
- AN8.63 (Sankhitta — In Brief — jhana + vipassana)
- MN44 (Culavedalla — Q&A with Dhammadinna)
- SN12.61 (Assutava — Uninstructed)
- SN22.79 (Khajjaniya — Being Devoured)

**Add more to reach ~200-300 total.** Fill in from each collection proportionally:
- DN: 10-15 suttas (the long discourses — pick the most teachable, skip repetitive ones)
- MN: 50-70 suttas (richest collection for practice instruction)
- SN: 60-80 suttas (shorter, focused teachings — good for search hits)
- AN: 50-70 suttas (numbered lists, practical advice)
- KN: 10-20 (Dhammapada selections, Sutta Nipata, Udana, Itivuttaka)

Use your judgment for the rest. Prioritize suttas that:
- Contain vivid similes or stories
- Give practical meditation/ethics instruction
- Address common life situations (grief, anger, relationships, work)
- Are frequently referenced in introductory Buddhism courses

### Step 3: Tests

Create `tests/test_fetch_suttas.py`:

1. Test that `curated_ids.txt` exists and has 200+ entries
2. Test the segment-concatenation logic with a sample bilara JSON
3. Test the theme-assignment heuristic
4. Test the text truncation at sentence boundaries
5. Test the output format matches the expected schema

Use pytest (NOT trio — this is a data pipeline, all sync).

### Step 4: Run the scraper

Execute `scripts/fetch_sc_suttas.py` and verify:
- Output file `sutta_corpus/suttas.json` has 200+ entries
- Each entry has id, title, collection, text, themes
- No empty text fields
- Themes are reasonable (spot-check 10 random entries)

Commit the script, curation list, tests, AND the generated `suttas.json`.

## Constraints

- Only modify/create files in: `scripts/`, `sutta_corpus/`, `tests/`
- Do NOT modify: `src/`, `compose.yaml`, `Containerfile`, `.dapr/`
- Do NOT install new pip dependencies — use only stdlib + packages already in the project (requests is fine if already there, otherwise use urllib)
- The scraper must work offline after initial clone (no API calls to suttacentral.net at runtime)
- Keep `curated_ids.txt` as a separate file so we can easily add/remove suttas later
- Git operations: use subprocess, not gitpython

## Branch & Push

Work on branch: `feat/expand-sutta-corpus`. Commit AND push when done.
The orchestrator handles merge to main after review.

## Self-Review (mandatory before final commit)

Re-read your entire diff (`git diff main..HEAD`). Write out:

**Concerns (list exactly 3):**
1. [Something specific that could break]
2. [An edge case you didn't test]
3. [An assumption you're uncertain about]

**TDD compliance check:**
- [ ] I committed failing tests BEFORE implementation (check `git log --oneline`)
- [ ] Tests and implementation are in separate commits
- [ ] All tests pass
