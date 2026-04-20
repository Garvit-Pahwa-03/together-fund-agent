from fpdf import FPDF
import re
from datetime import datetime


class MemoPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(80, 80, 80)
        self.cell(
            0, 8,
            "Together Fund - Confidential Investment Screening Memo",
            align="L"
        )
        self.set_text_color(180, 180, 180)
        self.cell(
            0, 8,
            datetime.now().strftime("%B %d, %Y"),
            align="R",
            new_x="LMARGIN",
            new_y="NEXT"
        )
        self.set_draw_color(220, 220, 220)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(
            0, 10,
            f"Page {self.page_no()}/{{nb}} | Together Fund AI Agent",
            align="C"
        )


def markdown_to_pdf(
    markdown_text: str,
    output_path: str = "together_fund_memo.pdf"
):
    pdf = MemoPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 20, 15)

    lines = markdown_text.split("\n")

    for line in lines:
        line = line.rstrip()

        if line.strip() in ("---", "===", "***"):
            pdf.set_draw_color(220, 220, 220)
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.ln(4)
            continue

        if line.startswith("# "):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(20, 40, 80)
            pdf.multi_cell(0, 8, line[2:].strip())
            pdf.ln(2)
            continue

        if line.startswith("## "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(40, 80, 140)
            pdf.multi_cell(0, 7, line[3:].strip())
            pdf.ln(1)
            continue

        if line.startswith("### "):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(60, 60, 60)
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line[4:].strip())
            pdf.multi_cell(0, 6, clean)
            pdf.ln(1)
            continue

        if line.strip().startswith("|") and line.strip().endswith("|"):
            if re.match(r"^\|[\s\-:]+\|", line.strip()):
                continue
            pdf.set_font("Courier", "", 8)
            pdf.set_text_color(60, 60, 60)
            cells = [
                c.strip()
                for c in line.strip().strip("|").split("|")
            ]
            pdf.multi_cell(0, 5, "  |  ".join(cells))
            continue

        if line.strip().startswith(("- ", "* ")):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(50, 50, 50)
            clean = re.sub(
                r"\*\*(.+?)\*\*", r"\1", line.strip()[2:].strip()
            )
            pdf.set_x(20)
            pdf.multi_cell(175, 5, f"  *  {clean}")
            continue

        if line.strip():
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(50, 50, 50)
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line.strip())
            clean = re.sub(r"\*(.+?)\*", r"\1", clean)
            pdf.multi_cell(0, 5, clean)
        else:
            pdf.ln(2)

    pdf.output(output_path)
    return output_path