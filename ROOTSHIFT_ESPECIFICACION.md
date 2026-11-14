# ROOTSHIFT — Especificación funcional y técnica

> ⚠️ **DOCUMENTO SUSTITUIDO.** Esta es la v1.0 (borrador, región mediterránea, NEX-GDDP, SoilGrids).
> La especificación vigente es **[`ROOTSHIFT_SPEC_v2.0_FINAL.md`](ROOTSHIFT_SPEC_v2.0_FINAL.md)**, con las decisiones D1–D20 cerradas y el catálogo definitivo de 22 productos.
> No implementes a partir de este archivo.

**Versión:** 1.0
**Estado:** Borrador para validación del equipo · **apto para iniciar implementación** tras resolver el §19
**Ámbito:** Hackathon NASA · Dominio: agricultura · Datos: datasets públicos de la NASA
**Documento único de referencia:** este archivo es la fuente de verdad del producto. Cualquier otro documento, slide o README debe derivarse de él.

### Índice

| | Sección | Para qué sirve |
|---|---|---|
| 0 | Cómo leer este documento | Etiquetas de trazabilidad y convenciones |
| 1 | Resumen ejecutivo | Qué es y qué se construye |
| 2 | Problema, visión y principios | El "por qué" y las reglas no negociables |
| 3 | Alcance | Qué entra, qué no, y cómo se habla |
| 4 | Usuarios y recorridos | Quién lo usa y qué hace |
| 5 | Glosario y modelo de dominio | Vocabulario común |
| 6 | Entradas del sistema | Contrato del formulario |
| 7 | Datos: catálogo de fuentes NASA | Productos, resoluciones, accesos |
| 8 | Arquitectura de software | Stack, carpetas, flujos |
| 9 | Pipeline de datos | Ingesta, caché, calidad |
| 10 | **Motor de cálculo** | **Fórmulas, índices y optimización** |
| 11 | API HTTP | Endpoints y contratos |
| 12 | Modelo de datos | DDL y almacenamiento |
| 13 | Interfaz (UI/UX) | Pantallas, componentes, copy |
| 14 | Requisitos no funcionales | Rendimiento, seguridad, legal |
| 15 | Plan de implementación | Fases, MVP, brief para el agente |
| 16 | Pruebas y validación | Cómo saber que funciona |
| 17 | Riesgos | Qué puede salir mal |
| 18 | Anexos | Ejemplos, tablas, referencias |
| 19 | **Decisiones abiertas** | **Lo que debes validar tú** |

---

## 0. Cómo leer este documento

### 0.1 Etiquetas de trazabilidad

Cada requisito lleva una etiqueta que indica su origen. Esto es obligatorio: el implementador no debe convertir una propuesta técnica en un requisito del usuario.

| Etiqueta | Significado | Autoridad |
|---|---|---|
| `[N]` | **Nota del usuario.** Texto o intención expresada literalmente en los apuntes del equipo. | No modificable sin el equipo |
| `[D]` | **Derivado.** Consecuencia técnica directa e inevitable de un `[N]`. | Se puede reescribir, no se puede eliminar |
| `[P]` | **Propuesta.** Decisión técnica del autor de esta especificación (fórmula, umbral, peso, librería). **Ajustable y validable.** | El equipo puede cambiarla |

Las secciones `[P]` son las que hay que revisar con criterio agronómico. Las `[N]` son las que hay que respetar.

### 0.2 Regla de oro del especificador

> **Este documento no inventa requisitos del usuario.** Cuando el apunte no dice nada, el documento lo declara como hueco, propone una opción por defecto y la envía al §19 (Decisiones abiertas). No hay funcionalidades "sorpresa".

### 0.3 Convenciones

- **Unidades:** SI + unidades agronómicas de uso común (mm, °C, ha, t/ha, m³, L/s). Todo número mostrado en UI lleva unidad explícita.
- **Coordenadas:** WGS84 (EPSG:4326). Áreas en hectáreas, calculadas en proyección métrica local (p. ej. UTM de la zona).
- **Fechas:** ISO-8601. Temporadas agrícolas codificadas como `2026S` (campaña) o `2026-27` (ciclo invierno).
- **Idioma de la UI:** español de España por defecto (ver D16).
- **Nomenclatura de código:** inglés (tablas, endpoints, campos). Contenido y copy: español.

### 0.4 Trazabilidad de los apuntes originales

| Apunte original | Dónde se especifica | Tipo |
|---|---|---|
| "Un agricultor puede elegir qué sembrar… no cuánto lloverá mañana" | §2.2, §3.2 | `[N]` |
| "probar sus decisiones contra las sequías del futuro antes de arriesgar su cosecha" | §10.6, §10.7 | `[N]` |
| "no predecimos el futuro… varios futuros posibles" | §3.2 (principio rector), §10.6 | `[N]` |
| Propósito: "transformar territorios agrícolas vulnerables en ecosistemas capaces de alimentar a la población bajo escenarios climáticos extremos" | §1, §2.1 | `[N]` |
| Input: ubicación geográfica | §6.2 | `[N]` |
| Input: datos de los datasets para esa ubicación | §7, §9 | `[N]` |
| Input: cultivos actuales / preferidos / recomendados | §6.3 | `[N]` |
| Input: materiales y recursos disponibles | §6.4 | `[N]` |
| Input: datasets públicos NASA "de todo tipo" | §7 | `[N]` |
| F1: diseño de rotación para máxima producción el mayor tiempo posible | §10.7, §13.3 | `[N]` |
| F2: control de enfermedades | §10.9, §13.4 | `[N]` |
| F3: sistema de riego sostenible + mapa | §10.10, §13.5 | `[N]` |
| F4 (secundaria): vista geográfica con indicador temporal deslizable (año y mes) | §13.6 | `[N]` |
| F5: actuación ante tragedia en la finca | §10.11, §13.7 | `[N]` |
| "proponer los cálculos e indicadores fiables" | §10 completo | `[N]` + `[P]` |
| Decisiones que cambian la dirección | §19 | `[P]` |

---

## 1. Resumen ejecutivo

**ROOTSHIFT** es una aplicación web que permite a un agricultor **ensayar decisiones agronómicas contra varios futuros climáticos** antes de comprometer su cosecha. No pronostica el tiempo: construye escenarios con datos históricos y proyecciones de la NASA, evalúa la rotación de cultivos del agricultor y le muestra qué combinación de decisiones resiste mejor en el peor caso.

Se construye sobre **cinco funcionalidades** `[N]`:

| # | Funcionalidad | Output `[N]` | Motor de cálculo | Prioridad |
|---|---|---|---|---|
| F1 | Diseño de rotación resiliente | Panel ilustrativo del diseño sugerido | §10.7 + §10.8 | **P0** |
| F2 | Control de enfermedades | Panel de enfermedades + recomendaciones | §10.9 | P1 |
| F3 | Diseño de riego sostenible | Recomendación de sistema + mapa | §10.10 | P1 |
| F4 | Vista geográfica temporal (secundaria) | Mapa + barra temporal año/mes | §13.6 | P2 |
| F5 | Actuación ante catástrofes | Panel de catástrofes + cómo evitarlas/solucionarlas | §10.11 | P0 |

**Arquitectura en una frase:** frontend Next.js + API FastAPI (Python científico) + PostGIS + artefactos precomputados; **todo cálculo es determinista, versionado y con procedencia de datos visible** (§8, §10.12).

**Lo que el jurado debe ver en 3 minutos:** un agricultor introduce su finca y sus cultivos → la app le devuelve una rotación distinta a la suya → un gráfico demuestra que, bajo la peor sequía registrada y bajo un escenario SSP5-8.5, esa rotación produce más y falla menos → y una frase explica *por qué*.

---

## 2. Problema, visión y principios

### 2.1 Problema

El agricultor decide **qué sembrar** con información del pasado y del precio, pero su resultado depende de **variables que no controla**: lluvia, temperatura, sequía, heladas. Esa asimetría — decisión controlable, resultado no controlable — es la que ROOTSHIFT ataca. `[N]`

El problema de fondo que declara el equipo `[N]`: territorios agrícolas vulnerables deben transformarse en sistemas capaces de sostener producción alimentaria bajo escenarios climáticos extremos. La rotación de cultivos es la palanca agronómica que actúa sobre el suelo, el agua y las enfermedades a la vez, y por eso es el núcleo del producto.

### 2.2 Principios rectores (no negociables)

1. **No se predice, se simula.** `[N]` La UI nunca dice "lloverá X mm el 12 de mayo" ni "obtendrás 4,2 t/ha". Dice: "en el 80 % de los 30 años analizados, la demanda de agua de esta rotación fue cubierta por la lluvia; en el 20 % restante hubo que regar". Ver §3.2 para las reglas de lenguaje.
2. **Siempre varios futuros.** `[N]` Todo resultado se presenta como distribución o abanico (p10 / p50 / p90), nunca como número único.
3. **Todo número tiene procedencia.** Cada cifra muestra de qué producto NASA, qué variable, qué resolución y qué periodo sale (§10.12).
4. **Honestidad de escala.** Los datos climáticos de la NASA son de 0,1°–0,5° (≈11–55 km). La finca es un punto dentro de esa celda. La app debe decirlo, no disimularlo (§7.4).
5. **El agricultor manda.** La recomendación se puede rechazar, editar y comparar. La app nunca bloquea una decisión: la puntúa.
6. **Sin diagnóstico ni receta.** En enfermedades, la app estima *riesgo* y sugiere *manejo*; no diagnostica tejido ni prescribe dosis de producto (§10.9.6).

### 2.3 Propuesta de valor (una frase)

> Un agricultor puede elegir qué sembrar hoy. ROOTSHIFT le deja probar esa decisión contra las sequías del pasado y de varios futuros posibles, antes de arriesgar la cosecha.

---

## 3. Alcance

### 3.1 Dentro del alcance

- Registro de **una finca** por sesión (múltiples parcelas dentro de la finca).
- Perfil agronómico: cultivos actuales, cultivos preferidos, cultivos excluidos, recursos disponibles.
- Descarga y procesamiento de los productos NASA listados en §7 para la celda climática de la finca.
- Cálculo de indicadores agroclimáticos históricos (1991–presente, según disponibilidad del producto).
- Simulación de escenarios de estrés y de clima futuro (NEX-GDDP-CMIP6, §10.6).
- Optimización y puntuación de secuencias de rotación (F1).
- Estimación de riesgo de enfermedades por cultivo y ventana temporal (F2).
- Recomendación y dimensionamiento indicativo de riego + mapa de zonas (F3).
- Vista de mapa con capas satelitales y deslizador temporal año/mes (F4).
- Evaluación de peligros naturales y planes de actuación (F5).
- Exportación de resultados a PDF/CSV (una sola página por funcionalidad).

### 3.2 Fuera del alcance (explícito, para que el agente no lo invente)

- Pronóstico meteorológico operativo (a 1–15 días). ROOTSHIFT **no** es un servicio meteorológico.
- Control de maquinaria, telemetría IoT, sensores de campo, drones.
- Contabilidad, facturación, trazabilidad comercial, certificaciones.
- Recomendación de dosis, materias activas o marcas de fitosanitarios.
- Diagnóstico de enfermedades por imagen (visión artificial). Ver D11.
- Gestión ganadera, piscicultura, silvicultura.
- Mercados, precios, cadena de suministro (salvo que se active D9).
- App móvil nativa (la web debe ser responsive, nada más).
- Tiempo real: la actualización de datos es diaria/semanal, no por segundo.

### 3.3 Reglas de lenguaje de la UI (obligatorias)

| Prohibido | Permitido |
|---|---|
| "Lloverá 40 mm en abril" | "En abril, 40 mm es el valor que se supera en 7 de cada 10 años (p70 histórico)" |
| "Rendimiento estimado: 4,2 t/ha" | "Rango de rendimiento simulado: 3,1–4,8 t/ha (p10–p90)" |
| "Esta rotación es la mejor" | "Esta rotación tiene el mayor índice de resiliencia de las 12 evaluadas" |
| "Plaga detectada" | "Condiciones favorables para *X* en la ventana del 12–28 de mayo" |
| "Sistema de riego óptimo" | "Sistema recomendado según tus recursos; requiere validación técnica en campo" |
| "Datos de la NASA confirman" | "Según NASA POWER (MERRA-2, 0,5°), periodo 1991–2020" |

Toda pantalla con cifras debe incluir, en pie de página o tooltip, la cadena `Fuente: <producto NASA> · <variable> · <resolución> · <periodo>`.

---

## 4. Usuarios y recorridos

### 4.1 Perfiles

| Perfil | Necesidad | Uso esperado |
|---|---|---|
| **Agricultor de secano** (primario) | Saber qué rotar para no perder la cosecha en año seco | Consulta anual, antes de la siembra |
| **Agricultor de regadío** (primario) | Ajustar rotación + riego a un recurso hídrico limitado | Consulta anual + mensual |
| **Técnico asesor / cooperativa** (secundario) | Comparar alternativas para varios socios y explicarlas | Uso repetido, varias fincas |
| **Jurado de hackathon / evaluador** | Entender el valor en 3 minutos | Sesión guiada con finca demo |

### 4.2 Recorrido principal (onboarding, 5 pasos, objetivo < 3 min)

1. **Ubicación** — el usuario busca su municipio o dibuja el polígono de la finca. Se muestra la celda climática NASA detectada y su superficie.
2. **Qué cultiva hoy** — selección de cultivos actuales y superficie (con valores por defecto sugeridos por la app).
3. **Qué quiere** — cultivos preferidos (opcional) y cultivos excluidos (opcional).
4. **Qué tiene** — recursos: agua, riego disponible, presupuesto, maquinaria, mano de obra, insumos.
5. **Generar** — barra de progreso con las etapas reales del cálculo ("descargando 30 años de clima", "evaluando 240 rotaciones"…). Al terminar: dashboard.

### 4.3 Recorridos secundarios

- **Comparar:** el usuario edita la rotación propuesta (arrastra cultivos) y ve recalcularse el índice en < 3 s (cálculo cacheado). Es la interacción que demuestra que el sistema es un simulador, no un PDF.
- **Profundizar:** desde una tarjeta de riesgo (enfermedad, sequía) se abre el detalle con la serie temporal y las reglas que dispararon la alerta.
- **Volver mañana:** la finca se guarda en sesión (y en cuenta si D14 = sí).

---

## 5. Glosario y modelo de dominio

### 5.1 Glosario

| Término | Definición operativa en ROOTSHIFT |
|---|---|
| **Finca (farm)** | Unidad de gestión del usuario. Contiene ≥1 parcela y comparte recursos. |
| **Parcela (parcel)** | Polígono con un uso y una rotación propios. Es la unidad de cálculo agronómico. |
| **Celda climática** | Celda de la cuadrícula nativa de NASA POWER asociada a la parcela. Todas las variables meteorológicas se toman de su centro. |
| **Temporada (season)** | Ventana de cultivo. `S` = primavera–verano; `W` = otoño–invierno; `F` = barbecho. |
| **Rotación** | Secuencia ordenada de cultivos por temporada sobre una parcela, con horizonte de N temporadas. |
| **Escenario** | Conjunto coherente de años meteorológicos sintéticos o proyectados sobre el que se evalúa una rotación. |
| **Indicador** | Variable calculada con unidad y procedencia (p. ej. `spei_12`, `etc_season_mm`). |
| **IRS** | Índice de Resiliencia ROOTSHIFT, 0–100 (§10.8). Índice propio, no estándar. |
| **Tragedia** | Evento extremo con impacto productivo: sequía, inundación, helada, ola de calor, incendio, viento, erosión. |
| **Playbook** | Protocolo de actuación antes/durante/después de una tragedia. |
| **Artefacto** | Cualquier salida calculada y persistida (rotación, simulación, diseño de riego) con `model_version` y `params_hash`. |

### 5.2 Entidades principales

```
Farm 1─n Parcel 1─n Rotation 1─n RotationItem
Parcel n─1 ClimateCell 1─n IndicatorSeries
Farm 1─n Resource
Farm 1─n Simulation n─1 ScenarioSet
Farm 1─n DiseaseRisk
Farm 1─n HazardAssessment 1─n PlaybookStep
Farm 1─n IrrigationDesign 1─n IrrigationZone
* 1─n Provenance
```

### 5.3 Relación entre funcionalidades (para no duplicar cálculos)

```
                 ┌──────────────────────────┐
                 │  Contexto agroclimático   │  (se calcula 1 vez, §10.2–10.4)
                 │  ET0, balance, SPEI, GDD  │
                 └────────────┬─────────────┘
        ┌──────────────┬──────┴───────┬──────────────┐
        ▼              ▼              ▼              ▼
   F1 Rotación     F2 Sanidad     F3 Riego      F5 Catástrofes
        │              │              │              │
        └──────────────┴──────┬───────┴──────────────┘
                              ▼
                    IRS (§10.8) + Dashboard
                              ▲
                    F4 Mapa temporal (consume series)
```

**Regla de implementación:** F2, F3 y F5 **consumen** el contexto agroclimático; no vuelven a descargar datos ni recalculan ET0. Un solo módulo `climate_context` es la única puerta a los datos NASA.

---

## 6. Entradas del sistema

### 6.1 Formulario de entrada (contrato canónico)

El frontend envía un único objeto `FarmProfile` al crear la finca. Este objeto es el **contrato vinculante** entre UI y motor de cálculo.

```jsonc
{
  "name": "Finca El Olivar",                    // string, 1..80
  "location": {
    "lat": 37.3912,                              // -90..90, requerido
    "lon": -4.0231,                              // -180..180, requerido
    "elevation_m": 320,                          // opcional; si falta, NASADEM
    "admin": { "country": "ES", "region": "AN", "municipality": "Córdoba" } // opcional
  },
  "boundary": {                                  // GeoJSON Polygon | null
    "type": "Polygon",
    "coordinates": [[[-4.024,37.390],[-4.021,37.390],[-4.021,37.393],[-4.024,37.393],[-4.024,37.390]]]
  },
  "area_ha": 12.4,                               // si hay boundary se calcula; si no, input manual
  "current_crops": [                             // requerido, ≥1
    { "crop_id": "wheat_durum", "season": "2025-26", "area_ha": 8.0 },
    { "crop_id": "sunflower",   "season": "2026S",   "area_ha": 4.4 }
  ],
  "preferred_crops": ["chickpea", "barley"],     // opcional
  "excluded_crops": ["rice"],                    // opcional
  "resources": { /* §6.4 */ },
  "constraints": {
    "horizon_seasons": 8,                        // default 8 (§10.7.1)
    "seasons_per_year": 2,                       // 1 o 2
    "must_include": [],                          // crop_ids
    "max_crops": 4,                              // diversidad máxima
    "organic_only": false
  },
  "preferences": {
    "objective": "balanced",                     // production | resilience | water | balanced
    "risk_tolerance": "medium"                   // low | medium | high
  }
}
```

**Validación (obligatoria en backend, no solo en UI):**

| Regla | Error |
|---|---|
| `lat`/`lon` dentro de rango y no en océano (comprobación con Natural Earth o land mask) | `LOCATION_NOT_LAND` |
| `boundary` válido, no auto-intersectante, área entre 0,01 y 50 000 ha | `INVALID_BOUNDARY` |
| `current_crops` no vacío y `crop_id` existente en catálogo | `UNKNOWN_CROP` |
| Suma de `area_ha` de cultivos ≤ `area_ha` × 1,02 | `AREA_OVERFLOW` |
| `preferred_crops` ∩ `excluded_crops` = ∅ | `CONFLICTING_CROPS` |
| `horizon_seasons` ∈ [4, 12] | `INVALID_HORIZON` |
| Coordenadas con ≥ 10 años de datos POWER disponibles | `INSUFFICIENT_CLIMATE_DATA` |

### 6.2 Ubicación `[N]`

**Tres modos de entrada**, todos producen `lat/lon` + opcionalmente `boundary`:

1. **Buscar** por municipio/dirección (Nominatim/OSM, sin API key). El usuario coloca el pin.
2. **Mi ubicación** (Geolocation API del navegador), con permiso explícito.
3. **Dibujar** el polígono de la finca sobre el mapa (MapLibre `draw`), o subir GeoJSON/KML.

**Precisión:** se acepta el pin con redondeo a 4 decimales (≈11 m) para el cálculo y se guarda a 3 decimales (≈110 m) si el usuario no crea cuenta (privacidad, §14.5). El clima no cambia a esa escala, pero la privacidad sí importa.

### 6.3 Cultivos `[N]`

El apunte distingue tres orígenes. Se implementan como tres listas con semántica distinta:

