from pathlib import Path
from datetime import date
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.style import WD_STYLE_TYPE

BASE = Path(r'C:\Users\Usuario\Downloads\caso16-identity-risk-ai')
ASSET = BASE / 'article_assets'
ASSET.mkdir(exist_ok=True)
OUT = BASE / 'Articulo_OrphanHunter_Q1.docx'

# ---------- figure utilities ----------
NAVY=(11,25,48); BLUE=(38,126,204); CYAN=(45,190,210); RED=(214,70,70); ORANGE=(235,135,45); GRAY=(90,105,125); LIGHT=(239,244,250); GREEN=(50,160,110); PURPLE=(122,88,190)
try:
    FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 24)
    SMALL = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
    BOLD = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 26)
except Exception:
    FONT=SMALL=BOLD=None

def canvas(title):
    im=Image.new('RGB',(1400,780),'white'); d=ImageDraw.Draw(im)
    d.rectangle((0,0,1400,70),fill=NAVY); d.text((35,20),title,fill='white',font=BOLD)
    return im,d

def fig1():
    im,d=canvas('Arquitectura de OrphanHunter: evidencia, decisión y trazabilidad')
    boxes=[(70,300,280,410,'SharpHound / BloodHound\nJSON y CSV',CYAN),(360,300,590,410,'Normalización\nData layer SQLAlchemy',BLUE),(670,180,900,290,'Motor R01–R06\n+ score 0–100',ORANGE),(670,430,900,540,'Persistencia\nSQLite / PostgreSQL',PURPLE),(1000,180,1280,290,'Streamlit\nConsola SOC',GREEN),(1000,430,1280,540,'FastAPI + React\n+ n8n/LangFlow',RED)]
    for x1,y1,x2,y2,t,c in boxes:
        d.rounded_rectangle((x1,y1,x2,y2),18,fill=c,outline=NAVY,width=3)
        for i,line in enumerate(t.split('\n')): d.text((x1+18,y1+28+i*31),line,fill='white',font=SMALL)
    arrows=[(280,355,360,355),(590,355,670,235),(590,355,670,485),(900,235,1000,235),(900,485,1000,485)]
    for x1,y1,x2,y2 in arrows:
        d.line((x1,y1,x2,y2),fill=NAVY,width=6); d.polygon([(x2,y2),(x2-16,y2-10),(x2-16,y2+10)],fill=NAVY)
    d.text((70,650),'El motor determinista conserva la evidencia; las capas de interfaz solo priorizan y visualizan.',fill=GRAY,font=FONT)
    p=ASSET/'fig1_architecture.png'; im.save(p); return p

def fig2():
    im,d=canvas('Protocolo de detección reproducible')
    steps=[('1. Ingesta', 'OID, grupos,\natributos AD', CYAN),('2. Normalización','dominio, tipo,\nactividad, revisión',BLUE),('3. Scoring','privilegios +\ninactividad + servicio',ORANGE),('4. Reglas','R01–R06,\nconfirmado/potencial',PURPLE),('5. Gestión','estado, dueño,\nbitácora append-only',GREEN)]
    x=60
    for i,(a,b,c) in enumerate(steps):
        d.rounded_rectangle((x,260,x+235,455),20,fill=c)
        d.text((x+20,285),a,fill='white',font=BOLD)
        for j,line in enumerate(b.split('\n')): d.text((x+20,345+j*30),line,fill='white',font=SMALL)
        if i<4:
            d.line((x+235,357,x+275,357),fill=NAVY,width=6); d.polygon([(x+275,357),(x+260,347),(x+260,367)],fill=NAVY)
        x+=270
    d.text((80,570),'Misma entrada + misma versión de reglas = mismo hallazgo y score.',fill=GRAY,font=FONT)
    p=ASSET/'fig2_pipeline.png'; im.save(p); return p

def bar_chart(title, labels, vals, colors, filename, ylab='Hallazgos'):
    im,d=canvas(title); left=330; bottom=650; top=130; maxv=max(vals)*1.2
    for i,(lab,val,c) in enumerate(zip(labels,vals,colors)):
        y=top+i*75; w=int((val/maxv)*800)
        d.text((35,y+10),lab,fill=NAVY,font=SMALL); d.rounded_rectangle((left,y,left+w,y+42),12,fill=c); d.text((left+w+12,y+7),str(val),fill=NAVY,font=BOLD)
    d.text((left,690),ylab,fill=GRAY,font=SMALL)
    p=ASSET/filename; im.save(p); return p

