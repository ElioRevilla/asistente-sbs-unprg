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

    def generate(self, concept: str, variant_index: int = 0) -> SyntheticCase:
        category = self._category_from_concept(concept)
        template = self._template_for_concept(
            concept=concept,
            category=category,
            variant_index=variant_index,
        )
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
        variant_index: int,
    ) -> ExampleTemplate:
        if self._is_minorist_concept(concept):
            return self._minorist_variant(
                category=category,
                microenterprise="microempresa" in concept.lower(),
                variant_index=variant_index,
            )
        base = self._TEMPLATES[category]

        return base

    def _minorist_variant(
        self,
        *,
        category: Category,
        microenterprise: bool,
        variant_index: int,
    ) -> ExampleTemplate:
        base = self._TEMPLATES[category]
        variants = self._minorist_variants(category)
        variant = variants[variant_index % len(variants)]
        debtor_name, credit_label, credit_type, amount, days_late, context = variant
        if microenterprise:
            debtor_name = self._microenterprise_names(category)[
                variant_index % len(self._microenterprise_names(category))
            ]
            credit_label = "microempresa"
            credit_type = CreditType.MES
        return ExampleTemplate(
            category=base.category,
            debtor_name=debtor_name,
            credit_type=credit_type,
            credit_type_label=credit_label,
            amount=amount,
            days_late=days_late,
            financial_context=context,
            source_article=base.source_article,
        )

    def _minorist_variants(
        self,
        category: Category,
    ) -> list[tuple[str, str, CreditType, Decimal, int, str]]:
        return {
            Category.NORMAL: [
                (
                    "Comercial Los Sauces",
                    "consumo no revolvente",
                    CreditType.CONSUMO,
                    Decimal("4500.00"),
                    4,
                    "mantiene pagos casi al dia y flujo estable",
                ),
                (
                    "Libreria Central",
                    "pequena empresa",
                    CreditType.PEQUENA_EMPRESA,
                    Decimal("18000.00"),
                    7,
                    "paga dentro del rango normal y conserva ventas estables",
                ),
                (
                    "Servicios Alba",
                    "consumo no revolvente",
                    CreditType.CONSUMO,
                    Decimal("3200.00"),
                    0,
                    "no presenta atraso y mantiene ingresos regulares",
                ),
            ],
            Category.CPP: [
                (
                    "Servicios Rivas",
                    "consumo no revolvente",
                    CreditType.CONSUMO,
                    Decimal("6200.00"),
                    18,
                    "presenta atrasos recientes, pero conserva ingresos regulares",
                ),
                (
                    "Minimarket Grau",
                    "pequena empresa",
                    CreditType.PEQUENA_EMPRESA,
                    Decimal("22000.00"),
                    30,
                    "esta justo en el limite superior del rango CPP",
                ),
                (
                    "Textiles Romero",
                    "consumo no revolvente",
                    CreditType.CONSUMO,
                    Decimal("5100.00"),
                    9,
                    "acumula el primer tramo de atraso relevante",
                ),
            ],
            Category.DEFICIENTE: [
                (
                    "Distribuidora Norte",
                    "consumo no revolvente",
                    CreditType.CONSUMO,
                    Decimal("10000.00"),
                    45,
                    "sus ingresos bajaron y viene acumulando retrasos",
                ),
                (
                    "Panaderia La Union",
                    "pequena empresa",
                    CreditType.PEQUENA_EMPRESA,
                    Decimal("15500.00"),
                    31,
                    "esta en el primer dia del rango Deficiente",
                ),
                (
                    "Ferreteria San Jose",
                    "consumo no revolvente",
                    CreditType.CONSUMO,
                    Decimal("7800.00"),
                    60,
                    "esta en el limite superior antes de pasar a Dudoso",
                ),
            ],
            Category.DUDOSO: [
                (
                    "Bazar Santa Rosa",
                    "consumo no revolvente",
                    CreditType.CONSUMO,
                    Decimal("8500.00"),
                    75,
                    "tiene ventas inestables y retrasos prolongados",
                ),
                (
                    "Abarrotes El Sol",
                    "pequena empresa",
                    CreditType.PEQUENA_EMPRESA,
                    Decimal("26000.00"),
                    61,
                    "acaba de ingresar al rango Dudoso",
                ),
                (
                    "Confecciones Rivera",
                    "consumo no revolvente",
                    CreditType.CONSUMO,
                    Decimal("9300.00"),
                    120,
                    "esta en el limite superior de la categoria Dudoso",
                ),
            ],
            Category.PERDIDA: [
                (
                    "Taller El Progreso",
                    "consumo no revolvente",
                    CreditType.CONSUMO,
                    Decimal("12000.00"),
                    140,
                    "no registra pagos recientes y su actividad esta paralizada",
                ),
                (
                    "Restaurante La Esquina",
                    "pequena empresa",
                    CreditType.PEQUENA_EMPRESA,
                    Decimal("34000.00"),
                    121,
                    "supera el rango Dudoso y entra a Perdida",
                ),
                (
                    "Importaciones Vega",
                    "consumo no revolvente",
                    CreditType.CONSUMO,
                    Decimal("11100.00"),
                    180,
                    "mantiene atraso severo y no muestra recuperacion de pagos",
                ),
            ],
        }[category]

    def _microenterprise_names(self, category: Category) -> list[str]:
        return {
            Category.NORMAL: [
                "Bodega Los Pinos",
                "Jugueria San Miguel",
                "Zapateria El Trebol",
            ],
            Category.CPP: [
                "Bodega Santa Elena",
                "Cevicheria Mar Azul",
                "Taller Mecanico Ruiz",
            ],
            Category.DEFICIENTE: [
                "Bodega San Martin",
                "Panaderia La Union",
                "Ferreteria San Jose",
            ],
            Category.DUDOSO: [
                "Abarrotes El Sol",
                "Confecciones Rivera",
                "Polleria Las Brisas",
            ],
            Category.PERDIDA: [
                "Restaurante La Esquina",
                "Taller El Progreso",
                "Importaciones Vega",
            ],
        }[category]

    def _is_minorist_concept(self, concept: str) -> bool:
        normalized = concept.lower()
        return any(
            marker in normalized
            for marker in (
                "microempresa",
                "pequena",
                "pequeña",
                "consumo",
                "minorista",
            )
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
