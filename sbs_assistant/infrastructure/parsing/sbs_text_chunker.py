from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from sbs_assistant.domain.entities.chunk import Chunk
from sbs_assistant.domain.entities.provision_rule import ProvisionRule
from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.credit_type import CreditType

ARTICLE_PATTERN = re.compile(
    r"(?P<header>Articulo\s+(?P<article>\d+)[°º]?\s*[.-]?)",
    flags=re.IGNORECASE,
)
CHAPTER_PATTERN = re.compile(r"CAP[IÍ]TULO\s+[IVXLC]+[^\n]*", flags=re.IGNORECASE)
PERCENT_PATTERN = re.compile(r"(?P<value>\d{1,2}(?:[.,]\d+)?)\s*%")
SECTION_PATTERN = re.compile(
    r"(?m)^\s*(?P<numeral>\d+(?:\.\d+)*)\.?[ \t]+"
    r"(?P<title>[A-ZÁÉÍÓÚÑ][^\n]{2,140})$"
)


@dataclass(frozen=True, slots=True)
class SbsRegulationTextChunker:
    """Parse raw SBS regulation text into article-level chunks."""

    def chunk(self, text: str) -> list[Chunk]:
        normalized_text = self._normalize_text(text)
        section_chunks = self._chunk_sections(normalized_text)
        if len(section_chunks) >= 3:
            return section_chunks

        matches = list(ARTICLE_PATTERN.finditer(normalized_text))
        if not matches:
            return [
                Chunk(
                    id="documento_completo",
                    text=normalized_text,
                    content_type="regla",
                    topics=self._infer_topics(normalized_text),
                )
            ]

        chunks: list[Chunk] = []
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else None
            article_number = int(match.group("article"))
            article_text = normalized_text[start:end].strip()
            chunks.append(
                Chunk(
                    id=f"art_{article_number}",
                    text=article_text,
                    chapter=self._find_chapter(normalized_text[:start]),
                    article=article_number,
                    content_type=self._infer_content_type(article_text),
                    topics=self._infer_topics(article_text),
                )
            )
        return chunks

    def _chunk_sections(self, text: str) -> list[Chunk]:
        body_text = self._body_text(text)
        matches = [
            match
            for match in SECTION_PATTERN.finditer(body_text)
            if self._is_valid_section_heading(match.group("title"))
        ]
        chunks: list[Chunk] = []
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else None
            numeral = match.group("numeral")
            section_text = self._clean_section_text(body_text[start:end])
            if len(section_text) < 40:
                continue
            chunks.append(
                Chunk(
                    id=f"sec_{index + 1:03d}_{numeral.replace('.', '_')}",
                    text=section_text,
                    chapter=self._find_chapter(body_text[:start]),
                    numeral=numeral,
                    content_type=self._infer_content_type(section_text),
                    topics=self._infer_topics(section_text, numeral=numeral),
                )
            )
        return chunks

    def extract_provision_rules(self, text: str) -> list[ProvisionRule]:
        normalized_text = self._normalize_text(text)
        rules: list[ProvisionRule] = []
        segments = [segment.strip() for segment in re.split(r"[\n;]", normalized_text)]
        for category in Category:
            category_pattern = re.compile(re.escape(category.value), re.IGNORECASE)
            for segment in segments:
                category_match = category_pattern.search(segment)
                if not category_match:
                    continue
                percent_match = PERCENT_PATTERN.search(segment)
                if not percent_match:
                    continue
                percentage = Decimal(percent_match.group("value").replace(",", "."))
                position = normalized_text.find(segment)
                match_position = (
                    position + category_match.start() if position >= 0 else 0
                )
                source_article = self._nearest_source_article(
                    normalized_text,
                    match_position,
                )
                for credit_type in self._infer_credit_types(segment):
                    rule = ProvisionRule(
                        category=category,
                        credit_type=credit_type,
                        guarantee_type=None,
                        provision_percentage=percentage,
                        source_article=source_article,
                    )
                    if rule not in rules:
                        rules.append(rule)
        return rules

    def _normalize_text(self, text: str) -> str:
        text = text.replace("Artículo", "Articulo")
        text = text.replace("artículo", "articulo")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _body_text(self, text: str) -> str:
        matches = list(re.finditer(r"(?m)^\s*1\.\s+ALCANCE\s*$", text))
        if not matches:
            return text
        return text[matches[-1].start() :]

    def _is_valid_section_heading(self, title: str) -> bool:
        lowered = title.lower()
        invalid_terms = [
            "lima",
            "articulo modificado",
            "literal",
            "numeral",
            "resolución",
        ]
        if any(term in lowered for term in invalid_terms):
            return False
        return any(character.isalpha() for character in title)

    def _clean_section_text(self, text: str) -> str:
        text = re.sub(
            r"(?m)^.*Los Laureles N[º°]\s*214.*Telf\..*Fax:.*$",
            "",
            text,
        )
        text = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _find_chapter(self, text_before_article: str) -> str | None:
        matches = list(CHAPTER_PATTERN.finditer(text_before_article))
        if not matches:
            return None
        return matches[-1].group(0).strip()

    def _infer_content_type(self, text: str) -> str:
        lowered = text.lower()
        if "%" in text or "provision" in lowered:
            return "tabla"
        if "defin" in lowered or "se entiende por" in lowered:
            return "definicion"
        if "anexo" in lowered:
            return "anexo"
        return "regla"

    def _infer_topics(self, text: str, numeral: str | None = None) -> list[str]:
        lowered = text.lower()
        topics: list[str] = []
        keyword_topics = {
            "clasificacion": ["clasificacion", "clasificar", "categoria"],
            "provisiones": ["provision", "%"],
            "consumo": ["consumo"],
            "hipotecario": ["hipotecario"],
            "mes": ["microempresa", "mes"],
            "garantias": ["garantia", "garantias"],
        }
        for topic, keywords in keyword_topics.items():
            if any(keyword in lowered for keyword in keywords):
                topics.append(topic)
        topics.extend(self._infer_portfolio_topics(text, numeral))
        return topics

    def _infer_portfolio_topics(self, text: str, numeral: str | None) -> list[str]:
        if numeral is None:
            return []

        first_line = text.splitlines()[0].lower() if text.splitlines() else ""
        if "categor" not in first_line:
            return []

        if numeral.startswith("2."):
            return ["cartera_no_minorista"]
        if numeral.startswith("3."):
            return ["cartera_minorista"]
        if numeral.startswith("4."):
            return ["cartera_hipotecaria_vivienda"]
        return []

    def _infer_credit_types(self, text: str) -> list[CreditType]:
        lowered = text.lower()
        detected: list[CreditType] = []
        mapping = {
            CreditType.CONSUMO: ["consumo"],
            CreditType.HIPOTECARIO: ["hipotecario"],
            CreditType.MES: ["microempresa", "mes"],
            CreditType.CORPORATIVO: ["corporativo"],
            CreditType.GRAN_EMPRESA: ["gran empresa"],
            CreditType.MEDIANA_EMPRESA: ["mediana empresa"],
            CreditType.PEQUENA_EMPRESA: ["pequena empresa", "pequeña empresa"],
        }
        for credit_type, keywords in mapping.items():
            if any(keyword in lowered for keyword in keywords):
                detected.append(credit_type)
        return detected or [CreditType.CONSUMO]

    def _nearest_source_article(self, text: str, position: int) -> str:
        matches = list(ARTICLE_PATTERN.finditer(text[:position]))
        if not matches:
            return "documento"
        return f"Articulo {matches[-1].group('article')}"