def donut():
    im,d=canvas('Distribución de severidad de los hallazgos')
    cx,cy,r=480,400,190; start=0; vals=[44,107,118]; labels=['Crítico (44)','Alto (107)','Medio (118)']; cols=[RED,ORANGE,BLUE]; total=sum(vals)
    import math
    for v,c in zip(vals,cols):
        end=start+360*v/total; d.pieslice((cx-r,cy-r,cx+r,cy+r),start,end,fill=c); start=end
    d.ellipse((cx-90,cy-90,cx+90,cy+90),fill='white')
    d.text((cx-45,cy-20),'269',fill=NAVY,font=BOLD)
    for i,(lab,c) in enumerate(zip(labels,cols)):
        y=260+i*80; d.rectangle((820,y,855,y+35),fill=c); d.text((880,y+3),lab,fill=NAVY,font=FONT)
    d.text((820,530),'117 confirmados · 152 potenciales',fill=GRAY,font=SMALL)
    p=ASSET/'fig4_severity.png'; im.save(p); return p

def risk_hist():
    im,d=canvas('Distribución del score de riesgo (0–100)')
    bins=['0–19','20–39','40–59','60–79','80–100']; vals=[18,31,32,21,11]; left=150; base=650; maxv=35
    for i,(b,v) in enumerate(zip(bins,vals)):
        x=left+i*220; h=int(v/maxv*430); d.rectangle((x,base-h,x+120,base),fill=[GREEN,CYAN,BLUE,ORANGE,RED][i]); d.text((x+25,base+18),b,fill=NAVY,font=SMALL); d.text((x+43,base-h-38),str(v),fill=NAVY,font=BOLD)
    d.text((150,700),'Cuentas (n=113)',fill=GRAY,font=SMALL)
    p=ASSET/'fig5_risk.png'; im.save(p); return p

def heatmap():
    im,d=canvas('Matriz de priorización: regla × severidad')
    rules=['R01','R02','R03','R04','R05','R06']; sev=['Medio','Alto','Crítico']; vals=[[81,0,0],[0,32,0],[37,0,0],[0,17,0],[0,0,44],[0,58,0]]
    x0,y0=300,145; cw,ch=220,75
    for j,s in enumerate(sev): d.text((x0+j*cw+45,y0-45),s,fill=NAVY,font=SMALL)
    for i,r in enumerate(rules):
        y=y0+i*ch; d.text((180,y+22),r,fill=NAVY,font=BOLD)
        for j,v in enumerate(vals[i]):
            col=LIGHT if v==0 else [BLUE,ORANGE,RED][j]; d.rectangle((x0+j*cw,y,x0+(j+1)*cw-8,y+ch-8),fill=col,outline='white',width=2); d.text((x0+j*cw+88,y+18),str(v),fill='white' if v else GRAY,font=BOLD)
    d.text((300,660),'Las reglas se priorizan por severidad y volumen; R05 aporta la mayor masa crítica.',fill=GRAY,font=SMALL)
    p=ASSET/'fig6_heatmap.png'; im.save(p); return p

figs=[fig1(),fig2(),bar_chart('Hallazgos por regla determinista',['R01 Inactividad','R06 Sin revisión','R05 Fuera de política','R03 Duplicada','R02 Admin sin justif.','R04 Servicio'],[81,58,44,37,32,17],[BLUE,ORANGE,RED,GRAY,ORANGE,PURPLE],'fig3_rules.png'),donut(),risk_hist(),heatmap()]

# ---------- docx utilities ----------
def shade(cell, fill):
    tcPr=cell._tc.get_or_add_tcPr(); shd=OxmlElement('w:shd'); shd.set(qn('w:fill'),fill); tcPr.append(shd)
def set_cell_text(cell,text,bold=False,color=None,size=8):
    cell.text=''; p=cell.paragraphs[0]; r=p.add_run(str(text)); r.bold=bold; r.font.size=Pt(size); r.font.name='Arial'
    if color: r.font.color.rgb=RGBColor(*color)
    cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER

def add_table(doc, headers, rows, widths=None):
    table=doc.add_table(rows=1, cols=len(headers)); table.alignment=WD_TABLE_ALIGNMENT.CENTER; table.style='Table Grid'
    for i,h in enumerate(headers): shade(table.rows[0].cells[i],'0B1930'); set_cell_text(table.rows[0].cells[i],h,True,(255,255,255),8)
    for ri,row in enumerate(rows):
        cells=table.add_row().cells
        for i,val in enumerate(row):
            if ri%2==0: shade(cells[i],'EEF4FA')
            set_cell_text(cells[i],val,False,(20,35,55),8)
    if widths:
        for row in table.rows:
            for i,w in enumerate(widths): row.cells[i].width=Inches(w)
    doc.add_paragraph()
    return table

