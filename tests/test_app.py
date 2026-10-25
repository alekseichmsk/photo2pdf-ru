import os,sys,time,threading,urllib.request,urllib.error,uuid,pytest
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,ROOT)
os.environ["MIN_FILL"]="0"
import app,ipa
from http.server import ThreadingHTTPServer

@pytest.mark.parametrize("w,exp",[("traditional","трэдишнл"),("centuries-old","сэнчэриз-оулд"),("Japanese","джэпэниз"),("lunch","ланч"),
 ("history","хистэри"),("mother's","мазэз"),("the","зэ"),("fussy","фаси"),("popular","попьюлэ"),("vegetables","вэджитэблз"),
 ("nutritious","ньютришэс"),("people","пипл"),("work","уёк"),("5th","фифс"),("Today,","тэдэй")])
def test_trans(w,exp): assert ipa.trans(w)==exp
def test_ipa_nonrhotic(): assert ipa.ipa2ru("kɑː")=="ка"
def test_split(): assert app.split_sentences("Hi there. How are you?  Fine!\nOk")==["Hi there.","How are you?","Fine!","Ok"]
def test_token():
    t=app.make_token(); app.MIN_FILL=0; assert app.check_token(t) is None
    assert app.check_token(t[:-1]+("1" if t[-1]=="0" else "0")) and app.check_token("junk")
    app.MIN_FILL=3; assert "быстро" in app.check_token(app.make_token()); app.MIN_FILL=0
    assert "устарела" in app.check_token(app.make_token(time.time()-7200))
def test_image_kind():
    assert app.image_kind(b"\x89PNG\r\n\x1a\nxx")=="png" and app.image_kind(b"\xff\xd8\xffx")=="jpg" and app.image_kind(b"%PDF")is None

@pytest.fixture(scope="module")
def url():
    s=ThreadingHTTPServer(("127.0.0.1",0),app.H);threading.Thread(target=s.serve_forever,daemon=True).start()
    yield f"http://127.0.0.1:{s.server_port}";s.shutdown()
@pytest.fixture(autouse=True)
def reset(): app._hits.clear(); app.RATE_N=10; app.MIN_FILL=0
def post(u,path,fields,files=None,ip=None):
    b=uuid.uuid4().hex;body=b""
    for k,v in fields.items(): body+=f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k,(fn,data) in (files or {}).items(): body+=f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+data+b"\r\n"
    body+=f"--{b}--\r\n".encode()
    h={"Content-Type":"multipart/form-data; boundary="+b}
    if ip: h["X-Forwarded-For"]=ip
    try: r=urllib.request.urlopen(urllib.request.Request(u+path,body,h),timeout=300);return r.status,r.headers["Content-Type"],r.read()
    except urllib.error.HTTPError as e: return e.code,e.headers["Content-Type"],e.read()
def test_get(url):
    p=urllib.request.urlopen(url).read().decode(); assert "name=website" in p and "name=token" in p and "lang=ru" in p
    assert "cdn" not in p.lower() and "<script src" not in p
def test_text_pdf(url):
    c,t,b=post(url,"/text",{"text":"This is my house. It is big.","token":app.make_token()})
    assert c==200 and t=="application/pdf" and b[:4]==b"%PDF"
def test_photo_pdf(url):
    img=open(os.path.join(ROOT,"tests","sample.jpg"),"rb").read()
    c,t,b=post(url,"/convert",{"token":app.make_token()},{"photo":("p.jpg",img)})
    assert c==200 and b[:4]==b"%PDF"
def test_bad_image(url): assert post(url,"/convert",{"token":app.make_token()},{"photo":("x.jpg",b"not an image")})[0]==415
def test_honeypot(url): assert post(url,"/text",{"text":"Hi.","website":"spam","token":app.make_token()})[0]==400
def test_no_token(url): assert post(url,"/text",{"text":"Hi."})[0]==400
def test_too_fast(url):
    app.MIN_FILL=3; assert post(url,"/text",{"text":"Hi.","token":app.make_token()})[0]==400
def test_text_too_long(url): assert post(url,"/text",{"text":"a"*5001,"token":app.make_token()})[0]==413
def test_upload_too_big(url): assert post(url,"/convert",{"token":app.make_token()},{"photo":("x.jpg",b"\xff\xd8\xff"+b"0"*(11*1024*1024))})[0]==413
def test_rate_limit_and_captcha(url):
    app.RATE_N=2;ip="9.9.9.9"
    for _ in range(2): assert post(url,"/text",{"text":"Hi.","token":app.make_token()},ip=ip)[0]==200
    c,_,b=post(url,"/text",{"text":"Hi.","token":app.make_token()},ip=ip); assert c==429 and b"name=captcha" in b
    cid=b.decode().split("name=cid value=")[1].split(">")[0]; ans=app._caps[cid]
    assert post(url,"/text",{"text":"Hi.","token":app.make_token(),"cid":cid,"captcha":str(ans+1)},ip=ip)[0]==429
    c,_,b=post(url,"/text",{"text":"Hi.","token":app.make_token()},ip=ip);cid=b.decode().split("name=cid value=")[1].split(">")[0]
    assert post(url,"/text",{"text":"Hi.","token":app.make_token(),"cid":cid,"captcha":str(app._caps[cid])},ip=ip)[0]==200

def test_health_and_no_chrome():
    import app, inspect
    assert "chrom" not in inspect.getsource(app.render).lower()

def test_loading_state_and_health_v3():
    import app, inspect
    p=app.page()
    assert "Обрабатываю... это может занять до 2 минут" in p and "<script>" in p and "http" not in p.split("<script>")[1]
    assert "weasyprint-v3" in inspect.getsource(app.H.do_GET)

def test_ocr_prep_downscale(tmp_path):
    from PIL import Image
    import offline
    big=tmp_path/"b.png"; Image.new("RGB",(4000,3000),"white").save(big)
    p=offline.prep(str(big)); assert p and max(Image.open(p).size)<=offline.MAX_SIDE
    small=tmp_path/"s.png"; Image.new("RGB",(800,600),"white").save(small); assert offline.prep(str(small)) is None
