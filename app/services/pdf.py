"""Generación del PDF del estado de cuenta (fpdf2, fuentes base: texto en Latin-1)."""
from fpdf import FPDF

from app.models import config

_REEMPLAZOS = {"–": "-", "—": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "•": "-", "₡": "CRC "}


def _t(texto):
    s = str(texto)
    for a, b in _REEMPLAZOS.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def estado_cuenta_pdf(socio, periodo, resumen, membresia_tipo, generado_en):
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _t("Club Valle Alto"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, _t(f"Estado de cuenta - periodo {periodo}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    for etiqueta, valor in (("Socio", socio["nombre"]), ("Cédula", socio["cedula"]), ("Correo", socio["correo"]),
                            ("Membresía", membresia_tipo or "-"), ("Generado", generado_en)):
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(28, 6, _t(etiqueta + ":"))
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, _t(valor), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    anchos = (82, 24, 30, 24, 30)
    pdf.set_fill_color(225, 232, 226)
    pdf.set_font("Helvetica", "B", 9)
    for ancho, titulo in zip(anchos, ("Concepto", "Tipo", "Fecha límite", "Estado", "Monto")):
        pdf.cell(ancho, 7, _t(titulo), border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for c in resumen["cargos"]:
        concepto = _t(c["concepto"])
        if len(concepto) > 52:
            concepto = concepto[:49] + "..."
        pdf.cell(anchos[0], 7, concepto, border=1)
        pdf.cell(anchos[1], 7, _t("Cuota" if c["tipo"] == "cuota" else "Servicio"), border=1, align="C")
        pdf.cell(anchos[2], 7, _t(c["fecha_limite"]), border=1, align="C")
        pdf.cell(anchos[3], 7, _t(c["estado_efectivo"].capitalize()), border=1, align="C")
        pdf.cell(anchos[4], 7, _t(config.moneda(c["monto"])), border=1, align="R")
        pdf.ln()

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    for etiqueta, valor in (("Total del periodo", resumen["total"]), ("Pagado", resumen["pagado"]),
                            ("Pendiente de pago", resumen["pendiente"]), ("  de lo cual vencido", resumen["vencido"])):
        pdf.cell(140, 7, _t(etiqueta), align="R")
        pdf.cell(50, 7, _t(config.moneda(valor)), align="R")
        pdf.ln()
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 4, _t("Documento informativo generado por la plataforma del Club Valle Alto. Los pagos se registran "
                            "manualmente por el personal administrativo; este sistema no procesa pagos en línea ni emite facturas electrónicas."))
    return bytes(pdf.output())