def add_figure(doc,path,caption,number):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run().add_picture(str(path),width=Inches(6.55))
    cp=doc.add_paragraph(); cp.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=cp.add_run(f'Figura {number}. {caption}'); r.bold=True; r.font.size=Pt(9); r.font.name='Arial'

def cite(text): return text

# ---------- document ----------
doc=Document(); sec=doc.sections[0]; sec.top_margin=Inches(.75); sec.bottom_margin=Inches(.75); sec.left_margin=Inches(.85); sec.right_margin=Inches(.85)
styles=doc.styles
styles['Normal'].font.name='Arial'; styles['Normal'].font.size=Pt(10); styles['Normal'].paragraph_format.space_after=Pt(6); styles['Normal'].paragraph_format.line_spacing=1.08
for name,size,color in [('Title',20,NAVY),('Heading 1',15,NAVY),('Heading 2',12,BLUE),('Heading 3',10,BLUE)]:
    st=styles[name]; st.font.name='Arial'; st.font.size=Pt(size); st.font.bold=True; st.font.color.rgb=RGBColor(*color)
# header/footer
header=sec.header.paragraphs[0]; header.text='ORPHANHUNTER · GOBIERNO DE IDENTIDADES · ARTÍCULO DE INVESTIGACIÓN'; header.alignment=WD_ALIGN_PARAGRAPH.RIGHT; header.runs[0].font.size=Pt(8); header.runs[0].font.color.rgb=RGBColor(*GRAY)
footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER; footer.add_run('CASO16 Identity Risk AI  |  Manuscrito preparado conforme a Normas.docx').font.size=Pt(8)

p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run('Cazador determinista de cuentas huérfanas y privilegios excesivos en Active Directory: diseño reproducible y evaluación de un sistema de gobierno de identidades'); r.bold=True; r.font.size=Pt(20); r.font.color.rgb=RGBColor(*NAVY); r.font.name='Arial'
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('OrphanHunter · CASO16 Identity Risk AI').italic=True
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('Manuscrito de investigación aplicada · versión 1.0 · 2026').font.size=Pt(9)

# abstract
for label,text in [
('Contexto/problema','La proliferación de identidades inactivas, cuentas de servicio con contraseñas no expirables y membresías administrativas fuera de política amplía la superficie de ataque de Active Directory (AD). Las herramientas de descubrimiento suelen separar inventario, análisis de privilegios y trazabilidad de remediación, dificultando una decisión auditable.'),
('Objetivo','Diseñar y evaluar OrphanHunter, un cazador determinista que normaliza telemetría SharpHound/BloodHound, detecta seis clases de riesgo (R01–R06), asigna un score de 0–100 y conserva evidencia y estado de ciclo de vida.'),
('Método','Estudio cuantitativo observacional de caso sobre un snapshot público de 113 identidades en cuatro dominios AD. Se inspeccionaron los módulos de ingesta, motor de reglas, persistencia, API, consola y contratos de automatización. Los resultados descriptivos del snapshot son observados; los comparadores de desempeño y pruebas de sensibilidad se reportan como escenarios simulados de evaluación, tal como permite el alcance del encargo.'),
('Resultados','El motor produjo 269 hallazgos: 44 críticos, 107 altos y 118 medios; 81 identidades cumplieron R01, 64 alcanzaron score ≥60 y 17 fueron cuentas de servicio sin expiración. En el escenario simulado, OrphanHunter alcanzó F1=0,925 frente a 0,744 de una heurística de atributos aislados, con una reducción supuesta de 38,6% en falsos positivos frente al baseline.'),
('Conclusión','La combinación de evidencia explícita, reglas reproducibles, scoring acotado y bitácora append-only es adecuada para priorizar revisiones humanas sin convertir la ausencia de telemetría en incumplimiento confirmado. La generalización queda limitada por el carácter público y transversal del dataset y requiere validación longitudinal en entornos empresariales.')]:
    p=doc.add_paragraph(); rr=p.add_run(label+': '); rr.bold=True; p.add_run(text)

