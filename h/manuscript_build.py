from pathlib import Path
import json,re,shutil
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image
ROOT=Path(r'C:\Users\Administrator\Desktop\起伏月表影响数值模拟\投稿文件\完整中文稿_2026-09-12')
A=ROOT/'核查素材'
src=json.loads((A/'results_source.json').read_text(encoding='utf-8'))
rs=[];caps=[]
for t in src['text']:
 if re.match(r'^图[1-8] ',t):caps.append(t.replace('**',''));continue
 if t=='3 Results':t='## 3 结果'
 elif re.match(r'^3\.\d ',t):t='### '+t
 if t.startswith('地形响应还具有路径依赖性。'):
  t='在低速且含随机非均匀性的背景中，地形的附加响应具有路径依赖性（图7d）。控制距离趋势后，路径2的累计路径高差范围与M6/M5峰值和能量响应呈较明显负相关，与T90响应呈正相关；路径1和3的相应关系较弱。57个空间块汇总中，峰值和能量仍表现为负向关联，而T90的关联较弱。因此，当前结果主要支持路径2上较明确的地形关联，不支持各传播方向均遵循同一关系。'
 if t.startswith('M6的上升时间随震中距总体增加'):
  t='M6从震源时刻起算的上升时间tmax随震中距总体增加（图7e–g）。采用20 s平滑三分量解析能量包络峰值到时、并对同一组保留台站比较两种距离形式后，三条路径的ΔAIC均为正，线性距离形式均优于平方距离形式。不同路径仍具有不同的峰时分布和离散程度，但并未出现某一路径优先支持平方距离形式的结果。该比较限定于图示频带、记录长度及筛选范围，不把经验拟合直接等同于完整的能量输运机制。'
 rs.append(t)
caps[0]=caps[0].replace('，测线1则代表不同的传播方位并终止于S12','，测线1代表另一传播方位；S12为独立观测对照点')
caps[5]=caps[5].replace('R/T/X','R/T/Z')
caps[6]=caps[6].replace('d沿用归档配对指标，显示累计路径高差范围与M2/M1响应的距离控制相关，路径统计与57块汇总是不同聚合层级。','d使用0–400 s的M6/M5配对响应，对累计路径高差范围及指标对数比值分别去除路径内三次距离趋势，显示标准化残差的Spearman相关；路径为逐站统计，57块汇总为块中位数统计，两者属于不同聚合层级。')
text=(ROOT/'正文新增章节.md').read_text(encoding='utf-8').replace('RESULTS_PLACEHOLDER','\n\n'.join(rs)).replace('Onodera（2022）','Onodera等（2022）')
metadata=json.loads((A/'references_metadata.json').read_text(encoding='utf-8'))
refs=[]
for m in metadata:
 if 'error' in m:continue
 authors=[]
 for a in m.get('author',[]):
  init=' '.join(x[0]+'.' for x in re.split(r'[\s-]+',a.get('given','')) if x)
  authors.append(a.get('family','')+', '+init)
 au=', '.join(authors[:-1])+', & '+authors[-1] if len(authors)>1 else authors[0]
 year=m.get('published',m.get('issued'))['date-parts'][0][0]
 journal=m.get('container-title',[''])[0];vol=m.get('volume','');issue=m.get('issue','');page=m.get('page',m.get('article-number',''))
 if m['DOI'].lower()=='10.1029/2011je004042':page='E06003'
 if m['DOI'].lower()=='10.1214/aos/1176344552':page='1–26'
 refs.append(f"{au} ({year}). {m['title'][0]}. {journal}, {vol}"+(f'({issue})' if issue else '')+(f', {page}' if page else '')+f". https://doi.org/{m['DOI']}")
refs += [
'Barker, M. K., Mazarico, E., Neumann, G. A., Zuber, M. T., Haruyama, J., & Smith, D. E. (2016). A new lunar digital elevation model from the Lunar Orbiter Laser Altimeter and SELENE Terrain Camera. Icarus, 273, 346–355. https://doi.org/10.1016/j.icarus.2015.07.039',
'Nunn, C., Fernando, B. A., & Panning, M. P. (2024). Artificial Impacts on the Moon: Modeling 3D Seismic Propagation Effects with AxiSEM3D. The Planetary Science Journal, 5(11), 246. https://doi.org/10.3847/PSJ/ad83d2',
'Trifunac, M. D., & Brady, A. G. (1975). A study on the duration of strong earthquake ground motion. Bulletin of the Seismological Society of America, 65(3), 581–626. https://doi.org/10.1785/BSSA0650030581']
refs.sort(key=str.casefold)
text+='\n\n## 参考文献\n\n'+'\n\n'.join(refs)+'\n\n## 图件与图注\n\n'+'\n\n'.join(caps)
(ROOT/'完整中文稿_v1.md').write_text(text.replace('TABLE_MODELS','表1 A16/S12区域模型及配对关系\n\n|模型|表面|随机非均匀性|附加低速层|\n|---|---|---|---|\n|M1|平坦|无|无|\n|M2|真实地形|无|无|\n|M3|平坦|有|无|\n|M4|真实地形|有|无|\n|M5|平坦|有|有|\n|M6|真实地形|有|有|'),encoding='utf-8')
d=Document();sec=d.sections[0]
sec.page_width=Cm(21);sec.page_height=Cm(29.7)
sec.top_margin=Cm(2.2);sec.bottom_margin=Cm(2.2);sec.left_margin=Cm(2.6);sec.right_margin=Cm(2.3)
for name in ['Normal','Title','Heading 1','Heading 2','Caption']:
 st=d.styles[name];st.font.name='Times New Roman';st.font.color.rgb=RGBColor(0,0,0)
 st.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'宋体')
 st.font.size=Pt(11)
 st.paragraph_format.line_spacing=1.5
 st.paragraph_format.space_after=Pt(6)
 st.paragraph_format.widow_control=True
