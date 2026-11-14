"""PDF and CSV export of a rotation report (spec 3.1, 13.3).

The PDF is a one-to-two page printable summary: farm, context, resilience index,
rotation, scenarios, nutrients and caveats. Every number carries its caveat and
the attribution footer, because a report outlives the screen it came from.
"""

from __future__ import annotations

import csv
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .. import catalog, config

ACCENT = colors.HexColor("#2f6b3f")
INK = colors.HexColor("#1b231c")
MUTED = colors.HexColor("#5a6b5f")
LINE = colors.HexColor("#c9d6cc")
HEAD_BG = colors.HexColor("#eef3ee")

LABELS = {
    "en-US": {
        "title": "ROOTSHIFT · Field report",
        "subtitle": "Rotation resilience assessment",
        "field": "Field",
        "county": "County",
        "area": "Area",
        "date": "Date",
        "confidence": "Confidence",
        "resilience": "Resilience index",
        "production": "Production index",
        "p10": "p10",
        "p90": "p90",
        "fail": "Bad-season chance",
        "recovery": "Recovery after the worst year",
        "three": "Three dry years in a row",
        "rotation": "Proposed rotation",
        "season": "Season",
        "crop": "Crop",
        "family": "Family",
        "water": "Water demand (mm)",
        "yield": "Yield (t/ha)",
        "scenarios": "Scenarios",
        "scenario": "Scenario",
        "p50": "p50",
        "cv": "CV",
        "nutrients": "Nutrient balance",
        "item": "Item",
        "value": "Value",
        "findings": "Why this rotation",
        "sources": "Data sources",
        "product": "Product",
        "variable": "Variable",
        "resolution": "Resolution",
        "period": "Period",
        "caveats": "Caveats",
        "disclaimer": "Simulated results, not predictions. A technical adviser should review any change.",
        "attribution": "Data provided by NASA and USDA-NRCS. Universidad de Alicante.",
        "legal": "ROOTSHIFT is a simulation tool. It is not affiliated with, or endorsed by, NASA, USDA or the University of Alicante.",
        "nRemoval": "N removal (kg/ha)",
        "nFix": "N fixation credit (kg/ha)",
        "nApplied": "N applied (kg/ha)",
        "nBalance": "N balance (kg/ha)",
        "pBalance": "P2O5 balance (kg/ha)",
        "kBalance": "K2O balance (kg/ha)",
        "years": "yr",
    },
    "es-ES": {
        "title": "ROOTSHIFT · Informe de parcela",
        "subtitle": "Evaluación de la resiliencia de la rotación",
        "field": "Parcela",
        "county": "Condado",
        "area": "Superficie",
        "date": "Fecha",
        "confidence": "Confianza",
        "resilience": "Índice de resiliencia",
        "production": "Índice de producción",
        "p10": "p10",
        "p90": "p90",
        "fail": "Probabilidad de campaña mala",
        "recovery": "Recuperación tras el peor año",
        "three": "Tres años secos seguidos",
        "rotation": "Rotación propuesta",
        "season": "Campaña",
        "crop": "Cultivo",
        "family": "Familia",
        "water": "Demanda de agua (mm)",
        "yield": "Rendimiento (t/ha)",
        "scenarios": "Escenarios",
        "scenario": "Escenario",
        "p50": "p50",
        "cv": "CV",
        "nutrients": "Balance de nutrientes",
        "item": "Concepto",
        "value": "Valor",
        "findings": "Por qué esta rotación",
        "sources": "Fuentes de datos",
        "product": "Producto",
        "variable": "Variable",
        "resolution": "Resolución",
        "period": "Periodo",
        "caveats": "Advertencias",
        "disclaimer": "Resultados simulados, no predicciones. Cualquier cambio debería revisarlo un técnico.",
        "attribution": "Datos de NASA y USDA-NRCS. Universidad de Alicante.",
        "legal": "ROOTSHIFT es una herramienta de simulación. No está afiliada ni respaldada por la NASA, el USDA ni la Universidad de Alicante.",
        "nRemoval": "Extracción de N (kg/ha)",
        "nFix": "Crédito de fijación de N (kg/ha)",
        "nApplied": "N aportado (kg/ha)",
        "nBalance": "Balance de N (kg/ha)",
        "pBalance": "Balance de P2O5 (kg/ha)",
        "kBalance": "Balance de K2O (kg/ha)",
        "years": "años",
    },
}


