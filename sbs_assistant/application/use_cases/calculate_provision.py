from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sbs_assistant.domain.ports.provision_rule_repository_port import (
    ProvisionRuleRepositoryPort,
)


@dataclass(frozen=True, slots=True)
class ProvisionCalculation:
    """Deterministic provisioning result for a simple debtor case."""

    credit_type: str
    category: str
    guarantee_type: str
    days_late: int
    amount: Decimal
    provision_percentage: Decimal
    provision_amount: Decimal
    classification_source: str
    provision_source: str


class ProvisionCalculator:
    """Classify simple debtor cases and calculate provisions by code."""

    def __init__(self, repository: ProvisionRuleRepositoryPort) -> None:
        self._repository = repository

    async def try_calculate_from_question(
        self,
        question: str,
    ) -> ProvisionCalculation | None:
        credit_type = self._detect_credit_type(question)
        days_late = self._detect_days_late(question)
        amount = self._detect_amount(question)
        if credit_type is None or days_late is None or amount is None:
            return None

        category = self._classify_by_days(credit_type=credit_type, days_late=days_late)
        if category is None:
            return None

        guarantee_type = self._detect_guarantee_type(question)
        rule = await self._repository.find_percentage(
            category=category,
            credit_type=credit_type,
            guarantee_type=guarantee_type,
        )
        if rule is None:
            return None

        percentage = Decimal(rule.provision_percentage)
        provision_amount = (amount * percentage / Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        return ProvisionCalculation(
            credit_type=credit_type,
            category=category,
            guarantee_type=guarantee_type,
            days_late=days_late,
            amount=amount,
            provision_percentage=percentage,
            provision_amount=provision_amount,
            classification_source=self._classification_source(credit_type, category),
            provision_source=rule.source_article,
        )

    def _detect_credit_type(self, question: str) -> str | None:
        normalized = self._normalize(question)
        if "consumo no revolvente" in normalized:
            return "consumo_no_revolvente"
        if "consumo revolvente" in normalized:
            return "consumo_revolvente"
        if "hipotecario" in normalized:
            return "hipotecario"
        if "microempresa" in normalized:
            return "microempresa"
        if "pequena empresa" in normalized or "pequena empresa" in normalized:
            return "pequena_empresa"
        return None

    def _detect_days_late(self, question: str) -> int | None:
        normalized = self._normalize(question)
        match = re.search(r"(\d{1,4})\s*dias?\s+de\s+atraso", normalized, re.I)
        if not match:
            match = re.search(r"atraso\s+de\s+(\d{1,4})\s*dias?", normalized, re.I)
        return int(match.group(1)) if match else None

    def _detect_amount(self, question: str) -> Decimal | None:
        match = re.search(r"(?:S/\s*|S\.\s*/\s*|soles\s*)?(\d[\d,\.]*)", question)
        if not match:
            return None
        raw_amount = match.group(1).replace(",", "")
        return Decimal(raw_amount)

    def _detect_guarantee_type(self, question: str) -> str:
        normalized = self._normalize(question)
        if "autoliquidable" in normalized:
            return "garantia_preferida_autoliquidable"
        if "muy rapida" in normalized:
            return "tabla_3_garantia_muy_rapida"
        if "garantia preferida" in normalized:
            return "tabla_2_garantia_preferida"
        return "tabla_1_sin_garantia_o_no_cubierto"

    def _classify_by_days(self, credit_type: str, days_late: int) -> str | None:
        if credit_type in {
            "pequena_empresa",
            "microempresa",
            "consumo_revolvente",
            "consumo_no_revolvente",
        }:
            if days_late <= 8:
                return "Normal"
            if days_late <= 30:
                return "CPP"
            if days_late <= 60:
                return "Deficiente"
            if days_late <= 120:
                return "Dudoso"
            return "Perdida"

        if credit_type == "hipotecario":
            if days_late <= 30:
                return "Normal"
            if days_late <= 60:
                return "CPP"
            if days_late <= 120:
                return "Deficiente"
            if days_late <= 365:
                return "Dudoso"
            return "Perdida"

        return None

    def _classification_source(self, credit_type: str, category: str) -> str:
        if credit_type in {
            "pequena_empresa",
            "microempresa",
            "consumo_revolvente",
            "consumo_no_revolvente",
        }:
            return f"Capítulo II, numeral {self._minorista_numeral(category)}"
        if credit_type == "hipotecario":
            return f"Capítulo II, numeral {self._hipotecario_numeral(category)}"
        return "Capítulo II"

    def _minorista_numeral(self, category: str) -> str:
        return {
            "Normal": "3.1",
            "CPP": "3.2",
            "Deficiente": "3.3",
            "Dudoso": "3.4",
            "Perdida": "3.5",
        }[category]

    def _hipotecario_numeral(self, category: str) -> str:
        return {
            "Normal": "4.1",
            "CPP": "4.2",
            "Deficiente": "4.3",
            "Dudoso": "4.4",
            "Perdida": "4.5",
        }[category]

    def _normalize(self, text: str) -> str:
        translation = str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")
        return text.translate(translation).lower()
