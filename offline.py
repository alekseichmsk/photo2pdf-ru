import re,subprocess,csv,io,statistics
from ipa import trans
def ocr_lines(img):
    t=subprocess.run(['tesseract',img,'-','tsv'],capture_output=True,text=True).stdout
    g={}
    for r in csv.DictReader(io.StringIO(t),delimiter='\t',quoting=csv.QUOTE_NONE):
        if r['level']!='5' or not r['text'].strip(): continue
        k=(r['block_num'],r['par_num'],r['line_num']);g.setdefault(k,[]).append(r)
    return [dict(text=' '.join(w['text'] for w in ws),top=min(int(w['top']) for w in ws),left=int(ws[0]['left']),h=statistics.median(int(w['height']) for w in ws),conf=statistics.mean(float(w['conf']) for w in ws)) for ws in g.values()]
SPK=re.compile(r"^[^A-Za-z]*([A-Z][a-z]+):\s*(.*)$")
def parse(img):
    ls=ocr_lines(img); labels=[];text=[]
    for l in ls:
        m=SPK.match(l['text'])
        if m and not m.group(2): labels.append((l['top'],m.group(1),l['left']))
        else: text.append(l)
    good=[l for l in text if l['conf']>60 and (len(re.findall(r'[A-Za-z]{2,}',l['text']))>=2 or (l['conf']>85 and re.search(r'[A-Za-z]{4,}',l['text'])))]
    if good:  # keep main text column/size
        x=statistics.median(l['left'] for l in good);h=statistics.median(l['h'] for l in good)
        good=[l for l in good if abs(l['left']-x)<h*6 and 0.7*h<l['h']<1.4*h]
    good.sort(key=lambda l:l['top']);labels.sort()
    out=[]
    if labels:
        start={}
        for s in labels:
            c=min(good,key=lambda l:abs(l['top']-s[0]),default=None)
            if c and abs(c['top']-s[0])<c['h']*1.3 and id(c) not in start: start[id(c)]=s[1]
        for l in good:
            if id(l) in start: out.append([start[id(l)],l['text'],0])
            elif out: out[-1][1]+=' '+l['text']
    else:
        para=[];prev=None
        for l in good:
            if prev and l['top']-prev>l['h']*2.2: out.append(['',' '.join(para),0]);para=[]
            para.append(l['text']);prev=l['top']
        if para: out.append(['',' '.join(para),0])
    return [(n,clean(t)) for n,t,_ in out]
def clean(t):
    t=t.replace('’',"'").replace(' | ',' I ').replace('|','I').replace('...','…').replace('…',' … ')
    t=re.sub(r'(\w)\s+…','\\1 …',t); return re.sub(r'\s+',' ',t).strip()
