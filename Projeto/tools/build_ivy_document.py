"""Gera o caderno mestre Ivy.docx com layout verificável em Word."""

from __future__ import annotations

import argparse
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Inches, Pt, RGBColor


NAVY = "203748"
BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
MUTED = "64748B"
LIGHT_BLUE = "E8EEF5"
LIGHT_GRAY = "F4F6F9"
BORDER = "CBD5E1"
WHITE = "FFFFFF"
INK = "172033"
GOLD = "8A6A16"
PAGE_WIDTH_DXA = 9360
TABLE_INDENT_DXA = 120


def set_run_font(
    run,
    *,
    name: str = "Calibri",
    size: float | None = None,
    color: str | None = None,
    bold: bool | None = None,
    italic: bool | None = None,
) -> None:
    run.font.name = name
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), name)
    if size is not None:
        run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def set_style_font(style, name: str, size: float, color: str, bold: bool = False) -> None:
    style.font.name = name
    style._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:ascii"), name)
    style._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), name)
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor.from_string(color)
    style.font.bold = bold


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def set_cell_margins(cell, *, top: int = 80, start: int = 120, bottom: int = 80, end: int = 120) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin_name, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        margin = tc_mar.find(qn(f"w:{margin_name}"))
        if margin is None:
            margin = OxmlElement(f"w:{margin_name}")
            tc_mar.append(margin)
        margin.set(qn("w:w"), str(value))
        margin.set(qn("w:type"), "dxa")


def paragraph_bottom_border(paragraph, color: str = BORDER, size: int = 6, space: int = 5) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is None:
        p_bdr = OxmlElement("w:pBdr")
        p_pr.append(p_bdr)
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), str(space))
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)


def remove_paragraph_borders(element) -> None:
    p_pr = element._element.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is not None:
        p_pr.remove(p_bdr)


def set_paragraph_shading(paragraph, fill: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shading = p_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        p_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def set_paragraph_left_border(paragraph, color: str = BLUE, size: int = 18, space: int = 8) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is None:
        p_bdr = OxmlElement("w:pBdr")
        p_pr.append(p_bdr)
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), str(size))
    left.set(qn("w:space"), str(space))
    left.set(qn("w:color"), color)
    p_bdr.append(left)


def set_keep_with_next(paragraph) -> None:
    paragraph.paragraph_format.keep_with_next = True


def add_page_field(paragraph) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    value = OxmlElement("w:t")
    value.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instruction, separate, value, end])
    set_run_font(run, size=9, color=MUTED)


def add_hyperlink(paragraph, text: str, url: str) -> None:
    relation_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relation_id)
    run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), BLUE)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    r_pr.extend([color, underline])
    text_node = OxmlElement("w:t")
    text_node.text = text
    run.extend([r_pr, text_node])
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_numbering_definition(doc: Document, *, numbered: bool) -> int:
    numbering = doc.part.numbering_part.element
    abstract_ids = [
        int(node.get(qn("w:abstractNumId")))
        for node in numbering.findall(qn("w:abstractNum"))
    ]
    num_ids = [int(node.get(qn("w:numId"))) for node in numbering.findall(qn("w:num"))]
    abstract_id = max(abstract_ids, default=-1) + 1
    num_id = max(num_ids, default=0) + 1

    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "singleLevel")
    abstract.append(multi)

    level = OxmlElement("w:lvl")
    level.set(qn("w:ilvl"), "0")
    start = OxmlElement("w:start")
    start.set(qn("w:val"), "1")
    num_fmt = OxmlElement("w:numFmt")
    num_fmt.set(qn("w:val"), "decimal" if numbered else "bullet")
    level_text = OxmlElement("w:lvlText")
    level_text.set(qn("w:val"), "%1." if numbered else "•")
    justification = OxmlElement("w:lvlJc")
    justification.set(qn("w:val"), "left")
    suffix = OxmlElement("w:suff")
    suffix.set(qn("w:val"), "tab")

    p_pr = OxmlElement("w:pPr")
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "num")
    tab.set(qn("w:pos"), "540")
    tabs.append(tab)
    indent = OxmlElement("w:ind")
    indent.set(qn("w:left"), "540")
    indent.set(qn("w:hanging"), "270")
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:after"), "80")
    spacing.set(qn("w:line"), "300")
    spacing.set(qn("w:lineRule"), "auto")
    p_pr.extend([tabs, indent, spacing])

    level.extend([start, num_fmt, level_text, justification, suffix, p_pr])
    abstract.append(level)
    numbering.append(abstract)

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract_ref = OxmlElement("w:abstractNumId")
    abstract_ref.set(qn("w:val"), str(abstract_id))
    num.append(abstract_ref)
    numbering.append(num)
    return num_id


def apply_numbering(paragraph, num_id: int) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    num_id_node = OxmlElement("w:numId")
    num_id_node.set(qn("w:val"), str(num_id))
    num_pr.extend([ilvl, num_id_node])
    p_pr.append(num_pr)


def add_list(doc: Document, items: list[str], *, numbered: bool = False) -> None:
    num_id = add_numbering_definition(doc, numbered=numbered)
    for item in items:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(4)
        paragraph.paragraph_format.line_spacing = 1.25
        apply_numbering(paragraph, num_id)
        run = paragraph.add_run(item)
        set_run_font(run, size=11, color=INK)


