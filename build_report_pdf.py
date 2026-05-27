"""Generate the P01 final report PDF following the Moodle template structure."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    KeepTogether, Image
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

OUT = "DSS_###_P01.pdf"

styles = getSampleStyleSheet()
H1 = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=18, spaceAfter=12,
                    spaceBefore=14, textColor=colors.HexColor('#1F3864'),
                    fontName='Helvetica-Bold')
H2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=14, spaceAfter=8,
                    spaceBefore=12, textColor=colors.HexColor('#2E5497'),
                    fontName='Helvetica-Bold')
H3 = ParagraphStyle('H3', parent=styles['Heading3'], fontSize=12, spaceAfter=6,
                    spaceBefore=10, textColor=colors.HexColor('#2E5497'),
                    fontName='Helvetica-Bold')
BODY = ParagraphStyle('Body', parent=styles['BodyText'], fontSize=10.5,
                      leading=14, alignment=TA_JUSTIFY, spaceAfter=6)
BULLET = ParagraphStyle('Bullet', parent=BODY, leftIndent=14, bulletIndent=2,
                        spaceAfter=2)
CAP = ParagraphStyle('Caption', parent=BODY, fontSize=9.5, alignment=TA_CENTER,
                     textColor=colors.HexColor('#444444'), spaceBefore=2,
                     spaceAfter=10, fontName='Helvetica-Oblique')
TITLE = ParagraphStyle('Title', parent=styles['Title'], fontSize=24,
                       spaceAfter=16, alignment=TA_CENTER,
                       textColor=colors.HexColor('#1F3864'),
                       fontName='Helvetica-Bold')
SUB = ParagraphStyle('Sub', parent=BODY, alignment=TA_CENTER, fontSize=12,
                     textColor=colors.HexColor('#404040'))
CODE = ParagraphStyle('Code', parent=BODY, fontName='Courier', fontSize=8.5,
                      leading=10.5, alignment=TA_LEFT, leftIndent=10,
                      backColor=colors.HexColor('#F4F4F4'),
                      borderPadding=4, spaceBefore=4, spaceAfter=8)


def p(t, s=BODY):
    return Paragraph(t, s)


def bullets(items, s=BULLET):
    return [Paragraph(f"&bull;&nbsp;&nbsp;{x}", s) for x in items]


def table_style(header_bg='#1F3864', body_bg='#FFFFFF', alt_bg='#F2F2F2',
                grid='#888888', header_fg='#FFFFFF', font_size=8.5):
    ts = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.HexColor(header_fg)),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, -1), font_size),
        ('ALIGN',      (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW',  (0, 0), (-1, 0), 0.6, colors.HexColor(grid)),
        ('GRID',       (0, 0), (-1, -1), 0.25, colors.HexColor(grid)),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.HexColor(body_bg), colors.HexColor(alt_bg)]),
        ('LEFTPADDING',  (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING',   (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
    ])
    return ts


def make_table(data, col_widths=None, **kw):
    # wrap cells in Paragraph with small style for word-wrap
    cell_style = ParagraphStyle('cell', parent=BODY, fontSize=8.5, leading=10.5,
                                 alignment=TA_LEFT, spaceAfter=0)
    cell_h = ParagraphStyle('cellh', parent=cell_style, fontName='Helvetica-Bold',
                             alignment=TA_CENTER, textColor=colors.white)
    wrapped = []
    for ri, row in enumerate(data):
        new = []
        for c in row:
            if isinstance(c, Paragraph):
                new.append(c)
            else:
                txt = '' if c is None else str(c)
                new.append(Paragraph(txt, cell_h if ri == 0 else cell_style))
        wrapped.append(new)
    t = Table(wrapped, colWidths=col_widths, repeatRows=1)
    t.setStyle(table_style(**kw))
    return t


story = []

# ---------------- COVER ----------------
story.append(Spacer(1, 4*cm))
story.append(p("Data Mart Implementation (P01)", TITLE))
story.append(p("DECISION SUPPORT SYSTEMS, 2025-26", SUB))
story.append(Spacer(1, 4*cm))
story.append(p("<b>Team ###:</b> Samuel José, Miray, Ognyan Dimitrov", SUB))
story.append(Spacer(1, 0.3*cm))
story.append(p("Date: 2026-05-05", SUB))
story.append(PageBreak())

# ---------------- 1. INTRODUCTION ----------------
story.append(p("1. Introduction", H1))
story.append(p(
    "The goal of this project is to design and implement a <b>data mart</b> based on the "
    "operational database of <i>Wide World Importers</i> (WWI), a fictitious wholesale "
    "novelty-goods importer headquartered in San Francisco, US. WWI&rsquo;s customers are mostly "
    "companies who resell to individuals &mdash; specialty stores, supermarkets, computing stores, "
    "tourist-attraction shops &mdash; across the United States."))
story.append(p(
    "The OLTP source covers WWI&rsquo;s full sales workflow: customers place <b>orders</b>, those orders "
    "are converted into <b>invoices</b> (with <b>invoice lines</b> at item granularity), items are "
    "physically moved through one of several <b>delivery methods</b>, and customers settle invoices via "
    "<b>customer transactions</b> linked to <b>payment methods</b>. When stock runs out, items are "
    "<b>backordered</b> and shipped later in a separate shipment. This work focuses on the "
    "<i>post-order</i> portion of the workflow &mdash; invoicing, fulfilment and the goods sold &mdash; "
    "so the data mart can answer questions such as <i>&ldquo;Which products topped sales last month?&rdquo;</i>, "
    "<i>&ldquo;Which sales territories grew the most?&rdquo;</i> or "
    "<i>&ldquo;How does invoice volume vary by delivery method and salesperson?&rdquo;</i>."))
story.append(p(
    "The deliverables include: (i) the dimensional model (Data Warehouse matrix, ER diagram, data "
    "description maps), (ii) the implementation of the <b>ELT process under the medallion "
    "architecture</b> (Bronze &rarr; Silver &rarr; Gold) on a Postgres target, and (iii) automated "
    "<b>data-quality checks</b> that validate the loaded mart."))

# ---------------- 2. DATA SOURCES ----------------
story.append(p("2. Data sources", H1))
story.append(p(
    "The operational source is the <b>WWI sample database</b>, hosted on PostgreSQL at "
    "<font face='Courier'>postgres2.ipca.pt</font> (database <font face='Courier'>wwi</font>). "
    "The relational model is the <i>adapted</i> WWI ER diagram presented in the project guide: it covers "
    "<font face='Courier'>customers</font>, <font face='Courier'>customercategories</font>, "
    "<font face='Courier'>buyinggroups</font>, <font face='Courier'>people</font> (employees and contacts), "
    "<font face='Courier'>cities</font> / <font face='Courier'>stateprovinces</font> / <font face='Courier'>countries</font> (geography), "
    "<font face='Courier'>stockitems</font> / <font face='Courier'>stockgroups</font> / <font face='Courier'>colors</font> / <font face='Courier'>packagetypes</font> (catalog), "
    "<font face='Courier'>orders</font> / <font face='Courier'>orderlines</font> (orders), "
    "<font face='Courier'>invoices</font> / <font face='Courier'>invoicelines</font> (billing), "
    "<font face='Courier'>customertransactions</font> / <font face='Courier'>paymentmethods</font> / "
    "<font face='Courier'>transactiontypes</font> (financial events) and "
    "<font face='Courier'>deliverymethods</font> (logistics)."))
story.append(p(
    "Data profiling was performed against the live source with <font face='Courier'>scripts/data_profiling.py</font> "
    "(VPN ON) and re-validated against the offline snapshots stored in <font face='Courier'>tmp_snapshots/</font>. "
    "The relevant business objects and their volumes are summarized below."))

# Table 1
t1 = [
    ["Event / object", "Table", "Nr. records", "Nr. cols", "PK", "PK uniqueness"],
    ["Buying groups", "buyinggroups", "2", "2", "buyinggroupid", "100.00%"],
    ["Cities", "cities", "37,940", "5", "cityid", "100.00%"],
    ["Colors", "colors", "36", "2", "colorid", "100.00%"],
    ["Countries", "countries", "190", "8", "countryid", "100.00%"],
    ["Customer categories", "customercategories", "8", "2", "customercategoryid", "100.00%"],
    ["Customers", "customers", "663", "28", "customerid", "100.00%"],
    ["Customer transactions", "customertransactions", "97,147", "12", "customertransactionid", "100.00%"],
    ["Delivery methods", "deliverymethods", "10", "2", "deliverymethodid", "100.00%"],
    ["Invoice lines", "invoicelines", "228,265", "11", "invoicelineid", "100.00%"],
    ["Customer invoices", "invoices", "70,510", "23", "invoiceid", "100.00%"],
    ["Order lines", "orderlines", "231,412", "9", "orderlineid", "100.00%"],
    ["Customer orders", "orders", "73,595", "14", "orderid", "100.00%"],
    ["Package types", "packagetypes", "14", "2", "packagetypeid", "100.00%"],
    ["Payment methods", "paymentmethods", "4", "2", "paymentmethodid", "100.00%"],
    ["Employees and contacts", "people", "1,111", "18", "personid", "100.00%"],
    ["Special deals", "specialdeals", "2", "12", "specialdealid", "100.00%"],
    ["State provinces", "stateprovinces", "53", "6", "stateprovinceid", "100.00%"],
    ["Stock groups", "stockgroups", "10", "2", "stockgroupid", "100.00%"],
    ["Products / stock items", "stockitems", "227", "22", "stockitemid", "100.00%"],
    ["Transaction types", "transactiontypes", "13", "2", "transactiontypeid", "100.00%"],
]
story.append(make_table(t1, col_widths=[3.3*cm, 3.0*cm, 2.0*cm, 1.4*cm, 3.4*cm, 2.6*cm]))
story.append(p("Table 1: Summary of WWI database contents", CAP))

story.append(p("Profiling findings (relevant to the mart):", H3))
story += bullets([
    "All primary keys present 100% uniqueness, so business keys can be reused as join columns into the dimensional layer.",
    "<font face='Courier'>paymentmethodid</font> lives on <font face='Courier'>customertransactions</font> (not on <font face='Courier'>invoices</font>), so payment information is collected from the transactions side, not directly from invoice headers.",
    "The <font face='Courier'>countries</font> snapshot exhibits a column-name typo (<font face='Courier'>ountryname</font>); this is corrected during the silver transform.",
    "<font face='Courier'>invoicelines</font> (228,265 rows) and <font face='Courier'>invoices</font> (70,510 rows) are the highest-volume operational events, so they drive the grain of the two fact tables.",
])

# ---------------- 3. DIMENSIONAL MODELLING ----------------
story.append(PageBreak())
story.append(p("3. Dimensional modelling", H1))
story.append(p("Goals and analytical questions", H2))
story.append(p("The data mart was designed to support a self-service analytic layer answering questions such as:"))
story += bullets([
    "Which <b>stock items</b> generated the highest revenue last month / quarter / year?",
    "Which <b>customer categories</b> or <b>sales territories</b> show the largest sales growth?",
    "Which <b>salespersons</b> are top performers (by invoice volume and by line value)?",
    "How does the choice of <b>delivery method</b> affect invoice value and on-time fulfilment?",
    "What is the <b>invoice amount</b> distributed by <b>customer</b>, <b>date</b>, <b>location</b> and <b>delivery method</b>?",
    "What is the breakdown of <b>payments</b> by <b>payment method</b> and <b>transaction type</b> (auxiliary, served from <font face='Courier'>customertransactions</font>)?",
])
story.append(p(
    "These questions translate to two confirmed business processes &mdash; <b>Sales</b> (line-level) and "
    "<b>Invoicing</b> (header-level) &mdash; sharing conformed dimensions for time, customer, employee and location."))

# Table 2 — DW Matrix
story.append(p("Data Warehouse Matrix", H2))
t2 = [
    ["BUSINESS PROCESS \\ DIMENSION", "DimDate", "DimCustomer", "DimEmployee", "DimProduct", "DimLocation", "DimDeliveryMethod", "DimPaymentMethod"],
    ["Sales (FactSales) — invoice line", "X", "X", "X", "X", "X", "", ""],
    ["Invoicing (FactInvoices) — invoice header", "X", "X", "X", "", "X", "X", ""],
    ["Payments (auxiliary, customertransactions)", "X", "X", "", "", "", "", "X"],
]
story.append(make_table(t2, col_widths=[5.2*cm, 1.4*cm, 1.7*cm, 1.7*cm, 1.6*cm, 1.6*cm, 2.1*cm, 2.0*cm]))
story.append(p("Table 2: Data Warehouse Matrix", CAP))
story.append(p(
    "The two primary fact tables loaded into Gold are <font face='Courier'>FactSales</font> and "
    "<font face='Courier'>FactInvoices</font>. The third row (Payments) is currently materialized at the silver "
    "level via <font face='Courier'>silver.stg_*</font> for completeness; it can be promoted to Gold as "
    "<font face='Courier'>FactPayments</font> if the analytical scope is later widened."))

# ---------------- 4. DESIGN ----------------
story.append(PageBreak())
story.append(p("4. Design of the dimensional data model", H1))
story.append(p("Fact tables — granularity and measures", H2))
story.append(p("<b>FactSales</b> &mdash; <i>grain: one row per invoice line</i> (one row per <font face='Courier'>invoicelines.invoicelineid</font>)."))
fs = [
    ["Measure", "Type", "Derivation"],
    ["Quantity", "Additive", "Direct from invoicelines.quantity"],
    ["UnitPrice", "Non-additive (avg)", "Direct from invoicelines.unitprice"],
    ["TaxAmount", "Additive", "Direct from invoicelines.taxamount"],
    ["ExtendedPrice", "Additive", "Direct from invoicelines.extendedprice (= quantity × unitprice + tax)"],
    ["LineProfit", "Additive", "Direct from invoicelines.lineprofit"],
]
story.append(make_table(fs, col_widths=[3.2*cm, 3.5*cm, 9.0*cm]))
story.append(Spacer(1, 6))

story.append(p("<b>FactInvoices</b> &mdash; <i>grain: one row per invoice header</i> (one row per <font face='Courier'>invoices.invoiceid</font>)."))
fi = [
    ["Measure", "Type", "Derivation"],
    ["InvoiceAmount", "Additive", "SUM(invoicelines.extendedprice) over the invoice"],
    ["PaymentDelay_Days", "Semi-additive", "MIN(customertransactions.transactiondate) − invoices.invoicedate"],
    ["OutstandingBalance", "Semi-additive", "InvoiceAmount − SUM(customertransactions.transactionamount)"],
]
story.append(make_table(fi, col_widths=[4.2*cm, 3.0*cm, 8.5*cm]))
story.append(Spacer(1, 4))
story.append(p(
    "<font face='Courier'>PaymentDelay_Days</font> and <font face='Courier'>OutstandingBalance</font> are "
    "<b>derived measures</b> computed during the silver-to-gold step by joining "
    "<font face='Courier'>customertransactions</font> against <font face='Courier'>invoices</font>."))

story.append(p("Dimensions and SCD policy", H2))
dims = [
    ["Dimension", "SCD type", "Justification"],
    ["DimDate", "Static (Type 0)", "Calendar dimension generated programmatically; no history needed."],
    ["DimCustomer", "Type 2", "Customers can change category, name, etc.; history matters for trend analysis."],
    ["DimEmployee", "Type 2", "Salesperson role and full name change over time."],
    ["DimProduct", "Type 2", "Stock items can be renamed / rebranded."],
    ["DimLocation", "Type 2", "Composite of cities × stateprovinces × countries; treated as Type 2 for consistency."],
    ["DimDeliveryMethod", "Type 2 (small)", "Track renames; only 10 rows."],
    ["DimPaymentMethod", "Type 2 (small)", "Track renames; only 4 rows."],
]
story.append(make_table(dims, col_widths=[3.5*cm, 3.0*cm, 9.2*cm]))
story.append(Spacer(1, 4))
story.append(p(
    "Surrogate keys (auto-incrementing <font face='Courier'>SERIAL</font>) decouple the dimensional model "
    "from the OLTP business keys and enable Type 2 history (multiple rows per business key, controlled by "
    "<font face='Courier'>version</font> / <font face='Courier'>date_from</font> / <font face='Courier'>date_to</font>)."))

# ER Diagram (text-based since mermaid won't render in PDF)
story.append(p("ER Diagram (star schema)", H2))
story.append(p(
    "The star schema is composed of two fact tables (<b>FactSales</b>, <b>FactInvoices</b>) and seven "
    "dimensions sharing conformed surrogate keys. The diagram is reproduced as a textual map below; the "
    "Mermaid source is bundled in <font face='Courier'>REPORT.md</font> for graphical rendering."))

er_diagram = (
    "                          +--------------+\n"
    "                          |   DimDate    |\n"
    "                          +------+-------+\n"
    "                                 |\n"
    "    +------------+        +------+-------+        +-------------------+\n"
    "    | DimProduct +------->|              |<-------+ DimDeliveryMethod |\n"
    "    +------------+        |              |        +-------------------+\n"
    "                          |  FactSales   |\n"
    "    +-------------+       |              |\n"
    "    | DimCustomer +------>|              |\n"
    "    +-------------+       |              |        +------------------+\n"
    "                          |              |        |  FactInvoices    |<--+ DimEmployee\n"
    "    +-------------+       |              |        |                  |   +-----------+\n"
    "    | DimEmployee +------>+------+-------+        |                  |\n"
    "    +-------------+              ^                +---------+--------+\n"
    "                                 |                          ^\n"
    "    +--------------+             |                          |\n"
    "    |  DimLocation +-------------+--------------------------+\n"
    "    +--------------+\n"
    "\n"
    "    (DimPaymentMethod is populated from customertransactions; it is conformed but\n"
    "     joined indirectly to FactInvoices via invoiceid mapping.)\n"
)
story.append(Paragraph("<pre>" + er_diagram.replace('<','&lt;').replace('>','&gt;') + "</pre>", CODE))
story.append(p("Data description maps for the two reference dimensions (DimCustomer and DimProduct) are presented in <b>Appendix A</b>."))

# ---------------- 5. IMPLEMENTATION ----------------
story.append(PageBreak())
story.append(p("5. Data mart implementation", H1))
story.append(p(
    "The pipeline follows the <b>medallion architecture</b> (Bronze &rarr; Silver &rarr; Gold) on a Postgres "
    "DWH (Supabase). Source extraction (over VPN, against <font face='Courier'>postgres2.ipca.pt</font>) and "
    "DWH loading (off VPN) are split across separate notebook cells so the operator toggles VPN exactly once."))
arch = (
    "public.* (WWI source — VPN ON)\n"
    "        |  save -> CSV + schema JSON in tmp_snapshots/, tmp_increments/\n"
    "        v\n"
    "bronze.* (full-fidelity copy — VPN OFF)\n"
    "        |  read active snapshot, clean, conform\n"
    "        v\n"
    "silver.stg_* (staging, project-only columns — VPN OFF)\n"
    "        |  SCD Type 2 for dims, surrogate-key lookups for facts\n"
    "        v\n"
    "gold.* (star schema — VPN OFF)\n"
)
story.append(Paragraph("<pre>" + arch.replace('<','&lt;').replace('>','&gt;') + "</pre>", CODE))

story.append(p("Notebooks and transformations", H2))
nb = [
    ["Notebook", "Layer", "Responsibility"],
    ["00_setup.ipynb", "meta", "Loads .env, builds engines, creates bronze/silver/gold schemas, deploys bronze._load_control and the gold DDL."],
    ["01_bronze.ipynb", "bronze", "Two-phase pattern. Extract (VPN ON): dumps each source table to tmp_snapshots/<table>.csv with schema JSON. Apply (VPN OFF): rebuilds bronze tables from the JSON, loads CSVs and registers each load into bronze._load_control."],
    ["02_silver.ipynb", "silver", "DROP+CREATE staging tables, applies clean_str to free-text fields, fixes the ountryname → country typo, joins customercategories, joins cities × stateprovinces × countries, computes derived measures."],
    ["03_gold.ipynb", "gold", "Generates DimDate, calls load_scd2() per dimension (uses row_hash() to detect changes), then loads FactSales and FactInvoices via surrogate-key lookup against the current dim row (date_to IS NULL). Indexes/constraints applied from scripts/create_indexes_and_constraints.sql."],
]
story.append(make_table(nb, col_widths=[3.0*cm, 1.8*cm, 11.0*cm]))

story.append(p("Key ELT functions", H2))
story += bullets([
    "<font face='Courier'>make_engine()</font> — factory returning the right SQLAlchemy engine for source vs DWH.",
    "<font face='Courier'>register_load()</font> — writes one row to <font face='Courier'>bronze._load_control</font> per applied snapshot/increment.",
    "<font face='Courier'>compute_row_hash() / row_hash()</font> — canonicalize values and hash with MD5 over '|'-joined SCD2 attributes.",
    "<font face='Courier'>load_scd2()</font> — closes the previous current row (<font face='Courier'>date_to = run_at</font>) and inserts <font face='Courier'>version + 1</font> when a hash change is detected; otherwise no-ops.",
])

story.append(p("Quality checks (04_quality_checks.py)", H2))
story.append(p("For every load, the script writes <font face='Courier'>quality_report.json</font> and exits non-zero if any check fails:"))
story += bullets([
    "<b>Orphan FKs</b> in both fact tables.",
    "<b>Unmapped FKs</b> &mdash; silver business keys with no current dim row (silent data-loss detection).",
    "<b>Duplicate current dim rows</b> (must be 0 thanks to partial-unique indexes).",
    "<b>Null percentages</b> on business keys vs <font face='Courier'>THRESHOLD_NULL_PERCENT = 5.0</font>.",
    "<b>Row-count reconciliation</b> between <font face='Courier'>silver.stg_*</font> and <font face='Courier'>gold.dim* (current)</font>.",
])

story.append(p("Data mart content — summary of loaded rows (run: 2026-05-05)", H2))
content = [
    ["Gold table", "Current rows", "Notes"],
    ["gold.DimDate", "(calendar)", "Snapshot dimension covering invoice / transaction date range."],
    ["gold.DimEmployee", "1,111", "SCD2; reconciled silver→gold 1,111 ↔ 1,111."],
    ["gold.DimCustomer", "663", "SCD2; reconciled 663 ↔ 663."],
    ["gold.DimProduct", "227", "SCD2; reconciled 227 ↔ 227."],
    ["gold.DimLocation", "37,940", "SCD2; composite city × state × country, reconciled 37,940 ↔ 37,940."],
    ["gold.DimDeliveryMethod", "10", "Reconciled 10 ↔ 10."],
    ["gold.DimPaymentMethod", "4", "Reconciled 4 ↔ 4."],
    ["gold.FactSales", "228,265", "Grain = invoice line, derived from invoicelines."],
    ["gold.FactInvoices", "70,510", "Grain = invoice header, derived from invoices."],
]
story.append(make_table(content, col_widths=[4.5*cm, 2.5*cm, 9.0*cm]))
story.append(Spacer(1, 4))
story.append(p(
    "<b>Quality verdict:</b> all orphan-FK counts = 0, all unmapped-FK counts = 0, no duplicate current "
    "rows and 0% nulls on every business key. The mart is internally consistent."))

# ---------------- 6. CONCLUSION ----------------
story.append(PageBreak())
story.append(p("6. Conclusion", H1))
story.append(p("Strengths.", H3))
story += bullets([
    "End-to-end medallion architecture (Bronze &rarr; Silver &rarr; Gold) with clean separation between source extraction (VPN ON) and DWH loading (VPN OFF).",
    "Seven dimensions and two facts following textbook Kimball patterns: SERIAL surrogate keys, SCD Type 2 with version / date_from / date_to, partial-unique indexes guarding the current row.",
    "<b>Idempotent pipeline</b>: silver tables are DROP+CREATE on every run, gold dimensions merged via SCD2 hashing, bronze._load_control records every apply for full traceability.",
    "Automated quality checks (04_quality_checks.py + 99_verification.py) close the loop: a failing FK or duplicate dim row breaks the build, not the report.",
])
story.append(p("Weaknesses / known limitations.", H3))
story += bullets([
    "DimDate is loaded as a snapshot covering only the observed invoice date range; a fully-attributed calendar (fiscal year, holidays, weekday names) would broaden time-based analysis.",
    "Payments are exposed only via silver staging and the auxiliary customertransactions mapping; a dedicated FactPayments would make payment-method analytics first-class.",
    "Source-side schema typos (ountryname) are silently fixed in silver but not pushed back as a data-quality issue to the source owners.",
    "OrderLines and the fulfilment side (backorders) are not modelled; the mart focuses on invoiced sales only.",
])
story.append(p("Future work.", H3))
story += bullets([
    "Promote silver.stg_fact_invoices payment join into a Gold FactPayments table.",
    "Extend DimDate with a generated 2010–2030 range and standard fiscal/holiday attributes.",
    "Add aggregate / cumulative tables (agg_sales_monthly, agg_sales_by_territory) for dashboard latency.",
    "Wire the quality report into a CI step so an ERROR row in bronze._load_control blocks downstream layers automatically.",
])

# ---------------- 7. BIBLIOGRAPHY ----------------
story.append(p("7. Bibliography", H1))
story += bullets([
    "Kimball, R., &amp; Ross, M. (2013). <i>The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling</i> (3rd ed.). Wiley.",
    "Inmon, W. H. (2005). <i>Building the Data Warehouse</i> (4th ed.). Wiley.",
    "Microsoft. (n.d.). <i>Wide World Importers sample database overview</i>. Retrieved from https://docs.microsoft.com/en-us/sql/samples/wide-world-importers-what-is",
    "Databricks. (2023). <i>What is the medallion lakehouse architecture?</i> Retrieved from https://www.databricks.com/glossary/medallion-architecture",
    "The PostgreSQL Global Development Group. (2024). <i>PostgreSQL 16 Documentation</i>. Retrieved from https://www.postgresql.org/docs/16/",
])

# ---------------- APPENDIX A ----------------
story.append(PageBreak())
story.append(p("Appendix A — Data description maps", H1))
story.append(p(
    "This appendix documents the column-level mapping between the source (OLTP) and the data mart (Gold) "
    "for the two reference dimensions, <b>DimCustomer</b> and <b>DimProduct</b>."))

# Table 3 - DimCustomer header
story.append(p("Table 3 — Data description map of DimCustomer", H3))
hdr = [
    ["Name", "Type of table", "Nr. records", "Description"],
    ["DimCustomer", "Dimension", "663 (current)", "Customers of WWI, with category resolved from customercategories. SCD Type 2: history preserved via version / date_from / date_to."],
]
story.append(make_table(hdr, col_widths=[2.5*cm, 2.5*cm, 2.6*cm, 8.4*cm]))
story.append(Spacer(1, 4))

t3 = [
    ["Column", "Description", "Data type", "SCD", "Src table", "Src column", "Src type", "ETL rules", "Example"],
    ["CustomerKey", "Surrogate key", "INT (SERIAL)", "1", "—", "—", "—", "Auto-generated by Postgres SERIAL.", "1, 2, 3, …"],
    ["CustomerID", "Business key", "INT", "1", "customers", "customerid", "int4", "Direct copy.", "832"],
    ["CustomerName", "Customer name", "VARCHAR(255)", "2", "customers", "customername", "varchar", "clean_str (trim, empty → NULL).", "Alvin Bollinger"],
    ["Category", "Customer category", "VARCHAR(255)", "2", "customercategories", "customercategoryname", "varchar", "LEFT JOIN on customercategoryid, then clean_str.", "Novelty Shop"],
    ["version", "SCD2 version", "INT", "—", "—", "—", "—", "Set to 1 on insert; +1 on hash diff.", "1, 2"],
    ["date_from", "Validity start", "TIMESTAMP", "—", "—", "—", "—", "run_at of the load that introduced the row.", "2026-05-04 22:00:00"],
    ["date_to", "Validity end", "TIMESTAMP", "—", "—", "—", "—", "NULL = current; set on UPDATE detection.", "NULL"],
]
story.append(make_table(t3, col_widths=[2.0*cm, 2.0*cm, 1.7*cm, 0.8*cm, 1.7*cm, 2.0*cm, 1.4*cm, 3.5*cm, 2.4*cm]))
story.append(p(
    "<b>SCD Type 2 detection.</b> Each silver row is hashed over [CustomerName, Category]; if the hash "
    "differs from the current gold row for the same CustomerID, the gold row is closed (date_to = run_at) "
    "and a new row is inserted with version + 1.", BODY))

# Table 4
story.append(Spacer(1, 8))
story.append(p("Table 4 — Data description map of DimProduct", H3))
hdr2 = [
    ["Name", "Type of table", "Nr. records", "Description"],
    ["DimProduct", "Dimension", "227 (current)", "Stock items sold by WWI, including commercial brand. SCD Type 2 to capture renames / rebrandings."],
]
story.append(make_table(hdr2, col_widths=[2.5*cm, 2.5*cm, 2.6*cm, 8.4*cm]))
story.append(Spacer(1, 4))
t4 = [
    ["Column", "Description", "Data type", "SCD", "Src table", "Src column", "Src type", "ETL rules", "Example"],
    ["ProductKey", "Surrogate key", "INT (SERIAL)", "1", "—", "—", "—", "Auto-generated by Postgres SERIAL.", "1, 2, 3, …"],
    ["StockItemID", "Business key", "INT", "1", "stockitems", "stockitemid", "int4", "Direct copy.", "11"],
    ["StockItemName", "Item name", "VARCHAR(255)", "2", "stockitems", "stockitemname", "varchar", "clean_str (trim, empty → NULL).", "Spy uniform"],
    ["Brand", "Brand", "VARCHAR(255)", "2", "stockitems", "brand", "varchar", "clean_str; may be NULL for unbranded.", "Northwind, NULL"],
    ["version", "SCD2 version", "INT", "—", "—", "—", "—", "Same as DimCustomer.", "1, 2"],
    ["date_from", "Validity start", "TIMESTAMP", "—", "—", "—", "—", "run_at of the load.", "2026-05-04 22:00:00"],
    ["date_to", "Validity end", "TIMESTAMP", "—", "—", "—", "—", "NULL for current row.", "NULL"],
]
story.append(make_table(t4, col_widths=[2.0*cm, 2.0*cm, 1.7*cm, 0.8*cm, 1.7*cm, 2.0*cm, 1.4*cm, 3.5*cm, 2.4*cm]))
story.append(Spacer(1, 4))
story.append(p(
    "<b>SCD legend:</b> 1 = SCD Type 1 (overwrite); 2 = SCD Type 2 (track history); — = technical column."))

# ---------------- APPENDIX B ----------------
story.append(PageBreak())
story.append(p("Appendix B — SQL DW Script", H1))
story.append(p(
    "Full DDL &mdash; schemas, bronze._load_control, the seven dimensions, both facts, indexes and "
    "partial-unique constraints. Maintained at <font face='Courier'>scripts/dw_script.sql</font>."))

with open(os.path.join(os.path.dirname(__file__) or '.', 'scripts', 'dw_script.sql'),
          'r', encoding='utf-8') as f:
    sql_text = f.read()

# Render the SQL as preformatted code
import html
escaped = html.escape(sql_text).replace('\n', '<br/>')
story.append(Paragraph(escaped, CODE))


# ---------------- BUILD ----------------
def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#888888'))
    canvas.drawString(2*cm, 1.2*cm, f"DSS P01 — Data Mart (WWI)")
    canvas.drawRightString(A4[0] - 2*cm, 1.2*cm, f"page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2*cm, bottomMargin=2*cm,
    title="DSS P01 — WWI Data Mart Report",
    author="Samuel José, Miray, Ognyan Dimitrov"
)
doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
print(f"OK -> {OUT}")