FINDING_TEMPLATES = {
    "WATER_GAP_COVERED": {
        "en": "The proposed rotation cuts seasonal irrigation demand by {pct}% versus the current one.",
        "es": "La rotación propuesta reduce la demanda estacional de riego un {pct}% frente a la actual.",
    },
    "LEGUME_BREAK": {
        "en": "Adds {count} legume season(s), breaking the cereal disease cycle.",
        "es": "Añade {count} campaña(s) con leguminosa, rompiendo el ciclo de enfermedades del cereal.",
    },
    "FAMILY_BREAK": {
        "en": "No two consecutive seasons share a plant family.",
        "es": "Ninguna campaña consecutiva repite familia botánica.",
    },
    "PRODUCTION_SHIFT": {
        "en": "Relative production changes by {pct}% versus the current rotation.",
        "es": "La producción relativa cambia un {pct}% frente a la rotación actual.",
    },
    "NUTRIENT_DEFICIT": {
        "en": "Nitrogen removal exceeds inputs plus fixation by {deficit} kg N/ha.",
        "es": "La extracción de nitrógeno supera los aportes más la fijación en {deficit} kg N/ha.",
    },
    "CARBON_GAIN": {
        "en": "The surrounding landscape is a net carbon sink over the reference period.",
        "es": "El entorno es un sumidero neto de carbono en el periodo de referencia.",
    },
    "DROUGHT_SENSITIVITY": {
        "en": "Under a three-year drought the rotation holds an index of {proposed} versus {current} today.",
        "es": "Con tres años secos, la rotación mantiene un índice de {proposed} frente a {current} actual.",
    },
}

CAVEAT_TEMPLATES = {
    "SOIL_REGIONAL": {
        "en": "Soil from a regional survey or default profile; local variability is not represented.",
        "es": "Suelo de un estudio regional o perfil por defecto; no se representa la variabilidad local.",
    },
    "SYNTHETIC_SATELLITES": {
        "en": "Satellite layers are synthetic fixtures (SMAP, MODIS, GLDAS, GAEZ multipliers). Climate and soil are real.",
        "es": "Las capas satelitales son sintéticas (SMAP, MODIS, GLDAS, multiplicadores GAEZ). El clima y el suelo son reales.",
    },
    "SHORT_SERIES": {
        "en": "Short climate series: percentiles are fragile.",
        "es": "Serie climática corta: los percentiles son frágiles.",
    },
    "PRECIP_MIXED": {
        "en": "Monthly precipitation from GPM IMERG; daily extremes from POWER.",
        "es": "Precipitación mensual de GPM IMERG; extremos diarios de POWER.",
    },
}


IRS_TEXT = {
    "highly_resilient": {
        "en": ("Highly resilient", "Holds up across most of the futures tested."),
        "es": ("Muy resiliente", "Resiste bien en la mayoría de los futuros evaluados."),
    },
    "resilient": {
        "en": ("Resilient", "Holds up in most scenarios; water or diversity are the weak points."),
        "es": ("Resiliente", "Resiste en la mayoría de escenarios; flojea en agua o diversidad."),
    },
    "vulnerable": {
        "en": ("Vulnerable", "Works in normal years; loses production in bad ones."),
        "es": ("Vulnerable", "Funciona en años normales; pierde producción en los malos."),
    },
    "highly_vulnerable": {
        "en": ("Highly vulnerable", "High chance of failure under drought or heat."),
        "es": ("Muy vulnerable", "Alta probabilidad de fallo con sequía o calor."),
    },
    "critical": {
        "en": ("Critical", "This system is not sustainable under the scenarios tested."),
        "es": ("Crítico", "Este sistema no es sostenible en los escenarios evaluados."),
    },
}


def _irs_text(irs: dict, locale: str) -> tuple[str, str]:
    entry = IRS_TEXT.get(irs.get("label_code", ""))
    if not entry:
        return irs.get("label", ""), irs.get("description", "") or ""
    return entry["es" if locale.startswith("es") else "en"]


def _render(templates: dict, code: str, locale: str, params: dict, fallback: str) -> str:
    entry = templates.get(code)
    if not entry:
        return fallback
    text = entry["es" if locale.startswith("es") else "en"]
    for key, value in (params or {}).items():
        text = text.replace("{" + key + "}", str(value))
    return text


def _labels(locale: str) -> dict:
    return LABELS["es-ES" if locale.startswith("es") else "en-US"]


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontName="Helvetica-Bold", fontSize=18, textColor=INK, spaceAfter=2, alignment=0),
        "subtitle": ParagraphStyle("s", parent=base["Normal"], fontName="Helvetica", fontSize=10, textColor=MUTED, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11, textColor=ACCENT, spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("b", parent=base["Normal"], fontName="Helvetica", fontSize=8.5, textColor=INK, leading=11),
        "small": ParagraphStyle("sm", parent=base["Normal"], fontName="Helvetica", fontSize=7.5, textColor=MUTED, leading=9.5),
        "finding": ParagraphStyle("f", parent=base["Normal"], fontName="Helvetica", fontSize=8.5, textColor=INK, leading=11, leftIndent=8, bulletIndent=0),
    }


