from docx import Document
doc = Document(r'P01 Report Template - Data Mart.docx')
for i, t in enumerate(doc.tables, 1):
    print(f'\n=== TABLE {i} ===')
    for r in t.rows:
        print(' | '.join(c.text for c in r.cells))