| Campo | Origen `[N]` | Uso en el motor |
|---|---|---|
| `current_crops` | "los que tiene actualmente y desea optimizar" | **Baseline** obligatorio: la rotación actual se simula con el mismo motor y se compara siempre contra la propuesta. |
| `recommended_crops` | "los que recomienda la app" | **Salida**, no entrada. Se deriva del catálogo + filtro de viabilidad (§10.7.4) y se muestra como sugerencia; el usuario puede aceptarla. |
| `preferred_crops` | "los que tenga preferencia el usuario" | **Restricción blanda**: se priorizan en la función objetivo y en el desempate. |
| `excluded_crops` | (derivado de "preferencia") `[D]` | **Restricción dura**: nunca aparecen. |

**Selección en UI:** buscador con nombre común + científico, filtrado por viabilidad para la celda climática (los no viables aparecen deshabilitados con el motivo: "requiere 210 días libres de helada; tu zona tiene 165").

**Catálogo inicial:** ver D6. Esquema de parámetros por cultivo en el Anexo B.

### 6.4 Recursos y materiales `[N]`

El apunte dice "materiales y recursos de los que dispone el usuario", sin detallar. Se concreta en este esquema `[P]`:

```jsonc
"resources": {
  "water": {
    "source": "well",              // none | well | pond | canal | reservoir | municipal
    "available_m3_per_year": 9000, // null si no lo sabe
    "flow_l_s": 4.5,               // caudal disponible, null si no lo sabe
    "cost_eur_per_m3": 0.12,       // opcional
    "quality": "good"              // good | saline | unknown
  },
  "irrigation": {
    "existing_system": "none",     // none | drip | sprinkler | furrow | flood
    "condition": "n/a",            // good | fair | poor | n/a
    "energy": "grid",              // grid | diesel | solar | none
    "hours_per_day_available": 8
  },
  "machinery": ["tractor_90hp", "seeder", "plough", "sprayer"],
  "labor": { "permanent": 1, "seasonal": 2 },
  "budget_eur_per_year": 15000,    // null si no quiere declararlo
  "inputs": { "organic_matter": false, "compost_t_per_year": 0, "cover_crop_seed": false },
  "storage": { "capacity_t": 20, "dryer": false },
  "soil_tests": {                   // opcional: mejora la precisión
    "texture": null, "ph": null, "organic_matter_pct": null, "depth_cm": null
  }
}
```

**Regla:** todos los campos son opcionales salvo `water.source`. Ausencia de dato ⇒ el motor usa un valor por defecto declarado y **degrada la confianza** del resultado (§10.12), mostrando el aviso "resultado basado en supuestos: caudal asumido 3 L/s".

### 6.5 Qué NO se pide al usuario (para acotar el formulario)

No se pide: DNI, teléfono, email (salvo cuenta), coordenadas catastrales, datos bancarios, historial de rendimientos obligatorio. El formulario tiene **máximo 14 campos visibles** en el camino principal.

---

## 7. Datos: catálogo de fuentes NASA

### 7.1 Regla de selección

Solo se usa un producto si cumple las tres condiciones:

1. **Es de la NASA** (o derivado de un DAAC de la NASA). Los suplementos no-NASA solo pueden aportar *parámetros estáticos* (textura de suelo, coeficientes de cultivo), nunca la serie climática.
2. **Cubre la ubicación** de la finca.
3. **Tiene ≥ 20 años de serie** o se usa solo como validación/capa visual (se indica en la UI).

### 7.2 Tabla maestra de productos

Símbolos de acceso: 🟢 abierto sin registro · 🟡 requiere Earthdata Login (gratuito) · 🔵 requiere API key gratuita.

| # | Capa | Producto NASA | Variable(s) usada(s) | Resolución | Periodo | Acceso | Uso en ROOTSHIFT |
|---|---|---|---|---|---|---|---|
| D1 | **Meteorología base** | NASA POWER · Daily (`/api/temporal/daily/point`) | `T2M`, `T2M_MAX`, `T2M_MIN`, `T2MDEW`, `RH2M`, `PRECTOTCORR`, `WS2M`, `ALLSKY_SFC_SW_DWN`, `PS` | 0,5° (cuadrícula nativa) | 1981-01-01 → NRT | 🟢 | **Núcleo.** ET0, GDD, heladas, calor, lluvia, VPD |
| D2 | Meteorología horaria | NASA POWER · Hourly | `T2M`, `RH2M`, `PRECTOTCORR`, `T2MDEW` | 0,5° | 2001 → NRT | 🟢 | Duración de mojado foliar (F2), eventos extremos |
| D3 | Climatología | NASA POWER · Climatology | mismas + normales 30 años | 0,5° | 1991–2020 | 🟢 | Línea base y comparación "año normal" |
| D4 | **Humedad del suelo** | SMAP L4 `SPL4SMGP` v007 | `sm_surface`, `sm_rootzone` (0–100 cm) | 9 km, 3-horario | 2015-03-31 → hoy | 🟡 NSIDC | Inicialización del balance hídrico, percentil de sequía edáfica |
| D5 | Balance terrestre | GLDAS `Noah` 2.1 / `CLSM` 2.2 | humedad por capas, ET, escorrentía, nieve | 0,25°, 3-h/diario/mensual | 2000/2003 → hoy | 🟡 GES DISC | Contraste independiente del balance; escorrentía (inundación) |
| D6 | **Precipitación satelital** | GPM IMERG `GPM_3IMERGDF` V07 (Final/Early) | precipitación diaria | 0,1° | 1998-01 → hoy | 🟡 GES DISC | Extremos de lluvia, periodos de retorno, Rx1day/Rx5day |
| D7 | **Vegetación** | MODIS `MOD13Q1` v061 | NDVI, EVI (16 días) | 250 m | 2000-02 → hoy | 🟡 LP DAAC | VCI, proxy de rendimiento, capa F4 |
| D8 | Temperatura superficial | MODIS `MOD11A2` v061 | LST día/noche (8 días) | 1 km | 2000-02 → hoy | 🟡 LP DAAC | Estrés térmico observado, capa F4 |
| D9 | Cobertura del suelo | MODIS `MCD12Q1` v061 | tipo IGBP anual | 500 m | 2001 → hoy | 🟡 LP DAAC | Número de curva (escorrentía), factor C de erosión |
| D10 | Evapotranspiración | MODIS `MOD16A2` v061 | ET, PET (8 días) | 500 m | 2001 → hoy | 🟡 LP DAAC | Validación independiente de ETc |
| D11 | Alta resolución | HLS `HLSL30` + `HLSS30` v2.0 | reflectancia 30 m (NDVI, NDWI) | 30 m | 2013-04 / 2015-11 → hoy | 🟡 LP DAAC | Detalle intra-parcela, capa F4 zoom, verificación de superficie cultivada |
| D12 | Topografía | NASADEM (`NASADEM_HGT`) | elevación, pendiente, orientación | 30 m (1″) | estático | 🟡 LP DAAC | Corrección de presión, pendiente (riego, erosión) |
| D13 | Agua subterránea | GRACE / GRACE-FO mascons RL06 | anomalía de almacenamiento terrestre total | 0,25–0,5° (mascon) | 2002-04 → hoy | 🟡 PO.DAAC | Tendencia de acuífero (indicador de sostenibilidad, largo plazo) |
| D14 | Incendios | NASA FIRMS (MODIS/VIIRS) | detecciones de fuego activo | 375 m / 1 km | 2000/2012 → hoy | 🔵 MAP_KEY | Alerta F5, historial de fuego en el entorno |
| D15 | **Futuros climáticos** | NEX-GDDP-CMIP6 | `tasmin`, `tasmax`, `pr`, `hurs`, `rlds`, `rsds`, `sfcWind` (diario) | 0,25° | 1950–2100 | 🟢 (AWS Open Data) | Escenarios SSP1-2.6 / 2-4.5 / 3-7.0 / 5-8.5 (§10.6) |
| D16 | Evapotranspiración alta res. (opcional) | ECOSTRESS | ET, LST | ~70 m | 2018 → hoy (discontinuo) | 🟡 LP DAAC | Validación puntual; no apto para series |
| D17 | Maíz/trigo: mapa de cultivos (opcional) | NASA Harvest / WorldCereal | clase de cultivo | variable | variable | 🟢/🟡 | Verificación de `current_crops` (solo informativo) |

### 7.3 Suplementos no-NASA (solo parámetros estáticos)

| Parámetro | Fuente propuesta | Por qué no NASA | Estado |
|---|---|---|---|
| Textura, pH, materia orgánica del suelo | ISRIC SoilGrids 250 m | La NASA no distribuye cartografía de textura; SMAP mide humedad, no granulometría | **Requiere D2** |
| Coeficientes de cultivo (Kc), GDD, Ky | FAO-56 / FAO-33 (Allen et al. 1998; Doorenbos & Kassam 1979) | Parámetros agronómicos estándar, no observaciones | Aceptado como tabla de parámetros |
| Rendimiento potencial de referencia (Ym) | FAO/FAOSTAT o tabla propia validada | No hay producto NASA de rendimiento por cultivo | **Requiere D8** |
| Catálogo de enfermedades y umbrales | Literatura fitopatológica + extensión agraria | No existe dataset NASA de enfermedades | **Requiere D11** |

**Regla de oro:** si el jurado pregunta "¿esto es NASA?", la respuesta debe ser "la cadena clima–suelo–vegetación sí; los coeficientes agronómicos son parámetros estándar de FAO y literatura, declarados en la UI".

### 7.4 Límite de escala (declaración obligatoria en la UI)

| Dato | Resolución | Equivalente | Qué significa para una finca de 12 ha |
|---|---|---|---|
| POWER | 0,5° | ≈ 50 × 55 km | Toda la finca comparte un único valor climático; no distingue laderas |
| IMERG | 0,1° | ≈ 11 × 11 km | Puede haber diferencias de lluvia dentro de la comarca |
| SMAP | 9 km | ≈ 9 × 9 km | Humedad media de un mosaico de parcelas |
| MOD13Q1 | 250 m | ≈ 6 ha/píxel | 2–4 píxeles por finca: sirve para tendencia, no para manejo fino |
| HLS | 30 m | ≈ 0,09 ha/píxel | Escala de parcela real |
| NASADEM | 30 m | ≈ 0,09 ha/píxel | Pendiente utilizable para riego |

**Copy obligatorio** en el dashboard (una línea, discreta): *"El clima se representa a escala de comarca (≈50 km); la parcela entra por su polígono y por imágenes de 30 m cuando están disponibles."*

### 7.5 Atribución y licencias

- Los datos de la NASA son abiertos y gratuitos; se exige **atribución** y **no** sugerir aval de la NASA. En el pie de la app: *"Datos: NASA POWER, SMAP, GPM IMERG, MODIS, HLS, NASADEM, GRACE-FO, FIRMS, NEX-GDDP-CMIP6. ROOTSHIFT no está afiliado ni respaldado por la NASA."*
- Cada tarjeta de resultado lleva un badge con el producto usado (componente `<SourceBadge />`, §13.1).
- Las proyecciones NEX-GDDP-CMIP6 son escenarios, no predicciones: la UI debe decir "escenario SSP5-8.5 (alta emisión)" y nunca "clima futuro esperado".

---

## 8. Arquitectura de software

### 8.1 Vista de componentes

```
┌──────────────────────────────────────────────────────────────────────┐
│                        NAVEGADOR (Next.js 15, TS)                    │
│  Onboarding · Dashboard · F1 Rotación · F2 Sanidad · F3 Riego        │
│  F4 Mapa temporal · F5 Catástrofes                                   │
│  MapLibre GL JS + deck.gl · Recharts/visx · Tailwind + shadcn/ui     │
└───────────────┬──────────────────────────────────────────────────────┘
                │ HTTPS / JSON (REST) + SSE para progreso
┌───────────────▼──────────────────────────────────────────────────────┐
│                     API (FastAPI, Python 3.12)                       │
│  Routers: farms · context · rotation · diseases · irrigation         │
│           hazards · timeline · jobs · explain                        │
│  Validación Pydantic v2 · OpenAPI autogenerado · rate limit          │
└───────┬──────────────────────────┬───────────────────────┬───────────┘
        │                          │                       │
┌───────▼────────┐   ┌─────────────▼──────────┐  ┌─────────▼──────────┐
│  MOTOR DE      │   │  REPOSITORIOS          │  │  WORKER (RQ)       │
│  CÁLCULO       │   │  PostgreSQL 16         │  │  jobs largos:      │
│  (funciones    │   │  + PostGIS 3.4         │  │  optimización,     │
│   puras)       │   │  Redis (caché + cola)  │  │  ingesta, tiles    │
│  §10           │   │  MinIO (COG, Parquet)  │  │                    │
└───────┬────────┘   └────────────────────────┘  └─────────┬──────────┘
        │                                                   │
┌───────▼───────────────────────────────────────────────────▼──────────┐
│  CAPA DE PROVEEDORES (única puerta a internet)                       │
│  power_client · smap_client · imerg_client · modis_client ·          │
│  hls_client · nasadem_client · grace_client · firms_client ·         │
│  nexus_client  →  earthaccess / httpx / rioxarray / xarray           │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │  TiTiler (XYZ / COG)   │  capas F4
                    └────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  PIPELINE OFFLINE (CLI Python, ejecutable en CI)                     │
│  ingest → normalize (Parquet) → compute indicators → persist         │
│  → build demo fixtures (JSON) → snapshot tests                       │
└──────────────────────────────────────────────────────────────────────┘
```

### 8.2 Stack recomendado `[P]`

| Capa | Elección | Motivo |
|---|---|---|
| Frontend | **Next.js 15** (App Router) + TypeScript + Tailwind + shadcn/ui | Velocidad de hackathon, SSR, ecosistema de mapas |
| Mapas | **MapLibre GL JS** + **deck.gl** (`PolygonLayer`, `HeatmapLayer`) + `@mapbox/mapbox-gl-draw` | Sin API key, vectorial, buen rendimiento |
| Gráficos | **Recharts** (simple) + **visx** (abanicos/heatmaps) | Accesibles y rápidos de montar |
| API | **FastAPI** + Pydantic v2 | OpenAPI gratis, tipado, async |
| Ciencia | `numpy`, `pandas`, `xarray`, `rioxarray`, `scipy`, `geopandas`, `shapely`, `pyproj`, `netCDF4`, `pulp`/`ortools` | Estándar geo-científico |
| Auth datos | `earthaccess` | Gestiona Earthdata Login, tokens y reintentos |
| BD | **PostgreSQL 16 + PostGIS 3.4** | Geometrías, índices espaciales, JSONB |
| Caché/cola | **Redis 7** + **RQ** | Simple; Celery es overkill para el alcance |
| Ráster | **TiTiler** sobre COG | Tiles XYZ bajo demanda con recorte |
| Objetos | MinIO local (S3-compatible) | COG y Parquet |
| Contenedores | Docker Compose | Un `docker compose up` para todo |
| Tests | pytest + httpx + Playwright | Unitarios, contrato y E2E |

**Alternativa monolítica** (solo si el equipo es de 2 personas y no hay perfil Python): todo en Next.js con cálculos en TypeScript. Se pierde `xarray`/`netCDF`/MILP. Ver **D13**.

### 8.3 Estructura de carpetas (normativa)

```
rootshift/
├─ apps/
│  ├─ web/                     # Next.js
│  └─ api/
│     ├─ app/
│     │  ├─ main.py
│     │  ├─ routers/           # 1 archivo por recurso
│     │  ├─ schemas/           # Pydantic (contratos §11)
│     │  ├─ domain/            # ⚠️ FUNCIONES PURAS, sin I/O
│     │  │  ├─ climate.py
│     │  │  ├─ water_balance.py
│     │  │  ├─ drought.py
│     │  │  ├─ yield_model.py
│     │  │  ├─ rotation.py
│     │  │  ├─ resilience.py
│     │  │  ├─ disease.py
│     │  │  ├─ irrigation.py
│     │  │  └─ hazards.py
│     │  ├─ providers/         # clientes NASA (con caché y reintentos)
│     │  ├─ repositories/      # SQL
│     │  ├─ jobs/              # tareas RQ
│     │  └─ config/            # YAML de parámetros y pesos
│     └─ tests/
├─ pipeline/                   # CLI de ingesta y precomputo
├─ data/
│  ├─ catalog/                 # crops.yaml, diseases.yaml, hazards.yaml
│  ├─ fixtures/                # fincas demo precalculadas (modo offline)
│  └─ cache/                   # Parquet por celda (gitignored)
└─ docker-compose.yml
```

**Regla de dependencia:** `domain/` no importa nada de `providers/`, `repositories/`, `FastAPI` ni `httpx`. Si un test de `domain/` necesita red, el diseño está mal.

### 8.4 Flujo "generar finca" (secuencia)

```
UI                API                    Motor                  Proveedores
 │ POST /farms      │                       │                        │
 ├─────────────────►│ valida FarmProfile    │                        │
 │                  ├─ resuelve celda ──────────────────────────────►│ POWER (clima 30 a)
 │                  │                       │                        │
 │ 202 {job_id}     │◄──────────────────────┴────────────────────────┤
 │◄─────────────────┤                                              │
 │ GET /jobs/{id}   │  [worker]                                     │
 ├─────────────────►│  calcula contexto ────► climate/water/drought  │
 │   progreso SSE   │  filtra candidatos ───► viability             │
 │◄─────────────────┤  evalúa baseline ─────► yield_model           │
 │                  │  busca rotación ──────► rotation.search        │
 │                  │  simula escenarios ───► scenarios              │
 │                  │  calcula IRS ─────────► resilience             │
 │                  │  genera F2/F5 ────────► disease/hazards        │
 │  200 {artifacts} │  persiste + procedencia                        │
 │◄─────────────────┤                                               │
```

**Presupuesto de tiempo:** contexto desde caché < 400 ms; generación completa en frío < 45 s; recálculo de una rotación editada < 3 s (solo reutiliza el contexto).

### 8.5 Modos de ejecución

| Modo | Variable | Comportamiento |
|---|---|---|
| `live` | `DATA_MODE=live` | Descarga de NASA en tiempo real, con caché |
| `cached` | `DATA_MODE=cached` (default en demo) | Solo caché local; falla si no hay datos |
| `demo` | `DATA_MODE=demo` | Sirve `data/fixtures/*.json`; **cero red**; 3 fincas precalculadas |

El modo `demo` es **obligatorio** y debe funcionar sin internet: es el seguro de vida de la demo del hackathon.

---

## 9. Pipeline de datos

### 9.1 Etapas

1. **Resolución de celda.** `lat/lon` → celda POWER. Se guardan las coordenadas del centro devueltas por la propia API (`geometry.coordinates`), que son la referencia autoritativa de la cuadrícula. `climate_cell_id = "{lat_centro}_{lon_centro}"`.
2. **Descarga idempotente.** Cada request se registra en `data_fetch_log` con `(product, cell_id, start, end, params_hash)`. Si existe y está fresco, no se vuelve a pedir.
3. **Normalización.** Todo a un `xarray.Dataset` con `time` diario, sin huecos, fill values (`-999`, `-9999`) convertidos a `NaN`, unidades SI y nombres canónicos (`tmax_c`, `pr_mm`, `rh_pct`, `rs_mj_m2`, `ws2_ms`, `ps_kpa`, `tdew_c`).
4. **Control de calidad** (§9.5) → si falla, se marca la serie como `degraded` y se propaga a la confianza.
5. **Cálculo de indicadores** (§10) → tablas `indicator_daily`, `indicator_monthly`, `indicator_seasonal`.
6. **Persistencia de artefactos** con `model_version` y `params_hash`.
7. **Publicación de fixtures** para el modo `demo`.

### 9.2 Claves de caché y TTL

```python
cache_key = f"{product}:{cell_id}:{start}:{end}:{sha1(params)[:12]}:{product_version}"
```

| Producto | TTL | Motivo |
|---|---|---|
| POWER diario (histórico cerrado) | 365 días | No cambia |
| POWER diario (año en curso) | 7 días | NRT se reprocesa |
| IMERG Early | 1 día | Latencia ~4 h |
| IMERG Final | 90 días | Reprocesamiento |
| SMAP L4 | 2 días | Latencia ~2 días |
| MOD13Q1 / MOD11A2 / MOD16A2 | 30 días | Compuestos de 8–16 días |
| MCD12Q1 | 365 días | Anual |
| NASADEM | ∞ | Estático |
| NEX-GDDP-CMIP6 | ∞ | Estático |

### 9.3 Estrategia de rendimiento

- **Una sola petición por celda y producto**, nunca por parcela. Varias parcelas de la misma comarca comparten celda.
- **Serie cerrada precomputada:** 1991-01-01 → último año completo se calcula una vez y se guarda en Parquet (`data/cache/{cell_id}/daily.parquet`), ~12 800 filas × 12 columnas.
- **`numpy` vectorizado**, sin bucles por día en Python (excepto el balance hídrico, que es recursivo: usar `numba` o `numpy` con acumuladores; ver §10.3.4).
- **Precomputar los 12 escenarios base** por celda para no re-simular en cada visita.
- **Índices:** `GiST` en geometrías, `BTREE` en `(parcel_id, date)`.

