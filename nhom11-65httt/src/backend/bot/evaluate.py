"""Field-level extraction and duplicate-pair evaluation metrics per TV1-07 specs."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from deduplicator import Deduplicator
from extractor import enrich_row


@dataclass(frozen=True)
class FieldMetrics:
    """Precision, recall, and F1 for a single extracted attribute."""

    field: str
    n_eligible: int
    n_gold_positive: int
    tp: int
    fp: int
    fn: int
    precision: float | None
    recall: float | None
    f1: float | None


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator > 0 else None


def evaluate_extraction(samples: list[dict[str, dict[str, str]]]) -> list[FieldMetrics]:
    """Evaluate extractor against labeled gold records (separate from live market KPIs)."""
    fields = ("rent_vnd_month", "price_basis", "area_m2", "room_type", "ward")
    counts = {field: {"tp": 0, "fp": 0, "fn": 0, "gold_pos": 0} for field in fields}

    for sample in samples:
        raw = dict(sample["input"])
        gold = sample["gold"]
        pred = enrich_row(raw, explicit_amenities=raw.get("amenities", ""), price_raw=raw.get("price_raw", ""))

        for field in fields:
            g_val = str(gold.get(field, "") or "").strip()
            p_val = str(pred.get(field, "") or "").strip()
            if g_val:
                counts[field]["gold_pos"] += 1
            if p_val and g_val and p_val == g_val:
                counts[field]["tp"] += 1
            elif p_val and not g_val:
                counts[field]["fp"] += 1
            elif g_val and not p_val:
                counts[field]["fn"] += 1
            elif p_val and g_val and p_val != g_val:
                counts[field]["fp"] += 1
                counts[field]["fn"] += 1

    results: list[FieldMetrics] = []
    for field in fields:
        tp = counts[field]["tp"]
        fp = counts[field]["fp"]
        fn = counts[field]["fn"]
        prec = _ratio(tp, tp + fp)
        rec = _ratio(tp, tp + fn)
        f1 = round(2 * tp / (2 * tp + fp + fn), 4) if (2 * tp + fp + fn) > 0 else (0.0 if counts[field]["gold_pos"] > 0 else None)
        results.append(
            FieldMetrics(
                field=field,
                n_eligible=len(samples),
                n_gold_positive=counts[field]["gold_pos"],
                tp=tp,
                fp=fp,
                fn=fn,
                precision=prec,
                recall=rec,
                f1=f1,
            )
        )
    return results


def evaluate_duplicate_pairs(pairs: list[dict[str, object]]) -> dict[str, object]:
    """Evaluate Deduplicator precision and recall on a labeled pair benchmark."""
    dedup = Deduplicator()
    tp = fp = fn = 0
    for pair in pairs:
        left = pair["left"]
        right = pair["right"]
        gold_same = bool(pair["gold_same_room"])
        pred_same = dedup.classify_pair(left, right) == "confirmed"
        if pred_same and gold_same:
            tp += 1
        elif pred_same and not gold_same:
            fp += 1
        elif not pred_same and gold_same:
            fn += 1

    return {
        "n_pairs": len(pairs),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": _ratio(tp, tp + fp),
        "recall": _ratio(tp, tp + fn),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).resolve().parent / "fixtures" / "synthetic_eval.json",
        help="Path to labeled evaluation JSON fixture",
    )
    parser.add_argument(
        "--split",
        choices=("all", "development", "holdout"),
        default="all",
        help="Filter labeled samples/pairs by split when present in the fixture",
    )
    args = parser.parse_args()
    data = json.loads(args.fixture.read_text(encoding="utf-8"))
    samples = data.get("extraction_samples", [])
    pairs = data.get("duplicate_pairs", [])
    if args.split != "all":
        samples = [item for item in samples if item.get("split") == args.split]
        pairs = [item for item in pairs if item.get("split") == args.split]
    extraction_metrics = evaluate_extraction(samples)
    dup_metrics = evaluate_duplicate_pairs(pairs)
    print(f"Fixture: {args.fixture.name} (origin={data.get('origin', 'synthetic')}, split={args.split})")
    for item in extraction_metrics:
        print(
            f"  {item.field:16s} | n={item.n_eligible} gold+={item.n_gold_positive} "
            f"TP={item.tp} FP={item.fp} FN={item.fn} P={item.precision} R={item.recall} F1={item.f1}"
        )
    print(f"  duplicate_pairs  | {dup_metrics}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