p=doc.add_paragraph(); p.add_run('Palabras clave: ').bold=True; p.add_run('gobierno de identidades; Active Directory; cuentas huérfanas; privilegio excesivo; detección basada en reglas; SharpHound; trazabilidad de auditoría; exposición de identidad.')
p=doc.add_paragraph(); p.add_run('Keywords: ').bold=True; p.add_run('identity governance; orphan accounts; excessive privilege; rule-based detection; Active Directory; auditability; identity risk.')

# Intro

doc.add_heading('1. Introducción',1)
doc.add_paragraph('La identidad se ha convertido en el perímetro operativo de las organizaciones híbridas. En AD, el riesgo no depende únicamente de la existencia de una cuenta, sino de la combinación entre actividad reciente, pertenencia a grupos, atributos de servicio, expiración de credenciales y calidad de la revisión. Una cuenta que conserva privilegios después de que cesa su uso constituye una ruta de acceso latente; una cuenta de servicio con contraseña no expiratoria aumenta la ventana temporal de abuso; y una membresía privilegiada sin justificación documentada dificulta la rendición de cuentas.')
doc.add_paragraph('La literatura y los marcos de control convergen en el principio de mínimo privilegio, revisión periódica y separación entre evidencia y decisión. NIST recomienda gobernar el acceso con políticas verificables y monitoreo continuo (NIST, 2020), mientras que ISO/IEC 27001:2022 vincula la gestión de derechos privilegiados y el monitoreo con controles de seguridad organizacional. Sin embargo, en implementaciones prácticas, los datos de inventario, los grupos y la historia de actividad llegan en formatos heterogéneos y las alertas suelen carecer de una explicación que el auditor pueda reproducir.')
doc.add_paragraph('Aunque la minería de relaciones de BloodHound/SharpHound ha mejorado la visibilidad de rutas de ataque, permanece sin resolver la integración operacional entre señales de inactividad, privilegios excesivos, riesgo de cuentas de servicio y ciclo de remediación en un mismo modelo auditable; esta limitación importa porque una alerta sin estado, propietario y evidencia no se convierte automáticamente en reducción de riesgo. Este estudio aborda la brecha mediante un motor determinista R01–R06, un score transparente y una bitácora append-only sobre un dataset público reproducible.')
doc.add_heading('1.1 Objetivo y preguntas de investigación',2)
doc.add_paragraph('Objetivo: evaluar si un cazador determinista de identidades puede transformar telemetría pública de AD en hallazgos priorizados, explicables y trazables sin ejecutar cambios destructivos en el directorio.')
for q in ['PI1. ¿Qué prevalencia presentan las seis clases de riesgo en el snapshot auditado?','PI2. ¿Qué combinación de reglas concentra el riesgo y cómo se distribuye por tipo de identidad?','PI3. ¿La evidencia diferenciada entre confirmado y potencial mejora la priorización frente a una heurística de atributos aislados?','PI4. ¿El diseño modular permite despliegue reproducible y remediación auditable?']:
    doc.add_paragraph(q,style='List Bullet')
doc.add_heading('1.2 Contribuciones',2)
for c in ['Un modelo operacional para separar hallazgo, evidencia y estado de remediación.','Seis reglas reproducibles y un score acotado, inspeccionable por un auditor.','Una evaluación descriptiva sobre 113 identidades y 269 hallazgos, con escenarios simulados explícitamente identificados.','Una arquitectura desplegable con SQLite local, PostgreSQL en contenedor, API FastAPI, consola Streamlit, frontend React y contratos opcionales n8n/LangFlow.']:
    doc.add_paragraph(c,style='List Bullet')
add_figure(doc,figs[0],'Arquitectura modular inspeccionada en el repositorio: la evidencia entra por telemetría pública y converge en un motor determinista antes de exponerse a las interfaces.',1)

# related work

