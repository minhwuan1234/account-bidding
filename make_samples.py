"""Create the sample DOCX/PDF used by the README and tests."""

from pathlib import Path

from docx import Document
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


root = Path(__file__).parent / "samples"
root.mkdir(exist_ok=True)

doc = Document()
doc.add_heading("Project Brief", level=1)
doc.add_paragraph("This document describes the project scope and submission requirements.")
doc.add_heading("1. Scope of Work", level=2)
doc.add_paragraph("The supplier will design and deliver a working prototype.")
doc.add_heading("1.1 Deliverables", level=3)
table = doc.add_table(rows=1, cols=2)
table.style = "Table Grid"
table.rows[0].cells[0].text = "Item"
table.rows[0].cells[1].text = "Due"
for item, due in [("Prototype", "Week 2"), ("Report", "Week 4")]:
    row = table.add_row()
    row.cells[0].text = item
    row.cells[1].text = due
doc.add_heading("2. Submission", level=2)
doc.add_paragraph("Submit the proposal before the deadline.")
doc.save(root / "sample.docx")

styles = getSampleStyleSheet()
story = [
    Paragraph("Project Brief", styles["Heading1"]),
    Paragraph("This document describes the project scope and submission requirements.", styles["BodyText"]),
    Spacer(1, 10),
    Paragraph("1. Scope of Work", styles["Heading2"]),
    Paragraph("The supplier will design and deliver a working prototype.", styles["BodyText"]),
    Spacer(1, 10),
    Paragraph("1.1 Deliverables", styles["Heading3"]),
]
pdf_table = Table([["Item", "Due"], ["Prototype", "Week 2"], ["Report", "Week 4"]], colWidths=[130, 100])
pdf_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.7, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey)]))
story += [pdf_table, Spacer(1, 10), Paragraph("2. Submission", styles["Heading2"]), Paragraph("Submit the proposal before the deadline.", styles["BodyText"])]
SimpleDocTemplate(str(root / "sample.pdf")).build(story)

styleless = Document()
styleless.add_paragraph("Request for Quotation")
styleless.add_paragraph("Provision of Public Relations and Communications Services")
styleless.add_paragraph("SECTION 1: REQUEST FOR QUOTATION (RFQ)")
styleless.add_paragraph("UNDP kindly requests your quotation for the services described in this RFQ.")
styleless.add_paragraph("Deadline for submission is 20 October 2026.")
styleless.save(root / "styleless_rfq.docx")
print(root)