def _table(data, widths, header_bg=HEAD_BG, font_size=8, wrap_body=False):
    # Wrap header cells in Paragraphs so long labels wrap instead of overlapping.
    head_style = ParagraphStyle(
        "th",
        fontName="Helvetica-Bold",
        fontSize=font_size,
        leading=font_size + 1.5,
        textColor=INK,
    )
    body = [data[0]] + data[1:]
    header = [Paragraph(str(cell), head_style) for cell in data[0]]
    if wrap_body:
        body_style = ParagraphStyle(
            "tb",
            fontName="Helvetica",
            fontSize=font_size,
            leading=font_size + 1.5,
            textColor=INK,
        )
        rows = [header] + [[Paragraph(str(cell), body_style) for cell in row] for row in body[1:]]
    else:
        rows = [header] + body[1:]

    table = Table(rows, colWidths=widths, hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                ("TEXTCOLOR", (0, 0), (-1, 0), INK),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("TEXTCOLOR", (0, 1), (-1, -1), INK),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _crop_name(crop_id: str, locale: str) -> str:
    try:
        return catalog.crop_name(crop_id, locale)
    except KeyError:
        return crop_id


def build_pdf(context: dict, rotation: dict, locale: str = "en-US") -> bytes:
    L = _labels(locale)
    S = _styles()
    farm = context["farm"]
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"ROOTSHIFT — {farm.get('name', '')}",
        author="ROOTSHIFT",
        pageCompression=0,  # keeps the text extractable for tests and copy-paste
    )

    story = []
    story.append(Paragraph(L["title"], S["title"]))
    story.append(Paragraph(L["subtitle"], S["subtitle"]))

    meta = [
        [L["field"], farm.get("name", "—"), L["county"], farm.get("county", "—")],
        [L["area"], f"{context['area_ha']} ha", L["date"], date.today().isoformat()],
        [L["confidence"], f"{context['confidence']}/100", "", ""],
    ]
    story.append(_table(meta, [25 * mm, 62 * mm, 25 * mm, 56 * mm]))
    story.append(Spacer(1, 6))

    irs = rotation["irs"]
    m = rotation["metrics"]
    irs_label, irs_desc = _irs_text(irs, locale)
    story.append(Paragraph(L["resilience"], S["h2"]))
    story.append(
        Paragraph(
            f"<b>{irs['value']}/100</b> — {irs_label}. {irs_desc}",
            S["body"],
        )
    )
    story.append(Spacer(1, 4))

    kpis = [
        [L["production"], L["p10"], L["p50"], L["p90"], L["fail"], L["recovery"], L["three"]],
        [
            m["production_index"],
            m["p10_index"],
            m["p50_index"],
            m["p90_index"],
            f"{round(m['p_fail'] * 100)}%",
            f"{m['recovery_years']} {L['years']}",
            f"{round(m['p_drought3'] * 100)}%",
        ],
    ]
    story.append(_table(kpis, [27 * mm, 16 * mm, 16 * mm, 16 * mm, 27 * mm, 32 * mm, 30 * mm]))
    story.append(Spacer(1, 4))

    rows = [[L["season"], L["crop"], L["family"], L["water"], L["yield"]]]
    for item in rotation["sequence"]:
        name = item.get("crop_name_es") if locale.startswith("es") else item.get("crop_name")
        rows.append(
            [
                item.get("season", ""),
                name or _crop_name(item.get("crop_id", ""), locale),
                item.get("family", ""),
                f"{round(item.get('nir_mm') or 0)}",
                f"{item.get('yield_t_ha') or 0:.1f}",
            ]
        )
    rotation_table = _table(rows, [24 * mm, 56 * mm, 34 * mm, 30 * mm, 26 * mm])
    story.append(KeepTogether([Paragraph(L["rotation"], S["h2"]), rotation_table]))
    story.append(Spacer(1, 4))

    srows = [[L["scenario"], L["p10"], L["p50"], L["p90"], L["cv"], L["fail"]]]
    for key in ("S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7"):
        sc = (rotation.get("scenarios") or {}).get(key)
        if not sc:
            continue
        srows.append(
            [
                key,
                sc["p10_index"],
                sc["p50_index"],
                sc["p90_index"],
                f"{sc['cv']:.3f}",
                f"{round(sc['p_fail'] * 100)}%",
            ]
        )
    scenario_table = _table(srows, [22 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 28 * mm])
    story.append(KeepTogether([Paragraph(L["scenarios"], S["h2"]), scenario_table]))
    story.append(Spacer(1, 4))

    nut = rotation["nutrients"]
    mapping = {
        "nRemoval": "n_removal_kg_ha",
        "nFix": "n_fixation_kg_ha",
        "nApplied": "n_input_kg_ha",
        "nBalance": "n_balance_kg_ha",
        "pBalance": "p2o5_balance_kg_ha",
        "kBalance": "k2o_balance_kg_ha",
    }
    nrows = [[L["item"], L["value"]]]
    for key, field_name in mapping.items():
        nrows.append([L[key], nut.get(field_name, "—")])
    nutrient_table = _table(nrows, [70 * mm, 30 * mm])
    story.append(KeepTogether([Paragraph(L["nutrients"], S["h2"]), nutrient_table]))
    story.append(Spacer(1, 4))

    if rotation.get("findings"):
        story.append(Paragraph(L["findings"], S["h2"]))
        for finding in rotation["findings"]:
            text = _render(FINDING_TEMPLATES, finding["code"], locale, finding.get("params", {}), finding.get("text", ""))
            story.append(Paragraph("• " + text, S["finding"]))

    if context.get("caveats"):
        story.append(Paragraph(L["caveats"], S["h2"]))
        codes = context.get("caveat_codes") or []
        for index, caveat in enumerate(context["caveats"]):
            code = codes[index] if index < len(codes) else ""
            story.append(Paragraph("• " + _render(CAVEAT_TEMPLATES, code, locale, {}, caveat), S["small"]))

    from .context import provenance_for

    provenance = provenance_for(context)
    if provenance:
        story.append(Paragraph(L["sources"], S["h2"]))
        prows = [[L["product"], L["variable"], L["resolution"], L["period"]]]
        for entry in provenance[:8]:
            prows.append(
                [
                    entry.get("product", ""),
                    (entry.get("variable") or "")[:42],
                    entry.get("resolution", ""),
                    entry.get("period", ""),
                ]
            )
        story.append(_table(prows, [44 * mm, 62 * mm, 30 * mm, 34 * mm], font_size=7, wrap_body=True))

    story.append(Spacer(1, 8))
    story.append(Paragraph(L["disclaimer"], S["small"]))
    story.append(Paragraph(L["attribution"], S["small"]))
    story.append(Paragraph(L["legal"], S["small"]))
    story.append(Paragraph(f"ROOTSHIFT v{config.MODEL_VERSION}", S["small"]))

    doc.build(story)
    return buffer.getvalue()