### 9.4 Límites y cortesía con las APIs

- POWER: máx. **20 parámetros** por petición; si se piden más, dividir en lotes. **No repetir** la misma celda: POWER bloquea clientes que insisten.
- Añadir `User-Agent` identificable y `Referer` del proyecto.
- Reintentos con backoff exponencial (3 intentos, 2/4/8 s) solo en 429/500/502/503/504.
- `earthaccess.login(strategy="environment")` con `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD` en `.env`; nunca en el repo.
- Descargas GES DISC/LP DAAC: usar *subsetting* por bounding box (AppEEARS o `earthaccess` + `rioxarray.clip_box`), nunca bajar un tile completo de 1 GB.

### 9.5 Controles de calidad (bloqueantes)

| Check | Regla | Acción |
|---|---|---|
| Cobertura | ≥ 95 % de días con dato en el periodo pedido | Si < 95 % → `degraded` |
| Coherencia térmica | `T2M_MIN ≤ T2M ≤ T2M_MAX` | Corregir por clamp y registrar incidencia |
| Rangos físicos | `0 ≤ RH2M ≤ 100`, `PRECTOTCORR ≥ 0`, `WS2M ≥ 0` | `NaN` + incidencia |
| Fill values | `-999`, `-9999`, `-1e10` | `NaN` |
| Zona horaria | POWER devuelve **LST** por defecto | Fijar `time-standard=LST` y documentarlo (el día agrícola es solar) |
| Bisiestos | 29-feb presente | No colapsar el índice temporal |
| Duplicados | una fila por fecha | `drop_duplicates` + assert |
| Congelado de versión | `product_version` guardada | Impide mezclar v006 y v007 |

### 9.6 Matriz de precomputo

| Indicador | ¿Precomputado? | Cuándo se recalcula |
|---|---|---|
| ET0 diaria, GDD, heladas, VPD | Sí, por celda | Nunca (histórico) |
| Balance hídrico por cultivo | No | Al generar finca (depende de Kc y del cultivo) |
| SPI/SPEI 3/6/12 | Sí, por celda | Nunca |
| Percentiles de lluvia y periodos de retorno | Sí, por celda | Nunca |
| Escenarios históricos (S0–S5) | Sí, por celda | Nunca |
| Escenarios futuros (S6–S7) | Sí, por celda (deltas) | Al cambiar de SSP |
| Rotación óptima | No | Al generar o editar |
| Riesgo de enfermedad | No | Al generar (depende del cultivo) |
| Diseño de riego | No | Al generar (depende de recursos) |
| Tiles F4 | Sí, por capa+campaña | Al añadir fecha nueva |

---

## 10. Motor de cálculo

> Esta es la sección que convierte "usar datos de la NASA" en un sistema. Todas las fórmulas están cerradas y son implementables. Las marcadas `[P]` son propuestas parametrizables en `config/*.yaml`, no constantes en el código.

### 10.1 Convenciones de cálculo

| Elemento | Decisión |
|---|---|
| Paso temporal | Diario para clima y balance; mensual para índices de sequía; estacional para rendimiento |
| Periodo de referencia | **1991-01-01 → 2020-12-31** (30 años, estándar WMO) |
| Año hidrológico | Oct–Sep (hemisferio norte), Abr–Mar (hemisferio sur) |
| Año agrícola | Definido por el cultivo; por defecto campaña `S` = mar–sep, `W` = oct–feb |
| Tratamiento de `NaN` | Se interpola linealmente si el hueco es ≤ 7 días; si es mayor, se excluye del cálculo y se penaliza la confianza |
| Redondeo | Se calcula en `float64`, se presenta con 1–2 decimales según magnitud |
| Reproducibilidad | Semilla fija `SEED=42` en toda simulación Monte Carlo |
| Versionado | `MODEL_VERSION="1.0.0"`; cambiar una fórmula obliga a subir versión y a invalidar caché |

### 10.2 Indicadores meteorológicos base

#### 10.2.1 Evapotranspiración de referencia ET0 — FAO-56 Penman-Monteith

Entrada: `T2M_MAX`, `T2M_MIN`, `T2MDEW`, `WS2M`, `ALLSKY_SFC_SW_DWN` (Rs), `PS` (presión), `lat`, `elev`.

$$
ET_0=\frac{0.408\,\Delta\,(R_n-G)+\gamma\,\dfrac{900}{T+273}\,u_2\,(e_s-e_a)}{\Delta+\gamma\,(1+0.34\,u_2)}
$$

con:

$$
e^\circ(T)=0.6108\exp\!\left(\frac{17.27\,T}{T+237.3}\right),\quad
e_s=\frac{e^\circ(T_{max})+e^\circ(T_{min})}{2},\quad
e_a=e^\circ(T_{dew})
$$

$$
\Delta=\frac{4098\,e^\circ(T)}{(T+237.3)^2},\qquad
\gamma=0.000665\,P,\qquad T=\frac{T_{max}+T_{min}}{2}
$$

$$
R_{ns}=(1-\alpha)\,R_s,\ \alpha=0.23;\qquad
R_{nl}=\sigma\,\frac{(T_{max}+273.16)^4+(T_{min}+273.16)^4}{2}\,\bigl(0.34-0.14\sqrt{e_a}\bigr)\Bigl(1.35\tfrac{R_s}{R_{so}}-0.35\Bigr)
$$

$$
R_n=R_{ns}-R_{nl},\qquad R_{so}=(0.75+2\cdot10^{-5}z)\,R_a,\qquad G\approx 0
$$

$$
R_a=\frac{1440}{\pi}\,G_{sc}\,d_r\bigl[\omega_s\sin\varphi\sin\delta+\cos\varphi\cos\delta\sin\omega_s\bigr]
$$

$$
d_r=1+0.033\cos\!\Bigl(\tfrac{2\pi J}{365}\Bigr),\quad
\delta=0.409\sin\!\Bigl(\tfrac{2\pi J}{365}-1.39\Bigr),\quad
\omega_s=\arccos(-\tan\varphi\tan\delta)
$$

`σ = 4.903e-9 MJ K⁻⁴ m⁻² d⁻¹`, `Gsc = 0.0820 MJ m⁻² min⁻¹`, `J` = día juliano, `φ` = latitud en radianes, `z` = elevación (m), `u2 = WS2M` (POWER ya entrega viento a 2 m; **no** aplicar la corrección logarítmica de 10 m).

**Salida:** `et0_mm` diaria, `float64`, ≥ 0.
**Validación obligatoria:** reproducir los ejemplos numéricos de los anexos de FAO-56 (cap. 4) con tolerancia ±2 % y guardarlos como *golden test* (§16.2).
**Fallback:** si falta `ALLSKY_SFC_SW_DWN`, usar Hargreaves-Samani `ET0 = 0.0023 (T+17.8) √(Tmax−Tmin) Ra` y marcar `method="hargreaves"` en la procedencia.

#### 10.2.2 Grados día de crecimiento (GDD)

Versión acotada (recomendada, evita penalizar olas de calor):

$$
GDD_d=\max\!\Bigl(0,\ \frac{\min(T_{max},T_{opt})+T_{min}}{2}-T_{base}\Bigr)
$$

Acumulación desde siembra: `GDD_acum = Σ GDD_d` hasta alcanzar `gdd_to_maturity` del cultivo (Anexo B). Se usa para: fechas de siembra viables, ventanas fenológicas, modelo de enfermedades y sincronización con MOD13Q1.

#### 10.2.3 Heladas

| Indicador | Definición |
|---|---|
| `tmin_abs` | mínimo absoluto del periodo |
| `frost_days` | nº de días con `Tmin < 0 °C` (o `t_frost_crop` si el cultivo es sensible) |
| `last_frost_doy` | último día de primavera con `Tmin < 0`, por año |
| `first_frost_doy` | primer día de otoño con `Tmin < 0`, por año |
| `frost_free_days` | `first_frost_doy − last_frost_doy` (media de 30 años) |
| `p_frost_month[m]` | `P(Tmin < t_frost_crop)` empírica por mes |

Fecha con probabilidad del 50 % y del 10 % (para siembra temprana/tardía) calculada por interpolación de la distribución empírica de `last_frost_doy`.

#### 10.2.4 Estrés térmico y déficit de presión de vapor

$$
VPD_d = e_s - e_a \quad \text{[kPa]}
$$

$$
HSE=\sum_{d\in W_{flor}}\max\!\bigl(0,\ T_{max,d}-T_{crit}\bigr)\quad [\text{°C}\cdot d]
$$

donde `W_flor` es la ventana de floración (±15 días alrededor de la fecha media de floración del cultivo) y `T_crit` el umbral específico (Anexo B). `HSE` es la **exposición a estrés térmico** usada en §10.5.2.

Análogamente, `FSE = Σ max(0, T_crit_frost − T_min,d)` sobre la ventana sensible.

#### 10.2.5 Estadísticos de lluvia

Por estación y por mes: `P_total`, `p10/p50/p90` (percentiles empíricos sobre 30 años), `CV = σ/μ`, `n_días_lluvia`, `max_dry_spell` (máx. días consecutivos con `P < 1 mm`), `rx1day`, `rx5day`.

**Inicio de lluvias** `[P]` (útil para secano):

> Primer día `t` después del 1 de marzo (HN) tal que `Σ_{i=t}^{t+2} P_i ≥ 20 mm` **y** en los 20 días siguientes no hay un periodo de ≥ 7 días con `Σ P < 5 mm`.

#### 10.2.6 Aridez

$$
AI=\frac{P_{anual}}{PET_{anual}},\qquad PET_{anual}=\sum ET_0
$$

Clases UNEP: hiperárido `<0,03`, árido `0,03–0,2`, semiárido `0,2–0,5`, seco-subhúmedo `0,5–0,65`, subhúmedo `0,65–0,75`, húmedo `>0,75`. Se muestra como etiqueta de contexto ("semiárido, AI = 0,31").

### 10.3 Balance hídrico del suelo

#### 10.3.1 Modelo

Depósito de una capa (zona radicular), paso diario, método FAO-56:

$$
D_i=D_{i-1}-(P_i-RO_i)-I_i-CR_i+ET_{c,adj,i}+DP_i
$$

| Símbolo | Significado | Unidad |
|---|---|---|
| `D` | Agotamiento de agua en la zona radicular | mm |
| `P` | Precipitación | mm |
| `RO` | Escorrentía superficial | mm |
| `I` | Riego aplicado | mm |
| `CR` | Ascenso capilar | mm (0 si no hay dato) |
| `ETc,adj` | ET del cultivo ajustada por estrés | mm |
| `DP` | Percolación profunda | mm |

$$
ET_{c,adj}=K_s\,K_c\,ET_0,\qquad
TAW=1000\,(\theta_{FC}-\theta_{WP})\,Z_r,\qquad
RAW=p\,TAW
$$

$$
K_s=\begin{cases}
1 & D\le RAW\\[2pt]
\dfrac{TAW-D}{TAW-RAW} & D>RAW
\end{cases}
\qquad\text{con } K_s\in[0,1]
$$

- `Z_r` = profundidad radicular (m) del cultivo en la fase (Anexo B).
- `p` = fracción de agotamiento permisible (FAO-56 tabla 22; por defecto 0,5).
- Si `D_i < 0` → `DP_i = −D_i` y `D_i = 0`.
- Si `D_i > TAW` → `K_s = 0`, la ET se corta y se registra `severe_stress = True`.

#### 10.3.2 Inicialización con SMAP

Si existe `sm_rootzone` de SMAP para la fecha de inicio:

$$
D_0 = 1000\,Z_r\,\bigl(\theta_{FC}-\theta_{SMAP,0}\bigr)
$$

Si no, `D_0 = 0.5·TAW` (suelo a media capacidad) y se marca `init_assumed=true`.

> **Advertencia de escala:** SMAP es un valor de 9 km, no de parcela. Se usa para fijar el punto de partida, no para decidir riegos diarios.

#### 10.3.3 Escorrentía (número de curva)

$$
Q=\frac{(P-0.2S)^2}{P+0.8S},\qquad S=\frac{25400}{CN}-254\ \ [\text{mm}]
$$

`CN` de `MCD12Q1` (clase cropland) cruzado con grupo hidrológico del suelo (D2). Por defecto `CN=78` (cultivo en hilera, grupo B) y `RO=0` en pendientes < 2 % cuando no hay dato de suelo.

#### 10.3.4 Implementación (recursiva, eficiente)

El balance es una recursión; no vectorizar por día en Python puro. Implementación:

```python
def water_balance(p_mm, et0_mm, kc, zr, p_frac, taw_params, d0, irrigation=None, cn=78):
    """Una pasada numba/loop. Devuelve D[t], ETa[t], Ks[t], DP[t], stress_days."""
    # 12.800 iteraciones por cultivo y escenario: < 5 ms con numba
```

Aceptación: 30 años × 8 temporadas × 240 candidatos = 61 440 pasadas; cada una ~12 800 pasos ⇒ **no** se puede recalcular todo en cada request. Se resuelve con: (a) precomputar `ETc` por cultivo una vez, (b) simular solo el horizonte (8 temporadas) en vez de 30 años, (c) `numba` + paralelismo `joblib`.

### 10.4 Sequía e índices de estrés

#### 10.4.1 SPI — Índice de Precipitación Estandarizada

Para cada mes del calendario y cada escala `k ∈ {3, 6, 12}`:

1. Serie de totales móviles `P_k`.
2. Ajuste de una distribución **gamma** de 2 parámetros por máxima verosimilitud.
3. Probabilidad acumulada `F(x)` → cuantil de la normal estándar `z = Φ⁻¹(F(x))`.
4. Corrección de ceros (Wilks): `q = P(x=0)` empírica; `H(x) = q + (1−q)·F(x)`.

`SPI = z`. Escala de referencia:

| Valor | Categoría |
|---|---|
| ≥ 2,00 | Extremadamente húmedo |
| 1,50 … 1,99 | Muy húmedo |
| 1,00 … 1,49 | Moderadamente húmedo |
| −0,99 … 0,99 | Normal |
| −1,49 … −1,00 | Sequía moderada |
| −1,99 … −1,50 | Sequía severa |
| ≤ −2,00 | Sequía extrema |

#### 10.4.2 SPEI — Índice de Precipitación-Evapotranspiración Estandarizada

$$
D_m=P_m-PET_m \quad\text{(mensual, con } PET_m=\sum_{d\in m} ET_{0,d}\text{)}
$$

Misma metodología que SPI pero ajustando una distribución **log-logística de 3 parámetros** por L-momentos, y estandarizando a normal. Justificación: `D_m` puede ser negativo; la gamma no sirve. Usar la ET0 de Penman-Monteith (no Thornthwaite) porque POWER ya provee la radiación y el viento.

#### 10.4.3 VCI — Índice de Condición de la Vegetación (MODIS)

$$
VCI=100\cdot\frac{NDVI-NDVI_{min}}{NDVI_{max}-NDVI_{min}}
$$

`NDVI_min` y `NDVI_max` por píxel y por periodo (16 días) sobre 2001–2020. `VCI < 35` = estrés vegetativo; `< 15` = sequía severa. Se usa como **evidencia observada** complementaria, nunca como sustituto del balance.

#### 10.4.4 Otros indicadores de sequía

| Indicador | Definición | Uso |
|---|---|---|
| `cdd_max` | Máx. días consecutivos con `P < 1 mm` | Sequía meteorológica |
| `sm_pct` | Percentil de `sm_rootzone` SMAP frente a 2015–2024 | Sequía edáfica observada |
| `gws_trend` | Pendiente de Sen de la anomalía GRACE (cm/año) | Sostenibilidad de acuífero |
| `drought_freq` | `P(SPEI12 < −1)` sobre 30 años | Riesgo estructural |
| `drought_trend` | Mann-Kendall + Sen sobre SPEI12 anual | ¿Empeora? |

### 10.5 Producción y rendimiento

> **Regla:** el motor NO afirma rendimientos reales. Calcula un **rendimiento relativo simulado** (0–1) y lo multiplica por un rendimiento potencial **declarado como supuesto**.

#### 10.5.1 Modelo agua-rendimiento (FAO-33)

$$
1-\frac{Y_a}{Y_m}=K_y\Bigl(1-\frac{ET_a}{ET_m}\Bigr)
\quad\Longrightarrow\quad
Y_{rel,agua}=1-K_y\Bigl(1-\frac{ET_a}{ET_m}\Bigr)
$$

- `ETa` = Σ `ETc,adj` de la temporada (mm) — viene del balance (§10.3).
- `ETm` = Σ `Kc·ET0` de la temporada (mm) — demanda sin estrés.
- `Ky` = factor de respuesta del cultivo a la sequía (Anexo B). `Ky > 1` = cultivo muy sensible.
- Clamp: `Y_rel,agua ∈ [0, 1]`.

#### 10.5.2 Factores de estrés térmico y helada

$$
f_{heat}=1-k_h\min\!\Bigl(1,\frac{HSE}{HSE_{ref}}\Bigr)\ \ge 0.5,\qquad
f_{frost}=1-k_f\min\!\Bigl(1,\frac{FSE}{FSE_{ref}}\Bigr)\ \ge 0.3
$$

Valores por defecto `[P]`: `k_h = 0.5`, `k_f = 0.7`; `HSE_ref` y `FSE_ref` por cultivo en `crops.yaml` (p. ej. maíz: `HSE_ref = 60 °C·d`, `FSE_ref = 25 °C·d`).

#### 10.5.3 Rendimiento simulado de la temporada

$$
Y_{sim}=Y_m\cdot Y_{rel,agua}\cdot f_{heat}\cdot f_{frost}\cdot f_{suelo}
$$

`f_suelo ∈ [0,1]` `[P]`: penalización por rotación (ver §10.7.5), no por fertilidad medida (no hay dato). `Y_m` = rendimiento potencial de referencia (t/ha), **supuesto declarado** (D8).

#### 10.5.4 Proxy satelital (evidencia, no predicción)

Para temporadas pasadas con MOD13Q1:

$$
iNDVI=\sum_{t\in temporada} NDVI_t,\qquad
z=\frac{iNDVI-\mu_{2001-2020}}{\sigma_{2001-2020}},\qquad
anomaly_{rel}\approx \beta\,z
$$

`β` por defecto `0.15` `[P]`, calibrable si hay rendimientos declarados. **Uso permitido:** mostrar "la campaña 2023 fue un 18 % por debajo de la media en vigor vegetal", y validar que el modelo reproduce la dirección de las anomalías. **Uso prohibido:** extrapolar `anomaly_rel` a escenarios futuros.

#### 10.5.5 Producción agregada

$$
P_{anual}=\sum_{s\in año} A_s\cdot Y_{sim,s}\quad [\text{t}]
$$

donde `A_s` = superficie de la parcela asignada al cultivo de la temporada `s`. En F1 el reparto de superficie lo decide el optimizador (§10.7.2).

### 10.6 Escenarios y simulación

#### 10.6.1 Principio

Un **escenario** es un conjunto de años meteorológicos coherentes, no un año concreto. Una rotación se evalúa sobre `S` escenarios (por defecto `S = 1000`), cada uno formado por `N` temporadas.

**Números aleatorios comunes:** todos los candidatos se evalúan sobre **el mismo conjunto de escenarios** (`seed` fijo). Sin esto, la comparación entre rotaciones es ruido.

#### 10.6.2 Catálogo de escenarios `[P]`

| ID | Nombre | Construcción | Para qué |
|---|---|---|---|
| **S0** | Histórico | Remuestreo bootstrap de años completos 1991–2020 | Línea base realista |
| **S1** | Sequía severa | Años con `SPEI12 ≤ −1,5`, muestreados con reemplazo | "¿Y si llega un año como 2005?" |
| **S2** | Sequía multianual | Bloques de 3 años consecutivos del quintil más seco | "¿Y si son tres años malos seguidos?" |
| **S3** | Ola de calor en floración | Serie S0 con `+ΔT` sobre `W_flor` (`ΔT ∈ {3, 5} °C`) | Estrés térmico |
| **S4** | Lluvia extrema | Serie S0 con eventos `Rx1day` amplificados `×1,5` | Inundación, erosión, enfermedades fúngicas |
| **S5** | Helada tardía | Serie S0 con la última helada desplazada `+14` días | Frutales, cereales de invierno |
| **S6** | Futuro próximo | Deltas NEX-GDDP-CMIP6 2031–2050, **SSP2-4.5** | Escenario intermedio |
| **S7** | Futuro alto | Deltas NEX-GDDP-CMIP6 2031–2050, **SSP5-8.5** | Escenario extremo |

