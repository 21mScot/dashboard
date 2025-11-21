from __future__ import annotations

import io
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Dict, Optional

from reportlab.lib import colors  # type: ignore[import]
from reportlab.lib.pagesizes import A4  # type: ignore[import]
from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import]
from reportlab.pdfgen import canvas  # type: ignore[import]
from reportlab.platypus import (  # type: ignore[import]
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.config.version import APP_VERSION
from src.core.capex import CapexBreakdown
from src.core.miner_models import MinerOption
from src.core.scenario_models import ScenarioResult
from src.core.site_metrics import SiteMetrics
from src.ui.assumptions import BulletItem, get_assumptions_sections
from src.ui.site_inputs import SiteInputs

Styles = getSampleStyleSheet()


def _dataclass_to_dict(obj) -> Dict:
    if obj is None:
        return {}
    if is_dataclass(obj):
        return asdict(obj)
    return dict(obj)


def _format_currency(value) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"£{numeric:,.0f}"


def _format_percentage(value: float) -> str:
    return f"{value:.1f}%"


def build_pdf_report(
    site_inputs: SiteInputs,
    miner: MinerOption,
    metrics: SiteMetrics,
    scenarios: Dict[str, ScenarioResult],
    client_share_pct: float,
    capex_breakdown: Optional[CapexBreakdown],
) -> bytes:
    """Generate a simple PDF snapshot for sharing with stakeholders."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title="Bitcoin Mining Snapshot",
        topMargin=60,
        bottomMargin=60,
    )
    story = []

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    header_text = "Bitcoin Mining Feasibility Snapshot"
    footer_text = f"Generated {now} • Version {APP_VERSION}"

    story.append(Paragraph("Site configuration", Styles["Heading2"]))
    site_table = Table(
        [
            ["Go-live date", f"{site_inputs.go_live_date:%d %b %Y}"],
            ["Project duration", f"{site_inputs.project_years} years"],
            ["Available power", f"{site_inputs.site_power_kw:,.0f} kW"],
            ["Electricity cost", f"£{site_inputs.electricity_cost:.3f} / kWh"],
            ["Expected uptime", _format_percentage(site_inputs.uptime_pct)],
            ["Cooling overhead", _format_percentage(site_inputs.cooling_overhead_pct)],
        ],
        hAlign="LEFT",
    )
    site_table.setStyle(_table_style())
    story.append(site_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Miner assumption", Styles["Heading2"]))
    miner_table = Table(
        [
            ["Model", miner.name],
            ["Hashrate", f"{miner.hashrate_th:.0f} TH/s"],
            ["Power draw", f"{miner.power_w} W"],
            ["Efficiency", f"{miner.efficiency_j_per_th:.1f} J/TH"],
            ["Supplier", miner.supplier or "—"],
            [
                "Indicative price",
                f"${miner.price_usd:,.0f}" if miner.price_usd else "—",
            ],
        ]
    )
    miner_table.setStyle(_table_style())
    story.append(miner_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Site performance snapshot", Styles["Heading2"]))
    if metrics.site_power_available_kw:
        power_util_pct = (
            metrics.site_power_used_kw / metrics.site_power_available_kw * 100
        )
    else:
        power_util_pct = 0.0
    metrics_table = Table(
        [
            ["ASICs supported", f"{metrics.asics_supported}"],
            ["BTC / day", f"{metrics.site_btc_per_day:.5f} BTC"],
            [
                "Revenue / day",
                f"£{metrics.site_revenue_gbp_per_day:,.0f} "
                f"(${metrics.site_revenue_usd_per_day:,.0f})",
            ],
            [
                "Electricity cost / day",
                _format_currency(metrics.site_power_cost_gbp_per_day),
            ],
            [
                "Net income / day",
                _format_currency(metrics.site_net_revenue_gbp_per_day),
            ],
            [
                "Site power utilisation",
                f"{power_util_pct:.1f}%",
            ],
            ["Spare capacity", f"{metrics.spare_capacity_kw:.1f} kW"],
        ]
    )
    metrics_table.setStyle(_table_style())
    story.append(metrics_table)
    story.append(Spacer(1, 12))

    if scenarios:
        story.append(Paragraph("Scenario summary", Styles["Heading2"]))
        scenario_rows = [
            [
                "Scenario",
                "Total BTC",
                "Client net income",
                "Payback",
                "ROI multiple",
                "Avg EBITDA margin",
            ]
        ]
        for label in ["base", "best", "worst"]:
            result = scenarios.get(label)
            if not result:
                continue
            scenario_rows.append(
                [
                    result.config.name.title(),
                    f"{result.total_btc:,.3f}",
                    _format_currency(result.total_client_net_income_gbp),
                    (
                        "N/A"
                        if result.client_payback_years == float("inf")
                        else f"{result.client_payback_years:.1f} yrs"
                    ),
                    f"{result.client_roi_multiple:,.2f}×",
                    _format_percentage(result.avg_ebitda_margin * 100),
                ]
            )
        scenario_table = Table(scenario_rows, repeatRows=1, hAlign="LEFT")
        scenario_table.setStyle(_table_style(header=True))
        scenario_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                ]
            )
        )
        story.append(
            Paragraph(
                f"Client revenue share selected: {client_share_pct:.0f}% of BTC "
                "revenue.",
                Styles["Normal"],
            )
        )
        story.append(scenario_table)
        story.append(Spacer(1, 12))

    if capex_breakdown and capex_breakdown.total_gbp > 0:
        story.append(Paragraph("CapEx breakdown", Styles["Heading2"]))
        breakdown_rows = [["Component", "Cost (GBP)"]]
        breakdown_rows.extend(
            [
                ("ASICs (miners)", capex_breakdown.asic_cost_gbp),
                ("Shipping", capex_breakdown.shipping_gbp),
                ("Import duty", capex_breakdown.import_duty_gbp),
                ("Spares allocation", capex_breakdown.spares_gbp),
                ("Racking / mounting", capex_breakdown.racking_gbp),
                ("Power & data cabling", capex_breakdown.cables_gbp),
                ("Switchgear & protection", capex_breakdown.switchgear_gbp),
                ("Networking & monitoring", capex_breakdown.networking_gbp),
                ("Installation labour", capex_breakdown.installation_labour_gbp),
                ("Certification & sign-off", capex_breakdown.certification_gbp),
            ]
        )
        breakdown_rows = [
            (label, _format_currency(value)) for label, value in breakdown_rows
        ]
        capex_table = Table(breakdown_rows, repeatRows=1, hAlign="LEFT")
        capex_table.setStyle(_table_style(header=True))
        capex_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ]
            )
        )
        story.append(capex_table)

    story.append(PageBreak())
    story.append(Paragraph("Appendix: Assumptions & Methodology", Styles["Heading1"]))
    story.append(
        Paragraph(
            "This appendix mirrors the in-app Assumptions & Methodology tab.",
            Styles["Normal"],
        )
    )
    for section in get_assumptions_sections():
        story.append(Spacer(1, 12))
        story.append(Paragraph(section.title, Styles["Heading2"]))
        for paragraph in section.paragraphs:
            story.append(Paragraph(paragraph, Styles["Normal"]))
        if section.bullets:
            story.append(_build_pdf_bullets(section.bullets))
        if section.table:
            appendix_table = Table(section.table, repeatRows=1, hAlign="LEFT")
            appendix_table.setStyle(_table_style(header=True))
            story.append(appendix_table)

    doc.build(
        story,
        onFirstPage=lambda canv, doc: _draw_header_footer(
            canv, doc, header_text, footer_text
        ),
        onLaterPages=lambda canv, doc: _draw_header_footer(
            canv, doc, header_text, footer_text
        ),
        canvasmaker=lambda *args, **kwargs: NumberedCanvas(*args, **kwargs),
    )
    buffer.seek(0)
    return buffer.read()


def _table_style(header: bool = False) -> TableStyle:
    style_commands = [
        ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if header:
        style_commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ]
        )
    return TableStyle(style_commands)


def _draw_header_footer(canvas_obj, doc, header_text: str, footer_text: str) -> None:
    canvas_obj.saveState()
    width, height = A4
    canvas_obj.setFont("Helvetica-Bold", 12)
    canvas_obj.drawString(doc.leftMargin, height - 40, header_text)
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.drawString(doc.leftMargin, 40, footer_text)
    canvas_obj.restoreState()


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(page_count)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count: int) -> None:
        self.setFont("Helvetica", 8)
        self.drawRightString(
            self._pagesize[0] - 40,
            40,
            f"Page {self._pageNumber} of {page_count}",
        )


def _build_pdf_bullets(bullets: list[BulletItem]) -> ListFlowable:
    def to_paragraph(text: str) -> Paragraph:
        cleaned = text.replace("`", "")
        return Paragraph(cleaned, Styles["Normal"])

    items = []
    for bullet in bullets:
        content: list = [to_paragraph(bullet.text)]
        if bullet.subitems:
            sub_flow = ListFlowable(
                [ListItem(to_paragraph(sub), leftIndent=20) for sub in bullet.subitems],
                bulletType="bullet",
            )
            content.append(sub_flow)
        items.append(ListItem(content, leftIndent=0))
    return ListFlowable(items, bulletType="bullet")
