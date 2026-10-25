"""British IPA (ipa-dict en_UK, fallback eSpeak-NG en-gb) -> Russian letters, school style."""
import os,re,subprocess,functools
HERE=os.path.dirname(os.path.abspath(__file__))
DICT=os.path.join(HERE,"data","en_UK.txt")
_D=None
FIX={"the":"зэ","a":"э","an":"эн","and":"энд","or":"о","of":"ов","to":"ту","from":"фром","for":"фо","are":"а",
     "can":"кэн","was":"уоз","were":"уё","at":"эт","but":"бат","be":"би","as":"эз","than":"зэн","that":"зэт","with":"уиз","into":"инту","such":"сач","some":"сам"}
def _load():
    global _D
    if _D is None:
        _D={}
        if os.path.exists(DICT):
            for line in open(DICT,encoding="utf-8"):
                if "\t" in line:
                    w,p=line.rstrip("\n").split("\t",1)
                    _D.setdefault(w.lower(),p.split(",")[0].strip().strip("/"))
    return _D
@functools.lru_cache(4096)
def espeak(text):
    try: return subprocess.run(["espeak-ng","-v","en-gb","-q","--ipa",text],capture_output=True,text=True,timeout=20).stdout.strip()
    except Exception: return ""
def lookup(w):
    d=_load()
    return d.get(w) or espeak(w)
VOW="аэиоуёюяей"
M=[("eɪ","эй"),("aɪ","ай"),("ɔɪ","ой"),("əʊ","оу"),("oʊ","оу"),("aʊ","ау"),("ɪə","иэ"),("iə","иэ"),("eə","эа"),("ɛə","эа"),("ʊə","уэ"),
   ("tʃ","ч"),("dʒ","дж"),("ʃ","ш"),("ʒ","ж"),("θ","с"),("ð","з"),("ŋɡ","нг"),("ŋ","нг"),("ɹ","р"),("r","р"),("ɡ","г"),("g","г"),("x","х"),
   ("iː","и"),("ɑː","а"),("ɔː","о"),("uː","у"),("ɜː","ё"),("ɝ","ё"),("ɚ","э"),("æ","э"),("ɛ","э"),("e","э"),("ɪ","и"),("ᵻ","и"),("i","и"),("ɒ","о"),("ɔ","о"),
   ("ʌ","а"),("ʊ","у"),("u","у"),("ə","э"),("ɐ","э"),("a","э"),("ɑ","а"),("o","о"),("ɜ","ё"),("j","й"),("w","у"),("h","х"),("ʔ","т"),
   ("b","б"),("d","д"),("f","ф"),("k","к"),("l","л"),("ɫ","л"),("m","м"),("n","н"),("p","п"),("s","с"),("t","т"),("v","в"),("z","з")]
def ipa2ru(p):
    p=re.sub(r"[ˈˌ.ˑ\u0329\u0361\u032f()/]","",p).replace("ː","ː")
    out="";i=0
    while i<len(p):
        for a,b in M:
            if p.startswith(a,i): out+=b;i+=len(a);break
        else: i+=1
    s=out
    s=re.sub(r"р(?![аэиоуёюяе])","",s)                 # non-rhotic
    s=re.sub(r"(?<=[бвгдзклмнпрстфхчшж])йу","ью",s); s=re.sub(r"йу","ю",s)
    s=re.sub(r"шэн","шн",s)                              # -tion
    s=re.sub(r"(?<=[бпткдгфвзсмнчж])эл(з?)$",r"л\1",s)   # people, table(s)
    s=re.sub(r"(?<=[^аэиоуё])шнэл$","шнл",s)
    s=re.sub(r"([бвгдзклмнпрстфхж])\1",r"\1",s)
    return s
def trans(word):
    w=word.lower().replace("’","'")
    w=re.sub(r"^[^a-z0-9]+|[^a-z0-9]+$","",w)
    if not w: return ""
    if w in FIX: return FIX[w]
    if "-" in w: return "-".join(trans(x) for x in w.split("-") if x)
    d=_load()
    if w in d: return ipa2ru(d[w])
    if w.endswith("'s") and w[:-2] in d:
        b=ipa2ru(d[w[:-2]]); return b+("с" if b[-1:] in "пткф" else "з")
    if w.endswith("s'"): return trans(w[:-1])
    return ipa2ru(espeak(w)) or w