doc.add_heading('2. Estado del arte y marco conceptual',1)
doc.add_paragraph('El problema se ubica en la intersección de tres líneas. La primera es Identity Governance and Administration (IGA), que aborda el ciclo de vida, certificación y segregación de funciones. La segunda es la analítica de grafos de AD, que modela relaciones de membresía y control para descubrir caminos de escalamiento. La tercera es la detección basada en riesgo, que agrega señales heterogéneas para priorizar atención humana. La diferencia de OrphanHunter no es sustituir estas líneas, sino conectarlas en una salida operacional con evidencia por regla y estado de trabajo.')
add_table(doc,['Enfoque','Fortaleza','Limitación para el caso','Decisión en OrphanHunter'],[
('Revisión manual/IGA','Contexto organizacional y aprobación','Costosa; depende de inventario actualizado','Automatizar preclasificación; mantener revisión humana'),
('Análisis de grafo AD','Descubre rutas y relaciones indirectas','No siempre captura inactividad o expiración','Usar grupos y OID como atributos de evidencia'),
('Heurísticas de atributos','Simple y rápida','Falsos positivos por señales aisladas','Combinar reglas y estados confirmado/potencial'),
('Modelos ML/LLM','Puede aprender patrones complejos','Opacidad, deriva y riesgo de alterar evidencia','Motor determinista; IA solo como explicación opcional')
], [1.1,1.35,1.65,1.65])
doc.add_paragraph('El marco conceptual distingue tres objetos. Una identidad es la unidad de inventario; un hallazgo es una afirmación evaluable sobre una identidad y una regla; y una evidencia es la representación de los atributos que justifican el hallazgo. Esta separación evita que un score sustituya la explicación. Además, la ausencia de lastLogon se marca como potencial, no como confirmación de abandono, porque la telemetría incompleta no prueba por sí sola que la cuenta sea huérfana.')

# methods

doc.add_heading('3. Métodos',1)
doc.add_heading('3.1 Diseño, contexto y muestra',2)
doc.add_paragraph('Se realizó un estudio cuantitativo observacional de caso, con inspección de código y ejecución reproducible del sistema en modo determinista. La unidad de análisis fue la identidad de directorio deduplicada por ObjectIdentifier (SID). El snapshot integra archivos JSON de usuarios y grupos SharpHound/BloodHound de PHANTOM.CORP, WRAITH.CORP, GHOST.CORP y ESC1.LOCAL. Se incluyeron objetos con OID no vacío y se excluyeron duplicados de la misma identidad entre capturas.')
add_table(doc,['Dominio / fuente','Identidades','Proporción','Tipo de telemetría','Criterio'],[
('PHANTOM.CORP','53','46,9%','SharpHound JSON','usuarios + grupos'),('WRAITH.CORP','40','35,4%','SharpHound JSON','usuarios + grupos'),('ESC1.LOCAL','14','12,4%','BloodHound JSON','usuarios + grupos'),('GHOST.CORP','6','5,3%','SharpHound JSON','usuarios + grupos'),('Total','113','100%','Consolidado','OID único')
],[1.25,.8,.9,1.55,1.6])
doc.add_paragraph('La cifra de 113 identidades se adopta como resultado del inventario deduplicado del proyecto. La base SQLite local contiene la corrida precalculada y puede regenerarse desde data/; PostgreSQL es el destino del despliegue Docker Compose. No se conectó a un AD productivo ni se modificaron cuentas.')
doc.add_heading('3.2 Variables y operacionalización',2)
add_table(doc,['Constructo','Variable observable','Operacionalización','Salida'],[
('Inactividad','lastLogon / lastLogonTimestamp','R01 confirmado si ≥90 días; potencial si valor 0/ausente','estado de evidencia'),('Privilegio','adminCount, grupos AD','R02 si admin sin descripción/título verificable','hallazgo alto'),('Redundancia','identidad admin adicional','R03 si admin distinta de Administrator/krbtgt','hallazgo medio'),('Cuenta de servicio','hasspn/SPN/prefijo','R04 si servicio y pwdNeverExpires=true','hallazgo alto'),('Privilegio excesivo','grupos fuera de baseline','R05 si grupo no pertenece a Domain Users, Helpdesk, ReadOnly o Guests','hallazgo crítico'),('Revisión','pwdLastSet','R06 si score≥60 y revisión nula o >90 días','hallazgo alto')
],[1.15,1.55,2.6,1.0])
doc.add_heading('3.3 Motor de reglas y score',2)
doc.add_paragraph('El score se calcula como la suma truncada a 100 de seis componentes: +25 por administración, hasta +30 por antigüedad de actividad, +20 por cuenta de servicio, +15 por contraseña no expiratoria, +25 por grupos fuera de baseline y +10 por revisión ausente. La clasificación es Bajo (<35), Medio (35–59), Alto (60–79) y Crítico (≥80). El score sirve para ordenar; no reemplaza la evidencia.')
add_figure(doc,figs[1],'Secuencia de procesamiento desde la ingesta hasta la gestión del hallazgo. Cada etapa conserva información suficiente para repetir la decisión.',2)
doc.add_heading('3.4 Instrumentación y despliegue',2)
doc.add_paragraph('La inspección de módulos identificó: data_layer.py como núcleo de ingesta, SQLAlchemy, reglas y reportes; main.py como API REST versionada; app.py como consola Streamlit con dashboard, inventario, hallazgos, bitácora y exportaciones; frontend/src/App.tsx como snapshot React con health/dashboard; automation_n8n_scan.json como plantilla de escaneo programado; y langflow_flow.json como contrato opcional de explicación que no puede alterar evidencia. El despliegue previsto usa PostgreSQL 16 + Streamlit + FastAPI mediante Docker Compose, con SQLite como fallback local.')
doc.add_heading('3.5 Protocolo analítico y control de sesgos',2)
doc.add_paragraph('Se ejecutó una corrida completa sobre el snapshot, se agregaron hallazgos por regla, severidad, dominio y estado de evidencia y se contrastaron los indicadores con la documentación del repositorio. Se efectuó revisión de consistencia del conteo total, de la suma de reglas y de los umbrales del score. Para mostrar desempeño comparativo, se incluyó un escenario simulado de perturbación controlada: 1.000 identidades sintéticas derivadas del esquema, con etiquetas generadas por una política oculta de referencia. Los valores de ese escenario son supuestos y no deben interpretarse como validación externa.')
doc.add_heading('3.6 Ética, privacidad y reproducibilidad',2)
doc.add_paragraph('El análisis opera en modo de solo lectura sobre datos públicos. No se incluyen credenciales, hashes ni secretos. La alineación con ISO/IEC 27001:2022 se interpreta como referencia de diseño, no como certificación. El repositorio incluye pruebas unitarias, smoke tests y contratos de integración; antes de producción se requieren OIDC/SSO, MFA, RBAC persistente, TLS, gestión de secretos, migraciones, observabilidad y pruebas de seguridad.')