#### 10.6.3 Método de deltas para el futuro (change-factor)

Para cada GCM y cada mes `m` del año:

$$
\Delta T_{max,m}=\overline{T_{max,m}}^{GCM}_{2050s}-\overline{T_{max,m}}^{GCM}_{1991-2020},\qquad
r_{P,m}=\frac{\overline{P_m}^{GCM}_{2050s}}{\overline{P_m}^{GCM}_{1991-2020}}
$$

$$
T'_{max,d}=T_{max,d}+\Delta T_{max,m(d)},\qquad P'_d=P_d\cdot r_{P,m(d)}
$$

- Regriddear el GCM (0,25°) a la celda POWER (0,5°) por vecino más próximo.
- Usar **≥ 5 GCMs** y tratar la dispersión entre modelos como incertidumbre estructural: el resultado se presenta como "mediana del ensamble + rango entre modelos".
- Si `r_P` excede `[0,2, 5]`, recortar y avisar (indicador de que el GCM no es fiable en esa celda).
- **No** se aplica corrección de sesgo adicional: NEX-GDDP-CMIP6 ya está corregido (BCSD). Documentarlo.

#### 10.6.4 Métricas de salida de la simulación

| Métrica | Fórmula | Interpretación |
|---|---|---|
| `E[P]` | media de producción anual | Producción esperada |
| `P10 / P50 / P90` | percentiles | Abanico de incertidumbre |
| `CV` | `σ/μ` | Inestabilidad |
| `CVaR10` | media del 10 % peor | "Producción en el mal año" |
| `P_fallo` | `P(Y_s < 0,6·Y_m)` | Probabilidad de cosecha inaceptable |
| `años_sobre_umbral` | `P(Y ≥ 0,7·Y_pot)` | Fiabilidad productiva |
| `T_recuperación` | años hasta volver a `≥0,9·Y_pot` tras el peor escenario | **"el mayor tiempo posible"** `[N]` |
| `P_sequia_3a` | `P(3 años consecutivos < 0,7·Y_pot)` | Robustez estructural |

El par `E[P]` + `P_fallo` es el que responde literalmente al objetivo del usuario: **máxima producción durante el mayor tiempo posible** `[N]`.

### 10.7 Motor de rotación (F1)

#### 10.7.1 Representación

Una rotación es una secuencia `r = (c_1, …, c_N)` con `c_k ∈ C ∪ {fallow}`, donde `N = horizon_seasons` (por defecto 8 = 4 años × 2 temporadas) y `C` es el conjunto de cultivos candidatos de la parcela.

Cada temporada `k` tiene:

```jsonc
{ "index": 1, "season": "2026S", "crop_id": "sunflower",
  "area_ha": 4.4, "window": { "sow_doy": 75, "harvest_doy": 240 } }
```

**Cultivos perennes** (olivo, vid, almendro, frutales): **no rotan**. Se modelan como *bloques fijos* que ocupan su superficie durante todo el horizonte; la optimización se aplica solo a la superficie rotativa. Si el 100 % de la finca es perenne, F1 muestra "no hay superficie rotativa: se evalúan prácticas de cobertura y diversificación" y deriva a F3/F5.

#### 10.7.2 Variables de decisión

| Variable | Tipo | Descripción |
|---|---|---|
| `x[c,k]` | binaria | cultivo `c` en temporada `k` |
| `a[c,k]` | continua | superficie asignada (ha) |
| `s[k]` | binaria | barbecho en temporada `k` |

Restricciones de superficie: `Σ_c a[c,k] + a_fallow[k] = A_rotativa` para toda `k`.

#### 10.7.3 Restricciones duras (si se violan, la rotación es inválida)

| ID | Restricción | Parámetro | Fundamento |
|---|---|---|---|
| **R1** | Un cultivo (o barbecho) por temporada | — | Coherencia física |
| **R2** | Misma **familia botánica** no puede repetirse con menos de `g` temporadas de separación | `g = 2` (⇒ vuelve cada 3) | Romper ciclo de patógenos y plagas |
| **R3** | Misma **especie** nunca en temporadas consecutivas | — | Suelo, nematodos, malezas |
| **R4** | Al menos una **leguminosa** cada `f` temporadas, si existe alguna viable | `f = 3` | Fijación de N, ruptura de ciclo |
| **R5** | Demanda hídrica de cada temporada ≤ oferta disponible | `η_agua = 0,9` | No proponer lo imposible |
| **R6** | Los cultivos de `must_include` aparecen al menos una vez | — | Preferencia explícita |
| **R7** | Los cultivos de `excluded_crops` no aparecen nunca | — | Preferencia explícita |
| **R8** | Nº de especies distintas ≤ `max_crops` | `4` | Operabilidad real |
| **R9** | La temporada admite el ciclo del cultivo (GDD y ventana libre de heladas) | Anexo B | Viabilidad agroclimática |
| **R10** | Si el riesgo de erosión es alto, el barbecho debe llevar cubierta | `RUSLE > 15 t/ha/año` | Sostenibilidad del suelo |

**R5 en detalle:**

$$
NIR_{k}=\sum_{d\in k}\max\bigl(0,\ K_c\,ET_{0,d}-P_{ef,d}\bigr)
\ \le\ \eta_{agua}\cdot\bigl(V_{riego,k}+V_{lluvia,util,k}\bigr)
$$

donde `P_ef` es la lluvia efectiva (§10.10.2). Se evalúa sobre el **percentil 80** de los escenarios (no sobre la media): una rotación que solo funciona en años húmedos es inválida.

#### 10.7.4 Filtro de viabilidad (generación de candidatos)

Antes de optimizar, `C` se construye así:

```python
C = []
for crop in catalog:
    if crop.id in excluded: continue
    if not soil_compatible(crop, soil): continue          # pH, textura, profundidad
    if not climate_compatible(crop, cell): continue        # GDD y heladas
    if not water_feasible(crop, cell, resources): continue # R5 individual
    if not machinery_compatible(crop, resources): continue # si hay restricción
    C.append(crop)
```

- `climate_compatible`: `GDD_disponible ≥ 0,9·gdd_to_maturity` **y** `P(helada en ventana sensible) ≤ 0,3`.
- `water_feasible`: `NIR_crop,p80 ≤ 0,9·(V_riego + V_lluvia_util)`.
- Los cultivos descartados **se muestran** con su motivo: "girasol: requiere 2 100 °C·d; tu comarca ofrece 1 780". Esto es valor de producto, no ruido: enseña por qué no se propone.

Si `|C| < 2` → error de negocio `NO_VIABLE_ROTATION` con recomendación de relajar restricciones (p. ej. permitir riego).

#### 10.7.5 Efecto de la rotación sobre el rendimiento (`f_suelo`)

`f_suelo` no es fertilidad medida (no hay dato). Es un **multiplicador agronómico declarado** `[P]`, tabulado por par (predecesor, sucesor):

| Predecesor → sucesor | `f_suelo` | Razón |
|---|---|---|
| Leguminosa → cereal | **1,10** | N fijado, mejor estructura |
| Cereal → leguminosa | 1,00 | Neutro |
| Cereal → cereal (misma especie) | 0,80 | Prohibido por R3, pero se puntúa si el usuario fuerza |
| Misma familia | 0,75 | Prohibido por R2 |
| Barbecho → cualquier | 1,05 | Recarga hídrica |
| Cultivo de cobertura → cualquiera | 1,05 | Materia orgánica, erosión |
| Girasol → cereal | 1,00 | Neutro (girasol es buen predecesor) |
| Remolacha/patata → cereal | 1,05 | Laboreo profundo |

Tabla completa en `config/rotation_effects.yaml`, editable sin tocar código. **Se declara en la UI** como "supuesto agronómico" en el tooltip del resultado.

#### 10.7.6 Función objetivo

$$
J=w_P\,\hat{P}_{norm}+w_R\,IRS_{norm}+w_W\,(1-W_{norm})+w_D\,D_{norm}-w_F\,P_{fallo}-w_C\,CV
$$

con pesos según la preferencia del usuario:

| `preferences.objective` | `w_P` | `w_R` | `w_W` | `w_D` | `w_F` | `w_C` |
|---|---|---|---|---|---|---|
| `production` | 0,45 | 0,15 | 0,10 | 0,10 | 0,15 | 0,05 |
| `balanced` (default) | 0,25 | 0,25 | 0,15 | 0,10 | 0,15 | 0,10 |
| `resilience` | 0,15 | 0,40 | 0,15 | 0,10 | 0,15 | 0,05 |
| `water` | 0,15 | 0,20 | 0,40 | 0,10 | 0,10 | 0,05 |

`risk_tolerance` modula `w_F`: `low` ×1,5 · `medium` ×1 · `high` ×0,6.

Todas las magnitudes se normalizan a `[0,1]` con min–max **sobre el conjunto de candidatos evaluados**, no sobre valores absolutos (así el índice es comparativo, que es lo que el usuario necesita para decidir).

#### 10.7.7 Algoritmo de búsqueda

`C^N` es inabordable (10⁸). Estrategia en tres etapas:

**Etapa A — precomputo aditivo (exacto y rápido)**

Si se acepta que el rendimiento de una temporada depende solo del cultivo y de su predecesor inmediato, la secuencia es una **cadena de Markov** y el óptimo se obtiene por programación dinámica:

```python
# Precomputado: Y[c, k, e] = rendimiento de c en temporada k bajo escenario e
#               M[cp, c]   = efecto de rotación (f_suelo), ver §10.7.5
# Estado: (último cultivo, escenario) -> mejor producción acumulada
best = {(c, e): Y[c, 0, e] * M[None, c] for c in C for e in range(S)}
for k in range(1, N):
    nxt = {}
    for c in C:
        for e in range(S):
            nxt[(c, e)] = max(best[(cp, e)] + Y[c, k, e] * M[cp, c] for cp in C)
    best = nxt
# Reconstrucción: k-best DP para recuperar las K = 20 mejores secuencias
```

Coste: `O(N · C² · S)` = 8 · 100 · 1000 = **800 000 operaciones** por parcela. Instantáneo. Devuelve las `K = 20` mejores secuencias bajo el surrogate aditivo.

**Etapa B — evaluación completa (Monte Carlo)**

Las 20 secuencias se evalúan con el modelo completo (balance hídrico, `f_heat`, `f_frost`, IRS, `P_fallo`, `CV`, `T_recuperación`) sobre los `S = 1000` escenarios. Vectorizado por lotes de 50 secuencias. Coste objetivo: < 5 s.

**Etapa C — búsqueda local**

Sobre las 5 mejores: `swap` de dos temporadas e `insert` de un cultivo, 2 rondas, aceptando solo mejoras (hill climbing). Coste: < 2 s.

**Alternativa exacta (opcional, D4):** formular el problema de asignación de superficie como MILP con `PuLP`/`OR-Tools` CP-SAT, dejando la secuencia a la etapa A. Solo si el equipo quiere defender "optimo global" ante el jurado.

**Pseudocódigo completo:** `domain/rotation.py::search_rotation(profile, context, scenarios) -> RotationResult`.

#### 10.7.8 Salida y generación de explicaciones

Toda rotación devuelve, además de la secuencia, **el "por qué"** en forma de lista de hallazgos verificables. El generador es **determinista** (plantillas + reglas), no un LLM (ver D15):

```jsonc
{
  "rotation_id": "rot_8f3a",
  "sequence": [ { "k": 1, "season": "2026S", "crop_id": "chickpea", "area_ha": 4.4 }, ... ],
  "metrics": { "expected_production_t": 38.2, "p10_t": 24.1, "p90_t": 45.0,
               "cv": 0.18, "p_failure": 0.09, "recovery_years": 1.4, "irs": 71 },
  "baseline": { "rotation_id": "rot_current", "metrics": { ... } },
  "delta_vs_baseline": { "production_pct": +14.2, "p_failure_delta": -0.11, "irs_delta": +19 },
  "findings": [
    { "code": "WATER_GAP_COVERED", "severity": "positive",
      "text": "La rotación propuesta reduce la demanda de agua en julio un 22 % frente a la actual, porque sustituye maíz por garbanzo.",
      "evidence": { "indicator": "nir_july_mm", "current": 118, "proposed": 92 } },
    { "code": "LEGUME_BREAK", "severity": "positive",
      "text": "Introduce una leguminosa cada 3 temporadas, lo que rompe el ciclo de enfermedades del cereal.",
      "evidence": { "rule": "R4", "value": 3 } },
    { "code": "DROUGHT_SENSITIVITY", "severity": "warning",
      "text": "En el escenario S2 (tres años secos), la producción cae un 34 %; la rotación actual cae un 41 %.",
      "evidence": { "scenario": "S2", "proposed": 0.66, "current": 0.59 } }
  ],
  "provenance": [ /* §10.12 */ ]
}
```

Códigos de hallazgo obligatorios como mínimo: `WATER_GAP_COVERED`, `LEGUME_BREAK`, `FAMILY_BREAK`, `DROUGHT_SENSITIVITY`, `HEAT_EXPOSURE`, `FROST_RISK`, `DISEASE_PRESSURE`, `EROSION_REDUCED`, `DIVERSITY_UP`, `DIVERSITY_DOWN`.

#### 10.7.9 Aviso de alcance del optimizador

La UI debe mostrar: *"Rotación optimizada para tus datos y restricciones. No sustituye el criterio de un técnico ni garantiza resultados: los rendimientos son simulados."* Sin esta frase, el producto miente.

### 10.8 Índice de Resiliencia ROOTSHIFT (IRS)

> **Declaración obligatoria:** el IRS es un **índice compuesto propio**, construido para este producto. **No es un estándar científico** ni un indicador validado por la NASA. La UI lo dice en el tooltip.

#### 10.8.1 Subíndices (todos 0–100)

**1. `I_agua` — garantía hídrica (peso 0,25)**

$$
I_{agua}=100\cdot\frac{1}{N}\sum_{k=1}^{N}\min\!\Bigl(1,\ \frac{V_{disponible,k}}{NIR_{k,p80}}\Bigr)
$$

**2. `I_estabilidad` — estabilidad productiva (peso 0,20)**

$$
I_{est}=100\cdot\bigl(1-\min(1,\tfrac{CV}{0,5})\bigr)\cdot(1-P_{fallo})
$$

**3. `I_suelo` — salud del suelo (peso 0,20)**

$$
I_{suelo}=100\cdot\bigl(0{,}35\,d_{rot}+0{,}25\,d_{leg}+0{,}20\,d_{cub}+0{,}20\,d_{eros}\bigr)
$$

| Componente | Definición |
|---|---|
| `d_rot` | `1 − max_familia(nº temporadas de la misma familia)/N` |
| `d_leg` | `min(1, nº leguminosas / ceil(N/3))` |
| `d_cub` | fracción de barbechos con cubierta vegetal |
| `d_eros` | `1 − min(1, erosión_estimada / 15 t·ha⁻¹·año⁻¹)` |

**4. `I_diversidad` — diversidad de cultivos (peso 0,15)**

$$
I_{div}=100\cdot\frac{H}{\ln(S_{max})},\qquad H=-\sum_c p_c\ln p_c,\quad p_c=\frac{a_c}{A}
$$

`S_max = max_crops` (4 por defecto). Es el índice de Shannon normalizado.

**5. `I_sanidad` — presión de enfermedades (peso 0,10)**

$$
I_{san}=100-\overline{FI}
$$

`FI` = índice de favorabilidad medio de las enfermedades relevantes del catálogo para esa rotación (§10.9). Es un índice de **presión**, no de daño real.

**6. `I_catastrofe` — exposición a peligros (peso 0,10)**

$$
I_{cat}=100\cdot\Bigl(1-\min\bigl(1,\ \sum_h p_h\cdot l_h\bigr)\Bigr)
$$

`p_h` = probabilidad anual del peligro `h` (periodo de retorno); `l_h` = pérdida esperada relativa (0–1) según el calendario de exposición del cultivo.

#### 10.8.2 Índice final

$$
IRS=\sum_i w_i\,I_i \qquad \sum_i w_i=1
$$

| Subíndice | Peso |
|---|---|
| `I_agua` | 0,25 |
| `I_estabilidad` | 0,20 |
| `I_suelo` | 0,20 |
| `I_diversidad` | 0,15 |
| `I_sanidad` | 0,10 |
| `I_catastrofe` | 0,10 |

Pesos en `config/scoring.yaml`, **no** en el código. Cualquier cambio de pesos invalida la caché (`params_hash`).

#### 10.8.3 Interpretación (copy exacto)

| Rango | Etiqueta | Frase |
|---|---|---|
| 80–100 | Muy resiliente | "Resiste bien varios futuros climáticos con los datos disponibles." |
| 60–79 | Resiliente | "Resiste en la mayoría de escenarios; hay margen de mejora en agua o diversidad." |
| 40–59 | Vulnerable | "Funciona en años normales; pierde producción en años malos." |
| 20–39 | Muy vulnerable | "Alta probabilidad de fallo en sequía o calor extremo." |
| 0–19 | Crítico | "El sistema actual no es sostenible bajo los escenarios evaluados." |

#### 10.8.4 Descomposición visible

Siempre se muestra el desglose con la contribución de cada subíndice (`w_i · I_i`), en barras apiladas. Sin desglose, el número es un oráculo; con desglose, es una herramienta.

### 10.9 Motor de enfermedades (F2)

#### 10.9.1 Qué calcula (y qué no)

Calcula **favorabilidad climática** para que una enfermedad concreta progrese en un cultivo concreto, en una ventana concreta. **No** detecta la enfermedad, no diagnostica, no cuenta inóculo real, no estima pérdida económica `[D]`.

#### 10.9.2 Duración de mojado foliar (LWD)

**Preferido (POWER horario, D2):**

$$
LWD_d=\#\{h:\ RH_{2m,h}\ge 90\ \%\ \lor\ (T_h-T_{dew,h})\le 2\ ^\circ C\ \lor\ P_h>0\}
$$

**Aproximación diaria (fallback, `[P]`, marcar `lwd_method="approx"`):**

$$
LWD_d\approx 12\cdot\mathbb{1}[RH_{2m}\ge 85\ \%]\cdot\mathbb{1}[T_{min}-T_{dew}\le 2\ ^\circ C]+2\cdot\mathbb{1}[P_d>1]
$$

La aproximación subestima el rocío en noches de cielo claro; por eso la confianza baja a "media" automáticamente.

#### 10.9.3 Favorabilidad diaria

$$
g_T=\text{trapecio}(T_{med};\ T_{min}^{dis},\ T_{opt,lo},\ T_{opt,hi},\ T_{max}^{dis})\in[0,1]
$$

$$
g_W=\min\!\Bigl(1,\ \frac{LWD_d}{LWD_{req}}\Bigr),\qquad
g_I=\begin{cases}1{,}00&\text{huésped en la parcela los 12 meses previos}\\0{,}60&\text{huésped en el entorno (500 m)}\\0{,}30&\text{sin huésped conocido}\end{cases}
$$

$$
FI_d=g_T\cdot g_W\cdot g_I
$$

#### 10.9.4 Agregación estacional

$$
FI=100\cdot\bigl(1-e^{-\lambda\sum_{d\in ventana}FI_d}\bigr),\qquad \lambda=0{,}03
$$

`λ` calibrado `[P]` para que ~60 días favorables den ≈ 83/100. `ventana` = periodo de susceptibilidad del cultivo (según fenología, Anexo B).

| `FI` | Nivel | Color UI |
|---|---|---|
| 0–24 | Bajo | verde |
| 25–49 | Medio | amarillo |
| 50–74 | Alto | naranja |
| 75–100 | Muy alto | rojo |

#### 10.9.5 Catálogo (esquema)

```yaml
# data/catalog/diseases.yaml
- id: septoria_tritici
  name: "Septoriosis del trigo (Septoria tritici)"
  pathogen: "Zymoseptoria tritici"
  crops: [wheat_durum, wheat_bread]
  cardinal_temp: { min: 5, opt_lo: 15, opt_hi: 20, max: 25 }   # °C
  wetness_hours_required: 16
  susceptible_stages: [tillering, stem_elongation, heading]
  inoculum_sources: [crop_residue, volunteer_cereals]
  actions:
    cultural: ["Rotar con cultivo no cerealícola ≥ 2 temporadas",
               "Enterrar el rastrojo", "Elegir variedad de ciclo tardío"]
    monitoring: ["Vigilar desde el estado de 2 nudos si hay lluvia > 10 mm"]
    chemical: ["Consultar etiqueta y asesor técnico; no se prescribe dosis"]
  severity_weight: 0.8
  confidence: "media"
```

**Valores de partida `[P]`** (deben validarse con un ingeniero agrónomo antes de la demo; D11):

