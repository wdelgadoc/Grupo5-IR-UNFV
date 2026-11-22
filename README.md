# VAOPE · Expediente de Ingeniería de Requerimientos

Trabajo grupal del curso **Ingeniería de Requerimientos**, Ciclo VI.
Universidad Nacional Federico Villarreal · Facultad de Ingeniería Industrial y de Sistemas ·
Escuela Profesional de Ingeniería de Sistemas · Lima, Perú · 2026.

**Docente:** Ing. Carlos Miguel Franco Del Carpio

## Página del proyecto

👉 **https://wdelgadoc.github.io/Grupo5-IR-UNFV/**

Reúne el expediente completo en cinco pestañas: Informe, Anexos, Dictamen,
Prototipo navegable y Presentación, esta última con un visor de las 31 láminas
de sustentación. Tiene modo claro y oscuro.

## De qué trata

Especificación y validación de los requerimientos del canal de venta de entradas
de VAOPE, una plataforma peruana de ticketera, aplicando el ciclo completo de la
ingeniería de requerimientos: elicitación, análisis, especificación formal bajo
IEEE 830-1998 e ISO/IEC/IEEE 29148, y validación con evidencia reproducible.

| Cifra | |
|---|---|
| 316 páginas | cinco tomos más el dictamen de cumplimiento |
| 39 | requerimientos funcionales y 10 no funcionales |
| 19 | casos de uso con ficha completa |
| 23 | reglas de negocio |
| 22 | escenarios de aceptación (CP-01 a CP-22) |
| 33 / 33 | comprobaciones de base de datos satisfactorias |
| 13 | actas de validación y control de cambios |

Línea base académica **v2.4**, congelada el 22 de noviembre de 2026 con huella
SHA-256 sobre el archivo de inventario.

## Contenido del repositorio

| Archivo | Qué es |
|---|---|
| `index.html` | Página del proyecto, autocontenida |
| `Informe_Tecnico_VAOPE_Tomo_I_Informe.docx` | Informe técnico · 99 páginas |
| `Informe_Tecnico_VAOPE_Tomo_II_Anexos_Especificacion.docx` | Anexos B, F y K · 42 páginas |
| `Informe_Tecnico_VAOPE_Tomo_III_Anexos_Prototipado.docx` | Anexos C y G · 30 páginas |
| `Informe_Tecnico_VAOPE_Tomo_IV_Anexos_Validacion_Pruebas.docx` | Anexos D, H, L, M y N · 94 páginas |
| `Informe_Tecnico_VAOPE_Tomo_V_Anexos_Control_Auditoria.docx` | Anexos A, E, I y J · 20 páginas |
| `Dictamen_Cumplimiento_4_Fases_IR_VAOPE.docx` | Dictamen de cumplimiento · 31 páginas |
| `Presentacion_VAOPE_CU-11_Grupo_5.pptx` | Sustentación · 31 láminas sobre el caso CU-11 |
| `Prototipo_navegable_VAOPE.html` | Prototipo de 16 pantallas, con guía y narración por voz |
| `VAOPE_esquema_pruebas_SQLite.sql` | 14 tablas, 1 vista y 18 disparadores |
| `VAOPE_ejecucion_pruebas_BD.py` | 33 comprobaciones, BD-01 a BD-33 |
| `resultados_bd.json` | Salida literal de la última ejecución |

## Reproducir la evidencia

```bash
python3 VAOPE_ejecucion_pruebas_BD.py
```

El guion crea la base en memoria a partir del esquema, ejecuta las 33
comprobaciones y escribe `resultados_bd.json`.

## Grupo 5

- Walter Delgado Córdova
- Miguel Castillo Morote
- Jose Frisancho Santillán
- Jhony Pascual Figueroa
- Dayrom Felix Miranda

## Alcance y declaraciones

Trabajo académico sobre un caso aplicado. **VAOPE no participó en su elaboración
y el expediente no constituye un pronunciamiento de la empresa.** El esquema de
base de datos y sus datos son propios y ficticios: acreditan la consistencia
interna de las reglas especificadas, no el sistema real de VAOPE.

Las actas del comité son actas simuladas del ejercicio académico y están
declaradas como tales. El escenario de aceptación CP-22 y las verificaciones
QA-RF19 y QA-RF20 están diseñados pero **no ejecutados** sobre el sistema real.