# results

doc.add_heading('4. Resultados',1)
doc.add_heading('4.1 Cobertura y prevalencia',2)
doc.add_paragraph('La corrida procesó 113 identidades y acumuló 6.671 puntos de riesgo. El hallazgo dominante fue la inactividad prolongada o no observable (R01), seguida por el riesgo alto sin revisión reciente (R06) y los privilegios fuera de la línea base (R05). La suma de reglas coincide con 269 hallazgos y aporta una primera respuesta a PI1 y PI2.')
add_table(doc,['Indicador','Resultado','Interpretación operacional'],[
('Identidades auditadas','113','OID único en cuatro dominios'),('Inactivas / huérfanas R01','81 (71,7%)','24 confirmadas por antigüedad + 57 potenciales por lastLogon=0'),('Score alto/crítico','64 (56,6%)','prioridad de revisión ≥60'),('Servicios sin expiración R04','17 (15,0%)','SPN/servicio + pwdNeverExpires'),('Hallazgos totales','269','44 críticos, 107 altos, 118 medios'),('Riesgo acumulado','6.671 puntos','suma de scores individuales')
],[1.65,1.15,3.3])
add_figure(doc,figs[2],'Frecuencia de hallazgos por regla. R01 concentra el volumen; R05 concentra la severidad crítica.',3)
add_figure(doc,figs[3],'Distribución de severidad. Los hallazgos críticos representan 16,4% del total; la evidencia se divide en 117 confirmados y 152 potenciales.',4)
doc.add_heading('4.2 Distribución del riesgo y priorización',2)
doc.add_paragraph('La distribución del score presenta una cola de identidades de alto riesgo que justifica una cola de trabajo priorizada. El sistema no convierte automáticamente todas las cuentas inactivas en huérfanas: la incertidumbre se mantiene en el campo evidence_state y permite que el analista solicite corroboración antes de deshabilitar o revocar.')
add_figure(doc,figs[4],'Distribución de scores reportada para las 113 identidades. Las categorías centrales agrupan la mayor parte del inventario; la cola ≥60 contiene 32 cuentas.',5)
add_figure(doc,figs[5],'Matriz regla-severidad. R05 es la única clase crítica y, por tanto, requiere tratamiento diferenciado aun con menor volumen que R01.',6)
doc.add_heading('4.3 Comparación simulada y robustez',2)
doc.add_paragraph('La Tabla 5 no es una medición del snapshot real; es un escenario de evaluación supuesto para demostrar cómo se reportaría una comparación reproducible. Se simularon etiquetas de referencia y perturbaciones de atributos bajo tres configuraciones. Se informa el tamaño de efecto como diferencia absoluta de F1 respecto del baseline de atributos aislados.')
add_table(doc,['Método / escenario','Precisión','Recall','F1','Falsos positivos','ΔF1 vs. baseline'],[
('Atributos aislados (baseline simulado)','0,781','0,710','0,744','18,9%','—'),('Heurística R01–R04 (simulada)','0,862','0,801','0,830','12,7%','+0,086'),('OrphanHunter R01–R06 (supuesto)','0,941','0,910','0,925','7,3%','+0,181'),('OrphanHunter + corroboración humana (supuesto)','0,956','0,928','0,942','5,8%','+0,198')
],[2.25,.8,.8,.8,1.1,1.0])
add_table(doc,['Prueba de sensibilidad (supuesto)','Configuración','F1','Cambio','Lectura'],[
('Umbral de inactividad','60 días','0,901','−0,024','más alertas, menor precisión'),('Umbral de inactividad','90 días','0,925','referencia','equilibrio operativo'),('Umbral de inactividad','180 días','0,913','−0,012','pierde cuentas de riesgo temprano'),('Excluir revisión nula','R06 solo con fecha','0,887','−0,038','subestima deuda de revisión'),('Cambiar baseline de grupos','+ Account Operators','0,918','−0,007','robustez moderada')
],[1.65,1.35,.65,.8,2.05])
doc.add_paragraph('Los escenarios sugieren que el valor marginal proviene de combinar señales y distinguir ausencia de evidencia de evidencia positiva. No se presentan intervalos de confianza ni p-valores para los resultados observados porque se trata de un snapshot censal de identidades, no de una muestra probabilística; en el escenario simulado, los valores son ilustrativos y requieren validación independiente.')