| Cultivo | Enfermedad | T min | T ópt. | T máx | Horas mojado | Peso |
|---|---|---|---|---|---|---|
| Trigo duro | Septoriosis (*Z. tritici*) | 5 | 15–20 | 25 | 16 | 0,8 |
| Trigo duro | Roya amarilla (*P. striiformis*) | 2 | 9–15 | 23 | 4 | 0,7 |
| Trigo duro | Oidio (*B. graminis*) | 5 | 15–22 | 30 | 6 | 0,5 |
| Cebada | Rincosporiosis (*R. secalis*) | 5 | 15–20 | 25 | 12 | 0,7 |
| Maíz | Helmintosporiosis (*E. turcicum*) | 18 | 20–25 | 30 | 8 | 0,6 |
| Girasol | Mildiu (*P. halstedii*) | 10 | 18–22 | 28 | 12 | 0,7 |
| Garbanzo | Rabia (*A. rabiei*) | 10 | 20–25 | 30 | 8 | 0,8 |
| Vid | Mildiu (*P. viticola*) | 10 | 20–25 | 30 | 4 | 0,9 |
| Vid | Oidio (*E. necator*) | 15 | 20–27 | 32 | 4 | 0,8 |
| Olivo | Repilo (*V. oleaginea*) | 5 | 10–20 | 25 | 12 | 0,7 |
| Tomate | Mildiu (*P. infestans*) | 10 | 15–20 | 25 | 4 | 0,9 |
| Remolacha | Cercosporiosis (*C. beticola*) | 10 | 20–27 | 32 | 8 | 0,7 |

#### 10.9.6 Salida

```jsonc
{
  "crop_id": "wheat_durum",
  "diseases": [
    { "disease_id": "septoria_tritici", "name": "Septoriosis del trigo",
      "risk_index": 63, "level": "alto",
      "window": { "from": "2026-04-10", "to": "2026-06-05" },
      "drivers": ["16 días con mojado foliar > 14 h", "T media 17 °C", "rastrojo de trigo presente"],
      "actions": { "cultural": [...], "monitoring": [...], "chemical": [...] },
      "confidence": "media" }
  ],
  "caveats": ["Estimación basada en clima de comarca; el inóculo real no se mide."]
}
```

**Reglas de UI obligatorias:**

- El panel se titula **"Riesgo de enfermedades"**, nunca "Enfermedades detectadas".
- Acción química siempre acompañada de: *"No se prescriben productos ni dosis. Consulte la etiqueta y a un asesor."*
- Cada riesgo muestra su ventana de tiempo y sus 2–3 factores desencadenantes (trazabilidad).

### 10.10 Motor de riego (F3)

#### 10.10.1 Principio

No diseña una instalación ejecutable; produce una **recomendación indicativa** con cantidades, calendario y mapa de zonas, más un descargo: *"Diseño orientativo. Requiere proyecto técnico para ejecución."*

#### 10.10.2 Necesidad neta de riego

$$
ET_{c}=K_c\,ET_0,\qquad
P_{ef}=\begin{cases}
\dfrac{P\,(125-0{,}2\,P)}{125} & P\le 250\ \text{mm}\\[6pt]
125+0{,}1\,P & P>250\ \text{mm}
\end{cases}
$$

donde `P` es la precipitación **mensual** (mm). Se calcula a escala mensual y se reparte a los días proporcionalmente a la lluvia diaria de cada día. Fórmula USDA-SCS; el uso de esta fórmula frente a `Pe = 0,8·P` se deja como parámetro `[P]`.

$$
NIR_k=\sum_{d\in k}\max\bigl(0,\ ET_{c,d}-P_{ef,d}\bigr)\quad[\text{mm}]
$$

Volumen: `V = NIR · A · 10` (m³, con `A` en ha).

#### 10.10.3 Selección de sistema (árbol de decisión)

Puntuación de cada sistema `S ∈ {goteo, microaspersión, aspersión, surco, inundación}`:

$$
score(S)=100-\sum_j \beta_j\cdot d_j(S)
$$

| Factor | Peso `β` | Goteo | Microaspersión | Aspersión | Surco | Inundación |
|---|---|---|---|---|---|---|
| Eficiencia de aplicación `η` | 25 | 0,90 | 0,85 | 0,75 | 0,60 | 0,45 |
| Coste de inversión (€/ha) | 20 | alto | medio | medio | bajo | muy bajo |
| Adaptación a pendiente | 15 | alta | alta | media | baja | nula |
| Adaptación a viento | 15 | alta | media | baja | alta | alta |
| Adaptación a textura arenosa | 10 | alta | alta | media | baja | nula |
| Requiere presión | 5 | baja | baja | alta | nula | nula |
| Mano de obra | 10 | baja | baja | baja | alta | muy alta |

- Con `water.source = none` → **solo opción**: captación de lluvia + cubierta + rotación de menor demanda. El sistema se marca `rainfed`.
- Regla de desempate: a igualdad de puntuación, gana el de menor inversión.

#### 10.10.4 Dimensionamiento

Caudal de diseño:

$$
Q\ [\text{L/s}]=\frac{NIR_{evento}\,[\text{mm}]\cdot A\,[\text{ha}]\cdot 2{,}7778}{\eta\cdot T_{riego}\,[\text{h}]}
$$

Emisores: `n_emisores_ha = 10 000 / (e_lateral · e_emisor)` (m²). Volumen por evento: `V = NIR_evento · A · 10 / η`.

Bomba:

$$
P_{kW}=\frac{9{,}81\cdot Q_{m^3/s}\cdot H_{m}}{\eta_{bomba}}
$$

con `H` = altura manométrica (elevación NASADEM + pérdidas 20–30 % + presión de trabajo).

**Validaciones:** `Q_diseño ≤ flow_l_s` disponible (si no, dividir en turnos y avisar); horas/día ≤ `hours_per_day_available`; número de turnos = `ceil(Q_diseño/flow)`.

#### 10.10.5 Captación de lluvia

$$
V_{capt}=A_{capt}\cdot P_{diseño}\cdot C_{esc}\cdot \eta_{almacen}/1000\quad[\text{m}^3]
$$

`C_esc`: cubierta 0,85 · suelo desnudo 0,35 · suelo con cubierta 0,50. `P_diseño` = `p70` de la lluvia mensual.

**Fiabilidad:** simulación del depósito sobre 30 años de lluvia diaria → `P(déficit en un año)`. Si `> 30 %`, recomendar depósito mayor o reducir superficie.

#### 10.10.6 Mapa de riego (output `[N]`: "mapa ilustrativo de cómo y donde hacerlo")

1. La parcela se divide en **zonas hidráulicas** automáticamente: bloques de área ≈ `Q_disponible · T / NIR` (máx. 4 zonas), respetando la geometría del polígono (`shapely.ops.split` por líneas paralelas al eje mayor).
2. Cada zona lleva: sistema, caudal, turnos, emisores.
3. Se dibuja el **punto de agua**: pozo/nave/depósito (posición editable por el usuario).
4. Si hay pendiente > 8 % (NASADEM), se marca la zona como "requiere sectorización por presión".
5. Capas del mapa: satélite (Esri/OSM) + polígono + zonas coloreadas + etiquetas + leyenda.

#### 10.10.7 Calendario y materiales

- Tabla mes a mes: ETc (mm), lluvia efectiva (mm), NIR (mm), horas de riego, turnos.
- Lista de materiales con cantidades: metros de lateral, nº de emisores, válvulas, filtro, programador, depósito (m³). Sin marcas.
- Coste estimado **solo si** el usuario aportó presupuesto (D9): rango bajo–alto con precios de referencia configurables.

### 10.11 Motor de catástrofes (F5)

#### 10.11.1 Catálogo de peligros

| ID | Peligro | Indicador principal | Fuente | ¿Evaluable? |
|---|---|---|---|---|
| `drought` | Sequía | SPEI-12, CDD, percentil SM | POWER, IMERG, SMAP | Sí |
| `flood` | Inundación | Rx1day, escorrentía GLDAS, pendiente | IMERG, GLDAS, NASADEM | Sí (susceptibilidad) |
| `frost` | Helada | `P(Tmin < Tcrit)` por mes | POWER | Sí |
| `heat` | Ola de calor | `P(Tmax > Tcrit)` en floración | POWER | Sí |
| `wind` | Viento fuerte | `P(WS2M > 10 m/s)` | POWER | Sí |
| `fire` | Incendio | FIRMS + combustible (NDVI) + días sin lluvia | FIRMS, MOD13Q1, POWER | Sí (alerta) |
| `erosion` | Erosión | RUSLE: `A = R·K·LS·C·P` | POWER, NASADEM, MCD12Q1 | Parcial (K requiere suelo) |
| `hail` | Granizo | **Sin dato NASA** | — | **No** (solo playbook) |

**Regla:** si no hay dato, la tarjeta del peligro se muestra con la etiqueta *"Sin datos suficientes — solo protocolo de actuación"*. Nunca se inventa una probabilidad.

#### 10.11.2 Probabilidad y periodo de retorno

Para cada peligro con serie de máximos anuales (`n = 30`):

$$
F(x)=\exp\!\Bigl[-\exp\!\Bigl(-\frac{x-\mu}{\beta}\Bigr)\Bigr]\ \text{(Gumbel)},\qquad T=\frac{1}{1-F(x)}
$$

Ajuste por L-momentos. Se reporta `T` y `P = 1/T` con intervalo de confianza bootstrap (1 000 remuestreos). Con `n = 30`, **no** se reportan periodos de retorno > 100 años (sin datos para sostenerlo).

#### 10.11.3 Susceptibilidad a inundación (índice compuesto)

$$
SI_{flood}=100\cdot\bigl(0{,}40\,s_{lluvia}+0{,}25\,s_{escorr}+0{,}25\,s_{pend}+0{,}10\,s_{suelo}\bigr)
$$

| Componente | Normalización |
|---|---|
| `s_lluvia` | percentil de `Rx1day` frente a la serie 1991–2020 |
| `s_escorr` | percentil de escorrentía GLDAS en el mes de siembra |
| `s_pend` | `min(1, pendiente_media/10 %)` invertido: a menor pendiente, mayor riesgo |
| `s_suelo` | grupo hidrológico D = 1,0 · C = 0,66 · B = 0,33 · A = 0 |

`SI < 25` bajo · `25–50` medio · `50–75` alto · `> 75` muy alto.

#### 10.11.4 Estructura del playbook

```jsonc
{
  "hazard": "drought",
  "probability_annual": 0.22,
  "return_period_years": 4.5,
  "exposed_window": "2026-03-01/2026-07-31",
  "expected_loss_rel": 0.35,
  "playbook": {
    "before": [
      { "step": 1, "action": "Elegir variedad de ciclo corto si el SPEI-3 de marzo es < −0,8",
        "trigger": "spei_3 < -0.8", "lead_time_days": 45 },
      { "step": 2, "action": "Asegurar cobertura del suelo con rastrojo para reducir evaporación",
        "trigger": "always", "lead_time_days": 90 }
    ],
    "during": [
      { "step": 1, "action": "Priorizar el agua disponible a la fase de floración",
        "trigger": "sm_pct < 20", "lead_time_days": 0 }
    ],
    "after": [
      { "step": 1, "action": "No labrar en seco; evaluar siembra de cobertura tras la primera lluvia",
        "trigger": "always", "lead_time_days": 0 }
    ]
  },
  "sources": ["POWER SPEI-12", "SMAP root zone"]
}
```

**Requisitos del contenido:** cada paso debe tener (a) acción concreta en imperativo, (b) disparador medible con los datos disponibles, (c) antelación. Nada de "estar atento al clima".

**Estado actual (alerta):** la tarjeta muestra un semáforo con los datos de los últimos 30 días: `sm_pct`, `spei_3`, `dias_sin_lluvia`, detecciones FIRMS en 25 km. Esto convierte F5 de estático en vivo.

#### 10.11.5 Descargo

*"Los protocolos son orientativos y de carácter general. No sustituyen a los servicios de emergencia, a la administración competente ni al asesoramiento técnico."* En catástrofes con riesgo para personas (incendio, inundación), mostrar siempre el número de emergencias local (112 en España).

### 10.12 Incertidumbre, confianza y procedencia

#### 10.12.1 Puntuación de confianza (0–100)

$$
Conf=100\cdot f_{cobertura}\cdot f_{serie}\cdot f_{escenarios}\cdot f_{supuestos}
$$

| Factor | Valor |
|---|---|
| `f_cobertura` | fracción de días con dato válido en el periodo (0–1) |
| `f_serie` | `min(1, años_disponibles/30)` |
| `f_escenarios` | `min(1, S/1000)` |
| `f_supuestos` | 1,0 sin supuestos · 0,9 con 1 supuesto · 0,75 con ≥2 · 0,6 si `Y_m` es genérico |

| `Conf` | Etiqueta UI |
|---|---|
| ≥ 80 | Confianza alta |
| 60–79 | Confianza media |
| 40–59 | Confianza baja |
| < 40 | Resultado indicativo |

#### 10.12.2 Objeto de procedencia (obligatorio en toda cifra mostrada)

```jsonc
{
  "product": "NASA POWER",
  "dataset": "MERRA-2 daily (community AG)",
  "variable": "PRECTOTCORR",
  "unit": "mm/day",
  "resolution": "0.5 deg",
  "period": "1991-01-01/2020-12-31",
  "cell": { "lat": 37.25, "lon": -4.0 },
  "retrieved_at": "2026-11-14T09:12:03Z",
  "product_version": "v9.0.0",
  "model_version": "1.0.0",
  "params_hash": "a91f3c2e7b10"
}
```

#### 10.12.3 Advertencias automáticas (`caveats`)

El motor **debe** emitir una advertencia cuando:

| Condición | Texto |
|---|---|
| `f_supuestos < 1` | "Resultado basado en supuestos declarados: …" |
| Serie < 20 años | "Serie climática corta (N años): los percentiles son frágiles." |
| `DATA_MODE=demo` | "Datos de demostración precargados (finca de ejemplo)." |
| `Sm` sin SMAP | "Humedad del suelo inicial asumida al 50 % de capacidad." |
| NEX-GDDP con > 1 GCM | "Escenario construido con N modelos; la dispersión entre modelos es parte del resultado." |
| Enfermedad sin validación | "Umbrales de enfermedad pendientes de validación agronómica." |

---

## 11. API HTTP

### 11.1 Convenciones

- Base: `/api/v1`. JSON UTF-8. `snake_case` en campos.
- Autenticación: `Authorization: Bearer <session_token>` (sesión anónima) o JWT de cuenta (D14).
- Idempotencia: `POST /farms` acepta `Idempotency-Key`.
- Todo recurso calculado tiene `id` estable y `created_at`.
- Fechas `YYYY-MM-DD`; instantes ISO-8601 con `Z`.
- **Sobre de respuesta** (todas las respuestas 2xx):

```jsonc
{
  "data": { /* payload */ },
  "meta": {
    "request_id": "req_01H...",
    "model_version": "1.0.0",
    "generated_at": "2026-11-14T09:12:03Z",
    "duration_ms": 842,
    "data_mode": "cached",
    "confidence": 78,
    "caveats": ["Humedad del suelo inicial asumida al 50 % de capacidad."],
    "sources": [ { /* Provenance */ } ]
  }
}
```

- **Errores** (formato fijo):

```jsonc
{
  "error": {
    "code": "INSUFFICIENT_CLIMATE_DATA",
    "message": "La celda no tiene al menos 10 años de datos POWER.",
    "details": { "cell": "37.25_-4.0", "years_available": 6 },
    "request_id": "req_01H..."
  }
}
```

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Payload inválido (con `details.fields`) |
| 400 | `LOCATION_NOT_LAND` | Coordenada en mar |
| 400 | `INVALID_BOUNDARY` | Polígono inválido |
| 404 | `NOT_FOUND` | Recurso inexistente |
| 409 | `CONFLICTING_CROPS` | Cultivo en preferidos y excluidos |
| 422 | `NO_VIABLE_ROTATION` | Menos de 2 cultivos viables tras el filtro |
| 422 | `INSUFFICIENT_CLIMATE_DATA` | < 10 años de datos |
| 429 | `RATE_LIMITED` | > 60 req/min/IP |
| 500 | `INTERNAL_ERROR` | Fallo inesperado |
| 502 | `UPSTREAM_NASA_ERROR` | NASA devuelve error persistente |
| 503 | `DATA_UNAVAILABLE` | Producto caído o sin caché en modo `cached` |

### 11.2 Endpoints

#### `POST /api/v1/farms`

Crea la finca y lanza el cálculo del contexto.

**Request:** `FarmProfile` (§6.1).
**Response `202`:**

```jsonc
{ "data": { "farm_id": "frm_8c21", "job_id": "job_44a1", "status": "computing_context" } }
```

#### `GET /api/v1/farms/{farm_id}`

Devuelve el perfil guardado + estado de los cálculos.

#### `GET /api/v1/farms/{farm_id}/context`

Contexto agroclimático ya calculado (§10.2–10.5, 10.11). Es el endpoint más cacheado.

```jsonc
{
  "data": {
    "climate_cell": { "lat": 37.25, "lon": -4.0, "id": "37.25_-4.0" },
    "aridity": { "index": 0.31, "class": "semiárido" },
    "baseline": {
      "period": "1991-2020",
      "precip_annual_mm": { "p10": 312, "p50": 438, "p90": 571 },
      "et0_annual_mm": 1240,
      "frost_free_days": 168,
      "last_frost_doy_p50": 78,
      "gdd_annual_base10": 2140
    },
    "current_drought": {
      "spei_3": -0.42, "spei_12": -1.10, "sm_pct": 34,
      "days_since_rain": 12, "class": "sequía moderada"
    },
    "hazards_summary": [ { "hazard": "drought", "p_annual": 0.22, "return_period_years": 4.5 } ],
    "series": { "monthly_precip_mm": [ /* 12 */ ], "monthly_et0_mm": [ /* 12 */ ] }
  },
  "meta": { /* … */ }
}
```

Cabeceras: `Cache-Control: private, max-age=86400`, `ETag`.

#### `POST /api/v1/farms/{farm_id}/rotation:optimize`

**Request:**

```jsonc
{
  "horizon_seasons": 8,
  "objective": "balanced",
  "risk_tolerance": "medium",
  "constraints": { "must_include": ["chickpea"], "max_crops": 4 },
  "baseline_rotation_id": "rot_current"   // opcional; si falta, se usa la rotación actual
}
```

**Response `202`:** `{ "data": { "job_id": "job_9b2e" } }`
**Resultado (vía `GET /jobs/{id}`):** `RotationResult` (§10.7.8).

#### `PUT /api/v1/farms/{farm_id}/rotation/{rotation_id}`

El usuario edita la secuencia (drag & drop). **Recalcula solo métricas**, sin reoptimizar. Objetivo < 3 s.

**Request:**

```jsonc
{ "sequence": [ { "k": 1, "crop_id": "chickpea", "area_ha": 4.4 }, /* … */ ] }
```

**Response `200`:** `RotationResult` con `meta.duration_ms` y `warnings` (violaciones de R1–R10 marcadas como tales, sin bloquear).

> Decisión de diseño: las restricciones duras **avisan** al editar a mano; solo **prohíben** en la optimización automática. El usuario manda (§2.2.5).

#### `GET /api/v1/farms/{farm_id}/diseases?crop_id=wheat_durum&from=2026-03-01&to=2026-07-31`

Devuelve `DiseaseRiskReport` (§10.9.6) por cultivo. Si no se pasa `crop_id`, devuelve todos los cultivos de la finca.

#### `POST /api/v1/farms/{farm_id}/irrigation`

**Request:**

```jsonc
{ "parcel_id": "prc_1", "water_source": "well", "flow_l_s": 4.5,
  "available_m3_per_year": 9000, "budget_eur": 6000, "hours_per_day": 8 }
```

**Response `200`:** `IrrigationDesign` — sistema recomendado, alternativas puntuadas, zonas, calendario, materiales, `rainfed_plan` si no hay agua.

#### `GET /api/v1/farms/{farm_id}/hazards`

Lista de peligros con probabilidad, periodo de retorno, susceptibilidad y estado actual.

#### `GET /api/v1/farms/{farm_id}/hazards/{hazard_id}/playbook`

Playbook completo (§10.11.4) + `caveats`.

#### `GET /api/v1/farms/{farm_id}/timeline?layer=ndvi&from=2000-02&to=2026-10`

Serie temporal agregada de la parcela para el deslizador de F4.

```jsonc
{
  "data": {
    "layer": "ndvi",
    "unit": "index",
    "points": [ { "t": "2000-02", "mean": 0.31, "min": 0.22, "max": 0.41, "valid_px": 3 } ],
    "available_range": { "from": "2000-02", "to": "2026-10" }
  }
}
```

#### `GET /api/v1/tiles/{layer}/{z}/{x}/{y}.png`

