"""Generate the sample weights CSV used by GeneGauge in demo mode.

Run: ``python scripts/generate_sample_data.py``

This writes ``data/weights.csv`` with 24 signals. It produces a *realistic-
shaped* demo dataset: effect sizes clustered around zero, with a handful
of larger positive and negative outliers. It is NOT real genomic data and
must not be used to draw any real-world conclusion.

Plugging in a real dataset later only requires writing a CSV with the same
four columns. See ``data/README.md``.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "weights.csv"

# Short, plain-English labels. None of them mention SNPs, alleles, or GWAS.
# These are purposely abstract so nobody mistakes the demo for real medical
# claims about a specific trait.
LABELS = [
    "Signal 1 - morning energy pattern",
    "Signal 2 - sleep regularity pattern",
    "Signal 3 - caffeine response pattern",
    "Signal 4 - short-term memory cue",
    "Signal 5 - stress recovery cue",
    "Signal 6 - endurance marker",
    "Signal 7 - focus marker",
    "Signal 8 - appetite timing cue",
    "Signal 9 - mood steadiness cue",
    "Signal 10 - temperature comfort cue",
    "Signal 11 - hydration preference",
    "Signal 12 - light sensitivity cue",
    "Signal 13 - sound sensitivity cue",
    "Signal 14 - early-riser tendency",
    "Signal 15 - late-night tendency",
    "Signal 16 - taste preference cue",
    "Signal 17 - scent sensitivity cue",
    "Signal 18 - fine-motor steadiness",
    "Signal 19 - balance-and-posture cue",
    "Signal 20 - reading stamina cue",
    "Signal 21 - verbal recall cue",
    "Signal 22 - spatial recall cue",
    "Signal 23 - calm-under-pressure cue",
    "Signal 24 - social energy cue",
]


def main(seed: int = 1729) -> None:
    rng = random.Random(seed)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["signal_id", "plain_label", "weight", "direction_hint"])
        for i, label in enumerate(LABELS, start=1):
            sid = f"S{i:03d}"
            # Most weights are small, a few are noticeably larger. Mix of +/-.
            base = rng.gauss(mu=0.0, sigma=0.35)
            if i % 7 == 0:
                base += rng.choice([-1.0, 1.0]) * rng.uniform(0.6, 1.2)
            weight = round(max(-1.8, min(1.8, base)), 3)
            direction = "up" if weight >= 0 else "down"
            w.writerow([sid, label, f"{weight}", direction])
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