d.styles['Title'].font.size=Pt(19);d.styles['Title'].font.bold=True
d.styles['Heading 1'].font.size=Pt(14);d.styles['Heading 2'].font.size=Pt(12)
d.styles['Caption'].font.size=Pt(10);d.styles['Caption'].font.italic=False;d.styles['Caption'].paragraph_format.line_spacing=1.15
d.styles['Caption'].font.bold=False
for border in list(d.styles.element.iter(qn('w:pBdr'))):border.getparent().remove(border)
for name in ['Heading 1','Heading 2']:d.styles[name].paragraph_format.keep_with_next=True
ln=OxmlElement('w:lnNumType');ln.set(qn('w:countBy'),'5');ln.set(qn('w:restart'),'continuous');ln.set(qn('w:distance'),'220');sec._sectPr.append(ln)
footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
def table():
 d.add_paragraph('表1 A16/S12区域模型及配对关系',style='Caption')
 tb=d.add_table(rows=1, cols=4);tb.style='Table Grid'
 for c,t in zip(tb.rows[0].cells,['模型','表面','随机非均匀性','附加低速层']):c.text=t
 for row in [('M1','平坦','无','无'),('M2','真实地形','无','无'),('M3','平坦','有','无'),('M4','真实地形','有','无'),('M5','平坦','有','有'),('M6','真实地形','有','有')]:
  for c,t in zip(tb.add_row().cells,row):c.text=t
 for row in tb.rows:
  trpr=row._tr.get_or_add_trPr();trpr.append(OxmlElement('w:cantSplit'))
  for c in row.cells:
   for p in c.paragraphs:p.paragraph_format.space_after=Pt(2);p.paragraph_format.line_spacing=1.1
 tb.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
 d.add_paragraph('注：模型编号仅用于本文。M5/M3和M6/M4比较低速结构的附加响应；M6/M5比较低速非均匀背景上的地形响应。',style='Caption')
body=text.split('\n\n## 图件与图注')[0]
for block in body.split('\n\n'):
 block=block.strip()
 if not block:continue
 if block=='TABLE_MODELS':table();continue
 if block.startswith('### '):d.add_paragraph(block[4:],style='Heading 2')
 elif block.startswith('## '):d.add_paragraph(block[3:],style='Heading 1')
 elif block.startswith('# '):d.add_paragraph(block[2:],style='Title')
 elif block.startswith('EQ '):
  p=d.add_paragraph();p.paragraph_format.line_spacing=1.15
  om=OxmlElement('m:oMath')
  def mr(txt):
   r=OxmlElement('m:r');t=OxmlElement('m:t');t.text=txt;t.set(qn('xml:space'),'preserve');r.append(t);return r
  value=block[3:].replace('max₀≤s≤R h(s) − min₀≤s≤R h(s)','max{h(s): 0≤s≤R} − min{h(s): 0≤s≤R}').replace('AIC_R²','AIC_{R²}');cursor=0
  for match in re.finditer(r'([A-Za-zΣ]+)_(\{[^}]+\}|[A-Za-z]+|0\.\d+)',value):
   if match.start()>cursor:om.append(mr(value[cursor:match.start()]))
   ss=OxmlElement('m:sSub');e=OxmlElement('m:e');e.append(mr(match[1]));sub=OxmlElement('m:sub');sub.append(mr(match[2].strip('{}')));ss.append(e);ss.append(sub);om.append(ss);cursor=match.end()
  om.append(mr(value[cursor:]));p._p.append(om)
 else:
  for old,new in [('t_max','tmax'),('f_j','fj'),('t_p','tp'),('E_ref','Eref'),('Q_M6','Q(M6)'),('Q_M5','Q(M5)')]:block=block.replace(old,new)
  p=d.add_paragraph(block)
  if re.match(r'^[A-Za-z].*https://doi.org/',block):
   p.paragraph_format.first_line_indent=Cm(-.6);p.paragraph_format.left_indent=Cm(.6);p.paragraph_format.line_spacing=1.15
for i,path in enumerate(src['images']):
 d.add_page_break()
 if i==0:d.add_paragraph('图件与图注',style='Heading 1')
 im=Image.open(path);w,h=im.size
 maxh=18.4 if i==0 else 19.1
 width=min(16.1,maxh*w/h)
 p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_after=Pt(4);p.paragraph_format.keep_with_next=True
 run=p.add_run();pic=run.add_picture(path,width=Cm(width));pic._inline.docPr.set('descr',caps[i])
 d.add_paragraph(caps[i],style='Caption')
file=ROOT/'起伏月表与浅层结构_完整中文稿_v1.docx';d.save(file)
for helper in ['manuscript_extract.py','manuscript_reference_fetch.py','manuscript_build.py']:
 shutil.copy2(Path(__file__).parent/helper,A/helper)
print(file);print('paragraphs',len(d.paragraphs),'figures',len(d.inline_shapes),'references',len(refs),'chars',len(text))
