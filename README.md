# Healthcare GEO Audit — Minimal Validation Probe

This is the **smallest thing that tests the riskiest assumption**, exactly as the
build plan's "FIRST ACTION" prescribes:

> *Do AI answers actually show meaningful gaps between competing practices in the
> same city + specialty?*

If you see "Dentist A in 8/10, Dentist B in 0/10" — the opportunity is real, build
the full thing. If you see "all dentists mentioned equally" or "no dentists named,
AI says 'search Google'" — stop and reassess.

## How it works

1. 10 realistic patient questions, hardcoded for "dentist in Austin, TX".
2. Each question is sent to a **web-grounded AI-search model** (default: GPT-4o-mini
   via OpenRouter, with its `:online` web-grounded plugin) — this is the same surface
   a patient hits when they ask an AI assistant, and it returns cited web sources.
3. For each of **9 real Austin dental practices**, count how many of the 10
   questions mention them, and how many named a *competitor but not them*.
4. Print the ranking. The shape of the distribution answers the thesis.

## Run

```bash
# 1. Python 3.9+, stdlib only — no pip installs required.
# 2. Get an API key at https://openrouter.ai/keys (recommended) or https://z.ai
export OPENROUTER_API_KEY="your-key-here"

# 3. Run the probe
python3 probe.py                 # real run against OpenRouter (~$0.10 of API)
python3 probe.py --mock          # dry run on canned answers, no key needed
python3 probe.py --provider zai  # alternative: GLM-4.6 via z.ai
python3 probe.py --queries 3     # cheaper smoke test (only first 3 queries)
```

## What "mentioned" means

We search each practice's full official name and any known short form
(e.g. "Forest Family Dentistry" / "Forest Family") case-insensitively inside the
model's answer text **and** the cited web-search snippets it returns. A practice
counts as mentioned in a question if it appears anywhere in that grounded answer.

## Files

```
probe.py            # the validation probe — the whole tool, deliberately one file
README.md           # this
.env.example        # shows the one env var you need
data/audits/        # each run dumps its raw JSON here for inspection
```

## What comes next (only if the probe shows real gaps)

This probe is Phase 0. The brief's Week 1/2 plan builds out:
`query_generator.py`, per-source connectors, an LLM mention-classifier,
share-of-voice scorer, and a markdown report. **Do not build that until this probe
shows "3 practices dominate, 2 are invisible" in a real market.** That single
check de-risks the entire business.
