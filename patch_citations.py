from docx import Document
from pathlib import Path
p=Path('Articulo_OrphanHunter_Q1.docx'); d=Document(p)
for para in d.paragraphs:
    if para.text.startswith('La literatura y los marcos de control convergen'):
        para.add_run(' En conjunto, estas recomendaciones se articulan con los principios de secure-by-design, Zero Trust y gestión de cuentas válidas (CISA, 2022; Microsoft, 2024; NIST, 2022; The MITRE Corporation, 2024).')
    if para.text.startswith('El problema se ubica en la intersección'):
        para.add_run(' La analítica de relaciones de AD se apoya en coleccionistas y modelos de caminos de ataque como los documentados para BloodHound (SpecterOps, 2024).')
    if para.text.startswith('La inspección de módulos identificó'):
        para.add_run(' La correspondencia concreta de cada módulo se resume en el Apéndice A (CASO16, 2026).')
    if para.text.startswith('Nota de transparencia:'):
        para.add_run(' El código, dataset y contratos descritos son los materiales técnicos del estudio (CASO16, 2026).')
d.save(p)
print('patched')