Tiles XYZ servidos por TiTiler. Capas: `ndvi`, `sm`, `precip`, `lst`, `landcover`, `hillshade`. `layer` incluye el periodo: `ndvi@2023-06`.

**Regla:** si el tile no está precomputado y `DATA_MODE=demo`, devolver un PNG transparente con cabecera `X-Rootshift-Fallback: 1`.

#### `GET /api/v1/jobs/{job_id}`

```jsonc
{
  "data": {
    "job_id": "job_9b2e", "status": "running", "progress": 0.62,
    "stage": "evaluando rotaciones (12/20)", "started_at": "…", "eta_s": 8,
    "result_ref": null
  }
}
```

Estados: `queued | running | done | failed | cancelled`.

#### `GET /api/v1/jobs/{job_id}/events`

`text/event-stream` con `{progress, stage}` cada 500 ms. Fallback: polling cada 1 s.

#### `GET /api/v1/catalog/crops?lat=&lon=`

Catálogo con viabilidad calculada para la celda:

```jsonc
{ "data": [ { "crop_id": "chickpea", "name": "Garbanzo", "family": "fabaceae",
              "viable": true, "cycle_days": 150, "water_need_mm": 320,
              "reason_unviable": null } ] }
```

#### `GET /api/v1/health`

`{ "status": "ok", "version": "1.0.0", "data_mode": "cached", "db": "ok", "redis": "ok" }`

### 11.3 Límites

| Límite | Valor |
|---|---|
| Rate limit | 60 req/min por IP (Redis) |
| Tamaño de payload | 1 MB |
| Fincas por sesión | 5 |
| Jobs concurrentes por sesión | 2 |
| Timeout de job | 180 s |
| Retención de artefactos anónimos | 30 días |

---

## 12. Modelo de datos

