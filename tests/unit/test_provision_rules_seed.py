import csv
from decimal import Decimal
from pathlib import Path


def test_provision_rules_seed_contains_core_tables() -> None:
    seed_path = Path("data/provision_rules_seed.csv")

    with seed_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 65
    assert _find_rate(rows, "Normal", "corporativo", "general") == Decimal("0.70")
    assert _find_rate(rows, "Normal", "hipotecario", "general") == Decimal("0.70")
    assert _find_rate(
        rows, "CPP", "todos", "tabla_1_sin_garantia_o_no_cubierto"
    ) == Decimal("5.00")
    assert _find_rate(
        rows, "Deficiente", "todos", "tabla_2_garantia_preferida"
    ) == Decimal("12.50")
    assert _find_rate(
        rows, "Perdida", "todos", "tabla_3_garantia_muy_rapida"
    ) == Decimal("30.00")
    assert _find_rate(
        rows,
        "Normal",
        "consumo_revolvente",
        "prociclica",
    ) == Decimal("1.50")
    assert _find_rate(
        rows,
        "Normal",
        "mediana_empresa",
        "prociclica",
    ) == Decimal("0.30")
    assert _find_rate(
        rows,
        "Normal",
        "consumo_no_revolvente",
        "prociclica_convenio_planilla_elegible",
    ) == Decimal("0.25")
    assert _find_rate(
        rows,
        "Normal",
        "consumo_no_revolvente",
        "prociclica_mes_4",
    ) == Decimal("0.70")


def test_provision_rules_seed_has_complete_prociclical_schedule() -> None:
    seed_path = Path("data/provision_rules_seed.csv")

    with seed_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    credit_types = {
        "corporativo",
        "gran_empresa",
        "mediana_empresa",
        "pequena_empresa",
        "microempresa",
        "consumo_revolvente",
        "consumo_no_revolvente",
        "hipotecario",
    }
    schedule_rows = [
        row
        for row in rows
        if row["tipo_garantia"]
        in {"prociclica_mes_2", "prociclica_mes_4", "prociclica_mes_6"}
    ]

    assert len(schedule_rows) == 24
    assert {row["tipo_credito"] for row in schedule_rows} == credit_types
    for credit_type in credit_types:
        assert {
            row["tipo_garantia"]
            for row in schedule_rows
            if row["tipo_credito"] == credit_type
        } == {"prociclica_mes_2", "prociclica_mes_4", "prociclica_mes_6"}


def test_fcc_seed_contains_all_factors() -> None:
    seed_path = Path("data/fcc_rules_seed.csv")

    with seed_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 5
    assert {row["codigo"] for row in rows} == {"a", "b", "c", "d", "e"}
    assert rows[0]["factor_conversion"] == "20.00"
    assert rows[3]["factor_conversion"] == "0.00"
    assert rows[4]["factor_conversion"] == "100.00"


def _find_rate(
    rows: list[dict[str, str]],
    category: str,
    credit_type: str,
    guarantee_type: str,
) -> Decimal:
    row = next(
        row
        for row in rows
        if row["categoria"] == category
        and row["tipo_credito"] == credit_type
        and row["tipo_garantia"] == guarantee_type
    )
    return Decimal(row["porcentaje_provision"])
