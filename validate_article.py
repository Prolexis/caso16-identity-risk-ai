from docx import Document
from pathlib import Path
p=Path('Articulo_OrphanHunter_Q1.docx')
d=Document(p)
text='\n'.join(x.text for x in d.paragraphs)
print('paragraphs',len(d.paragraphs),'tables',len(d.tables),'inline_shapes',len(d.inline_shapes),'chars',len(text))
for needle in ['Resumen','269','113','Figura 6','Referencias','Nota de transparencia']:
    print(needle, needle in text)
print('table_rows', [len(t.rows) for t in d.tables])
print('figs', sorted(str(x) for x in Path('article_assets').glob('fig*.png')))
