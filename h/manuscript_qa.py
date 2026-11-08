from pathlib import Path
from PIL import Image,ImageDraw
from pypdf import PdfReader
P=Path(r'C:\Users\Administrator\Desktop\起伏月表影响数值模拟\投稿文件\完整中文稿_2026-09-12\核查素材')
r=PdfReader(P/'manuscript.pdf')
for i,p in enumerate(r.pages,1):print(i,len(p.extract_text()),p.extract_text()[:55].replace('\n',' '))
files=sorted(P.glob('page-*.png'))
for b in range(0,len(files),6):
 out=Image.new('RGB',(1200,1700),'#dddddd');dr=ImageDraw.Draw(out)
 for j,p in enumerate(files[b:b+6]):
  im=Image.open(p);im.thumbnail((395,805));x=j%3*400;y=j//3*850;out.paste(im,(x,y+30));dr.text((x,y),p.stem,fill='black')
 out.save(P/f'contact-{b//6+1}.jpg')
