from __future__ import annotations

import json
import re

from sbs_assistant.domain.entities.case import SyntheticCase
from sbs_assistant.domain.ports.llm_port import LLMPort

SYSTEM_PROMPT = """
Eres un generador de variaciones narrativas para ejercicios educativos sobre
clasificación crediticia SBS.

Reglas:
- Responde solo JSON válido.
- No cambies categoría, días de atraso, monto, tipo de crédito ni fuente.
- No reveles la categoría correcta.
- Solo puedes variar nombre ficticio, rubro y situación narrativa.
- Usa español LATAM.
""".strip()


class LLMExampleCaseVariationService:
    """Use an LLM only to vary safe narrative fields of a template case."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def vary(self, case: SyntheticCase, concept: str) -> SyntheticCase:
        response = await self._llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=self._build_prompt(case=case, concept=concept),
        )
        variation = self._parse_json(response)
        if variation is None:
            return case

        description = dict(case.description)
        if nombre := variation.get("nombre_deudor"):
            description["nombre_deudor"] = str(nombre)
        if rubro := variation.get("rubro"):
            description["rubro"] = str(rubro)
        if situacion := variation.get("situacion"):
            description["situacion"] = str(situacion)

        return SyntheticCase(
            id=case.id,
            credit_type=case.credit_type,
            description=description,
            correct_category=case.correct_category,
            correct_provision=case.correct_provision,
            source_article=case.source_article,
            mode=case.mode,
        )

    def _build_prompt(self, case: SyntheticCase, concept: str) -> str:
        return json.dumps(
            {
                "concepto": concept,
                "caso_base": case.description,
                "campos_permitidos": [
                    "nombre_deudor",
                    "rubro",
                    "situacion",
                ],
                "campos_prohibidos": [
                    "tipo_credito",
                    "monto",
                    "dias_atraso",
                    "categoria_correcta",
                    "articulo_fuente",
                    "pregunta",
                ],
                "formato_respuesta": {
                    "nombre_deudor": "string",
                    "rubro": "string",
                    "situacion": "string",
                },
            },
            ensure_ascii=False,
        )

    def _parse_json(self, response: str) -> dict[str, object] | None:
        cleaned = response.strip()
        fenced_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.S)
        if fenced_match:
            cleaned = fenced_match.group(1).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
