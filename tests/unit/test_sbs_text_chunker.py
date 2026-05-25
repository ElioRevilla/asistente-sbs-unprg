from decimal import Decimal

from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.credit_type import CreditType
from sbs_assistant.infrastructure.parsing.sbs_text_chunker import (
    SbsRegulationTextChunker,
)


def test_chunker_splits_articles_and_infers_metadata() -> None:
    text = """
    CAPITULO I CLASIFICACION DEL DEUDOR
    Articulo 1. La clasificacion del deudor de consumo se realiza por categoria.
    Articulo 2. Las provisiones para credito hipotecario se calculan con porcentaje.
    """

    chunks = SbsRegulationTextChunker().chunk(text)

    assert [chunk.id for chunk in chunks] == ["art_1", "art_2"]
    assert chunks[0].article == 1
    assert chunks[0].chapter == "CAPITULO I CLASIFICACION DEL DEUDOR"
    assert "clasificacion" in chunks[0].topics
    assert chunks[1].content_type == "tabla"


def test_chunker_splits_numbered_regulation_sections() -> None:
    text = """
    INDICE
    1. ALCANCE
    2. DEFINICIONES
    CAPÍTULO I
    CONCEPTOS
    1. ALCANCE
    La presente norma aplica a empresas del sistema financiero.
    2. DEFINICIONES
    Créditos: suma de créditos directos e indirectos.
    2.1 Categoría Normal
    El deudor cumple puntualmente sus obligaciones.
    """

    chunks = SbsRegulationTextChunker().chunk(text)

    assert [chunk.id for chunk in chunks] == ["sec_001_1", "sec_002_2", "sec_003_2_1"]
    assert chunks[0].numeral == "1"
    assert "empresas del sistema financiero" in chunks[0].text


def test_chunker_keeps_section_content_across_page_breaks() -> None:
    text = """
    1. ALCANCE
    Texto inicial para activar el chunking por secciones numeradas.
    3.3 CATEGORÍA DEFICIENTE (2)
    Son aquellos deudores que registran atraso de treinta y uno (31) a sesenta
    (60) días calendario.
    3.4 CATEGORÍA DUDOSO (3)

    Los Laureles Nº 214 - Lima 27 - Perú Telf. : (511)2218990 Fax: (511) 4417760
    19
    Son aquellos deudores que registran atraso en el pago de sus créditos de
    sesenta y uno (61) a ciento veinte (120) días calendario.
    3.5 CATEGORÍA PÉRDIDA (4)
    Son aquellos deudores que muestran atraso de más de ciento veinte (120)
    días calendario.
    """

    chunks = SbsRegulationTextChunker().chunk(text)
    dudoso_chunk = next(chunk for chunk in chunks if chunk.numeral == "3.4")

    assert "CATEGORÍA DUDOSO" in dudoso_chunk.text
    assert "sesenta y uno (61) a ciento veinte (120)" in dudoso_chunk.text
    assert "Los Laureles" not in dudoso_chunk.text
    assert "\n19\n" not in dudoso_chunk.text
    assert all(chunk.numeral != "19" for chunk in chunks)


def test_chunker_tags_classification_sections_by_portfolio_type() -> None:
    text = """
    1. ALCANCE
    Texto inicial para activar el chunking por secciones numeradas.
    2.4 CATEGORÃA DUDOSO (3)
    El deudor presenta flujo de caja insuficiente.
    3.4 CATEGORÃA DUDOSO (3)
    Son aquellos deudores que registran atraso de sesenta y uno (61) a ciento
    veinte (120) dÃ­as calendario.
    4.4 CATEGORÃA DUDOSO (3)
    Son aquellos deudores que muestran atraso de ciento veintiuno (121) a
    trescientos sesenta y cinco (365) dÃ­as calendario.
    5.2 CLASIFICACIÃ“N CREDITICIA DEL DEUDOR
    Criterios generales para la clasificaciÃ³n crediticia.
    """

    chunks = SbsRegulationTextChunker().chunk(text)
    topics_by_numeral = {chunk.numeral: chunk.topics for chunk in chunks}

    assert "cartera_no_minorista" in topics_by_numeral["2.4"]
    assert "cartera_minorista" in topics_by_numeral["3.4"]
    assert "cartera_hipotecaria_vivienda" in topics_by_numeral["4.4"]
    assert not any(topic.startswith("cartera_") for topic in topics_by_numeral["5.2"])


def test_chunker_extracts_basic_provision_rules() -> None:
    text = """
    Articulo 10. Para creditos de consumo, la categoria Normal requiere 1.00%.
    Para creditos hipotecario, la categoria CPP requiere 2.50%.
    """

    rules = SbsRegulationTextChunker().extract_provision_rules(text)
    consumo_rule = next(
        rule for rule in rules if rule.credit_type == CreditType.CONSUMO
    )

    assert consumo_rule.category == Category.NORMAL
    assert consumo_rule.provision_percentage == Decimal("1.00")
    assert consumo_rule.source_article == "Articulo 10"
