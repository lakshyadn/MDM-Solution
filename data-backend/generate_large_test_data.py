import argparse
import csv
import random
from pathlib import Path
from typing import Dict, List, Tuple

FIELDS = [
    "id",
    "university_name",
    "country",
    "city",
    "founded_year",
    "student_count",
    "ranking",
    "type",
    "website",
]


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


def save_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def typo(text: str) -> str:
    if not text or len(text) < 3:
        return text
    i = random.randint(0, len(text) - 2)
    if text[i].isspace() or text[i + 1].isspace():
        return text
    chars = list(text)
    chars[i], chars[i + 1] = chars[i + 1], chars[i]
    return "".join(chars)


def maybe_typo(value: str, ratio: float) -> str:
    return typo(value) if random.random() < ratio else value


def clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def mutate_numeric(base: Dict[str, str]) -> Tuple[int, int, int]:
    founded_year = int(base["founded_year"])
    student_count = int(base["student_count"])
    ranking = int(base["ranking"])

    founded_year = clamp_int(founded_year + random.randint(-2, 2), 1000, 2026)
    student_count = clamp_int(student_count + random.randint(-1500, 1500), 500, 200000)
    ranking = clamp_int(ranking + random.randint(-3, 3), 1, 500)

    return founded_year, student_count, ranking


def pair_by_id(master1: List[Dict[str, str]], master2: List[Dict[str, str]]) -> List[Tuple[Dict[str, str], Dict[str, str]]]:
    m2_by_id = {row["id"]: row for row in master2}
    pairs: List[Tuple[Dict[str, str], Dict[str, str]]] = []
    for row in master1:
        match = m2_by_id.get(row["id"], row)
        pairs.append((row, match))
    return pairs


def generate_rows(
    pairs: List[Tuple[Dict[str, str], Dict[str, str]]],
    total_rows: int,
    given_typo_ratio: float,
    given_abbr_ratio: float,
    master2_fullform_ratio: float,
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
    out_master1: List[Dict[str, str]] = []
    out_master2: List[Dict[str, str]] = []
    out_given: List[Dict[str, str]] = []

    for idx in range(total_rows):
        base1, base2 = pairs[idx % len(pairs)]
        new_id = idx + 1

        founded_year, student_count, ranking = mutate_numeric(base1)

        m1_name = base1["university_name"]
        m2_alias_name = base2.get("university_name", m1_name)
        m2_name = m1_name if random.random() < master2_fullform_ratio else m2_alias_name

        m1_row = {
            "id": str(new_id),
            "university_name": m1_name,
            "country": base1["country"],
            "city": base1["city"],
            "founded_year": str(founded_year),
            "student_count": str(student_count),
            "ranking": str(ranking),
            "type": base1["type"],
            "website": base1["website"],
        }

        m2_row = {
            "id": str(new_id),
            "university_name": m2_name,
            "country": base2.get("country", base1["country"]),
            "city": base2.get("city", base1["city"]),
            "founded_year": str(founded_year),
            "student_count": str(student_count),
            "ranking": str(ranking),
            "type": base2.get("type", base1["type"]),
            "website": base2.get("website", base1["website"]),
        }

        given_name = m1_name
        roll = random.random()
        if roll < given_abbr_ratio:
            given_name = m2_alias_name
        elif roll < given_abbr_ratio + given_typo_ratio:
            given_name = typo(m1_name)

        given_row = {
            "id": str(new_id),
            "university_name": given_name,
            "country": base1["country"],
            "city": maybe_typo(base1["city"], given_typo_ratio * 0.35),
            "founded_year": str(founded_year),
            "student_count": str(student_count),
            "ranking": str(ranking),
            "type": maybe_typo(base1["type"], given_typo_ratio * 0.2),
            "website": maybe_typo(base1["website"], given_typo_ratio * 0.25),
        }

        out_master1.append(m1_row)
        out_master2.append(m2_row)
        out_given.append(given_row)

    return out_master1, out_master2, out_given


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate large synthetic datasets for discrepancy testing")
    parser.add_argument("--rows", type=int, default=1000, help="Number of rows to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--given-typo-ratio", type=float, default=0.18, help="Share of given rows with typo noise")
    parser.add_argument("--given-abbr-ratio", type=float, default=0.25, help="Share of given rows using abbreviation/alias forms")
    parser.add_argument("--master2-fullform-ratio", type=float, default=0.15, help="Share of master2 names that stay full-form")
    parser.add_argument(
        "--target-anomalies",
        type=int,
        default=None,
        help="Approximate target count of total field-level anomalies; auto-tunes given ratios when set",
    )
    parser.add_argument("--output-dir", type=str, default="generated", help="Output subfolder under data-backend")
    args = parser.parse_args()

    random.seed(args.seed)

    root = Path(__file__).parent
    master1_path = root / "master1.csv"
    master2_path = root / "master2.csv"

    if not master1_path.exists() or not master2_path.exists():
        raise FileNotFoundError("master1.csv and master2.csv must exist in data-backend")

    master1 = load_csv(master1_path)
    master2 = load_csv(master2_path)
    pairs = pair_by_id(master1, master2)

    given_typo_ratio = args.given_typo_ratio
    given_abbr_ratio = args.given_abbr_ratio

    # Optional auto-tuning for approximate anomaly budget.
    # Expected anomalies per row ≈ given_abbr_ratio + 1.8 * given_typo_ratio
    # (name alias/typo + city/type/website typo noise).
    if args.target_anomalies is not None and args.rows > 0:
        target_ratio = max(0.0, min(0.8, args.target_anomalies / args.rows))
        given_abbr_ratio = min(0.6, target_ratio * 0.5)
        given_typo_ratio = min(0.6, target_ratio * 0.28)

    out_master1, out_master2, out_given = generate_rows(
        pairs=pairs,
        total_rows=args.rows,
        given_typo_ratio=given_typo_ratio,
        given_abbr_ratio=given_abbr_ratio,
        master2_fullform_ratio=args.master2_fullform_ratio,
    )

    output_dir = root / args.output_dir
    save_csv(output_dir / "master1_1000.csv", out_master1)
    save_csv(output_dir / "master2_1000.csv", out_master2)
    save_csv(output_dir / "given_1000.csv", out_given)

    print(f"Generated datasets in: {output_dir}")
    print(f"Rows: {args.rows}")
    print(f"Given abbreviation/alias ratio: {given_abbr_ratio}")
    print(f"Given typo ratio: {given_typo_ratio}")
    if args.target_anomalies is not None:
        print(f"Target anomalies (approx): {args.target_anomalies}")


if __name__ == "__main__":
    main()
