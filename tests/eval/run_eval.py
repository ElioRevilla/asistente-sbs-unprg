"""Run offline evaluation requests against the SBS assistant API.

The runner uses a curated dataset with expected answers and expected citations.
It does not replace human review, but it gives a repeatable signal for:

- endpoint availability;
- citation coverage;
- factual keyword overlap with the curated answer;
- expected numeric values in calculation questions.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import time
import unicodedata
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

DEFAULT_DATASET = Path("tests/eval/sbs_validation_questions.json")
DEFAULT_OUTPUT = Path("tests/eval/eval_results.json")

STOPWORDS = {
    "ademas",
    "años",
    "bajo",
    "cada",
    "como",
    "con",
    "contra",
    "cuando",
    "cual",
    "cuales",
    "debe",
    "deben",
    "del",
    "desde",
    "donde",
    "dos",
    "el",
    "ella",
    "ellas",
    "ellos",
    "en",
    "entre",
    "esa",
    "ese",
    "esta",
    "estan",
    "este",
    "estos",
    "las",
    "los",
    "mas",
    "para",
    "pero",
    "por",
    "que",
    "segun",
    "sin",
    "sobre",
    "son",
    "sus",
    "una",
    "uno",
}


class EvalCase(BaseModel):
    """A curated validation question."""

    id: str
    question: str
    expected_answer: str
    expected_citations: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    difficulty: str
    answer_type: str
    expected_category: str | None = None
    expected_provision_rate: float | None = None
    expected_provision_amount: float | None = None


class EvalResult(BaseModel):
    """Evaluation result for one question."""

    id: str
    question: str
    status_code: int | None
    ok: bool
    answer_score: float
    citation_score: float
    numeric_score: float
    latency_ms: int
    matched_citations: list[str]
    missing_citations: list[str]
    answer: str
    error: str | None = None


def load_cases(path: Path) -> list[EvalCase]:
    """Load eval cases from JSON array or JSONL."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        raw_cases = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        raw_cases = json.loads(text)
    return [EvalCase.model_validate(item) for item in raw_cases]