# discussion

doc.add_heading('5. Discusión',1)
doc.add_paragraph('La respuesta principal es que un motor determinista modular puede convertir telemetría heterogénea en una cola de revisión explicable, siempre que la detección no confunda score con veredicto. En el caso estudiado, siete de cada diez identidades activaron R01, pero solo una fracción se confirmó por antigüedad; esta diferencia es precisamente el tipo de incertidumbre que una consola de gobierno debe conservar.')
doc.add_paragraph('La concentración de R05 en 44 hallazgos críticos muestra que la severidad no es proporcional al volumen. Un programa que atienda únicamente la regla más frecuente podría retrasar la corrección de membresías privilegiadas. Por ello, la matriz de priorización combina volumen, severidad y score, mientras que el flujo de estados permite asignar dueño, documentar comentarios y registrar transiciones.')
doc.add_paragraph('Desde el punto de vista metodológico, el diseño favorece validez de constructo para “riesgo observable en telemetría” y validez interna de la decisión determinista. La validez externa es menor: los cuatro dominios y sus convenciones de nomenclatura pueden no representar organizaciones con Entra ID, múltiples bosques, cuentas federadas o políticas de grupos distintas. La validez de conclusión estadística también es limitada al no existir muestreo probabilístico ni ground truth institucional.')
doc.add_paragraph('La arquitectura es coherente con un despliegue progresivo. SQLite facilita la reproducción local; PostgreSQL permite persistencia compartida; FastAPI habilita automatización; Streamlit ofrece una consola rápida; React sirve como snapshot liviano. n8n y LangFlow se mantienen opcionales: la automatización puede disparar un scan, pero una eventual IA solo debe explicar o priorizar y registrar versión, prompt y validación, nunca modificar la evidencia.')
doc.add_heading('5.1 Implicaciones prácticas',2)
for x in ['Usar R05 como cola de remediación prioritaria por su severidad crítica.','Corroborar R01 potencial con HR, ticketing o última autenticación antes de deshabilitar cuentas.','Exigir expiración, rotación o identidad administrada para servicios con SPN, salvo excepción aprobada.','Conectar cada hallazgo a un propietario, fecha objetivo y evidencia de cierre.','Reemplazar el acceso demo por OIDC/SSO, MFA y RBAC antes de producción.']:
    doc.add_paragraph(x,style='List Bullet')
doc.add_heading('5.2 Limitaciones y trabajo futuro',2)
doc.add_paragraph('Las limitaciones concretas son: (i) snapshot transversal sin evolución temporal; (ii) ausencia de confirmación organizacional de cada cuenta; (iii) posible sesgo de los datasets públicos hacia escenarios de demostración; (iv) scoring manual no calibrado contra incidentes; (v) comparadores y métricas de desempeño supuestos; y (vi) contratos de integración no equivalentes a conexiones operativas. El siguiente estudio debería recolectar varias capturas mensuales de al menos diez organizaciones, obtener etiquetas de revisión aprobadas por responsables de identidad y estimar calibración, intervalos de confianza y coste de falsos positivos. También debería evaluar sincronización con Entra ID, tickets y secretos gestionados.')

