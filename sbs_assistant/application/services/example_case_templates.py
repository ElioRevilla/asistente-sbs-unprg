from dataclasses import dataclass
from decimal import Decimal

from sbs_assistant.domain.entities.case import SyntheticCase
from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.credit_type import CreditType
from sbs_assistant.domain.value_objects.pedagogical_mode import PedagogicalMode


@dataclass(frozen=True, slots=True)
class ExampleTemplate:
    """Auditable template for a classification exercise."""

    category: Category
    debtor_name: str
    credit_type: CreditType
    credit_type_label: str
    amount: Decimal
    days_late: int
    financial_context: str
    source_article: str


class TemplateExampleCaseGenerator:
    """Generate deterministic debtor cases before adding LLM variation."""

    _TEMPLATES: dict[Category, ExampleTemplate] = {
        Category.NORMAL: ExampleTemplate(
            category=Category.NORMAL,
            debtor_name="Comercial Los Sauces",
            credit_type=CreditType.CONSUMO,
            credit_type_label="consumo no revolvente",
            amount=Decimal("4500.00"),
            days_late=4,
            financial_context="mantiene pagos casi al dia y flujo estable",
            source_article="Capítulo II, numeral 3.1",
        ),
        Category.CPP: ExampleTemplate(
            category=Category.CPP,
            debtor_name="Servicios Rivas",
            credit_type=CreditType.CONSUMO,
            credit_type_label="consumo no revolvente",
            amount=Decimal("6200.00"),
            days_late=18,
            financial_context=(
                "presenta atrasos recientes, pero conserva ingresos regulares"
            ),
            source_article="Capítulo II, numeral 3.2",
        ),
        Category.DEFICIENTE: ExampleTemplate(
            category=Category.DEFICIENTE,
            debtor_name="Distribuidora Norte",
            credit_type=CreditType.CONSUMO,
            credit_type_label="consumo no revolvente",
            amount=Decimal("10000.00"),
            days_late=45,
            financial_context="sus ingresos bajaron y viene acumulando retrasos",
            source_article="Capítulo II, numeral 3.3",
        ),
        Category.DUDOSO: ExampleTemplate(
            category=Category.DUDOSO,
            debtor_name="Bazar Santa Rosa",
            credit_type=CreditType.CONSUMO,
            credit_type_label="consumo no revolvente",
            amount=Decimal("8500.00"),
            days_late=75,
            financial_context="tiene ventas inestables y retrasos prolongados",
            source_article="Capítulo II, numeral 3.4",
        ),
        Category.PERDIDA: ExampleTemplate(
            category=Category.PERDIDA,
            debtor_name="Taller El Progreso",
            credit_type=CreditType.CONSUMO,
            credit_type_label="consumo no revolvente",
            amount=Decimal("12000.00"),
            days_late=140,
            financial_context=(
                "no registra pagos recientes y su actividad esta paralizada"
            ),
            source_article="Capítulo II, numeral 3.5",
        ),
    }

    def generate(self, concept: str) -> SyntheticCase:
        category = self._category_from_concept(concept)
        template = self._template_for_concept(concept=concept, category=category)
        description = {
            "nombre_deudor": template.debtor_name,
            "tipo_credito": template.credit_type_label,
            "monto": float(template.amount),
            "dias_atraso": template.days_late,
            "situacion": template.financial_context,
            "pregunta": "¿En qué categoría crediticia clasificarías a este deudor?",
        }
        return SyntheticCase(
            id=None,
            credit_type=template.credit_type,
            description=description,
            correct_category=template.category,
            correct_provision=None,
            source_article=template.source_article,
            mode=PedagogicalMode.EJEMPLIFICA,
        )

    def _template_for_concept(
        self,
        concept: str,
        category: Category,
    ) -> ExampleTemplate:
        if "microempresa" not in concept.lower():
            return self._TEMPLATES[category]

        base = self._TEMPLATES[category]
        return ExampleTemplate(
            category=base.category,
            debtor_name="Bodega San Martin",
            credit_type=CreditType.MES,
            credit_type_label="microempresa",
            amount=Decimal("10000.00"),
            days_late=base.days_late,
            financial_context=(
                "financia capital de trabajo para su negocio y registra "
                "atrasos en sus cuotas"
            ),
            source_article=base.source_article,
        )

    def _category_from_concept(self, concept: str) -> Category:
        normalized = concept.lower()
        if "normal" in normalized:
            return Category.NORMAL
        if "cpp" in normalized or "problemas potenciales" in normalized:
            return Category.CPP
        if "deficiente" in normalized:
            return Category.DEFICIENTE
        if "dudoso" in normalized:
            return Category.DUDOSO
        if "perdida" in normalized or "pérdida" in normalized:
            return Category.PERDIDA
        return Category.DEFICIENTE