def set_table_geometry(table, widths_dxa: list[int]) -> None:
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr

    tbl_width = tbl_pr.find(qn("w:tblW"))
    if tbl_width is None:
        tbl_width = OxmlElement("w:tblW")
        tbl_pr.append(tbl_width)
    tbl_width.set(qn("w:w"), str(sum(widths_dxa)))
    tbl_width.set(qn("w:type"), "dxa")

    tbl_indent = tbl_pr.find(qn("w:tblInd"))
    if tbl_indent is None:
        tbl_indent = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_indent)
    tbl_indent.set(qn("w:w"), str(TABLE_INDENT_DXA))
    tbl_indent.set(qn("w:type"), "dxa")

    layout = tbl_pr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        grid_col = OxmlElement("w:gridCol")
        grid_col.set(qn("w:w"), str(width))
        grid.append(grid_col)

    for row in table.rows:
        for cell, width in zip(row.cells, widths_dxa):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_width = tc_pr.find(qn("w:tcW"))
            if tc_width is None:
                tc_width = OxmlElement("w:tcW")
                tc_pr.append(tc_width)
            tc_width.set(qn("w:w"), str(width))
            tc_width.set(qn("w:type"), "dxa")
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths_dxa: list[int]):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    repeat_header(table.rows[0])
    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.text = header
        set_cell_shading(cell, LIGHT_BLUE)
    for data_row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(data_row):
            cells[index].text = value
    set_table_geometry(table, widths_dxa)

    for row_index, row in enumerate(table.rows):
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(2)
                paragraph.paragraph_format.line_spacing = 1.10
                for run in paragraph.runs:
                    set_run_font(
                        run,
                        size=9.5,
                        color=INK,
                        bold=row_index == 0,
                    )
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_callout(doc: Document, label: str, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Inches(0.12)
    paragraph.paragraph_format.right_indent = Inches(0.12)
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(10)
    paragraph.paragraph_format.line_spacing = 1.2
    set_paragraph_shading(paragraph, LIGHT_GRAY)
    set_paragraph_left_border(paragraph)
    label_run = paragraph.add_run(f"{label}: ")
    set_run_font(label_run, size=11, color=DARK_BLUE, bold=True)
    text_run = paragraph.add_run(text)
    set_run_font(text_run, size=11, color=INK)


def add_question_field(doc: Document, number: int, question: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(5)
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run(f"{number}. {question}")
    set_run_font(run, size=11, color=INK, bold=True)
    response = doc.add_paragraph()
    response.paragraph_format.left_indent = Inches(0.2)
    response.paragraph_format.space_after = Pt(9)
    response_run = response.add_run("Resposta: ")
    set_run_font(response_run, size=10.5, color=MUTED, italic=True)
    paragraph_bottom_border(response, color=BORDER, size=4, space=3)


def configure_document(doc: Document) -> None:
    doc.settings.odd_and_even_pages_header_footer = False
    section = doc.sections[0]
    section.start_type = WD_SECTION_START.NEW_PAGE
    section.different_first_page_header_footer = False
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.right_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    normal = doc.styles["Normal"]
    set_style_font(normal, "Calibri", 11, INK)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25

    title = doc.styles["Title"]
    set_style_font(title, "Calibri Light", 30, NAVY, bold=False)
    title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(0)
    title.paragraph_format.space_after = Pt(8)
    remove_paragraph_borders(title)

    subtitle = doc.styles["Subtitle"]
    set_style_font(subtitle, "Calibri", 15, DARK_BLUE)
    subtitle.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_before = Pt(0)
    subtitle.paragraph_format.space_after = Pt(8)

    heading_settings = {
        "Heading 1": (16, BLUE, 18, 10),
        "Heading 2": (13, BLUE, 14, 7),
        "Heading 3": (12, DARK_BLUE, 10, 5),
    }
    for name, (size, color, before, after) in heading_settings.items():
        style = doc.styles[name]
        set_style_font(style, "Calibri", size, color, bold=True)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    header = section.header
    header_paragraph = header.paragraphs[0]
    header_paragraph.paragraph_format.space_after = Pt(3)
    header_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = header_paragraph.add_run("IVY  |  CADERNO MESTRE DE ENGENHARIA")
    set_run_font(run, size=8.5, color=MUTED, bold=True)
    paragraph_bottom_border(header_paragraph, color=BORDER, size=5, space=4)

    footer = section.footer
    footer_paragraph = footer.paragraphs[0]
    footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer_paragraph.paragraph_format.space_before = Pt(3)
    run = footer_paragraph.add_run("Ivy  |  Página ")
    set_run_font(run, size=9, color=MUTED)
    add_page_field(footer_paragraph)


def add_cover(doc: Document) -> None:
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(58)

    kicker = doc.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    kicker.paragraph_format.space_after = Pt(14)
    run = kicker.add_run("CADERNO MESTRE DO PROJETO")
    set_run_font(run, size=10, color=GOLD, bold=True)

    doc.add_paragraph("IVY", style="Title")
    doc.add_paragraph(
        "Inteligência de engenharia mecânica e mecatrônica",
        style="Subtitle",
    )

    descriptor = doc.add_paragraph()
    descriptor.alignment = WD_ALIGN_PARAGRAPH.CENTER
    descriptor.paragraph_format.space_after = Pt(42)
    run = descriptor.add_run(
        "Visão, arquitetura, requisitos, segurança, roteiro e registro de desenvolvimento"
    )
    set_run_font(run, size=11, color=MUTED, italic=True)

    status = doc.add_paragraph()
    status.alignment = WD_ALIGN_PARAGRAPH.CENTER
    status.paragraph_format.space_after = Pt(5)
    run = status.add_run("Versão 0.9  |  Dashboard 0.3  |  9 de agosto de 2026")
    set_run_font(run, size=11, color=NAVY, bold=True)

    note = doc.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note.paragraph_format.space_after = Pt(36)
    run = note.add_run("Documento vivo - será atualizado conforme a Ivy evoluir")
    set_run_font(run, size=10, color=MUTED)

    add_callout(
        doc,
        "Missão",
        "Transformar uma intenção humana em um processo de engenharia rastreável: requisitos, cálculos, alternativas, modelos, simulações, revisão e protótipos seguros.",
    )
    doc.add_page_break()


def add_contents(doc: Document) -> None:
    doc.add_heading("Mapa do documento", level=1)
    add_list(
        doc,
        [
            "Visão e definição da Ivy",
            "O que é possível hoje e o que continua sendo ficção",
            "Arquitetura planejada",
            "Roteiro de desenvolvimento",
            "Passo 1 concluído: interpretador de requisitos",
            "Evolução 0.2: assistente conversacional de trabalho",
            "Passo 2 concluído: continuidade e memória de projetos",
            "Passo 3 concluído: calculadora de engenharia rastreável",
            "Evolução 0.5.1: conversa natural sem comandos obrigatórios",
            "Passo 4 concluído: comparação de conceitos mecânicos",
            "Passo 5 concluído: memória versionada e decisões",
            "Passo 6 concluído: verificador independente",
            "Passo 7 concluído: CAD paramétrico preliminar",
            "Dashboard conversacional e publicação: Ivy Command Center",
            "Primeiro caso de teste: garra robótica de 500 g",
            "Benchmark avançado: garra contextual de 1,5 kg",
            "Estrutura técnica e instruções de execução",
            "Perguntas para continuar o projeto da garra",
            "Registro de decisões e fontes",
        ],
    )
    add_callout(
        doc,
        "Regra central",
        "A Ivy não poderá apresentar uma hipótese como fato nem declarar um projeto seguro sem evidência verificável.",
    )


def add_vision(doc: Document) -> None:
    doc.add_heading("1. Visão e definição da Ivy", level=1)
    doc.add_paragraph(
        "A Ivy será uma plataforma de inteligência de engenharia inspirada em assistentes fictícios como a E.V.I.E. do universo do Homem-Aranha, mas construída com limites reais. Seu trabalho não será apenas conversar: ela deverá converter objetivos em requisitos, usar ferramentas matemáticas, comparar soluções, produzir modelos, executar simulações e registrar evidências antes de recomendar um protótipo."
    )
    doc.add_heading("Objetivo inicial", level=2)
    doc.add_paragraph(
        "Criar uma assistente de trabalho especializada em engenharia mecânica e mecatrônica para conversar, organizar atividades e apoiar projetos graduais, documentados e seguros."
    )
    doc.add_heading("Princípios permanentes", level=2)
    add_list(
        doc,
        [
            "Modelos de linguagem interpretam e planejam; ferramentas determinísticas fazem cálculos.",
            "Todo valor deve indicar se foi informado, convertido, calculado, estimado ou ainda desconhecido.",
            "Hipóteses permanecem visíveis até serem confirmadas pelo usuário ou por evidência.",
            "Simulação e revisão humana vêm antes de qualquer teste físico.",
            "Ações de alto risco exigem bloqueios, supervisão especializada e autorização explícita.",
            "O histórico do projeto deve permitir entender o que mudou, por que mudou e quem aprovou.",
        ],
    )


def add_reality_check(doc: Document) -> None:
    doc.add_heading("2. Possibilidades e limites reais", level=1)
    doc.add_paragraph(
        "Uma versão útil da Ivy já pode ser desenvolvida com tecnologias atuais. O equivalente completo mostrado no cinema não é possível porque engenharia física depende de materiais, energia, fabricação, ensaios e legislação - não apenas de inteligência computacional."
    )
    add_table(
        doc,
        ["Capacidade", "Situação atual", "Condição"],
        [
            ["Conversação natural", "Possível", "Texto e voz em tempo real"],
            ["Análise de imagens e sensores", "Possível", "Câmeras e sensores autorizados"],
            ["Pesquisa, código e cálculos", "Possível com revisão", "Fontes e ferramentas verificáveis"],
            ["Modelos 3D", "Parcialmente possível", "CAD parametrizado e revisão humana"],
            ["Simulação de mecanismos", "Possível", "Modelos físicos e condições bem definidas"],
            ["Controle de robôs", "Possível em escopo limitado", "Controladores rígidos e parada de emergência"],
            ["Armadura completa autônoma", "Ainda não", "Limites de energia, calor, massa e segurança"],
            ["Tecnologias que ignoram a física", "Impossível", "A IA não altera leis físicas"],
        ],
        [3100, 2100, 4160],
    )
    add_callout(
        doc,
        "Interpretação correta",
        "A Ivy acelerará o trabalho de engenheiros e inventores; ela não substituirá simulação, fabricação, ensaios ou especialistas responsáveis.",
    )


def add_architecture(doc: Document) -> None:
    doc.add_heading("3. Arquitetura planejada", level=1)
    doc.add_paragraph(
        "A plataforma será montada por camadas independentes. Essa separação impede que uma resposta verbal seja confundida com uma ordem física segura."
    )
    add_list(
        doc,
        [
            "Interface: recebe texto, voz, imagens e dados de sensores e apresenta o trabalho no dashboard visual.",
            "Orquestrador: decide qual módulo pode atender cada parte do pedido.",
            "Modelo de raciocínio: interpreta linguagem e propõe um plano de trabalho.",
            "Interpretador de requisitos: separa fatos, hipóteses, restrições e dúvidas.",
            "Motor matemático: executa cálculos com unidades e fórmulas explícitas.",
            "Memória de projeto: guarda versões, decisões, arquivos, resultados e aprovações.",
            "CAD e simulação: gera geometrias parametrizadas e testa conceitos em ambiente virtual.",
            "Verificador: procura inconsistências, unidades erradas e conclusões sem evidência.",
            "Camada robótica: converte objetivos aprovados em comandos limitados para controladores.",
            "Camada de segurança: permissões, registros, limites físicos e parada de emergência.",
        ],
        numbered=True,
    )
    doc.add_heading("Fluxo de trabalho", level=2)
    flow = doc.add_paragraph()
    flow.alignment = WD_ALIGN_PARAGRAPH.CENTER
    flow.paragraph_format.space_before = Pt(6)
    flow.paragraph_format.space_after = Pt(10)
    run = flow.add_run(
        "Pedido  →  Requisitos  →  Perguntas  →  Cálculos  →  Conceitos  →  Verificação  →  CAD  →  Simulação  →  Aprovação humana  →  Protótipo"
    )
    set_run_font(run, size=10.5, color=NAVY, bold=True)
    set_paragraph_shading(flow, LIGHT_BLUE)


def add_roadmap(doc: Document) -> None:
    doc.add_heading("4. Roteiro de desenvolvimento", level=1)
    add_table(
        doc,
        ["Etapa", "Módulo", "Resultado esperado", "Estado"],
        [
            ["1", "Requisitos", "Transformar ideias em briefing rastreável", "Concluído"],
            ["2", "Assistente", "Conversa, tarefas, notas e ferramentas", "Concluído"],
            ["3", "Cálculos", "Fórmulas, unidades, fontes e bloqueios", "Concluído"],
            ["4", "Conceitos", "Comparar mecanismos e estimar acionamento", "Concluído"],
            ["5", "Memória", "Versões, decisões e dependências", "Concluído"],
            ["6", "Verificador", "Revisão independente e testes", "Concluído"],
            ["7", "CAD", "Modelos 3D parametrizados", "Concluído"],
            ["UI", "Dashboard", "CAD, montagem e estado do projeto", "Concluído"],
            ["8", "Simulação", "Testes virtuais estruturais e robóticos", "Planejado"],
            ["9", "Voz e visão", "Interação natural e percepção", "Planejado"],
            ["10", "Robô virtual", "Controle em gêmeo digital", "Planejado"],
            ["11", "Robô físico", "Protótipo de baixa energia supervisionado", "Futuro"],
        ],
        [700, 1800, 4860, 2000],
    )
    doc.add_paragraph(
        "O desenvolvimento avançará somente quando a etapa anterior possuir critérios de aceitação e testes. Não treinaremos um modelo próprio antes de acumular exemplos reais de falhas que justifiquem essa especialização."
    )


def add_step_one(doc: Document) -> None:
    doc.add_heading("5. Passo 1 concluído: interpretador de requisitos", level=1)
    doc.add_paragraph(
        "O primeiro módulo funcional recebe uma descrição informal e produz um briefing estruturado. Ele foi projetado para impedir que a Ivy escolha componentes ou faça dimensionamentos antes de conhecer as condições essenciais."
    )
    doc.add_heading("Saída obrigatória", level=2)
    add_list(
        doc,
        [
            "Nome, objetivo e áreas de engenharia envolvidas.",
            "Requisitos explícitos com identificadores rastreáveis.",
            "Valores originais e unidades normalizadas.",
            "Hipóteses, informações ausentes e perguntas prioritárias.",
            "Risco preliminar, alertas e estado de prontidão.",
            "Próximo passo recomendado.",
        ],
    )
    doc.add_heading("Regras implementadas", level=2)
    add_list(
        doc,
        [
            "Pedido vazio é rejeitado.",
            "Conversões simples são feitas por código, não pelo modelo de linguagem.",
            "Projetos críticos são bloqueados antes de qualquer análise online.",
            "O modo local permite testar a estrutura sem uma chave de API.",
            "O modo online utiliza uma resposta estruturada conforme um esquema de dados.",
        ],
    )
    add_callout(
        doc,
        "Verificação",
        "Sessenta e oito testes automatizados foram executados com sucesso: trinta e dois da assistente, dez do verificador, oito do CAD, cinco da memória de projetos, quatro da comparação de conceitos, quatro da calculadora e cinco do interpretador.",
    )
    doc.add_heading("Evolução 0.2: assistente de trabalho", level=2)
    doc.add_paragraph(
        "A primeira interface tratava qualquer texto como descrição de projeto. Por isso, uma apresentação como “Olá Ivy, eu sou seu criador” gerava um briefing incorreto. A versão 0.2 substitui essa pergunta única por uma conversa contínua."
    )
    add_list(
        doc,
        [
            "Conversa aberta com os marcadores Você > e Ivy >.",
            "Reconhecimento da apresentação do criador sem abrir um projeto.",
            "Memória local para identidade informada, notas e tarefas.",
            "Pedidos em linguagem natural para adicionar, listar e concluir tarefas.",
            "Reconhecimento da intenção de criar ou consultar um projeto.",
            "Integração opcional com um modelo online para conversação mais ampla.",
        ],
    )
    add_callout(
        doc,
        "Limite atual",
        "No modo local, a conversa usa recursos programados e permanece limitada. Uma experiência mais próxima de assistentes fictícios exige conexão online e, em etapas futuras, voz, visão, acesso autorizado a arquivos e ferramentas de trabalho.",
    )


def add_step_two(doc: Document) -> None:
    doc.add_heading("6. Passo 2 concluído: continuidade de projetos", level=1)
    doc.add_paragraph(
        "A versão 0.4 resolve a principal limitação da etapa anterior: o briefing deixa de ser apenas uma resposta na tela e passa a ser um projeto persistente. A Ivy pode receber respostas em etapas, manter a numeração original das perguntas e retomar o trabalho depois de ser fechada."
    )
    doc.add_heading("Capacidades implementadas", level=2)
    add_list(
        doc,
        [
            "Identificador sequencial para cada projeto, como PRJ-001 e PRJ-002.",
            "Projeto ativo recuperado automaticamente ao reabrir a Ivy.",
            "Uma ou várias respostas numeradas registradas na mesma mensagem.",
            "Progresso visível, com respostas confirmadas e perguntas ainda pendentes.",
            "Lista de projetos e troca segura do projeto ativo.",
            "Persistência local no mesmo arquivo que guarda identidade, notas e tarefas.",
        ],
    )
    doc.add_heading("Exemplos em linguagem natural", level=2)
    add_table(
        doc,
        ["O que dizer", "Resultado"],
        [
            ["Crie um projeto para...", "Cria, guarda e ativa um novo projeto"],
            ["Como está o projeto?", "Mostra respostas, progresso e perguntas pendentes"],
            ["Mostre meus projetos", "Lista todos os projetos guardados"],
            ["Use o projeto 2", "Seleciona outro projeto como ativo"],
            ["A resposta 1 é...; a resposta 2 é...", "Guarda respostas ligadas às perguntas originais"],
        ],
        [3300, 6060],
    )
    add_callout(
        doc,
        "Regra de confiança",
        "Uma resposta guardada continua sendo um dado informado pelo usuário. Ela não se transforma automaticamente em cálculo validado, seleção de componente ou evidência de segurança.",
    )


def add_step_three(doc: Document) -> None:
    doc.add_heading("7. Passo 3 concluído: calculadora rastreável", level=1)
    doc.add_paragraph(
        "A versão 0.5 transforma requisitos e respostas do projeto em uma memória de cálculo determinística. Cada resultado indica de onde vieram os dados, qual fórmula foi usada, como os valores foram substituídos e quais hipóteses ainda precisam de validação."
    )
    doc.add_heading("Contrato de cada resultado", level=2)
    add_list(
        doc,
        [
            "Identificador rastreável e nome da grandeza.",
            "Fórmula e substituição numérica explícitas.",
            "Valor, unidade e classificação como calculado ou estimado por hipótese.",
            "Requisitos, respostas e hipóteses usados como fontes.",
            "Lista separada dos dimensionamentos que continuam bloqueados.",
        ],
    )
    doc.add_heading("Resultados do benchmark da garra", level=2)
    add_table(
        doc,
        ["Grandeza", "Resultado", "Classificação"],
        [
            ["Peso estático", "14,71 N", "Calculado"],
            ["Velocidade média", "0,15 m/s", "Calculado"],
            ["Aceleração triangular", "0,30 m/s²", "Estimado"],
            ["Força normal por dedo", "47,37 N", "Estimado"],
            ["Força normal total", "94,75 N", "Estimado"],
            ["Potência mecânica ideal", "2,21 W média; 4,55 W pico", "Mista"],
            ["Fonte elétrica nominal", "120 W contínuos; 180 W pico", "Calculado"],
            ["Cadência diária", "5.760 ciclos/dia", "Calculado"],
            ["Manutenção e vida", "17,36 e 173,61 dias de operação", "Calculado"],
        ],
        [3900, 3000, 2460],
    )
    doc.add_heading("Bloqueios mantidos", level=2)
    add_list(
        doc,
        [
            "Torque e rotação: faltam geometria, alavancas, transmissão e eficiência.",
            "PETG: faltam geometria, orientação de impressão e propriedades do lote.",
            "Contato com pessoas: o limite de força exige análise formal e ensaios.",
            "Custo: faltam conceitos de mecanismo, componentes e cotações.",
        ],
    )
    add_callout(
        doc,
        "Conversa natural",
        "Dizer “faça os cálculos” cria e guarda uma nova revisão. Dizer “mostre o último cálculo” recupera a memória existente. Se uma resposta mudar, a revisão anterior é marcada como desatualizada.",
    )
    doc.add_heading("Evolução 0.5.1: conversa sem comandos", level=2)
    add_list(
        doc,
        [
            "A linguagem natural passou a ser a interface principal; atalhos com / são opcionais.",
            "Pedidos para consultar o projeto atual não criam projetos duplicados.",
            "Respostas numeradas podem ser escritas como frases comuns.",
            "Cálculos, notas, tarefas, status e troca de projeto reconhecem intenções diretas.",
        ],
    )
    add_callout(
        doc,
        "Limite do Passo 3",
        "A calculadora não seleciona motor ou mecanismo e não declara o projeto seguro, validado ou pronto para fabricação.",
    )


def add_step_four(doc: Document) -> None:
    doc.add_heading("8. Passo 4 concluído: comparação de conceitos", level=1)
    doc.add_paragraph(
        "A versão 0.6 usa a memória de cálculo atual para comparar três arquiteturas mecânicas sob as mesmas condições. A Ivy registra princípio, hipóteses geométricas, fórmula, substituição, torque, rotação, velocidade, potência, vantagens e limitações de cada alternativa."
    )
    doc.add_heading("Conceitos avaliados", level=2)
    add_table(
        doc,
        ["Conceito", "Torque", "Velocidade", "Potência", "Pontuação"],
        [
            ["Fuso com roscas opostas", "0,345 N·m", "187,50 rpm", "6,77 W", "3,40/5"],
            ["Pinhão e duas cremalheiras", "1,115 N·m", "23,87 rpm", "2,79 W", "3,10/5"],
            ["Correia com carros opostos", "1,263 N·m", "19,89 rpm", "2,63 W", "2,95/5"],
        ],
        [3000, 1500, 1800, 1500, 1560],
    )
    doc.add_heading("Hipóteses do benchmark", level=2)
    add_list(
        doc,
        [
            "Força normal de referência: 47,37 N por dedo, calculada na revisão anterior.",
            "Abertura útil: 40 a 90 mm; movimento simétrico de 25 mm por dedo.",
            "Tempo comparativo de fechamento: 1,0 s, ainda sujeito a confirmação no ciclo real.",
            "Fuso: avanço de 8 mm/volta e eficiência 0,35.",
            "Pinhão: raio primitivo de 10 mm e eficiência 0,85.",
            "Polia: raio primitivo de 12 mm e eficiência 0,90.",
        ],
    )
    add_callout(
        doc,
        "Recomendação preliminar",
        "O fuso com roscas opostas foi recomendado somente para detalhamento e teste virtual. A pontuação favorece controle de posição e retenção potencial; não representa seleção de motor, componente comercial ou aprovação para fabricação.",
    )
    doc.add_heading("Validações ainda obrigatórias", level=2)
    add_list(
        doc,
        [
            "Confirmar tempo de fechamento, envelope e geometria completa do mecanismo.",
            "Dimensionar guias, mancais, eixos, fixações e estrutura impressa em PETG.",
            "Medir eficiência, atrito, folga, desgaste e regime térmico no protótipo.",
            "Executar análise formal de esmagamento, soltura de carga e falta de energia.",
            "Comparar curvas reais de torque, velocidade, corrente, custo e disponibilidade antes de escolher componentes.",
        ],
    )
    add_callout(
        doc,
        "Conversa natural e memória",
        "Dizer “compare os mecanismos da garra” cria uma revisão. Dizer “mostre os conceitos” recupera a análise guardada. Se respostas ou cálculos mudarem, a comparação anterior é marcada como desatualizada.",
    )


def add_step_five(doc: Document) -> None:
    doc.add_heading("9. Passo 5 concluído: memória versionada", level=1)
    doc.add_paragraph(
        "A versão 0.7 transforma o arquivo de memória em uma linha do tempo de engenharia. Cada alteração relevante recebe uma revisão geral crescente, enquanto cálculos e comparações mantêm também suas próprias revisões. Relatórios antigos deixam de ser sobrescritos e decisões passam a ter identificadores persistentes."
    )
    doc.add_heading("Eventos registrados", level=2)
    add_table(
        doc,
        ["Evento", "Quando acontece", "Registro produzido"],
        [
            ["Projeto criado", "Novo briefing é guardado", "Revisão inicial e evento EVT"],
            ["Resposta alterada", "O conteúdo realmente muda", "Antes, depois e perguntas afetadas"],
            ["Cálculo guardado", "A Ivy calcula ou recalcula", "Relatório completo preservado por revisão"],
            ["Comparação guardada", "A Ivy compara os mecanismos", "Alternativas e recomendação preservadas"],
            ["CAD guardado", "A Ivy gera uma geometria paramétrica", "Parâmetros, arquivos e assinaturas preservados"],
            ["Verificação guardada", "A Ivy audita cálculos ou conceitos", "Achados, estado e bloqueios preservados"],
            ["Decisão registrada", "O usuário confirma uma escolha", "DEC-001 e seguintes, motivo e revisão"],
        ],
        [2400, 3000, 3960],
    )
    doc.add_heading("Regras de integridade", level=2)
    add_list(
        doc,
        [
            "Revisões do projeto são crescentes e não são reutilizadas.",
            "Repetir uma resposta idêntica não cria uma mudança falsa.",
            "Cada cálculo, comparação, CAD e verificação novos são acrescentados ao histórico; o anterior permanece intacto.",
            "Mudanças em respostas continuam marcando cálculos, comparações e modelos CAD dependentes como desatualizados.",
            "A linha do tempo mostra até vinte eventos recentes e informa quando existem registros anteriores.",
        ],
    )
    add_callout(
        doc,
        "Compatibilidade com o PRJ-001",
        "Projetos criados antes da versão 0.7 são aceitos sem perda de dados. O cálculo e a comparação atuais são preservados como fotografias legadas, mas a Ivy não inventa eventos anteriores; o histórico detalhado começa na primeira mudança feita pela versão nova.",
    )
    doc.add_heading("Conversa natural", level=2)
    add_table(
        doc,
        ["O que dizer", "Resultado"],
        [
            ["Mostre o histórico do projeto", "Exibe revisões, mudanças e artefatos preservados"],
            ["O que mudou no projeto?", "Exibe a mesma linha do tempo"],
            ["Registre a decisão de... porque...", "Cria uma decisão com motivo e revisão"],
            ["Mostre as decisões", "Recupera todas as decisões ativas do projeto"],
        ],
        [3900, 5460],
    )
    add_callout(
        doc,
        "Verificação do Passo 5",
        "Sessenta e oito testes automatizados confirmam continuidade entre sessões, revisões crescentes, preservação de relatórios, compatibilidade com projetos antigos, decisões, CAD e verificação independente.",
    )


def add_step_six(doc: Document) -> None:
    doc.add_heading("10. Passo 6 concluído: verificador independente", level=1)
    doc.add_paragraph(
        "A versão 0.8 acrescenta uma segunda linha de defesa entre os cálculos da Ivy e qualquer uso técnico. O novo módulo não altera os artefatos que recebe e não confia apenas nos valores guardados: ele reconstrói os resultados por uma rotina separada, compara o esperado com o encontrado e registra cada verificação em uma revisão própria."
    )
    doc.add_heading("Escopo da auditoria", level=2)
    add_table(
        doc,
        ["Categoria", "O que é conferido", "Falha produzida"],
        [
            ["Integridade", "Contrato dos relatórios, identificadores únicos e fotografias históricas", "Erro e bloqueio"],
            ["Cálculos", "Valor recalculado com tolerância numérica explícita", "Erro e bloqueio"],
            ["Unidades", "Unidade esperada para cada grandeza", "Erro e bloqueio"],
            ["Hipóteses", "Classificação e dependência de resultados estimados", "Erro ou alerta"],
            ["Conceitos", "Torque, rotação, velocidade, potência, pontuação e ranking", "Erro e bloqueio"],
            ["Segurança", "Bloqueios, ausência de seleção de motor e limites formais", "Erro ou alerta"],
        ],
        [1900, 4760, 2700],
    )
    doc.add_heading("Estados do relatório", level=2)
    add_list(
        doc,
        [
            "sem_artefatos: ainda não existem cálculos ou conceitos para auditoria numérica.",
            "consistente_com_alertas: os itens verificáveis coincidem, mas hipóteses, segurança e fabricação continuam abertas.",
            "inconsistente: pelo menos um erro impede o uso técnico e bloqueia a recomendação até nova verificação.",
        ],
    )
    add_callout(
        doc,
        "Resultado do benchmark",
        "Depois da memória de cálculo, 88 verificações independentes são aprovadas. Depois da comparação dos três conceitos, são 117 verificações aprovadas. Em ambos os casos permanece um alerta formal de escopo e nenhum erro no cenário de referência.",
    )
    doc.add_heading("Falhas que a versão 0.8 detecta", level=2)
    add_list(
        doc,
        [
            "Valor numérico alterado, mesmo quando a fórmula escrita continua correta.",
            "Unidade trocada, resultado duplicado ou resultado criado sem entradas suficientes.",
            "Relatório atual diferente da fotografia preservada para a mesma revisão.",
            "Cálculo, comparação ou verificação desatualizados depois de uma mudança.",
            "Ranking invertido ou recomendação incompatível com as pontuações recalculadas.",
            "Ausência de bloqueios obrigatórios para PETG, contato com pessoas, torque ou custo.",
        ],
    )
    doc.add_heading("Execução automática e conversa natural", level=2)
    doc.add_paragraph(
        "Calcular ou comparar mecanismos executa e guarda uma verificação automática. Para uma auditoria completa, basta dizer “verifique o projeto”, “confira os cálculos” ou “faça uma revisão independente”. A frase “mostre a verificação” recupera a última revisão sem criar outra."
    )
    add_callout(
        doc,
        "Limite permanente",
        "O verificador confirma coerência matemática e documental. Ele não valida resistência real, segurança, normas, fabricação ou comportamento do protótipo; essas conclusões exigem CAD, simulação, análise de risco, ensaios e revisão profissional.",
    )


def add_step_seven(doc: Document) -> None:
    doc.add_page_break()
    doc.add_heading("11. Passo 7 concluído: CAD paramétrico preliminar", level=1)
    doc.add_paragraph(
        "A versão 0.9 transforma o conceito recomendado de fuso com roscas opostas em uma primeira geometria paramétrica rastreável. A Ivy usa os requisitos, cálculos e conceitos atuais, separa dimensões obrigatórias de hipóteses editáveis e guarda os arquivos com revisão, assinatura digital e vínculo às fontes que os originaram."
    )
    doc.add_heading("Parâmetros do modelo de referência", level=2)
    add_table(
        doc,
        ["Grupo", "Valores", "Classificação", "Origem"],
        [
            ["Abertura útil", "40 a 90 mm", "Requisito", "REQ-GEOM-001"],
            ["Curso por dedo", "25 mm", "Derivado", "Movimento simétrico"],
            ["Base", "150 × 60 × 10 mm", "Hipótese", "Envelope preliminar"],
            ["Carros", "24 × 44 × 12 mm", "Hipótese", "Geometria editável"],
            ["Dedos", "12 × 20 × 50 mm", "Hipótese", "Geometria editável"],
            ["Fuso", "Ø 8; avanço 8; comp. 140 mm", "Hipótese", "Conceito recomendado"],
            ["Guias", "Ø 8; distância 32 mm", "Hipótese", "Arranjo preliminar"],
            ["Folga visual", "0,5 mm", "Hipótese", "Não é tolerância fabril"],
        ],
        [1900, 2600, 1800, 3060],
    )
    doc.add_paragraph(
        "O relatório contém vinte parâmetros ao todo. Cada parâmetro guarda símbolo, valor, unidade, classificação e rastreabilidade; por isso uma medida estimada não é confundida com uma dimensão confirmada pelo usuário."
    )
    doc.add_heading("Arquivos produzidos", level=2)
    add_table(
        doc,
        ["Formato", "Finalidade", "Limite"],
        [
            ["OpenSCAD (.scad)", "Modelo paramétrico editável e autocontido", "Geometria conceitual"],
            ["STL (.stl)", "Prévia tridimensional para inspeção", "Não usar para fabricar"],
            ["SVG (.svg)", "Vista superior nas aberturas mínima e máxima", "Representação visual"],
            ["Manifesto (.json)", "Parâmetros, fontes, verificações e assinaturas SHA-256", "Registro técnico"],
        ],
        [2200, 3900, 3260],
    )
    doc.add_heading("Verificação independente do CAD", level=2)
    add_list(
        doc,
        [
            "Confere as revisões de cálculo e de conceito usadas como entrada.",
            "Recalcula os vinte parâmetros esperados por uma rotina separada.",
            "Confere faixa de abertura, curso simétrico, envelope, guias, dedos, fuso e folgas conceituais.",
            "Confere existência, tamanho, nome, conteúdo mínimo e assinatura SHA-256 dos quatro arquivos.",
            "Bloqueia seleção de componentes, aprovação de segurança e autorização de fabricação.",
        ],
    )
    add_callout(
        doc,
        "Resultado no PRJ-001",
        "Na cópia controlada do projeto real, a Ivy gerou vinte parâmetros e quatro arquivos. Dez verificações geométricas foram aprovadas; duas permaneceram como alertas formais. A auditoria completa aprovou 271 itens, manteve um alerta de escopo e encontrou zero erros.",
    )
    doc.add_heading("Conversa natural", level=2)
    add_table(
        doc,
        ["O que dizer", "Resultado"],
        [
            ["Crie o modelo CAD da garra", "Gera, guarda e verifica uma nova revisão"],
            ["Gere o CAD", "Executa a mesma etapa sem comando especial"],
            ["Mostre o último CAD", "Recupera parâmetros, alertas e caminhos dos arquivos"],
            ["Onde estão os arquivos CAD?", "Mostra os artefatos da revisão atual"],
        ],
        [3900, 5460],
    )
    add_callout(
        doc,
        "Limite do Passo 7",
        "O modelo é uma base virtual para revisão e simulação. Ele não contém ainda análise estrutural do PETG, tolerâncias de fabricação, roscas e mancais detalhados, fixações, sensores, proteções ou validação de segurança; portanto não está aprovado para fabricação.",
    )


def add_dashboard(doc: Document) -> None:
    doc.add_page_break()
    doc.add_heading("12. Dashboard conversacional: Ivy Command Center", level=1)
    doc.add_paragraph(
        "Antes do Passo 8, a Ivy recebeu uma interface própria para acompanhar o projeto como uma assistente de engenharia. Na versão 0.3, a conversa passou a ser o primeiro elemento da experiência: o usuário pergunta em linguagem natural e abre CAD, cálculos e verificações somente quando precisa. A direção estética usa uma base quase preta, tipografia clara e pequenos destaques em ciano e âmbar, com menos painéis e maior hierarquia visual. A aplicação Next.js continua publicada na Vercel sem exigir autenticação pelo ChatGPT."
    )

    image_path = (
        Path(__file__).resolve().parents[2]
        / "ivy-dashboard"
        / "public"
        / "og-v2.png"
    )
    if image_path.exists():
        image = doc.add_picture(str(image_path), width=Inches(6.35))
        image._inline.docPr.set(
            "descr",
            "Conceito visual do dashboard Ivy 0.3 com conversa em primeiro plano, navegação mínima e uma prévia técnica secundária da garra robótica.",
        )
        image._inline.docPr.set("name", "Dashboard visual da Ivy")
        image_paragraph = doc.paragraphs[-1]
        image_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        image_paragraph.paragraph_format.space_before = Pt(6)
        image_paragraph.paragraph_format.space_after = Pt(3)
        caption = doc.add_paragraph()
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption.paragraph_format.space_after = Pt(10)
        run = caption.add_run("Ivy Dashboard 0.3 — conversa primeiro, contexto técnico quando necessário.")
        set_run_font(run, size=8.5, color=MUTED, italic=True)

    doc.add_heading("O que a versão 0.3 mostra", level=2)
    add_list(
        doc,
        [
            "Composer de conversa como ação principal da primeira tela, sem comandos obrigatórios.",
            "Sugestões rápidas para revisar o PRJ-001, continuar cálculos, abrir o CAD ou verificar segurança.",
            "Contexto compacto com requisitos-chave, progresso, prévia CAD e bloqueio de fabricação.",
            "Workspace secundário com modelo tridimensional, rotação, montagem em cinco etapas e vista CAD.",
            "Layout responsivo, navegação reduzida e uso restrito de cor para estados e alertas.",
        ],
    )
    add_callout(
        doc,
        "Estado da conversa",
        "A interface atual demonstra respostas contextuais do PRJ-001. A integração com um modelo de IA e a persistência de conversas serão realizadas em etapa posterior; a tela não representa ainda um serviço de IA online completo.",
    )
    doc.add_heading("Referências de experiência", level=2)
    doc.add_paragraph(
        "A organização foi informada por padrões atuais de produtos de IA: conversa como ponto de partida, projetos com contexto persistente, áreas de trabalho dedicadas para artefatos e fontes secundárias acessíveis sob demanda. Esses padrões foram reinterpretados para engenharia e não reproduzem a identidade visual de nenhuma plataforma."
    )
    doc.add_heading("Interações disponíveis", level=2)
    add_table(
        doc,
        ["Controle", "Resultado"],
        [
            ["Perguntar à Ivy", "Inicia uma conversa em linguagem natural com o contexto do PRJ-001"],
            ["Sugestões rápidas", "Abrem revisões de projeto, cálculos, CAD ou segurança"],
            ["Abrir workspace", "Move a pessoa da conversa para a área técnica do projeto"],
            ["Montar modelo", "Reproduz a sequência de montagem desde a vista explodida"],
            ["Continuar ou pausar", "Controla a animação etapa por etapa"],
            ["Explodir", "Separa visualmente os componentes"],
            ["Rotação", "Altera o ângulo da visualização tridimensional"],
            ["Modelo 3D / Vista CAD", "Alterna entre montagem e planta técnica"],
            ["Etapas da montagem", "Permite saltar diretamente para uma peça"],
        ],
        [3100, 6260],
    )
    add_callout(
        doc,
        "Regra de segurança da interface",
        "O dashboard não transforma uma geometria conceitual em projeto aprovado. Ele exibe permanentemente que a fabricação está bloqueada e que ainda faltam simulação, tolerâncias e validação de segurança.",
    )
    add_callout(
        doc,
        "Disponibilidade",
        "A versão 0.3 está disponível publicamente em https://ivy-engineering-command-center.vercel.app e continua disponível para uso local na pasta Ivy. A publicação não exige login. A ligação automática GitHub-Vercel ainda depende da criação do repositório GitHub; até lá, novas versões devem ser publicadas diretamente na Vercel.",
    )


def add_case_study(doc: Document) -> None:
    doc.add_heading("13. Primeiro caso de teste: garra robótica", level=1)
    doc.add_paragraph(
        "Entrada utilizada: “Projete uma garra robótica capaz de levantar um objeto de 500 gramas.”"
    )
    doc.add_heading("Requisitos confirmados", level=2)
    add_table(
        doc,
        ["Identificador", "Requisito", "Origem", "Normalização"],
        [
            ["REQ-FUNC-001", "Segurar e levantar o objeto definido", "Usuário", "Não aplicável"],
            ["REQ-PERF-001", "Levantar uma carga de 500 g", "Usuário", "0,5 kg"],
        ],
        [1700, 3700, 1700, 2260],
    )
    doc.add_heading("Informações ainda ausentes", level=2)
    add_list(
        doc,
        [
            "Forma, dimensões, material e fragilidade do objeto.",
            "Abertura mínima, abertura máxima e curso da garra.",
            "Orientação, velocidade e aceleração do movimento.",
            "Fonte de alimentação e frequência de operação.",
            "Massa, dimensões e orçamento permitidos para o mecanismo.",
            "Processos de fabricação e ferramentas disponíveis.",
            "Ambiente de operação, contato com pessoas e critérios de segurança.",
        ],
    )
    add_callout(
        doc,
        "Resultado",
        "Risco preliminar baixo; estado: necessita esclarecimentos. Nenhum motor, material ou mecanismo foi escolhido prematuramente.",
    )

    doc.add_heading("Benchmark avançado da versão 0.3", level=2)
    doc.add_paragraph(
        "No teste avançado, o pedido informa nove restrições relevantes sobre uma garra elétrica de dois dedos. A versão anterior reconhecia apenas a massa de 1,5 kg e voltava a perguntar por dados que já estavam no texto. A versão 0.3 passou a extrair os fatos pelo contexto, calcular valores derivados e adaptar as perguntas ao que realmente falta."
    )
    add_table(
        doc,
        ["Critério", "Antes", "Versão 0.3"],
        [
            ["Restrições reconhecidas", "1 de 9", "9 de 9"],
            ["Perguntas repetidas", "Sim", "Não"],
            ["Risco perto de pessoas", "Baixo", "Médio + alertas"],
            ["Cálculos derivados", "Nenhum", "Peso, velocidade e cadência"],
            ["Plano de dimensionamento", "Ausente", "8 verificações listadas"],
            ["Seleção prematura de motor", "Não", "Não"],
        ],
        [3600, 2400, 3360],
    )
    doc.add_heading("Resultado esperado para a pergunta avançada", level=2)
    add_list(
        doc,
        [
            "Faixa de largura: 40 a 90 mm.",
            "Carga máxima: 1,5 kg; peso estático aproximado: 14,71 N.",
            "Elevação: 30 cm em até 2 s; velocidade média de referência: 0,15 m/s.",
            "Cadência: 12 ciclos/min = 0,2 Hz = 5 s por ciclo.",
            "Alimentação: 12 V; estrutura impressa em PETG; orçamento: R$ 600.",
            "Operação próxima a pessoas classificada como risco médio.",
        ],
    )
    add_callout(
        doc,
        "Critério de aprovação",
        "Para este benchmark, a resposta é considerada 10/10 somente quando reconhece todas as restrições, não repete perguntas, mostra cálculos rastreáveis, explicita dados faltantes e mantém a seleção de componentes bloqueada.",
    )


def add_technical_structure(doc: Document) -> None:
    doc.add_heading("14. Estrutura técnica atual", level=1)
    doc.add_paragraph(
        "O projeto funcional acompanha este documento em uma subpasta separada. Os principais arquivos são:"
    )
    add_table(
        doc,
        ["Arquivo principal", "Responsabilidade"],
        [
            ["Executar Ivy.bat", "Iniciador de dois cliques para Windows"],
            ["Executar Dashboard Ivy.bat", "Iniciador local do centro de comando visual"],
            ["ivy.py", "Inicialização simples da aplicação"],
            ["Dashboard/app", "Interface Next.js, montagem interativa e painéis do PRJ-001 publicados na Vercel"],
            ["assistant.py", "Conversa natural, projetos, CAD, verificação automática, histórico, decisões, tarefas e conexão online"],
            ["calculator.py", "Cálculos, rastreabilidade, hipóteses e bloqueios"],
            ["concepts.py", "Comparação de mecanismos, estimativas, ranking e bloqueios"],
            ["cad.py", "Parâmetros, verificações geométricas e exportação SCAD, STL, SVG e JSON"],
            ["verifier.py", "Recálculo independente, unidades, dependências, integridade e bloqueios"],
            ["project_memory.py", "Revisões, eventos, relatórios preservados e decisões persistentes"],
        ],
        [2700, 6660],
    )
    doc.add_heading("Suporte e dados", level=2)
    add_table(
        doc,
        ["Arquivo", "Responsabilidade"],
        [
            ["models.py", "Contrato de dados e validações"],
            ["interpreter.py", "Interpretação local e integração opcional com IA"],
            ["safety.py", "Triagem preliminar de risco"],
            ["cli.py", "Entrada da assistente e do modo de projeto"],
            ["reporting.py", "Formatação dos briefings de engenharia"],
            ["data/ivy_memory.json", "Projetos, respostas, versões, decisões, cálculos, comparações, CAD e verificações locais"],
        ],
        [2700, 6660],
    )
    doc.add_heading("Cobertura automatizada", level=2)
    add_table(
        doc,
        ["Teste ou especificação", "Cobertura"],
        [
            ["test_assistant.py", "Conversa, continuidade, CAD, verificação automática, histórico e decisões"],
            ["test_cad.py", "Parâmetros, arquivos, bloqueios, revisões e falhas de entrada do CAD"],
            ["test_verifier.py", "Recálculo, unidades, alterações, ranking, arquivos CAD e bloqueios"],
            ["test_project_memory.py", "Revisões, eventos, legado e integridade da memória"],
            ["test_calculator.py", "Resultados numéricos e bloqueios da calculadora"],
            ["test_concepts.py", "Resultados numéricos e bloqueios da comparação"],
            ["test_interpreter.py", "Interpretação de requisitos e risco"],
            ["docs/SPEC.md", "Contrato e critérios de aceitação da versão"],
        ],
        [3000, 6360],
    )
    doc.add_heading("Execução local", level=2)
    code = doc.add_paragraph()
    code.paragraph_format.left_indent = Inches(0.25)
    code.paragraph_format.right_indent = Inches(0.25)
    code.paragraph_format.space_before = Pt(4)
    code.paragraph_format.space_after = Pt(10)
    set_paragraph_shading(code, "EEF2F7")
    run = code.add_run("python ivy.py --assistant --mode auto")
    set_run_font(run, name="Consolas", size=9.5, color=INK)
    doc.add_paragraph(
        "O Python 3.12.10 e o ambiente isolado da Ivy já foram testados com sucesso. O SyntaxError observado ocorreu porque o comando foi digitado no modo interativo, não no PowerShell."
    )
    doc.add_paragraph(
        "A integração online está preparada, mas ainda não foi executada porque não existe uma chave de API configurada. O modelo padrão poderá ser alterado pela variável IVY_MODEL."
    )
    doc.add_heading("Como iniciar corretamente no Windows", level=2)
    doc.add_paragraph(
        "A maneira mais simples é abrir a pasta Ivy na Área de Trabalho e dar dois cliques em Executar Ivy.bat. Depois da preparação inicial, a janela mostra Você > e permanece aberta para uma conversa contínua. Fale normalmente com a Ivy."
    )
    doc.add_paragraph(
        "Exemplos: “como está o projeto?”, “faça os cálculos”, “compare os mecanismos”, “crie o modelo CAD”, “mostre o último CAD”, “verifique o projeto”, “mostre o histórico”, “registre a decisão de... porque...”, “anote que...” e “crie uma tarefa...”. Os atalhos iniciados por / continuam funcionando, mas são opcionais. Projetos, versões, decisões, cálculos, comparações, modelos CAD, verificações, respostas, notas e tarefas permanecem somente neste computador."
    )
    add_callout(
        doc,
        "Atenção ao símbolo >>>",
        "Esse símbolo indica que o Python interativo está aberto; nesse local, “python ivy.py ...” gera SyntaxError. Digite exit(), pressione Enter e execute o comando no PowerShell.",
    )
    doc.add_paragraph(
        "Alternativamente, abra o PowerShell na pasta Área de Trabalho\\Ivy\\Projeto e execute o comando mostrado acima."
    )


def add_questionnaire(doc: Document) -> None:
    doc.add_heading("15. Informações para continuar o projeto da garra", level=1)
    doc.add_paragraph(
        "Estas respostas alimentam os cálculos e a comparação de conceitos da Ivy. Elas podem ser guardadas naturalmente, por exemplo: “a resposta 1 é...; a resposta 2 é...”. É válido responder “não sei”; nesse caso, a Ivy deve manter o dado como ausente em vez de inventá-lo."
    )
    questions = [
        "Qual objeto a garra deverá levantar? Informe formato, tamanho aproximado e material.",
        "Qual deve ser a abertura mínima e máxima da garra?",
        "Você prefere atuação elétrica ou deseja que a Ivy compare as opções?",
        "Quantos ciclos por minuto e quantas horas por dia são esperados?",
        "Quais ferramentas de fabricação estão disponíveis, como impressora 3D?",
        "Existe um limite inicial de orçamento?",
        "A garra trabalhará próxima a pessoas ou apenas em bancada isolada?",
    ]
    for index, question in enumerate(questions, 1):
        add_question_field(doc, index, question)


def add_decisions_and_sources(doc: Document) -> None:
    doc.add_heading("16. Registro de decisões", level=1)
    add_table(
        doc,
        ["Data", "Decisão", "Motivo"],
        [
            ["09/08/2026", "Nome adotado: Ivy", "Identidade definida pelo usuário"],
            ["09/08/2026", "Foco inicial em mecânica e mecatrônica", "Alinhamento com projetos físicos"],
            ["09/08/2026", "Começar por software e simulação", "Reduzir custo e risco"],
            ["09/08/2026", "Primeiro benchmark: garra de 500 g", "Problema seguro e mensurável"],
            ["09/08/2026", "Separar linguagem, cálculos e controle", "Evitar ações baseadas em respostas não verificadas"],
            ["09/08/2026", "Criar iniciador de dois cliques", "Simplificar o uso no Windows"],
            ["09/08/2026", "Criar assistente conversacional v0.2", "Não tratar toda fala como descrição de projeto"],
            ["09/08/2026", "Criar analisador contextual v0.3", "Passar no benchmark avançado sem repetir perguntas"],
            ["09/08/2026", "Criar continuidade de projetos v0.4", "Retomar respostas sem reiniciar o briefing"],
            ["09/08/2026", "Criar calculadora rastreável v0.5", "Separar resultados, hipóteses e bloqueios"],
            ["09/08/2026", "Tornar comandos opcionais na v0.5.1", "Permitir interação por linguagem natural"],
            ["09/08/2026", "Comparar conceitos mecânicos na v0.6", "Estimar acionamento antes de escolher componentes"],
            ["09/08/2026", "Criar memória versionada na v0.7", "Preservar mudanças, relatórios e decisões sem apagar o passado"],
            ["09/08/2026", "Criar verificador independente na v0.8", "Bloquear resultados divergentes antes do uso técnico"],
            ["09/08/2026", "Criar CAD paramétrico preliminar na v0.9", "Converter o conceito recomendado em geometria rastreável sem liberar fabricação"],
            ["09/08/2026", "Criar o dashboard Ivy Command Center", "Visualizar CAD, montagem, parâmetros e alertas em uma interface de trabalho"],
            ["09/08/2026", "Publicar o dashboard na Vercel", "Disponibilizar um endereço público sem autenticação pelo ChatGPT"],
            ["09/08/2026", "Redesenhar o dashboard 0.3 com conversa em primeiro plano", "Transformar a Ivy em uma assistente de trabalho simples, moderna e orientada ao diálogo"],
        ],
        [1500, 3500, 4360],
    )

    doc.add_heading("17. Fontes técnicas consultadas", level=1)
    sources = [
        (
            "OpenAI - Saídas estruturadas",
            "https://developers.openai.com/api/docs/guides/structured-outputs",
        ),
        (
            "OpenAI - Chamadas de funções e ferramentas",
            "https://developers.openai.com/api/docs/guides/function-calling",
        ),
        (
            "OpenAI - API em tempo real",
            "https://platform.openai.com/docs/api-reference/realtime",
        ),
        (
            "ROS 2 - Tópicos, serviços e ações",
            "https://docs.ros.org/en/jazzy/How-To-Guides/Topics-Services-Actions.html",
        ),
        (
            "NVIDIA Isaac Sim - Simulação de robôs",
            "https://docs.isaacsim.omniverse.nvidia.com/latest/robot_simulation/index.html",
        ),
        (
            "NIST - Gestão de riscos de IA",
            "https://airc.nist.gov/airmf-resources/airmf/5-sec-core/",
        ),
        (
            "Thomson Linear - Relação entre força, avanço, eficiência e torque de fusos",
            "https://www.thomsonlinear.com/downloads/articles/Why_Go_Metric_taen.pdf",
        ),
        (
            "KHK Gears - Geometria e deslocamento de pinhão e cremalheira",
            "https://khkgears.net/gear-knowledge/gear-technical-reference/calculation-gear-dimensions/",
        ),
        (
            "Gates - Relação entre tensão efetiva e torque em correias sincronizadoras",
            "https://www.gates.com/content/dam/documents-library/whitepapers/timing-belt-theory-white-paper.pdf",
        ),
        (
            "OpenSCAD - Documentação do modelador paramétrico",
            "https://openscad.org/documentation.html",
        ),
        (
            "Vercel - Visão geral de deployments",
            "https://vercel.com/docs/deployments",
        ),
        (
            "OpenAI - Projetos no ChatGPT",
            "https://help.openai.com/en/articles/10169521-using-projects-in-chatgpt",
        ),
        (
            "Anthropic - Artifacts no Claude",
            "https://support.anthropic.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them",
        ),
        (
            "Google - Canvas no Gemini",
            "https://blog.google/products-and-platforms/products/gemini/gemini-collaboration-features/",
        ),
        (
            "Perplexity - Spaces",
            "https://hub-prod.perplexity.ai/hub/faq/what-are-spaces",
        ),
    ]
    num_id = add_numbering_definition(doc, numbered=False)
    for label, url in sources:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(2)
        paragraph.paragraph_format.line_spacing = 1.05
        apply_numbering(paragraph, num_id)
        add_hyperlink(paragraph, label, url)

    doc.add_heading("18. Próximo passo: simulação virtual", level=1)
    doc.add_paragraph(
        "A próxima versão iniciará o Passo 8 usando o CAD da garra em análises virtuais estruturais e cinemáticas. "
        "As propriedades do material, cargas, vínculos e condições de movimento continuarão explícitas e rastreáveis."
    )
    doc.add_heading("Entregas planejadas", level=2)
    add_list(
        doc,
        [
            "Casos de carga para aperto, elevação, aceleração, parada e perda de energia.",
            "Análise estrutural preliminar de tensão e deformação com propriedades do PETG tratadas como hipóteses até medição.",
            "Simulação cinemática das aberturas de 40 e 90 mm, curso dos dedos e possíveis interferências.",
            "Relatórios versionados com entradas, resultados, alertas, arquivos e assinaturas digitais.",
            "Comparação dos resultados com critérios de aceitação; fabricação continuará bloqueada até revisão humana e ensaios.",
        ],
    )
    add_callout(
        doc,
        "Critério de avanço",
        "O Passo 8 estará concluído quando a Ivy reproduzir casos virtuais rastreáveis, detectar violações estruturais ou cinemáticas e preservar claramente o que foi calculado, estimado e ainda precisa de ensaio.",
    )


def build_document(output_path: Path) -> None:
    doc = Document()
    configure_document(doc)
    doc.core_properties.title = "Ivy - Caderno Mestre de Engenharia"
    doc.core_properties.subject = "Visão, arquitetura, requisitos e histórico do projeto Ivy"
    doc.core_properties.author = "Projeto Ivy"
    doc.core_properties.last_modified_by = "Projeto Ivy"
    doc.core_properties.keywords = "Ivy, inteligência artificial, engenharia, mecatrônica"
    doc.core_properties.comments = "Documento vivo do projeto Ivy"

    add_cover(doc)
    add_contents(doc)
    add_vision(doc)
    add_reality_check(doc)
    add_architecture(doc)
    add_roadmap(doc)
    add_step_one(doc)
    add_step_two(doc)
    add_step_three(doc)
    add_step_four(doc)
    add_step_five(doc)
    add_step_six(doc)
    add_step_seven(doc)
    add_dashboard(doc)
    add_case_study(doc)
    add_technical_structure(doc)
    add_questionnaire(doc)
    add_decisions_and_sources(doc)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera o caderno mestre Ivy em DOCX")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build_document(args.output.resolve())
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