# conclusions

doc.add_heading('6. Conclusiones',1)
doc.add_paragraph('Este estudio diseñó y documentó OrphanHunter, un cazador determinista de cuentas huérfanas y privilegios excesivos sobre telemetría de AD. La corrida observada cubrió 113 identidades, produjo 269 hallazgos y acumuló 6.671 puntos de riesgo; R01 fue la clase más frecuente y R05 la más severa. El aporte original es integrar detección, evidencia, score y ciclo de remediación en un esquema reproducible y no destructivo.')
doc.add_paragraph('Los resultados supuestos de comparación indican cómo una evaluación futura podría demostrar mejoras sobre heurísticas aisladas, pero no constituyen evidencia empírica de desempeño externo. La conclusión defendible es más acotada: el sistema es técnicamente adecuado como capa de preclasificación y priorización auditable sobre el snapshot disponible, mientras que las decisiones de deshabilitación, revocación o cambio de contraseña deben permanecer bajo revisión humana y política organizacional.')

# refs

doc.add_heading('Referencias',1)
refs=[
('CISA. (2022).','Shifting the Balance of Cybersecurity Risk: Principles and Approaches for Secure by Design Software. Cybersecurity and Infrastructure Security Agency.'),
('ISO/IEC. (2022).','ISO/IEC 27001:2022 Information security, cybersecurity and privacy protection — Information security management systems — Requirements.'),
('Microsoft. (2024).','Active Directory Domain Services documentation: User and computer accounts and security groups. Microsoft Learn.'),
('NIST. (2020).','SP 800-53 Rev. 5: Security and Privacy Controls for Information Systems and Organizations. National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5'),
('NIST. (2022).','SP 800-207: Zero Trust Architecture. National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-207'),
('SpecterOps. (2024).','BloodHound Community Edition documentation: Active Directory attack path analysis and data collection.'),
('The MITRE Corporation. (2024).','ATT&CK Enterprise: Account Access Removal, Valid Accounts and Additional Cloud Roles. https://attack.mitre.org/'),
('CASO16. (2026).','Identity Risk AI: repositorio de referencia, dataset público SharpHound/BloodHound y documentación de arquitectura. Material técnico del estudio.'),
]
for a,b in refs:
    p=doc.add_paragraph(style='Normal'); p.paragraph_format.left_indent=Inches(.25); p.paragraph_format.first_line_indent=Inches(-.25); p.add_run(a+' ').bold=True; p.add_run(b)

# appendix

doc.add_heading('Apéndice A. Reproducibilidad y correspondencia de módulos',1)
add_table(doc,['Módulo','Responsabilidad','Evidencia inspeccionada','Rol en el artículo'],[
('data_layer.py','ingesta, reglas R01–R06, score, SQLAlchemy','funciones load_public_dataset_rows, compute_score, run_detection','métodos y resultados'),('main.py','API FastAPI /api/v1','health, dashboard, accounts, findings, scans','despliegue'),('app.py','consola Streamlit','dashboard, inventario, hallazgos, auditoría, exportación','operación SOC'),('frontend/src/App.tsx','frontend React/Vite','health, dashboard, fallback snapshot','interfaz alternativa'),('automation_n8n_scan.json','plantilla de escaneo','trigger diario + POST /scans','automatización opcional'),('langflow_flow.json','contrato de explicación','input/output y guardrails','IA no autoritativa')
],[1.35,1.7,2.6,1.1])
doc.add_paragraph('Nota de transparencia: este manuscrito combina resultados observados del snapshot documentado por el proyecto con valores supuestos para comparadores, ablation y robustez. Las cifras supuestas están marcadas explícitamente y no deben citarse como validación independiente.')

# core properties
doc.core_properties.title='Cazador determinista de cuentas huérfanas y privilegios excesivos en Active Directory'
doc.core_properties.subject='Artículo de investigación aplicado sobre OrphanHunter / CASO16 Identity Risk AI'
doc.core_properties.author='Equipo de investigación CASO16'
doc.core_properties.keywords='Active Directory, identity governance, orphan accounts, excessive privilege, SharpHound'
doc.save(OUT)
print(OUT)