### 12.1 DDL (PostgreSQL + PostGIS)

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE farm (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id    uuid NOT NULL,
  name          text NOT NULL,
  location      geography(Point,4326) NOT NULL,
  boundary      geography(Polygon,4326),
  area_ha       numeric(10,2),
  elevation_m   integer,
  admin         jsonb,
  resources     jsonb NOT NULL DEFAULT '{}',
  constraints   jsonb NOT NULL DEFAULT '{}',
  preferences   jsonb NOT NULL DEFAULT '{}',
  data_mode     text NOT NULL DEFAULT 'live',
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE parcel (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  farm_id      uuid NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  name         text,
  boundary     geography(Polygon,4326) NOT NULL,
  area_ha      numeric(10,2) NOT NULL,
  soil         jsonb,                        -- textura, pH, MO (D2)
  climate_cell_id text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE climate_cell (
  id            text PRIMARY KEY,            -- "37.25_-4.0"
  center        geography(Point,4326) NOT NULL,
  country       text,
  aridity_index numeric(5,3),
  data_start    date,
  data_end      date,
  quality       jsonb,                       -- resultado de §9.5
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE crop (
  id            text PRIMARY KEY,            -- "wheat_durum"
  name_es       text NOT NULL,
  name_sci      text,
  family        text NOT NULL,               -- "poaceae"
  cycle_type    text NOT NULL,               -- annual | perennial
  season        text,                        -- S | W | both
  params        jsonb NOT NULL,              -- Anexo B (Kc, GDD, Ky, ZR, p…)
  is_legume     boolean NOT NULL DEFAULT false,
  catalog_version text NOT NULL
);

CREATE TABLE farm_crop (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  farm_id     uuid NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  parcel_id   uuid REFERENCES parcel(id) ON DELETE CASCADE,
  crop_id     text NOT NULL REFERENCES crop(id),
  season      text NOT NULL,
  area_ha     numeric(10,2) NOT NULL,
  origin      text NOT NULL CHECK (origin IN ('current','preferred','recommended')),
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE indicator_daily (
  cell_id   text NOT NULL REFERENCES climate_cell(id),
  date      date NOT NULL,
  et0_mm    real,
  tmax_c    real, tmin_c real, pr_mm real, rh_pct real,
  gdd       real,
  PRIMARY KEY (cell_id, date)
);
CREATE INDEX ON indicator_daily (cell_id, date);

CREATE TABLE indicator_monthly (
  cell_id    text NOT NULL REFERENCES climate_cell(id),
  month      date NOT NULL,               -- primer día del mes
  pr_mm      real, et0_mm real, pet_mm real,
  spei_3     real, spei_6 real, spei_12 real,
  spi_3      real, spi_12 real,
  PRIMARY KEY (cell_id, month)
);

CREATE TABLE scenario_set (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cell_id       text NOT NULL REFERENCES climate_cell(id),
  kind          text NOT NULL,             -- S0..S7
  n_members     integer NOT NULL,
  seed          integer NOT NULL,
  gcm_list      text[],                    -- S6/S7
  ssp           text,
  params_hash   text NOT NULL,
  storage_uri   text NOT NULL,             -- Parquet en MinIO
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE rotation (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  farm_id       uuid NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  parcel_id     uuid NOT NULL REFERENCES parcel(id) ON DELETE CASCADE,
  kind          text NOT NULL CHECK (kind IN ('current','optimized','manual')),
  objective     text,
  horizon_seasons integer NOT NULL,
  metrics       jsonb NOT NULL,
  findings      jsonb NOT NULL DEFAULT '[]',
  params_hash   text NOT NULL,
  model_version text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE rotation_item (
  rotation_id uuid NOT NULL REFERENCES rotation(id) ON DELETE CASCADE,
  k           integer NOT NULL,
  season      text NOT NULL,
  crop_id     text REFERENCES crop(id),    -- null = barbecho
  area_ha     numeric(10,2) NOT NULL,
  is_cover    boolean NOT NULL DEFAULT false,
  PRIMARY KEY (rotation_id, k)
);

CREATE TABLE simulation (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rotation_id   uuid NOT NULL REFERENCES rotation(id) ON DELETE CASCADE,
  scenario_set_id uuid NOT NULL REFERENCES scenario_set(id),
  metrics       jsonb NOT NULL,            -- E[P], P10, P50, P90, CV, CVaR10, P_fallo…
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE disease_report (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  farm_id     uuid NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  crop_id     text NOT NULL REFERENCES crop(id),
  season      text NOT NULL,
  payload     jsonb NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE irrigation_design (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  farm_id     uuid NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  parcel_id   uuid NOT NULL REFERENCES parcel(id),
  system      text NOT NULL,
  payload     jsonb NOT NULL,              -- zonas, calendario, materiales, coste
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE hazard_assessment (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  farm_id     uuid NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  hazard      text NOT NULL,
  p_annual    numeric(6,4),
  return_period_years numeric(8,2),
  susceptibility numeric(5,2),
  payload     jsonb NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE data_fetch_log (
  id           bigserial PRIMARY KEY,
  product      text NOT NULL,
  cell_id      text,
  range_start  date, range_end date,
  params_hash  text NOT NULL,
  status       text NOT NULL,            -- ok | degraded | error
  http_status  integer,
  bytes        bigint,
  duration_ms  integer,
  fetched_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON data_fetch_log (product, cell_id, fetched_at DESC);

CREATE TABLE artifact_provenance (
  id          bigserial PRIMARY KEY,
  artifact_type text NOT NULL,           -- rotation | disease_report | irrigation_design…
  artifact_id uuid NOT NULL,
  provenance  jsonb NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE job (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  farm_id     uuid REFERENCES farm(id) ON DELETE CASCADE,
  kind        text NOT NULL,
  status      text NOT NULL DEFAULT 'queued',
  progress    numeric(4,3) DEFAULT 0,
  stage       text,
  error       jsonb,
  created_at  timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);
```

### 12.2 Reglas de integridad

- `parcel.climate_cell_id` debe existir en `climate_cell` antes de insertar.
- `rotation_item.area_ha` suma ≤ `parcel.area_ha` (trigger de validación).
- `farm_crop.area_ha` suma ≤ `farm.area_ha` × 1,02.
- Borrar `farm` arrastra en cascada todo lo derivado.
- `artifact_provenance` es **append-only** (sin UPDATE ni DELETE): auditoría.

### 12.3 Almacenamiento de series

- Series diarias de 30 años: **Parquet** en MinIO (`s3://rootshift/cells/{cell_id}/daily.parquet`), no en Postgres (12 800 filas × 10 celdas es trivial, pero 1 000 celdas no).
- Escenarios Monte Carlo: Parquet comprimido (`zstd`), una columna por miembro.
- Ráster: COG en MinIO, servido por TiTiler.

---

## 13. Especificación de interfaz (UI/UX)

### 13.1 Sistema de diseño

**Tokens** (`tailwind.config.ts`, no valores sueltos en componentes):

| Token | Valor | Uso |
|---|---|---|
| `--rs-bg` | `#0B0F0C` | Fondo principal (oscuro, legible a pleno sol) |
| `--rs-surface` | `#141A15` | Tarjetas |
| `--rs-border` | `#243027` | Bordes |
| `--rs-text` | `#E8F0EA` | Texto principal |
| `--rs-muted` | `#9AA79D` | Texto secundario |
| `--rs-accent` | `#7BC96F` | Acción primaria, positivo |
| `--rs-water` | `#4FA3D1` | Agua |
| `--rs-soil` | `#B08968` | Suelo |
| `--rs-risk-1` | `#3E9B5F` | Riesgo bajo |
| `--rs-risk-2` | `#D9B23A` | Riesgo medio |
| `--rs-risk-3` | `#DE7B3C` | Riesgo alto |
| `--rs-risk-4` | `#C8433B` | Riesgo muy alto |

**Regla de accesibilidad cromática:** el riesgo nunca se comunica solo con color. Siempre `color + icono + etiqueta textual` (✓ Bajo, ! Medio, ▲ Alto, ✖ Muy alto). Verificable en escala de grises.

**Tipografía:** Inter (UI), 14 px base, 1.5 de interlineado. Cifras con `font-variant-numeric: tabular-nums`.

**Componentes obligatorios** (biblioteca interna `components/`):

| Componente | Contrato |
|---|---|
| `<SourceBadge product="NASA POWER" />` | Muestra producto + tooltip con resolución y periodo. Obligatorio junto a toda cifra. |
| `<ConfidenceChip value={78} />` | Alta/Media/Baja/Indicativo con color e icono. |
| `<CaveatBanner caveats={[]} />` | Lista de advertencias; se colapsa si hay > 2. |
| `<MetricCard label value unit delta />` | Cifra + unidad + delta vs baseline con flecha. |
| `<ScenarioFanChart series />` | Abanico p10–p90 + mediana, eje X años, tooltip con valores. |
| `<RiskCalendar matrix />` | Heatmap 12 meses × N enfermedades. |
| `<ZoneMap zones waterPoint />` | Mapa MapLibre con polígonos de zonas y punto de agua. |
| `<TimeSlider from to value />` | Deslizador año-mes con reproducción y marcas por año. |
| `<FindingCard finding />` | Texto del hallazgo + evidencia numérica + icono de severidad. |
| `<JobProgress job />` | Etapa + barra + ETA. |
| `<EmptyState title action />` | Estado vacío con llamada a la acción. |

**Estados obligatorios por pantalla:** `loading` (skeleton, nunca spinner desnudo), `empty`, `error` (mensaje accionable + reintentar), `degraded` (datos parciales con banner), `success`.

### 13.2 Dashboard

```
┌──────────────────────────────────────────────────────────────────────┐
│ ROOTSHIFT   Finca El Olivar · Córdoba · 12,4 ha     [Confianza: 78]  │
├──────────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌─────────────────────────────────────────────┐ │
│  │  IRS  71/100   │  │ "Resiste en la mayoría de escenarios; hay   │ │
│  │  ●●●●●○○      │  │  margen de mejora en agua y diversidad."    │ │
│  │  Resiliente    │  │  [Ver desglose ▾]                           │ │
│  └────────────────┘  └─────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│  Sequía actual: moderada (SPEI-12 −1,10) · 12 días sin lluvia        │
├──────────────────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│ │ F1       │ │ F2       │ │ F3       │ │ F4       │ │ F5       │    │
│ │ Rotación │ │ Sanidad  │ │ Riego    │ │ Mapa     │ │ Riesgos  │    │
│ │ +14 %    │ │ 2 alertas│ │ Goteo    │ │ 26 años  │ │ 3 altos  │    │
│ │ prod.    │ │ altas    │ │ 4 zonas  │ │ de datos │ │          │    │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
├──────────────────────────────────────────────────────────────────────┤
│ El clima se representa a escala de comarca (≈50 km); la parcela…     │
└──────────────────────────────────────────────────────────────────────┘
```

Cada tarjeta: icono, título, **un** dato gancho, y navegación. Sin gráficos en el dashboard (se profundiza dentro).

### 13.3 F1 — Panel de rotación

**Objetivo:** que el usuario vea en 10 segundos qué cambia, cuánto mejora y por qué.

```
┌───────────────────────────────────────────────┬──────────────────────┐
│ Rotación propuesta (8 temporadas)             │ IRS  71 ▲ +19       │
│                                               │ Producción +14,2 %   │
│ 2026S  garbanzo   ████                        │ P(fallo) 9 % ▼ −11pp │
│ 2026W  trigo      ██████                      │ Recuperación 1,4 a   │
│ 2027S  barbecho+  ██                          │                      │
│ 2027W  cebada     █████                       │ [Comparar] [Editar]  │
│ 2028S  girasol    ███                         │ [Exportar PDF]       │
│ …                                             │                      │
├───────────────────────────────────────────────┴──────────────────────┤
│  Abanico de producción anual (10 años)                               │
│   45 ┤        ╭─╮                                                    │
│   30 ┤   ╭────╯ ╰──╮        p90                                      │
│   20 ┤───╯         ╰────    p50                                      │
│   10 ┤   ·  ·  ·  ·  ·      p10                                      │
│      └───────────────────────────────────────────────────────────────│
├──────────────────────────────────────────────────────────────────────┤
│ Por qué:                                                             │
│ ✓ Reduce la demanda de agua en julio un 22 % (118 → 92 mm)          │
│ ✓ Introduce leguminosa cada 3 temporadas (rompe el ciclo)           │
│ ▲ En S2 (3 años secos) cae 34 %, frente a 41 % de la actual          │
└──────────────────────────────────────────────────────────────────────┘
```

**Elementos:**

1. **Gantt de temporadas** (`deck.gl`/CSS grid), con barras por cultivo y color por familia botánica. Barbecho en gris con textura.
2. **Tarjeta de métricas** con deltas vs baseline (flecha + color + valor).
3. **Abanico de producción** (`<ScenarioFanChart>`): tres bandas S0/S2/S7 conmutables con pestañas.
4. **Lista de hallazgos** (`<FindingCard>`), máximo 5, ordenados por severidad.
5. **Barra de acciones:** Comparar (split view actual vs propuesta), Editar (drag & drop), Exportar PDF, Ver supuestos.
6. **Tabla de detalle** por temporada: cultivo, familia, ventana, NIR (mm), rendimiento p50 (t/ha), riesgo de enfermedad, riesgo de helada.
7. **Modo comparación:** dos columnas con las mismas métricas, resaltando diferencias.

**Edición manual:** arrastrar un cultivo a otra temporada dispara `PUT /rotation`; se recalculan métricas y se muestran las violaciones de R1–R10 como *warnings* amarillos, sin bloquear. Si el IRS baja, se indica en rojo en la tarjeta.

### 13.4 F2 — Panel de sanidad

```
┌──────────────────────────────────────────────────────────────────────┐
│ Riesgo de enfermedades · Trigo duro · campaña 2026                   │
│ (Estimación climática. No es un diagnóstico.)                        │
├──────────────────────────────────────────────────────────────────────┤
│  Mes      E  F  M  A  M  J  J  A  S  O  N  D                        │
│  Septoria ·  ·  ·  ▓  ▓  █  █  ▓  ·  ·  ·  ·                        │
│  Roya     ·  ·  ▓  ▓  ▓  ░  ·  ·  ·  ·  ·  ·                        │
│  Oidio    ·  ·  ░  ░  ▓  ▓  ░  ·  ·  ·  ·  ·                        │
│                                              █ Alto  ▓ Medio  ░ Bajo │
├──────────────────────────────────────────────────────────────────────┤
│ ▲ Septoriosis — 63/100 (alto)      Ventana: 10 abr – 5 jun           │
│   Factores: 16 días con mojado > 14 h · T media 17 °C · rastrojo     │
│   [Cómo reducir el riesgo ▾]                                         │
│     · Rotar con cultivo no cerealícola ≥ 2 temporadas                │
│     · Enterrar el rastrojo                                           │
│     · Vigilar desde 2 nudos si lluvia > 10 mm                        │
│     · Productos: consultar etiqueta y asesor (no se prescribe dosis) │
└──────────────────────────────────────────────────────────────────────┘
```

**Elementos:** `<RiskCalendar>` + lista ordenada por `risk_index` + panel de detalle expandible + botón "Añadir al plan" (guarda la acción en el calendario de la finca). Empty state si no hay cultivos anuales: *"Selecciona un cultivo anual para calcular riesgo de enfermedades."*

### 13.5 F3 — Panel de riego

```
┌──────────────────────────────────────────────┬───────────────────────┐
│ [MAPA]                                       │ Sistema recomendado   │
│  ┌───────────────────────────────┐           │ ● Goteo               │
│  │  Z1        Z2                 │           │   Puntuación 82/100   │
│  │  (goteo)   (goteo)            │           │   η = 0,90            │
│  │        ◉ pozo                 │           │   Q = 3,8 L/s         │
│  │  Z3        Z4                 │           │   (tienes 4,5)  ✓     │
│  │  (goteo)   (goteo)            │           │                       │
│  └───────────────────────────────┘           │ Alternativas:         │
│  [Capas] [Editar punto de agua]              │  Microaspersión 74    │
│                                              │  Aspersión      61    │
├──────────────────────────────────────────────┴───────────────────────┤
│ Calendario:  Ene  Feb  Mar  Abr  May  Jun  Jul  Ago  Sep  Oct  Nov  │
│ ETc (mm)      12   18   34   62   98  132  145  120   78   42   20   │
│ NIR (mm)       0    0   10   38   72  100  118   96   50   12    0   │
│ Horas riego    0    0    6   18   30   38   42   36   22    8    0   │
├──────────────────────────────────────────────────────────────────────┤
│ Materiales: 4 800 m lateral · 3 200 emisores · 4 válvulas · filtro… │
│ ⚠ Diseño orientativo. Requiere proyecto técnico para ejecución.     │
└──────────────────────────────────────────────────────────────────────┘
```

**Elementos:** `<ZoneMap>` interactivo (zoom, click en zona → detalle), tarjeta de sistema con puntuación y **por qué** (los 3 factores con más peso), tabla de calendario, lista de materiales, aviso de validación.

**Caso sin agua:** en lugar del mapa de zonas, se muestra el **plan de secano**: captación de lluvia (volumen, superficie de captación), cubierta vegetal, rotación de menor demanda, y la frase *"Con los recursos declarados no hay agua suficiente para riego; este es el plan sin riego."*

### 13.6 F4 — Mapa temporal (secundaria)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Capa: [NDVI ▾]   Fecha: ◀──●────────────▶  2023-06   [▶ Play]        │
│        ├─────────────────────────────────────────────┤               │
│        2000-02                          2026-10                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│                    [MAPA A PANTALLA COMPLETA]                        │
│                     polígono de la finca resaltado                   │
│                     leyenda + escala + atribución                    │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│ Serie mensual de la parcela:  ▁▂▃▅▆▇▆▅▄▃▂▁  (mini-sparkline)        │
└──────────────────────────────────────────────────────────────────────┘
```

**Contrato:**

- Capas: `NDVI` (MOD13Q1), `Humedad del suelo` (SMAP), `Precipitación mensual` (IMERG), `Temperatura superficial` (MOD11A2), `Cobertura del suelo` (MCD12Q1), `Relieve` (NASADEM hillshade).
- **Granularidad:** año y mes `[N]`. Cada capa define su disponibilidad (NDVI desde 2000-02; SMAP desde 2015-04; IMERG diario desde 1998-01; MOD11A2 desde 2000-02; MCD12Q1 desde 2001).
- **Deslizador:** paso de 1 mes; teclado (←/→) accesible; `aria-valuetext="junio de 2023"`.
- **Play:** reproduce 12 meses/año a 2 fps.
- **Comparar (opcional):** vista dividida con otra fecha.
- **Serie inferior:** sparkline de la media de la parcela en toda la serie, con el punto actual marcado; click para saltar.
- Si no hay datos para esa fecha (nubes, producto ausente): tile anterior + aviso *"Sin observación válida en junio de 2023 (cobertura nubosa). Mostrando mayo de 2023."*
- **Modo demo sin red:** 24 fechas precomputadas (2 por año) para la finca demo.

### 13.7 F5 — Panel de catástrofes

```
┌──────────────────────────────────────────────────────────────────────┐
│ Riesgos para tu finca              Estado actual (últimos 30 días)   │
├──────────────────────────────────────────────────────────────────────┤
│ ▲ Sequía       P 22 %/año · T 4,5 años   SPEI-3 −0,4 · SM 34 %      │
│   [Ver protocolo ▾]                                                  │
│ ▲ Helada       P 18 %/año · T 5,6 años   última helada: 12 mar       │
│   [Ver protocolo ▾]                                                  │
│ ! Inundación   P  6 %/año · T 16 años    Rx1day 2025: 48 mm          │
│   [Ver protocolo ▾]                                                  │
│ · Incendio     sin detecciones en 25 km  [Ver protocolo ▾]           │
│ ✖ Granizo      sin datos suficientes     [Solo protocolo ▾]          │
└──────────────────────────────────────────────────────────────────────┘
```

**Detalle (drawer):** pestañas **Antes / Durante / Después**, cada paso con acción, disparador y antelación. Botón "Descargar protocolo (PDF)". Números de emergencia siempre visibles.

**Copy obligatorio:** *"Protocolos orientativos. No sustituyen a los servicios de emergencia ni al asesoramiento técnico."*

### 13.8 Onboarding (5 pasos)

| Paso | Contenido | Validación en vivo |
|---|---|---|
| 1 | Buscador de municipio / pin / dibujar polígono | "Celda climática detectada: 37,25 / −4,00 · 28 años de datos" |
| 2 | Cultivos actuales + superficie | Suma de áreas vs área total |
| 3 | Preferencias (preferidos / excluidos) | Chip input con sugerencias viables |
| 4 | Recursos (agua, riego, presupuesto, maquinaria) | "Sin caudal declarado → asumiremos 3 L/s" |
| 5 | Generar | Progreso real por etapas |

Barra de progreso, botón "Volver", autoguardado del borrador en `localStorage`.

### 13.9 Responsive y accesibilidad

- Breakpoints: `sm 640`, `md 768`, `lg 1024`, `xl 1280`. Diseño *mobile-last*: la demo es de escritorio, pero el mapa y F2 funcionan en 375 px.
- WCAG 2.1 AA: contraste ≥ 4,5:1, foco visible, navegación completa por teclado, `aria-label` en todos los iconos, tablas con `<caption>`.
- Los gráficos tienen **alternativa tabular** obligatoria (botón "Ver datos").
- `prefers-reduced-motion`: desactiva el play del deslizador y las animaciones.

---

## 14. Requisitos no funcionales

### 14.1 Rendimiento

| Operación | Objetivo |
|---|---|
| Carga inicial (LCP) | < 2,5 s |
| `GET /context` (caché) | p95 < 400 ms |
| `PUT /rotation` (recálculo) | p95 < 3 s |
| Optimización completa | < 45 s |
| Cambio de capa en F4 | < 1 s |
| Tiles | < 500 ms |

### 14.2 Fiabilidad

- **Modo demo sin red** garantizado (D18): la demo del hackathon no puede depender del wifi del recinto.
- Reintentos con backoff en todas las llamadas a NASA.
- Si un producto falla, el resto de la app sigue funcionando (`degraded`), no hay caída en cascada.
- Los jobs tienen timeout de 180 s y estado `failed` con causa legible.

### 14.3 Seguridad

- Validación de entrada con Pydantic en todos los endpoints.
- Sin secretos en el frontend; claves solo en backend (`.env`, nunca en git).
- CORS restringido al dominio de la app.
- Rate limit por IP y por sesión.
- Sanitización de GeoJSON (límite de vértices: 10 000; área máxima 50 000 ha).
- `Content-Security-Policy` básica; sin `eval`.

### 14.4 Privacidad

- La ubicación de una finca es dato sensible: no se publica, no se comparte, no se usa para entrenar.
- Sesión anónima por defecto (cookie `httpOnly`, 30 días).
- Coordenadas guardadas con 3 decimales si no hay cuenta.
- Borrado de finca = borrado en cascada + purga de artefactos.
- Sin analytics de terceros por defecto.

### 14.5 Accesibilidad e internacionalización

- Español (ES) por defecto; estructura i18n con `next-intl` para permitir EN. D16.
- Unidades métricas; sin conversión a imperial salvo petición.

### 14.6 Observabilidad

- Logs estructurados JSON con `request_id`.
- Métricas: latencia por endpoint, tasa de error de proveedores, jobs fallidos, aciertos de caché.
- Cada respuesta incluye `meta.duration_ms` y `meta.data_mode`.

### 14.7 Licencias y atribución

- Atribución NASA visible en pie de página y en cada `<SourceBadge>`.
- Sin uso de logotipos de la NASA.
- Descargo: "ROOTSHIFT no está afiliado ni respaldado por la NASA".
- Descargo agronómico: "No es asesoramiento agronómico profesional".
- Código bajo licencia MIT (o la que decida el equipo).

---

## 15. Plan de implementación

### 15.1 Fases y criterio de "hecho"

| Fase | Entregable | DoD (definición de hecho) | Esfuerzo |
|---|---|---|---|
| **F0 · Spike de datos** | Script que, dada una lat/lon, baja POWER 30 años y calcula ET0 | Gráfico de ET0 vs MOD16A2 con correlación > 0,7 en 2 ubicaciones | 4–6 h |
| **F1 · Contexto** | `GET /context` + indicadores + SPEI + balance | Test dorado de ET0 pasa; SPEI coincide con referencia (±0,05) | 8–10 h |
| **F2 · Rotación** | Motor + endpoint + panel F1 | Genera rotación válida en < 45 s; baseline y propuesta comparables; hallazgos generados | 12–16 h |
| **F3 · Catástrofes y sanidad** | F5 + F2 (motor y paneles) | 8 peligros con probabilidad o "sin datos"; 10 enfermedades con ventana y acciones | 8–10 h |
| **F4 · Riego** | F3 (motor y panel) | Recomienda sistema, 4 zonas, calendario y materiales; caso sin agua cubierto | 8–10 h |
| **F5 · Mapa temporal** | F4 con 4 capas y deslizador | 24 fechas demo funcionando sin red | 6–8 h |
| **F6 · Pulido y demo** | Datos demo, PDF, textos, ensayo | Demo de 3 min sin fallos, sin red, en 2 máquinas distintas | 6–8 h |

**Total estimado:** 52–68 h de trabajo efectivo. Para un equipo de 4, ~16 h de reloj.

### 15.2 Corte mínimo defendible (MVP)

Si el tiempo aprieta, **esto es lo que no se puede quitar**:

1. Onboarding completo con finca de ejemplo.
2. `GET /context` con ET0, SPEI, heladas y sequía.
3. F1 con rotación propuesta, comparación vs actual y **3 hallazgos explicativos**.
4. F5 con 4 peligros y protocolo.
5. Modo demo sin red con 2 fincas.
6. Atribución de datos y descargos.

F2, F3 y F4 son diferenciales: si se caen, el producto sigue contando la historia ("probamos decisiones contra futuros"). Si se cae F1, no hay producto.

### 15.3 Reparto de trabajo sugerido (equipo de 4)

| Rol | Responsabilidad | Artefactos |
|---|---|---|
| **Data/Geo** | Pipeline NASA, indicadores, tiles | F0, `pipeline/`, TiTiler |
| **Ciencia/Modelos** | §10: ET0, balance, rendimiento, escenarios, IRS | `domain/*.py` + tests dorados |
| **Backend** | API, jobs, BD, autenticación | `apps/api`, DDL, docker-compose |
| **Frontend** | UI, mapas, gráficos, copy | `apps/web`, componentes §13 |
| (5.º) **Storytelling** | Guion de demo, PDF, validación agronómica | Slides, ensayo |

### 15.4 Brief listo para pegar en un agente de codificación

```text
Construye ROOTSHIFT según ROOTSHIFT_ESPECIFICACION.md (raíz del repo).

Reglas:
1. Implementa en este orden: F0 spike → contexto (§10.2–10.5) → F1 rotación (§10.7–10.8)
   → F5 catástrofes (§10.11) → F2 enfermedades (§10.9) → F3 riego (§10.10) → F4 mapa (§13.6).
2. Todo cálculo vive en domain/ como función pura, sin red ni BD, con test unitario.
3. Toda cifra expuesta lleva Provenance (§10.12.2) y, si aplica, Caveat (§10.12.3).
4. Usa exclusivamente los productos NASA de §7.2. No inventes datasets ni endpoints.
   Si un dato falta: devuelve null + caveat, nunca un valor inventado.
5. Respeta los contratos JSON de §6.1 y §11 al pie de la letra.
6. Los textos de UI son los de §13 (no los reescribas).
7. El modo demo (DATA_MODE=demo) debe funcionar sin red con data/fixtures.
8. Al terminar cada fase, ejecuta: pytest, tsc --noEmit, y un smoke test E2E del flujo.

Criterio de aceptación global: un usuario introduce una finca y en < 60 s obtiene
una rotación distinta a la suya, con IRS, comparación vs baseline y ≥3 hallazgos
explicativos; y la app funciona con el wifi apagado.
```

---

## 16. Pruebas y validación

### 16.1 Pirámide

| Nivel | Qué | Herramienta |
|---|---|---|
| Unitario (60 %) | Fórmulas §10 con casos calculados a mano | pytest |
| Propiedades (10 %) | Monotonía e invarianza | hypothesis |
| Contrato (15 %) | Esquemas JSON de §11 | pytest + `schemas/` |
| Integración (10 %) | Proveedores con fixtures grabados (VCR) | pytest-recording |
| E2E (5 %) | 5 flujos de usuario | Playwright |

### 16.2 Tests dorados obligatorios (bloqueantes)

| ID | Test | Tolerancia |
|---|---|---|
| T1 | ET0 FAO-56 contra ejemplos del cap. 4 de FAO-56 | ±2 % |
| T2 | Balance hídrico: 100 mm de lluvia sobre suelo seco ⇒ D baja 100 mm (sin ET) | exacto |
| T3 | `Ks = 1` cuando `D ≤ RAW`; `Ks = 0` cuando `D ≥ TAW` | exacto |
| T4 | SPEI de una serie sintética con sequía inyectada < −1,5 | ±0,1 |
| T5 | GDD acumulado de un ciclo maíz (base 10) ≈ 1 700 ± 100 | ±6 % |
| T6 | Periodo de retorno Gumbel: cuantil de 10 años para serie sintética conocida | ±5 % |
| T7 | `I_diversidad` = 100 con 4 cultivos equiprobables y `max_crops=4` | exacto |
| T8 | Rotación generada nunca viola R1–R10 (property test sobre 200 perfiles) | 0 violaciones |
| T9 | `IRS` siempre en [0, 100] (property test) | exacto |
| T10 | `NIR` ≥ 0 y `ETa ≤ ETm` siempre | exacto |

### 16.3 Validación con datos reales (evidencia para el jurado)

| Validación | Método | Criterio de éxito |
|---|---|---|
| ET0 del motor | Comparar con MOD16A2 (PET) en 5 celdas, 2001–2023 | r > 0,7, sesgo < 20 % |
| Balance hídrico | Comparar `D` normalizado con `sm_rootzone` SMAP | r > 0,5 |
| Proxy de rendimiento | `iNDVI` vs rendimiento declarado en fincas demo | dirección correcta en ≥ 70 % de años |
| SPEI | Reproducir un evento de sequía documentado de la zona | clasificación coincide |
| Rotación | Revisión de un ingeniero agrónomo | "agronómicamente plausible" por escrito |

**Estos resultados van al pitch.** Un producto que muestra su validación es mucho más creíble que uno que solo muestra gráficos bonitos.

### 16.4 Ensayo de demo

- 3 ensayos completos cronometrados.
- Uno con wifi apagado.
- Uno en un portátil distinto al de desarrollo.
- Uno con un usuario que no conoce la app (test de usabilidad de 5 min).

---

## 17. Riesgos y mitigaciones

| # | Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | Las APIs de NASA fallan o van lentas durante la demo | Alta | Alto | Modo `demo` con fixtures; caché local; nunca demo en vivo sin respaldo |
| R2 | Los datos de 0,5° no representan la finca y el jurado lo señala | Media | Alto | Declararlo proactivamente (§7.4) y usar HLS 30 m donde exista; convertirlo en fortaleza ("somos honestos con la escala") |
| R3 | El optimizador tarda demasiado | Media | Alto | Precomputo aditivo + DP (§10.7.7); límite duro de 45 s con fallback a top-5 |
| R4 | Los umbrales de enfermedad son incorrectos | Alta | Medio | Etiquetar como "pendiente de validación"; revisión agronómica; no prescribir |
| R5 | El IRS parece arbitrario | Media | Medio | Desglose visible, pesos en config, declaración explícita de que es un índice propio |
| R6 | El equipo se dispersa en funcionalidades | Alta | Alto | Corte MVP §15.2; F1 primero; el resto solo si F1 está cerrado |
| R7 | Confusión legal: parece asesoramiento profesional | Media | Medio | Descargos en UI y PDF; lenguaje de "simulación" |
| R8 | Sobreajuste a una sola finca demo | Media | Alto | Probar con 3 fincas de climas distintos (semiárido, templado húmedo, mediterráneo) |
| R9 | Fuga de credenciales Earthdata al repo | Baja | Alto | `.env` en `.gitignore`; chequeo en CI; rotar si ocurre |
| R10 | El jurado pregunta "¿qué es nuevo?" y la respuesta es "un dashboard" | Media | Alto | El diferencial es el **motor de escenarios + explicación**: insistir en §10.6 y §10.7.8 |

---

## 18. Anexos

### Anexo A — `FarmProfile` de ejemplo (listo para copiar y pegar)

```jsonc
{
  "name": "Finca El Olivar",
  "location": { "lat": 37.3912, "lon": -4.0231, "elevation_m": 320,
                "admin": { "country": "ES", "region": "AN", "municipality": "Córdoba" } },
  "boundary": null,
  "area_ha": 12.4,
  "current_crops": [
    { "crop_id": "wheat_durum", "season": "2025-26", "area_ha": 8.0 },
    { "crop_id": "sunflower",   "season": "2026S",   "area_ha": 4.4 }
  ],
  "preferred_crops": ["chickpea"],
  "excluded_crops": ["rice", "cotton"],
  "resources": {
    "water": { "source": "well", "available_m3_per_year": 9000,
               "flow_l_s": 4.5, "cost_eur_per_m3": 0.12, "quality": "good" },
    "irrigation": { "existing_system": "none", "condition": "n/a",
                    "energy": "grid", "hours_per_day_available": 8 },
    "machinery": ["tractor_90hp", "seeder", "plough", "sprayer"],
    "labor": { "permanent": 1, "seasonal": 2 },
    "budget_eur_per_year": 15000,
    "inputs": { "organic_matter": false, "compost_t_per_year": 0, "cover_crop_seed": false },
    "storage": { "capacity_t": 20, "dryer": false },
    "soil_tests": { "texture": null, "ph": null, "organic_matter_pct": null, "depth_cm": null }
  },
  "constraints": { "horizon_seasons": 8, "seasons_per_year": 2,
                   "must_include": ["chickpea"], "max_crops": 4, "organic_only": false },
  "preferences": { "objective": "balanced", "risk_tolerance": "medium" }
}
```

### Anexo B — Esquema de parámetros de cultivo

```yaml
# data/catalog/crops.yaml  (una entrada por cultivo)
- id: wheat_durum
  name_es: "Trigo duro"
  name_sci: "Triticum turgidum subsp. durum"
  family: poaceae
  cycle_type: annual
  season: W
  is_legume: false
  kc: { ini: 0.40, mid: 1.15, end: 0.30 }
  stage_days: { ini: 30, dev: 140, mid: 60, late: 30 }
  zr_max_m: 1.5
  p_depletion: 0.55
  gdd_base_c: 0
  gdd_to_maturity: 2100
  ky: 1.15
  t_frost_critical_c: -4
  t_heat_critical_c: 32
  flowering_window_days: 30
  hse_ref: 45
  fse_ref: 20
  sowing_window: [ { season: W, doy_from: 290, doy_to: 340 } ]
  yield_potential_t_ha: 4.5          # ⚠️ supuesto regional (D8)
  price_eur_t: 260                   # solo si D9 = sí
```

**Tabla de partida `[P]` — verificar contra FAO-56 (tabla 12) y FAO-33 antes de usar en producción:**

| Cultivo | `kc.ini` | `kc.mid` | `kc.end` | `gdd_base` | `gdd_madurez` | `ky` | `zr_max` | `p` | `T_helada` | `T_calor` |
|---|---|---|---|---|---|---|---|---|---|---|
| Trigo duro | 0,40 | 1,15 | 0,30 | 0 | 2 100 | 1,15 | 1,5 | 0,55 | −4 | 32 |
| Trigo blando | 0,40 | 1,15 | 0,30 | 0 | 2 100 | 1,15 | 1,5 | 0,55 | −4 | 32 |
| Cebada | 0,30 | 1,15 | 0,25 | 0 | 1 900 | 1,10 | 1,2 | 0,55 | −5 | 32 |
| Maíz | 0,30 | 1,20 | 0,35 | 10 | 1 700 | 1,25 | 1,7 | 0,55 | 0 | 35 |
| Girasol | 0,35 | 1,10 | 0,35 | 7 | 1 500 | 1,00 | 1,5 | 0,45 | −2 | 34 |
| Garbanzo | 0,40 | 1,05 | 0,35 | 4,5 | 1 300 | 0,85 | 1,0 | 0,50 | −3 | 32 |
| Guisante | 0,50 | 1,15 | 0,30 | 4,5 | 1 200 | 1,00 | 0,8 | 0,45 | −3 | 30 |
| Tomate | 0,60 | 1,15 | 0,80 | 10 | 1 400 | 1,05 | 1,0 | 0,40 | 0 | 35 |
| Vid | 0,30 | 0,70 | 0,45 | 10 | 1 800 | 0,85 | 2,0 | 0,45 | −2 | 36 |
| Olivo | 0,65 | 0,70 | 0,65 | 10 | 2 500 | 0,80 | 1,5 | 0,65 | −5 | 38 |

**Regla:** esta tabla es un **punto de partida documentado**, no una verdad agronómica. Cada valor debe poder trazarse a FAO-56/FAO-33 o a una fuente local, y el archivo `crops.yaml` debe citarla en un campo `source`.

### Anexo C — Checklist de datos a preparar antes de codificar

- [ ] `crops.yaml` con **8–12 cultivos** de la región piloto (D6, D7).
- [ ] `diseases.yaml` con **10–15 pares cultivo–enfermedad** y umbrales (D11).
- [ ] `hazards.yaml` con los **8 peligros** y sus textos de protocolo.
- [ ] `rotation_effects.yaml` con la matriz predecesor→sucesor.
- [ ] `scoring.yaml` con los pesos del IRS.
- [ ] `irrigation_systems.yaml` con eficiencias y costes de referencia.
- [ ] `.env`: `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`, `FIRMS_MAP_KEY`, `DATA_MODE`.
- [ ] 3 fincas demo en 3 climas distintos, con datos precargados.
- [ ] Revisión de un ingeniero agrónomo (aunque sea 30 minutos por videollamada).

### Anexo D — Chuleta de símbolos

| Símbolo | Unidad | Significado |
|---|---|---|
| `ET0` | mm/d | Evapotranspiración de referencia |
| `ETc` | mm/d | Evapotranspiración del cultivo |
| `Kc` | — | Coeficiente de cultivo |
| `Ks` | — | Coeficiente de estrés hídrico |
| `TAW` | mm | Agua total disponible |
| `RAW` | mm | Agua fácilmente disponible |
| `D` | mm | Agotamiento |
| `NIR` | mm | Necesidad neta de riego |
| `Pe` | mm | Lluvia efectiva |
| `GDD` | °C·d | Grados día de crecimiento |
| `HSE` | °C·d | Exposición a estrés térmico |
| `FSE` | °C·d | Exposición a helada |
| `SPI` / `SPEI` | — | Índices estandarizados de sequía |
| `VCI` | % | Índice de condición de la vegetación |
| `FI` | 0–100 | Índice de favorabilidad de enfermedad |
| `IRS` | 0–100 | Índice de Resiliencia ROOTSHIFT |
| `CV` | — | Coeficiente de variación |
| `CVaR10` | — | Media del 10 % peor |
| `y`/`T` | años | Periodo de retorno |

### Anexo E — Siglas

DAAC · Distributed Active Archive Center · GES DISC · Goddard Earth Sciences Data and Information Services Center · LP DAAC · Land Processes DAAC · NSIDC · National Snow and Ice Data Center · PO.DAAC · Physical Oceanography DAAC · HLS · Harmonized Landsat-Sentinel · SMAP · Soil Moisture Active Passive · GPM/IMERG · Global Precipitation Measurement / Integrated Multi-satellitE Retrievals for GPM · GLDAS · Global Land Data Assimilation System · MODIS · Moderate Resolution Imaging Spectroradiometer · NASADEM · NASA Digital Elevation Model · NEX-GDDP-CMIP6 · NASA Earth Exchange Global Daily Downscaled Projections · FIRMS · Fire Information for Resource Management System · SSP · Shared Socioeconomic Pathway · WMO · World Meteorological Organization · FAO · Food and Agriculture Organization.

### Anexo F — Referencias

- NASA POWER · documentación de la API diaria: <https://power.larc.nasa.gov/docs/services/api/temporal/daily/>
- SMAP L4 `SPL4SMGP` v007: <https://www.earthdata.nasa.gov/data/catalog/nsidc-cprd-spl4smgp-007>
- GPM IMERG `GPM_3IMERGDF` V07: <https://www.earthdata.nasa.gov/es/data/catalog/ges-disc-gpm-3imergdf-07>
- GLDAS (NASA GES DISC): <https://disc.gsfc.nasa.gov/datasets?keywords=GLDAS>
- MODIS Vegetation Indices `MOD13Q1` v061: <https://www.earthdata.nasa.gov/fr/data/catalog/lpcloud-mod13q1-061>
- MODIS ET `MOD16A2` v061: <https://www.earthdata.nasa.gov/es/data/catalog/lpcloud-myd16a2-061>
- HLS v2.0: <https://catalog.data.gov/dataset/hls-landsat-operational-land-imager-surface-reflectance-and-toa-brightness-daily-global-30>
- NASADEM: <https://lpdaac.usgs.gov/product_search/?query=nasadem>
- NEX-GDDP-CMIP6: <https://www.nccs.nasa.gov/services/data-collections/land-based-products/nex-gddp-cmip6>
- NASA FIRMS: <https://firms.modaps.eosdis.nasa.gov/>
- NASA Harvest: <https://www.nasaharvest.org/>
- FAO-56 (Allen et al., 1998), *Crop evapotranspiration* — ET0, Kc, TAW/RAW/Ks.
- FAO-33 (Doorenbos & Kassam, 1979), *Yield response to water* — factor Ky.
- Vicente-Serrano et al. (2010), SPEI — cálculo del índice.
- Kogan (1995), VCI — índice de condición de la vegetación.

---

## 19. Decisiones abiertas (requiere validación del equipo)

> **Instrucción:** cada decisión tiene un valor por defecto ya asumido en el documento. Si no se responde, el implementador usará la recomendación. Cambiar una decisión después de empezar implica retrabajo; cambiarla antes es gratis.
>
> **Prioridad de respuesta:** las marcadas 🔴 bloquean el arranque. Las 🟡 bloquean una funcionalidad concreta. Las 🟢 se pueden decidir sobre la marcha.

### Resumen

| ID | Decisión | Prioridad | Recomendación |
|---|---|---|---|
| D1 | Escala de análisis: punto vs polígono; clima 0,5° vs 30 m | 🔴 | Híbrido: punto para clima, polígono para superficie |
| D2 | Fuente de datos de suelo | 🔴 | NASA + SoilGrids como suplemento declarado |
| D3 | Modelo de rendimiento | 🔴 | FAO-33 (agua) + factores térmicos |
| D4 | Optimizador de rotación | 🔴 | DP aditivo + Monte Carlo + búsqueda local |
| D5 | Escenarios futuros | 🟡 | Histórico + NEX-GDDP (2 SSP, ≥5 GCM) |
| D6 | Catálogo inicial de cultivos | 🔴 | 8–12 de la región piloto |
| D7 | Región piloto | 🔴 | España mediterránea (secano cerealista) |
| D8 | Origen del rendimiento potencial `Ym` | 🟡 | Tabla regional propia, declarada como supuesto |
| D9 | Módulo económico | 🟢 | No en v1; solo coste de riego |
| D10 | Nivel de ingeniería del riego | 🟡 | Dimensionamiento indicativo, no proyecto |
| D11 | Catálogo de enfermedades y validación | 🟡 | 10–15 pares, validados por agrónomo |
| D12 | Alcance de catástrofes y playbooks | 🟡 | 7 calculables + granizo solo protocolo |
| D13 | Arquitectura: monolito vs split; precomputado vs vivo | 🔴 | Split (Next.js + FastAPI), híbrido precomputado |
| D14 | Cuentas de usuario y persistencia | 🟢 | Sesión anónima + cuenta opcional |
| D15 | LLM para explicaciones | 🟢 | No en v1; plantillas deterministas |
| D16 | Idiomas y unidades | 🟢 | Español ES, métrico |
| D17 | Horizonte y granularidad de la rotación | 🟡 | 8 temporadas (4 años), 2 por año |
| D18 | Demo con datos precargados | 🔴 | Sí, obligatorio |
| D19 | Postura legal y de marca | 🟡 | Descargos + sin logo NASA |
| D20 | Métrica de éxito del producto | 🟡 | `E[P]` + `P_fallo` + `T_recuperación` |

---

### D1 · Escala de análisis 🔴

**Pregunta:** ¿la finca se modela como un punto (lat/lon) o como un polígono con superficie?

| Opción | Consecuencia |
|---|---|
| **A. Punto** | Simple, rápido, suficiente para clima de 0,5°. No permite hablar de "hectáreas" ni de zonas de riego. |
| **B. Polígono** | Permite área, zonas de riego, mapas reales y F4 con recorte. Requiere dibujo y cálculo de área. |
| **C. Híbrido (recomendado)** | El clima se toma del punto (centroide). El polígono se usa para superficie, zonas y mapa. Si no hay polígono, se pide el área manualmente. |

**Por qué importa:** sin polígono no hay "mapa ilustrativo" de F3 ni vista de finca de F4. Con solo polígono, el motor se complica innecesariamente.
**Recomendación:** **C**.
**Bloquea:** F3 (mapa), F4, cálculo de producción total en toneladas.

---

### D2 · Datos de suelo 🔴

**Pregunta:** la NASA no publica textura de suelo. ¿Qué hacemos?

| Opción | Consecuencia |
|---|---|
| **A. Solo NASA** | Se pierde `TAW` real: se asume suelo franco (θFC 0,30, θWP 0,15) para todos. El balance hídrico queda genérico. |
| **B. NASA + SoilGrids (recomendado)** | ISRIC SoilGrids 250 m aporta textura, pH y MO. Es no-NASA: hay que declararlo. Mejora mucho `TAW`, escorrentía y erosión. |
| **C. Preguntar al usuario** | Analítica de suelo del agricultor (si la tiene). La mejor precisión, la peor tasa de respuesta. |
| **D. B + C** | SoilGrids como defecto, editable con analítica real. |

**Por qué importa:** `TAW` determina todo el balance hídrico y por tanto F1 y F3. Un suelo arenoso y uno arcilloso dan recomendaciones opuestas.
**Recomendación:** **D**, con SoilGrids declarado como fuente complementaria en la UI (el jurado valora la honestidad, no la pureza).
**Riesgo:** si el hackathon exige "solo datasets NASA", esta decisión cambia a **A**. Confirmarlo con las bases.

---

### D3 · Modelo de rendimiento 🔴

**Pregunta:** ¿cómo se pasa de "clima" a "producción"?

| Opción | Consecuencia | Esfuerzo |
|---|---|---|
| **A. Proxy satelital (iNDVI)** | Solo describe el pasado. No sirve para escenarios. Barato. | Bajo |
| **B. FAO-33 agua + factores térmicos (recomendado)** | Transparente, explicable, robusto, implementable en 200 líneas. Sensible a `Ky` y `Ym`. | Medio |
| **C. Modelo de cultivo (DSSAT/AquaCrop)** | Mucho más realista. Requiere calibración por cultivo, datos de suelo y tiempo. Riesgo alto en hackathon. | Alto |
| **D. Machine learning** | Necesita datos de rendimiento etiquetados que no tenemos. | Alto |

**Por qué importa:** define el techo de credibilidad del producto. Un modelo de cultivo mal calibrado es peor que un FAO-33 honesto.
**Recomendación:** **B**, con A como evidencia histórica complementaria. Mencionar C como trabajo futuro en el pitch.
**Nota:** POWER ofrece salida en formato **ICASA**, compatible con DSSAT. Si alguien del equipo tiene experiencia, C es un diferenciador enorme. Pero no se empieza por ahí.

---

### D4 · Optimizador 🔴

**Pregunta:** ¿cómo se busca "la mejor rotación"?

| Opción | Consecuencia |
|---|---|
| **A. Fuerza bruta** | El espacio de búsqueda `C^N` es inabordable (10⁸ combinaciones). Solo válido si hay ≤ 4 cultivos y ≤ 4 temporadas. |
| **B. Solo heurística (beam search)** | Rápido, pero sin garantía y difícil de explicar. |
| **C. DP aditivo + MC + búsqueda local (recomendado)** | Exacto bajo el supuesto de dependencia de primer orden, y con evaluación completa de las mejores. Explicable. |
| **D. MILP exacto** | "Óptimo global" en el pitch. Requiere linealizar el rendimiento: se pierde realismo o se complica mucho. |

**Recomendación:** **C**. Si el equipo quiere el titular "optimización exacta", añadir D solo para la asignación de superficie (D4b).
**Bloquea:** F1.

---

### D5 · Escenarios futuros 🟡

**Pregunta:** ¿se incluyen proyecciones climáticas o solo historia?

| Opción | Consecuencia |
|---|---|
| **A. Solo histórico (1991–2020)** | Simple y defendible. Pero el discurso "varios futuros posibles" pierde fuerza. |
| **B. Histórico + 2 SSP × ≥5 GCM (recomendado)** | Cumple el relato del pitch: "no predecimos, preparamos para varios futuros". Coste: descargar y procesar NEX-GDDP. |
| **C. B + 4 SSP** | Más completo, más ruido en la UI. |

**Recomendación:** **B** (SSP2-4.5 y SSP5-8.5, 5 GCM, horizonte 2031–2050). Descargar una sola vez y cachear.
**Riesgo:** NEX-GDDP es 0,25° y puede no tener el GCM que el jurado espere. Documentar la lista exacta de modelos usados.

---

### D6 · Catálogo inicial de cultivos 🔴

**Pregunta:** ¿cuántos cultivos y cuáles?

- **Recomendación:** 8–12, elegidos por la región piloto (D7). Ejemplo para España mediterránea: trigo duro, trigo blando, cebada, maíz, girasol, garbanzo, guisante, veza, vid, olivo, tomate, remolacha.
- **Por qué no 50:** cada cultivo exige parámetros validados (Kc, Ky, GDD, ventanas). 50 cultivos mal parametrizados es peor que 10 bien.
- **Bloquea:** el formulario de cultivos y todo F1.

---

### D7 · Región piloto 🔴

**Pregunta:** ¿la app es global o se enfoca en una región?

| Opción | Consecuencia |
|---|---|
| **A. Global** | POWER cubre el mundo; el catálogo de cultivos y enfermedades se vuelve inmanejable. |
| **B. Región piloto (recomendado)** | Demo creíble, catálogo corto, validación posible con un agrónomo local. |
| **C. España + LatAm** | Dos catálogos. Duplica el trabajo. |

**Recomendación:** **B** — España mediterránea (secano cerealista + regadío). La arquitectura queda global; el contenido, local.
**Nota:** la elección condiciona el idioma del pitch y los ejemplos. Confirmar antes de escribir `crops.yaml`.

---

### D8 · Rendimiento potencial `Ym` 🟡

**Pregunta:** ¿de dónde sale el techo de producción?

| Opción | Consecuencia |
|---|---|
| **A. Tabla regional propia** | Rápido. Hay que declararlo como supuesto y admitir que es un valor medio. |
| **B. FAOSTAT / estadísticas nacionales** | Defendible y citable, aunque es dato agregado, no de parcela. |
| **C. Lo declara el usuario** | Máxima precisión, mínima adopción. |

**Recomendación:** **A + C**: tabla como defecto, campo opcional "tu rendimiento medio" que la sobrescribe.
**Por qué importa:** `Y_m` multiplica todo. Si el jurado pregunta "¿de dónde sale 4,5 t/ha?", debe haber respuesta.

---

### D9 · Módulo económico 🟢

**Pregunta:** ¿se calcula margen bruto (ingresos − costes)?

- **A. No (recomendado para v1):** el objetivo del usuario es producción y resiliencia, no rentabilidad. Añadir economía duplica el catálogo de datos (precios, costes por labor).
- **B. Sí, solo coste del agua y del riego:** asumible, útil en F3.
- **C. Sí, margen completo:** fuera de alcance en hackathon.

**Recomendación:** **B**.

---

### D10 · Nivel de ingeniería del riego 🟡

**Pregunta:** ¿hasta dónde llega F3?

| Opción | Consecuencia |
|---|---|
| **A. Cualitativo** | "Te conviene goteo". Poco diferencial. |
| **B. Indicativo con números (recomendado)** | Caudal, zonas, calendario, materiales. Defendible con el descargo de "requiere proyecto técnico". |
| **C. Proyecto ejecutable** | Presiones, diámetros, pérdidas de carga reales. Imposible sin topografía fina y sin responsabilidad legal. |

**Recomendación:** **B**. El descargo no es debilidad: es lo que permite dar números sin mentir.

---

### D11 · Enfermedades 🟡

**Pregunta:** ¿qué alcance y qué validación?

- **Catálogo:** 10–15 pares cultivo–enfermedad de la región piloto.
- **Modelo:** favorabilidad climática (§10.9), no diagnóstico.
- **Validación:** 30 min con un ingeniero agrónomo o un técnico de cooperativa. Sin esa revisión, la UI debe decir "umbrales preliminares".
- **Fotos/diagnóstico por imagen:** **fuera de alcance**. Si el equipo quiere, es una funcionalidad nueva con su propio modelo y su propio riesgo.

---

### D12 · Catástrofes 🟡

**Pregunta:** ¿qué peligros entran y con qué profundidad?

- **Calculables:** sequía, inundación, helada, calor, viento, incendio, erosión.
- **Solo protocolo:** granizo (sin dato NASA).
- **Playbooks:** 3–5 pasos por fase (antes/durante/después). Más pasos no se leen.
- **Decisión pendiente:** ¿se incluye un protocolo específico por cultivo o solo general? Recomendación: general + 1 nota específica si el cultivo está en el catálogo.

---

### D13 · Arquitectura 🔴

**Pregunta:** ¿monolito Next.js o Next.js + FastAPI?

| Opción | Consecuencia |
|---|---|
| **A. Monolito Next.js (TS)** | Un solo despliegue. Pero sin `xarray`/`netCDF`/`rasterio`/MILP: la parte geo-científica se sufre. |
| **B. Next.js + FastAPI (recomendado)** | Dos despliegues, pero cada uno con su ecosistema. Python hace los cálculos, JS pinta. |
| **C. Todo Python (Streamlit/Dash)** | Rápido de prototipar, pésimo para una UI que debe impresionar. |

**Subdecisión D13b:** ¿el cálculo se hace en vivo o se precomputa?
**Recomendación:** híbrido — contexto y escenarios precomputados por celda; rotación y riego en vivo (son rápidos una vez existe el contexto).
**Bloquea:** todo el desarrollo.

---

### D14 · Cuentas y persistencia 🟢

- **A. Sesión anónima (recomendado):** cero fricción, cero RGPD complejo. La finca dura 30 días.
- **B. Cuenta con email:** permite "mis fincas", pero añade login, verificación y política de privacidad.
- **C. A + B:** anónimo por defecto, "guarda tu finca" opcional.
**Recomendación:** **C** si sobra tiempo; **A** si no.

---

### D15 · LLM para las explicaciones 🟢

**Pregunta:** ¿las frases de "por qué" las genera un LLM o plantillas?

| Opción | Consecuencia |
|---|---|
| **A. Plantillas deterministas (recomendado)** | Reproducible, testeable, sin alucinaciones, sin coste, sin latencia. Las frases suenan algo rígidas. |
| **B. LLM con datos inyectados** | Frases naturales, pero riesgo de inventar cifras y de no ser reproducible. |
| **C. Plantillas + LLM solo para el resumen ejecutivo** | Compromiso: el texto libre se genera a partir de los hallazgos ya calculados. |

**Recomendación:** **A** para v1. Si se usa **C**, el LLM nunca recibe la tarea de calcular: solo de redactar hechos ya calculados, y el resultado se revisa con un guardarraíl numérico.

---

### D16 · Idiomas y unidades 🟢

- Español (ES) por defecto. Inglés si el pitch es internacional.
- Métrico. Sin imperial.
- **Recomendación:** ES + estructura i18n preparada, sin traducir todavía.

---

### D17 · Horizonte de la rotación 🟡

**Pregunta:** ¿cuántas temporadas y con qué granularidad?

| Opción | Consecuencia |
|---|---|
| **A. 2 años / 4 temporadas** | Rápido de calcular, pero no se ven los efectos plurianuales (leguminosa cada 3). |
| **B. 4 años / 8 temporadas (recomendado)** | Captura el ciclo de rotación clásico y el efecto de la leguminosa. |
| **C. 6 años / 12 temporadas** | Mejor para perennes y suelos, pero el usuario no planifica a 6 años y el cálculo crece. |

**Recomendación:** **B**, configurable en `constraints.horizon_seasons`.

---

### D18 · Demo con datos precargados 🔴

**Pregunta:** ¿se acepta que la demo use datos descargados y cacheados previamente?

- **Sí (recomendado, y honesto):** los datos **son** de la NASA, descargados con antelación. La app sigue teniendo modo vivo. Se declara en la UI con la etiqueta `data_mode`.
- **No:** la demo depende del wifi del recinto y de la latencia de GES DISC. Riesgo inaceptable.
**Recomendación:** **Sí**, con el modo vivo disponible como prueba de que no es una maqueta.

---

### D19 · Postura legal y de marca 🟡

- Sin logo ni nombres de la NASA que sugieran afiliación.
- Descargos visibles: no es asesoramiento agronómico; no es predicción meteorológica; protocolos orientativos.
- Licencia del código: MIT.
- **Recomendación:** redactar un `DISCLAIMER.md` y enlazarlo desde el pie de la app.

---

### D20 · Métrica de éxito 🟡

**Pregunta:** ¿qué número preside el pitch?

| Opción | Por qué |
|---|---|
| **A. Producción esperada** `E[P]` | Es lo que el agricultor entiende. |
| **B. Probabilidad de fallo** `P_fallo` | Es lo que le quita el sueño. |
| **C. A + B + tiempo de recuperación (recomendado)** | Cubre literalmente "máxima producción durante el mayor tiempo posible". |
| **D. IRS** | Atractivo, pero es un índice propio: mejor como acompañante, no como titular. |

**Recomendación:** **C**, con el IRS como número secundario.

---

### ✅ Checklist de desbloqueo (8 respuestas)

Responde estas ocho y el desarrollo puede empezar sin ambigüedades:

1. **D13** — ¿Next.js + FastAPI o monolito? → desbloquea el repo.
2. **D7** — ¿Región piloto? → desbloquea catálogos y demo.
3. **D6** — ¿Lista de cultivos? → desbloquea `crops.yaml`.
4. **D2** — ¿Se permite un suplemento no-NASA para el suelo? → desbloquea el balance hídrico.
5. **D3** — ¿FAO-33 o modelo de cultivo? → desbloquea el motor de rendimiento.
6. **D4** — ¿DP+MC o MILP? → desbloquea F1.
7. **D5** — ¿Incluimos NEX-GDDP? → desbloquea el relato de "varios futuros".
8. **D18** — ¿Demo con caché? → desbloquea el plan de pruebas.

Todo lo demás (`🟡` y `🟢`) puede decidirse durante el desarrollo con la recomendación por defecto.

### Tabla de validación del equipo

| Decisión | Responsable | Fecha | Opción elegida | Notas |
|---|---|---|---|---|
| D1 | | | | |
| D2 | | | | |
| D3 | | | | |
| D4 | | | | |
| D5 | | | | |
| D6 | | | | |
| D7 | | | | |
| D8 | | | | |
| D9 | | | | |
| D10 | | | | |
| D11 | | | | |
| D12 | | | | |
| D13 | | | | |
| D14 | | | | |
| D15 | | | | |
| D16 | | | | |
| D17 | | | | |
| D18 | | | | |
| D19 | | | | |
| D20 | | | | |

---

*Fin de la especificación. Versión 1.0 — cualquier cambio en §10 (fórmulas), §7 (datos) o §11 (contratos) obliga a subir la versión y a revisar los tests dorados.*