def build_csv(context: dict, rotation: dict, locale: str = "en-US") -> str:
    L = _labels(locale)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    farm = context["farm"]
    writer.writerow(["# farm"])
    writer.writerow(["name", farm.get("name", "")])
    writer.writerow(["county", farm.get("county", "")])
    writer.writerow(["area_ha", context["area_ha"]])
    writer.writerow(["confidence", context["confidence"]])
    writer.writerow(["locale", "es-ES" if locale.startswith("es") else "en-US"])
    writer.writerow([])

    irs = rotation["irs"]
    m = rotation["metrics"]
    writer.writerow(["# metrics"])
    writer.writerow(["key", "value"])
    writer.writerow(["irs", irs["value"]])
    writer.writerow(["irs_label", irs.get("label_code", "")])
    writer.writerow(["production_index", m["production_index"]])
    writer.writerow(["p10_index", m["p10_index"]])
    writer.writerow(["p50_index", m["p50_index"]])
    writer.writerow(["p90_index", m["p90_index"]])
    writer.writerow(["p_fail", m["p_fail"]])
    writer.writerow(["recovery_years", m["recovery_years"]])
    writer.writerow(["p_drought3", m["p_drought3"]])
    writer.writerow([])

    writer.writerow(["# rotation"])
    writer.writerow([L["season"], L["crop"], "crop_id", L["family"], "nir_mm", "yield_t_ha"])
    for item in rotation["sequence"]:
        name = item.get("crop_name_es") if locale.startswith("es") else item.get("crop_name")
        writer.writerow([item.get("season", ""), name, item.get("crop_id", ""), item.get("family", ""),
                         item.get("nir_mm"), item.get("yield_t_ha")])
    writer.writerow([])

    writer.writerow(["# scenarios"])
    writer.writerow(["scenario", "p10_index", "p50_index", "p90_index", "cv", "p_fail"])
    for key in ("S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7"):
        sc = (rotation.get("scenarios") or {}).get(key)
        if sc:
            writer.writerow([key, sc["p10_index"], sc["p50_index"], sc["p90_index"], sc["cv"], sc["p_fail"]])
    writer.writerow([])

    nut = rotation["nutrients"]
    writer.writerow(["# nutrients"])
    writer.writerow(["key", "value"])
    for key, value in nut.items():
        writer.writerow([key, value])
    writer.writerow([])

    writer.writerow(["# findings"])
    writer.writerow(["code", "severity", "params"])
    for finding in rotation.get("findings", []):
        writer.writerow([finding["code"], finding["severity"], finding.get("params", {})])

    return "\ufeff" + buffer.getvalue()
