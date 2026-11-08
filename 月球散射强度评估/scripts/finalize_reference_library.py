from supplement_reference_pdfs import *
import csv

def build():
 records=[]
 for r in ROWS:
  r=fill(r)
  if r['doi']=='10.6038/cjg20150519':r.update(author='Jiang',year=2015,title='Numerical simulation of lunar seismic coda caused by scattering in upper Moon crust',type='journal-article')
  lp=META/(re.sub(r'[^\w.-]','_',r['doi'])+'_download.json')
  d=json.loads(lp.read_text(encoding='utf-8')) if lp.exists() else {}
  for k in ['author','year','title','type']:
   if not d.get(k):d[k]=r.get(k)
  records.append({**r,**d})
 for key in ['lpsc2025-1144','dainty1977','10.1016_j.pepi.2011.06.015']:
  p=META/(key+'_download.json')
  if p.exists():records.append(json.loads(p.read_text(encoding='utf-8')))
 papers=[r for r in records if r.get('type')!='dataset_or_code']
 saved=[r for r in papers if r.get('status')=='saved']
 missing=[r for r in papers if r.get('status')!='saved']
 # Verify every delivered PDF again, including its recorded hash and readable pages.
 for r in saved:
  p=OUT/r['filename'];b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==r['sha256']
  assert validate(b,r)['identity_verified'],p
  r['version']='公开全文（版本未进一步判定）'
  doc=pymupdf.open(p);txt=' '.join(page.get_text() for page in list(doc)[:2]).lower();doc.close()
  if 'manuscript submitted' in txt or 'preprint' in txt:r['version']='作者稿/预印本（以 PDF 首页为准）'
  elif r['doi'].lower() in txt:r['version']='期刊出版排版；仓储版可能附封面'
  if r['doi']=='10.1093/gji/ggaf504':r['version']+='；卷期年2026，在线年2025'
 lines=['# 项目参考文献下载清单','','更新日期：2026-11-03。', '',f'核对项目 docs 中 Markdown/BibTeX 的 DOI 引用，并补入未用 DOI 链接的 Dainty 1977、Onodera 2025 会议摘要及正文提及的 Garcia 2011。共 {len(papers)} 个论文/摘要条目，已取得并核验 {len(saved)} 个 PDF，尚缺 {len(missing)} 个。另有 {sum(r.get("type")=="dataset_or_code" for r in records)} 个数据或代码 DOI，不作为论文 PDF 计数。','','**2026-11-03 补充：核对原项目文献库和当前目录，补入 Kim 2026、Nunn 2024 等全文；其余缺失项见下表。**','','命名：第一作者姓氏 + 年份 + 正式文章题名.pdf。Windows 不允许的冒号等字符改为短横线。所有保存的 PDF 均检查文件头、页面可解析性、首页题名/作者或 DOI，以及 SHA-256。该检查确认文献身份和文件可读，不代表已逐页审读。','','## 已取得全文','','| 作者 年份 | 文章与本地文件 | 页数 | 版本说明 | 来源 |','|---|---|---:|---|---|']
 for r in sorted(saved,key=lambda x:(x['author'],x['year'],x['title'])):
  src=r['source'];src_link=f'[下载源]({src})' if src.startswith('http') else '本机已有全文（原路径见下载记录）'
  lines.append(f"| {r['author']} {r['year']} | [{r['title']}](<{r['filename']}>) | {r['validation']['pages']} | {r['version']} | {src_link} |")
 lines+=['','## 尚未取得全文','','这些条目已有准确引文，但当前公开下载入口遇到访问限制、连接/证书错误、仅提供元数据或未找到可下载全文；详细尝试保存在下载记录。未创建同名假 PDF。','','| 作者 年份 | 题名 | 官方入口 | 当前缺失情况 |','|---|---|---|---|']
 for r in sorted(missing,key=lambda x:(x.get('author') or '',x.get('year') or 0)):
  url='https://doi.org/'+r['doi'] if r['doi'].startswith('10.') else (r.get('attempts') or [{}])[0].get('url','')
  types=[]
  for a in r.get('attempts',[]):
   if a.get('status') in [401,403,429]:types.append('访问受限')
   if a.get('error'):types.append('连接/证书/解析错误')
   if a.get('status')==200:types.append('返回网页或非匹配全文')
  reason='；'.join(dict.fromkeys(types)) or '未取得可核验 PDF'
  lines.append(f"| {r.get('author')} {r.get('year')} | {' '.join(r.get('title','待核对').split())} | [入口]({url}) | {reason} |")
 lines+=['','## 数据与代码（非论文）','','以下只保留 DOI 入口，不重复下载大型波形/模拟数据：','']
 for r in records:
  if r.get('type')=='dataset_or_code':lines.append(f"- [{r['doi']}](https://doi.org/{r['doi']})")
 lines+=['','## 可追溯记录','','- `下载记录/文献状态.json`：每篇状态、实际下载来源、文件名、页数、校验值与尝试记录。','- `下载记录/doi_inventory.json`：DOI 在项目中的引用来源。','- `下载记录/all_metadata.json`：Crossref / OpenAlex 返回的作者、题名和公开版本地址。','- 原有 Zhang 2025 长文件名副本当前被其他程序占用，保留原位；新命名副本已建立，内容相同，仅计一次。','- 年份以期刊卷期年为准；Bracale 文件使用2026，并注明2025年在线发表。','- 本清单以当前项目文件可核对的引用为边界，不追溯下载每篇论文自身参考文献中的全部文章。','']
 (OUT/'参考文献下载清单.md').write_text('\n'.join(lines),encoding='utf-8')
 (META/'文献状态.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
 with (OUT/'参考文献下载清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['author','year','title','doi','status','filename','source']);w.writeheader()
  for r in papers:w.writerow({k:r.get(k,'') for k in w.fieldnames})
 print(json.dumps({'papers':len(papers),'saved':len(saved),'missing':len(missing),'dataset_code':sum(r.get('type')=='dataset_or_code' for r in records)},ensure_ascii=False))

if __name__=='__main__':build()