def normalize_text(value: str) -> str:
    """Normalize text for accent-insensitive matching."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.lower()
    value = re.sub(r"[^a-z0-9.%]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def keyword_score(expected: str, actual: str) -> float:
    """Return significant-token overlap between expected and actual answer."""
    expected_tokens = {
        _clean_token(token)
        for token in normalize_text(expected).split()
        if len(_clean_token(token)) >= 4 and _clean_token(token) not in STOPWORDS
    }
    if not expected_tokens:
        return 1.0

    actual_text = normalize_text(actual)
    matched = {token for token in expected_tokens if token in actual_text}
    return round(len(matched) / len(expected_tokens), 4)


def citation_score(
    expected_citations: list[str],
    response_citations: list[dict[str, Any]],
    answer: str,
) -> tuple[float, list[str], list[str]]:
    """Score whether expected citations appear in labels or answer text."""
    if not expected_citations:
        return 1.0, [], []

    citation_text = " ".join(
        str(citation.get("label", "")) + " " + str(citation.get("chunk_id", ""))
        for citation in response_citations
    )
    haystack = normalize_text(f"{answer} {citation_text}")

    matched: list[str] = []
    missing: list[str] = []
    for citation in expected_citations:
        if _citation_matches(citation, haystack):
            matched.append(citation)
        else:
            missing.append(citation)

    return round(len(matched) / len(expected_citations), 4), matched, missing


def numeric_score(case: EvalCase, answer: str) -> float:
    """Score expected calculation values when present."""
    expected_values = [
        case.expected_provision_rate,
        case.expected_provision_amount,
    ]
    expected_values = [value for value in expected_values if value is not None]
    if not expected_values:
        return 1.0

    normalized_answer = normalize_text(answer).replace(",", "")
    matched = 0
    for value in expected_values:
        exact = f"{value:.2f}".rstrip("0").rstrip(".")
        if exact in normalized_answer:
            matched += 1
    return round(matched / len(expected_values), 4)


async def fetch_firebase_token(
    api_key: str,
    email: str,
    password: str,
    timeout: float,
) -> str:
    """Fetch a Firebase ID token using email/password credentials."""
    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
        f"?key={api_key}"
    )
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    return str(data["idToken"])


async def evaluate_case(
    client: httpx.AsyncClient,
    case: EvalCase,
    token: str | None,
    top_k: int,
) -> EvalResult:
    """Evaluate one case against the API."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    started = time.perf_counter()
    try:
        response = await client.post(
            "/modes/explain",
            json={"question": case.question, "student_id": None, "top_k": top_k},
            headers=headers,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        response_data = response.json()
    except Exception as error:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return EvalResult(
            id=case.id,
            question=case.question,
            status_code=None,
            ok=False,
            answer_score=0.0,
            citation_score=0.0,
            numeric_score=0.0,
            latency_ms=latency_ms,
            matched_citations=[],
            missing_citations=case.expected_citations,
            answer="",
            error=str(error),
        )

    if response.status_code >= 400:
        return EvalResult(
            id=case.id,
            question=case.question,
            status_code=response.status_code,
            ok=False,
            answer_score=0.0,
            citation_score=0.0,
            numeric_score=0.0,
            latency_ms=latency_ms,
            matched_citations=[],
            missing_citations=case.expected_citations,
            answer="",
            error=json.dumps(response_data, ensure_ascii=False),
        )

    data = response_data.get("data", {})
    answer = str(data.get("answer", ""))
    citations = data.get("citations", [])
    answer_overlap = keyword_score(case.expected_answer, answer)
    cite_score, matched_citations, missing_citations = citation_score(
        case.expected_citations,
        citations,
        answer,
    )
    number_score = numeric_score(case, answer)
    ok = answer_overlap >= 0.35 and cite_score >= 0.75 and number_score >= 1.0

    return EvalResult(
        id=case.id,
        question=case.question,
        status_code=response.status_code,
        ok=ok,
        answer_score=answer_overlap,
        citation_score=cite_score,
        numeric_score=number_score,
        latency_ms=latency_ms,
        matched_citations=matched_citations,
        missing_citations=missing_citations,
        answer=answer,
    )


async def run_eval(args: argparse.Namespace) -> dict[str, Any]:
    """Run the evaluation suite."""
    cases = load_cases(args.dataset)
    if args.limit:
        cases = cases[: args.limit]

    token = args.token
    if not token and args.firebase_api_key:
        if not args.firebase_email or not args.firebase_password:
            raise ValueError(
                "--firebase-email and --firebase-password are required with "
                "--firebase-api-key"
            )
        token = await fetch_firebase_token(
            args.firebase_api_key,
            args.firebase_email,
            args.firebase_password,
            args.timeout,
        )

    async with httpx.AsyncClient(
        base_url=args.base_url.rstrip("/"),
        timeout=args.timeout,
    ) as client:
        results = [
            await evaluate_case(client, case, token=token, top_k=args.top_k)
            for case in cases
        ]

    ok_count = sum(result.ok for result in results)
    summary = {
        "base_url": args.base_url,
        "dataset": str(args.dataset),
        "total": len(results),
        "passed": ok_count,
        "failed": len(results) - ok_count,
        "pass_rate": round(ok_count / len(results), 4) if results else 0.0,
        "avg_answer_score": _mean(result.answer_score for result in results),
        "avg_citation_score": _mean(result.citation_score for result in results),
        "avg_numeric_score": _mean(result.numeric_score for result in results),
        "avg_latency_ms": int(_mean(result.latency_ms for result in results)),
    }
    return {
        "summary": summary,
        "results": [result.model_dump() for result in results],
    }


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--token", default=None)
    parser.add_argument("--firebase-api-key", default=None)
    parser.add_argument("--firebase-email", default=None)
    parser.add_argument("--firebase-password", default=None)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--fail-under", type=float, default=None)
    return parser


def main() -> None:
    """Run CLI."""
    args = build_parser().parse_args()
    report = asyncio.run(run_eval(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = report["summary"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nSaved detailed results to {args.output}")

    if args.fail_under is not None and summary["pass_rate"] < args.fail_under:
        raise SystemExit(1)


def _citation_matches(expected: str, haystack: str) -> bool:
    normalized = normalize_text(expected)
    numeral_match = re.search(r"numeral\s+([0-9]+(?:\.[0-9]+)?)", normalized)
    if numeral_match and f"numeral {numeral_match.group(1)}" in haystack:
        return True

    if "tabla 1" in normalized and "tabla 1" in haystack:
        return True
    if "anexo i" in normalized and "anexo i" in haystack:
        return True
    return normalized in haystack


def _clean_token(token: str) -> str:
    """Remove boundary punctuation that should not affect lexical matching."""
    return token.strip(".")


def _mean(values: Any) -> float:
    collected = list(values)
    if not collected:
        return 0.0
    return round(float(statistics.mean(collected)), 4)


if __name__ == "__main__":
    main()
