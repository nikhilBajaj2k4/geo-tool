#!/usr/bin/env python3
"""Run multiple GeoAudit tests with different markets and save all results."""
import json, os, sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe

TESTS = [
    {
        "id": "dentist-austin",
        "market": "dentists in Austin, TX",
        "description": "Austin dental clinics (baseline, Perplexity Sonar)",
        "practices": probe.PRACTICES,
        "queries": probe.QUERIES,
        "mock": False,
    },
    {
        "id": "dentist-kota",
        "market": "dentists in Kota, Rajasthan",
        "description": "Kota dental clinics (India market, Perplexity Sonar)",
        "practices": [
            {"name": "Crown Dental Care", "aliases": ["crown dental care", "crown dental"]},
            {"name": "Jaiswal Dental Clinic", "aliases": ["jaiswal dental clinic", "jaiswal dental"]},
            {"name": "Dr Sandeep Orthodontic and Dental Clinic", "aliases": ["dr sandeep orthodontic and dental clinic", "sandeep orthodontic", "dr sandeep"]},
            {"name": "Madhuvan Multispeciality Hospital Dental", "aliases": ["madhuvan multispeciality hospital dental", "madhuvan dental", "madhuvan multispeciality"]},
            {"name": "Mittal Dental Clinic", "aliases": ["mittal dental clinic", "mittal dental"]},
            {"name": "Sharma Dental Clinic", "aliases": ["sharma dental clinic", "sharma dental"]},
            {"name": "Kota Dental Hospital", "aliases": ["kota dental hospital", "kota dental"]},
            {"name": "Agarwal Dental Clinic", "aliases": ["agarwal dental clinic", "agarwal dental"]},
            {"name": "Shree Dental Care", "aliases": ["shree dental care"]},
        ],
        "queries": [
            "best dentist in kota rajasthan",
            "dental clinic near me kota",
            "top rated dentist in kota",
            "affordable dentist in kota",
            "root canal treatment kota",
            "dental implant specialist kota",
            "kids dentist in kota rajasthan",
            "cosmetic dentist kota rajasthan",
            "teeth whitening clinic kota",
            "emergency dental care kota",
        ],
        "mock": False,
    },
    {
        "id": "dermatologist-london",
        "market": "dermatologists in London, UK",
        "description": "London dermatology clinics (UK market, Perplexity Sonar)",
        "practices": [
            {"name": "Cadogan Clinic", "aliases": ["cadogan clinic", "cadogan"]},
            {"name": "Harley Street Dermatology Clinic", "aliases": ["harley street dermatology", "harley street dermatology clinic"]},
            {"name": "London Dermatology Centre", "aliases": ["london dermatology centre", "london dermatology center"]},
            {"name": "St John's Institute of Dermatology", "aliases": ["st john's institute of dermatology", "st johns institute"]},
            {"name": "Dermatology Consulting London", "aliases": ["dermatology consulting", "dermatology consulting london"]},
            {"name": "The Dermatology Clinic London", "aliases": ["the dermatology clinic", "dermatology clinic london"]},
            {"name": "Sk:N London", "aliases": ["sk:n", "sk:n london", "skn london"]},
            {"name": "Cranley Clinic", "aliases": ["cranley clinic", "cranley"]},
            {"name": "Devonshire Dermatology", "aliases": ["devonshire dermatology", "devonshire"]},
        ],
        "queries": [
            "best dermatologist in london uk",
            "top rated skin clinic london",
            "dermatologist near me harley street",
            "acne treatment specialist london",
            "skin cancer screening london",
            "cosmetic dermatologist london uk",
            "eczema specialist london",
            "mole check clinic london",
            "anti aging skin clinic london",
            "private dermatologist london appointment",
        ],
        "mock": False,
    },
]

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "test-runs")


def run():
    provider = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not provider:
        print("Set OPENROUTER_API_KEY to run live tests.")
        return 1

    api_key = os.environ["OPENROUTER_API_KEY"].strip()
    model = probe.DEFAULTS["openrouter"]
    os.makedirs(DATA_DIR, exist_ok=True)

    summary = {"tests": [], "runs_at": datetime.now(timezone.utc).isoformat()}

    for test in TESTS:
        print(f"\n{'='*70}")
        print(f"TEST: {test['id']} — {test['market']}")
        print(f"  {test['description']}")
        print(f"  Practices: {len(test['practices'])} | Queries: {len(test['queries'])}")
        print(f"{'='*70}")

        if test["mock"]:
            result = probe.run_audit(
                "openrouter", model, api_key,
                test["queries"], test["practices"],
                mock=True
            )
        else:
            result = probe.run_audit(
                "openrouter", model, api_key,
                test["queries"], test["practices"],
                market=test["market"]
            )

        # Print ranking
        print(f"\n  Verdict: {result['verdict']}")
        print(f"  Queries with any mention: {result['queries_with_any']}/{result['total_queries']}")
        print(f"  Total cost: ${result['total_cost']:.4f}")

        if result["errors"]:
            print(f"  Errors: {len(result['errors'])}")
            for e in result["errors"]:
                print(f"    [{e['query']}] {e['error']}")

        print("  Ranking:")
        for i, (r, c) in enumerate([(x["name"], x["count"]) for x in result["ranking"]]):
            bar = "#" * c
            print(f"    {i+1}. {r:<35} {c}/{result['total_queries']}  {bar}")

        # Save individual result
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"test-{test['id']}-{ts}.json"
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Track in summary
        summary["tests"].append({
            "id": test["id"],
            "market": test["market"],
            "verdict": result["verdict"],
            "total_queries": result["total_queries"],
            "queries_with_any": result["queries_with_any"],
            "total_cost": result["total_cost"],
            "ranking": result["ranking"][:5],
            "errors": len(result["errors"]),
            "file": filename,
        })

        print(f"\n  Saved to: data/test-runs/{filename}")

    # Save summary
    summary_path = os.path.join(DATA_DIR, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print("ALL TESTS COMPLETE")
    print(f"Summary saved to: data/test-runs/summary.json")
    print(f"{'='*70}")

    for t in summary["tests"]:
        icon = "✓" if "REAL" in t["verdict"] else "?" if "AMBIGUOUS" in t["verdict"] else "✗"
        print(f"  {icon} {t['id']}: {t['verdict']} ({t['queries_with_any']}/{t['total_queries']} queries, ${t['total_cost']:.4f})")

    return 0


if __name__ == "__main__":
    sys.exit(run())
