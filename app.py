# Фото/текст -> PDF: английский текст, русская транскрипция над словами, перевод под строкой. Полностью офлайн.
import os,re,time,hmac,hashlib,secrets,subprocess,tempfile,html,email,random,threading,collections
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import ipa
SECRET=os.environ.get("APP_SECRET","").encode() or secrets.token_bytes(32)
MIN_FILL=float(os.environ.get("MIN_FILL",3)); MAX_TOKEN_AGE=3600
RATE_N=int(os.environ.get("RATE_N",10)); RATE_WIN=600
MAX_UPLOAD=10*1024*1024; MAX_TEXT=5000
_hits=collections.defaultdict(collections.deque); _caps={}; _lock=threading.Lock()

def make_token(t=None):
    t=str(int(t if t is not None else time.time()))
    return t+"."+hmac.new(SECRET,t.encode(),hashlib.sha256).hexdigest()
def check_token(tok,now=None):
    now=now or time.time()
    try: t,sig=tok.split(".",1)
    except (ValueError,AttributeError): return "Неверная форма, обновите страницу"
    if not hmac.compare_digest(sig,hmac.new(SECRET,t.encode(),hashlib.sha256).hexdigest()): return "Неверная форма, обновите страницу"
    age=now-int(t)
    if age<MIN_FILL: return "Слишком быстро. Подождите пару секунд и отправьте снова"
    if age>MAX_TOKEN_AGE: return "Форма устарела, обновите страницу"
    return None
def rate_hit(ip,now=None):
    now=now or time.time()
    with _lock:
        q=_hits[ip]
        while q and now-q[0]>RATE_WIN: q.popleft()
        q.append(now); return len(q)>RATE_N
def new_captcha():
    a,b=random.randint(2,9),random.randint(2,9); cid=secrets.token_hex(8); _caps[cid]=a+b; return cid,f"{a} + {b}"
def image_kind(b):
    if b[:3]==b"\xff\xd8\xff": return "jpg"
    if b[:8]==b"\x89PNG\r\n\x1a\n": return "png"
    if b[:4]==b"RIFF" and b[8:12]==b"WEBP": return "webp"
    if b[:4] in (b"II*\x00",b"MM\x00*"): return "tif"
    if b[:2]==b"BM": return "bmp"
    return None
def split_sentences(text):
    return [x.strip() for x in re.split(r'(?<=[.!?])\s+',' '.join(text.split())) if x.strip()]

CSS="""*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#f4f6fb;color:#1f2430}
.c{max-width:640px;margin:32px auto;padding:28px;background:#fff;border-radius:16px;box-shadow:0 4px 24px rgba(30,40,80,.08)}
h1{font-size:22px;margin:0 0 6px}p.s{color:#667;margin:0 0 22px;font-size:14px}h2{font-size:16px;margin:22px 0 10px}
textarea,input[type=file],input[type=text]{width:100%;padding:12px;border:1px solid #d7dce8;border-radius:10px;font:inherit;background:#fafbfe}
textarea{min-height:180px;resize:vertical}button{margin-top:12px;width:100%;padding:13px;border:0;border-radius:10px;background:#4a6cf7;color:#fff;font-size:16px;cursor:pointer}
button:hover{background:#3b5be0}.hp{position:absolute;left:-9999px}.n{font-size:12px;color:#889;margin-top:6px}.or{text-align:center;color:#aab;margin:20px 0 0}
.e{background:#fff1f1;color:#a33;padding:10px 12px;border-radius:10px;margin-bottom:12px}@media(max-width:680px){.c{margin:0;border-radius:0;padding:20px}}"""
def page(err="",cap=None):
    tok=make_token(); hp='<div class=hp aria-hidden=true><label>Не заполняйте<input type=text name=website tabindex=-1 autocomplete=off></label></div>'
    c=""
    if cap: c=f'<label class=n>Проверка: сколько будет {cap[1]}?</label><input type=text name=captcha inputmode=numeric required><input type=hidden name=cid value={cap[0]}>'
    hid=f'<input type=hidden name=token value="{tok}">'+hp+c
    e=f'<div class=e>{html.escape(err)}</div>' if err else ""
    return f'''<!doctype html><html lang=ru><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Текст → PDF с транскрипцией</title><style>{CSS}</style>
<body><div class=c><h1>Английский текст → PDF</h1><p class=s>Над каждым словом — транскрипция русскими буквами, под строкой — перевод. Работает без интернета.</p>{e}
<h2>Вставьте текст</h2><form method=post enctype=multipart/form-data action=/text><textarea name=text maxlength={MAX_TEXT} required placeholder="Paste English text here..."></textarea><div class=n>До {MAX_TEXT} символов</div>{hid}<button>Сделать PDF</button></form>
<p class=or>или</p><h2>Загрузите фото страницы</h2><form method=post enctype=multipart/form-data action=/convert><input type=file name=photo accept="image/*" required><div class=n>JPG, PNG, WEBP, до 10 МБ</div>{hid}<button>Сделать PDF</button></form></div></body></html>'''

