# Gate G0 · Requisitos congelados

- Sprint: S02 · Tarea: S02-06
- Estado: **Pendiente de aprobación del equipo**
- Fecha de preparación: 2026-10-17

## Criterio del Gate
PRD v1.0, targets y costo objetivo aprobados; trazabilidad completa.

## Checklist

| Ítem | Documento | Estado |
|---|---|---|
| Misiones y condiciones de operación cuantificadas | [PRD.md](../requisitos/PRD.md) | Borrador listo |
| Historias de usuario con criterios de aceptación | [historias-usuario.md](../requisitos/historias-usuario.md) | Borrador listo |
| Targets con mínimo y objetivo vs DJI | [targets.md](../requisitos/targets.md) | Borrador listo |
| Costo objetivo y reparto del BOM | [target_cost.md](../negocio/target_cost.md) | Borrador listo; DS-I ≈ US$340 sobre objetivo |
| Trazabilidad requisito → verificación | [trazabilidad.md](../requisitos/trazabilidad.md) | Borrador listo |

## Decisiones que debe tomar el equipo

| # | Pregunta | Recomendación |
|---|---|---|
| 1 | ¿DS-D: 5 kg a 3 km a 4,500 msnm? | Sí, como objetivo; mínimo 4 kg |
| 2 | ¿Cámara de DS-I fija o intercambiable? | Fija en v1 (más barata); intercambiable en v2 |
| 3 | ¿RTK estándar u opcional en DS-I? | Opcional: baja el BOM base en ≈ US$140 |
| 4 | ¿Precios objetivo US$1,500 (DS-I) y US$3,500 (DS-D)? | Sí |
| 5 | ¿Mina piloto para las pruebas de campo? | Definir antes de S15 |
| 6 | ¿Tamaño del equipo? | Necesario para validar 80 h por sprint |
| 7 | ADR-001 (licencia) y ADR-002 (stack de simulación) | Aprobar las propuestas en `docs/decisiones.md` |

## Resultado
_(Completar en la revisión: Aprobado / Aprobado con observaciones / Rechazado, fecha y cambios pedidos. Luego tag git `req-v1.0`.)_
