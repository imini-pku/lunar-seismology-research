from pathlib import Path
from docx import Document
from PIL import Image,ImageOps,ImageDraw
import json
ROOT=Path(r'C:\Users\Administrator\Desktop\起伏月表影响数值模拟\投稿文件')
OUT=ROOT/'完整中文稿_2026-09-12'
OUT.mkdir(exist_ok=True)
A=OUT/'核查素材'; A.mkdir(exist_ok=True)
d=Document(ROOT/'Results审校_2026-09-09'/'Results部分_v1.docx')
texts=[p.text for p in d.paragraphs if p.text.strip()]
imgs=[]
for n,s in enumerate(d.inline_shapes,1):
 rid=s._inline.graphic.graphicData.pic.blipFill.blip.embed
 part=d.part.related_parts[rid]
 p=A/f'figure{n}{Path(part.partname).suffix}';p.write_bytes(part.blob);imgs.append(str(p))
(A/'results_source.json').write_text(json.dumps({'text':texts,'images':imgs},ensure_ascii=False,indent=2),encoding='utf-8')
sheet=Image.new('RGB',(1200,((len(imgs)+1)//2)*460),'white');dr=ImageDraw.Draw(sheet)
for i,p in enumerate(imgs):
 im=Image.open(p).convert('RGB');im.thumbnail((590,425));x=(i%2)*600;y=(i//2)*460
 sheet.paste(im,(x,y+25));dr.text((x,y),f'Figure {i+1}',fill='black')
sheet.save(A/'figures_overview.jpg')
print('\n'.join(texts))