def render(lines,out):
    h='<html><meta charset=utf-8><style>body{font-family:"DejaVu Sans",sans-serif;font-size:13px}.w{display:inline-block;text-align:center;margin:0 3px 4px 0}.t{font-size:10px;color:#555}.r{color:#225;margin:2px 0 12px}</style><body>'
    for L in lines:
        s=html.escape(L.get("speaker") or "")
        h+='<div>'+(f'<b>{s}:</b> ' if s else '')+''.join(f'<span class=w><span class=t>{html.escape(w["ru"])}</span><br>{html.escape(w["en"])}</span>' for w in L["words"])+f'</div><div class=r>{html.escape(L["translation"])}</div>'
    d=tempfile.mkdtemp();f=d+"/in.html";open(f,"w").write(h+"</body></html>")
    subprocess.run([os.environ.get("CHROME","google-chrome"),"--headless","--no-sandbox","--disable-gpu","--disable-dev-shm-usage","--disable-extensions","--no-zygote","--renderer-process-limit=1","--disable-software-rasterizer","--disable-background-networking","--disable-sync","--no-first-run","--mute-audio","--js-flags=--max-old-space-size=64","--no-pdf-header-footer","--print-to-pdf="+out,f],capture_output=True,timeout=120)
_tr=None
def _model():
    # Lightweight path: ctranslate2 + sentencepiece directly (avoids importing torch/stanza; ~150MB vs ~1GB RAM)
    global _tr
    if _tr is None:
        import ctranslate2,sentencepiece,glob,json
        base=os.environ.get("ARGOS_PACKAGES_DIR") or os.path.expanduser("~/.local/share/argos-translate/packages")
        d=next(p for p in glob.glob(base+"/*") if os.path.isfile(p+"/metadata.json") and (lambda m:m.get("from_code")=="en" and m.get("to_code")=="ru")(json.load(open(p+"/metadata.json"))))
        _tr=(ctranslate2.Translator(d+"/model",device="cpu",inter_threads=1,intra_threads=1,compute_type="int8"),sentencepiece.SentencePieceProcessor(model_file=d+"/sentencepiece.model"))
    return _tr
def tr(s):
    m,sp=_model(); out=[]
    for x in [p for p in re.split(r'(?<=[.!?])\s+',s.strip()) if p]:
        r=m.translate_batch([sp.encode(x,out_type=str)],beam_size=2,max_decoding_length=256)
        out.append(sp.decode(r[0].hypotheses[0]).replace("▁"," ").strip())
    return " ".join(out)
def convert(img,out):
    import offline
    rows=offline.parse(img)
    if not rows: raise RuntimeError("Текст на фото не распознан")
    render([dict(speaker=s,words=[dict(en=w,ru=ipa.trans(w)) for w in e.split() if w!='…'],translation=tr(e)) for s,e in rows],out)
def convert_text(text,out):
    sents=split_sentences(text)
    if not sents: raise RuntimeError("Пустой текст")
    render([dict(speaker="",words=[dict(en=w,ru=ipa.trans(w)) for w in e.split()],translation=tr(e)) for e in sents],out)

class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def send(self,code,body,ct="text/html; charset=utf-8"):
        self.send_response(code);self.send_header("Content-Type",ct);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self): self.send(200,page().encode())
    def fail(self,code,msg,cap=False): self.send(code,page(msg,new_captcha() if cap else None).encode())
    def do_POST(self):
        n=int(self.headers.get("Content-Length") or 0)
        if n>MAX_UPLOAD+64*1024:
            while n>0: n-=len(self.rfile.read(min(n,1<<16)) or b"x"*n)
            return self.fail(413,"Файл слишком большой (максимум 10 МБ)")
        raw=self.rfile.read(n)
        msg=email.message_from_bytes(b"Content-Type: "+(self.headers.get("Content-Type") or "").encode()+b"\r\n\r\n"+raw)
        if not msg.is_multipart(): return self.fail(400,"Неверный запрос")
        P={p.get_param("name",header="content-disposition"):p.get_payload(decode=True) or b"" for p in msg.get_payload()}
        g=lambda k:P.get(k,b"").decode("utf-8","replace").strip()
        if g("website"): return self.fail(400,"Запрос отклонён")
        err=check_token(g("token"))
        if err: return self.fail(400,err)
        ip=self.headers.get("X-Forwarded-For","").split(",")[0].strip() or self.client_address[0]
        if rate_hit(ip):
            cid=g("cid"); ans=_caps.pop(cid,None)
            if ans is None or g("captcha")!=str(ans): return self.fail(429,"Слишком много запросов. Решите пример и отправьте снова",cap=True)
        d=tempfile.mkdtemp();out=d+"/out.pdf"
        _job.acquire()
        try:
            if self.path=="/text":
                t=g("text")
                if len(t)>MAX_TEXT: return self.fail(413,f"Текст длиннее {MAX_TEXT} символов")
                convert_text(t,out)
            elif self.path=="/convert":
                b=P.get("photo",b"")
                if len(b)>MAX_UPLOAD: return self.fail(413,"Файл слишком большой (максимум 10 МБ)")
                k=image_kind(b)
                if not k: return self.fail(415,"Это не изображение (нужен JPG, PNG, WEBP)")
                img=d+"/p."+k;open(img,"wb").write(b);convert(img,out)
            else: return self.fail(404,"Не найдено")
            body=open(out,"rb").read()
            self.send_response(200);self.send_header("Content-Type","application/pdf");self.send_header("Content-Disposition","attachment; filename=text.pdf");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
        except Exception as e: self.fail(500,"Ошибка: "+str(e))
        finally: _job.release(); __import__("shutil").rmtree(d,ignore_errors=True)
_job=__import__("threading").Lock()  # one PDF job at a time (512MB RAM on free hosting)
if __name__=="__main__":
    if os.environ.get("PRELOAD","1")=="1":
        try: _model()
        except Exception as e: print("model preload failed:",e)
    ThreadingHTTPServer(("0.0.0.0",int(os.environ.get("PORT",8080))),H).serve_forever()
