# Inventario de tablas del Reglamento SBS

Fuente local revisada: `data/20160719_res-11356-2008.pdf`.

Metodo usado:

- Deteccion textual inicial con `pypdf` buscando `Tabla`, `Anexo`, `FCC`, `%`, `provision` y terminos relacionados.
- Render visual de paginas candidatas a PNG con `pypdfium2` para validar estructura de tablas.
- Cruce contra los archivos estructurados actuales:
  - `data/provision_rules_seed.csv`
  - `data/fcc_rules_seed.csv`
  - `db/migrations/002_create_fcc_rules.sql`

Nota: este inventario valida las tablas relevantes para el MVP de calculo y explicacion. No reemplaza una auditoria legal final ni una extraccion formal con Document AI.

## Resultado Ejecutivo

Las tablas necesarias para calculos del MVP estan estructuradas:

- Tasas de provision general: cubierta.
- Tasas especificas Tabla 1, Tabla 2 y Tabla 3: cubierta.
- Componente prociclico vigente del Anexo I: cubierta.
- Constitucion gradual Mes 2 / Mes 4 / Mes 6: cubierta.
- Factores de Conversion Crediticios: cubierta en tabla separada.

No todas las tablas o listas tabulares del PDF deben ir a SQL. Algunas son texto normativo, anexos contables o modificaciones historicas y se aprovechan mejor como chunks citables por RAG.

## Inventario

| ID | Pagina PDF | Seccion | Contenido | Estado | Implementacion |
| --- | ---: | --- | --- | --- | --- |
| T01 | 2 | Articulo Segundo, literal b | Tabla modificatoria con categorias antiguas: creditos comerciales, MES, consumo e hipotecarios | Solo RAG | No se carga a DB porque es parte modificatoria y queda superada por la version vigente del reglamento en pagina 20 |
| T02 | 3 | Anexo I sustituido, componente prociclico | Tabla modificatoria con categorias antiguas: comerciales, MES, consumo e hipotecarios | Solo RAG | No se carga a DB porque la version vigente detallada esta en pagina 34 |
| T03 | 10 | Capitulo I, numeral 3 | Factores de Conversion Crediticios de creditos indirectos: literales a-e | Estructurada | `fcc_rules`, `data/fcc_rules_seed.csv`, 5 filas |
| T04 | 20 | Capitulo III, numeral 2.1 | Tasas minimas de provisiones genericas para categoria Normal por tipo de credito | Estructurada | `provision_rules`, tipo_garantia=`general`, 8 filas |
| T05 | 20 | Capitulo III, numeral 2.1 | Tasas especificas por categoria de riesgo: Tabla 1, Tabla 2 y Tabla 3 | Estructurada | `provision_rules`, 12 filas |
| T06 | 20 | Capitulo III, numeral 2.1 | Regla textual de garantias preferidas autoliquidables: porcentaje no menor a 1% | Estructurada | `provision_rules`, tipo_garantia=`garantia_preferida_autoliquidable`, 4 filas |
| T07 | 34 | Anexo I, Capitulo I, numeral 2 | Componente prociclico vigente por 8 tipos de credito | Estructurada | `provision_rules`, tipo_garantia=`prociclica`, 8 filas |
| T08 | 34 | Anexo I, Capitulo I, numeral 2 | Regla textual de componente prociclico con garantias preferidas autoliquidables | Estructurada | `provision_rules`, tipo_garantia=`prociclica_garantia_preferida_autoliquidable`, 8 filas |
| T09 | 35 | Anexo I, Capitulo I, numeral 2 | Regla textual para convenios de descuento por planilla elegibles: 0.25% | Estructurada | `provision_rules`, tipo_garantia=`prociclica_convenio_planilla_elegible`, 1 fila |
| T10 | 36 | Anexo I, Capitulo II, numeral 2 | Tabla de constitucion gradual de provisiones prociclicas: Mes 2, Mes 4 y Mes 6 | Estructurada | `provision_rules`, tipo_garantia=`prociclica_mes_2/4/6`, 24 filas |
| T11 | 41-42 | Anexo A | Codigos y subcuentas contables para modificaciones al Manual de Contabilidad | Solo RAG | No se carga a DB porque no participa en calculo de provision del MVP |

## Cruce con Base de Datos

Estado esperado despues de migraciones y seeds:

```text
chunks=127
provision_rules=65
fcc_rules=5
```

Desglose esperado de `provision_rules`:

| Grupo | Filas |
| --- | ---: |
| Categoria Normal, tratamiento general | 8 |
| Tabla 1, Tabla 2 y Tabla 3 | 12 |
| Garantias preferidas autoliquidables | 4 |
| Componente prociclico vigente | 8 |
| Prociclica con garantias preferidas autoliquidables | 8 |
| Convenio de descuento por planilla elegible | 1 |
| Constitucion gradual Mes 2 / Mes 4 / Mes 6 | 24 |
| Total | 65 |

Desglose esperado de `fcc_rules`:

| Grupo | Filas |
| --- | ---: |
| Literales a-e de FCC | 5 |

## Decision

Para el siguiente incremento, podemos continuar con embeddings y RAG. Las tablas criticas para calculos numericos ya estan separadas del texto y verificadas visualmente. El resto del contenido tabular debe mantenerse como chunks citables hasta que un caso de uso concreto exija volverlo deterministico.
