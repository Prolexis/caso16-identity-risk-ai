from docx import Document
from pathlib import Path
p=Path(r'C:\Users\Usuario\Downloads\Normas.docx')
doc=Document(p)
for i, para in enumerate(doc.paragraphs):
    t=para.text.strip()
    if t:
        print(f'P{i}: {t}')
for ti, table in enumerate(doc.tables):
    print(f'\nTABLE {ti}')
    for row in table.rows:
        print(' | '.join(cell.text.strip().replace('\n',' / ') for cell in row.cells))
