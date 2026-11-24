#!/usr/bin/env python3
"""Parola del giorno Treccani -> wallpaper PNG + sito statico.
Uso: python3 update.py [--push]
"""
import json, re, sys, os, subprocess, datetime, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

def strip_html(s):
    s = re.sub(r"<style[^>]*>.*?</style>", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").replace("&#8220;", "\u201c").replace("&#8221;", "\u201d")
    return re.sub(r"\s+", " ", s).strip()

def today_word_url():
    """Link della parola del giorno dalla component 'Today' dell'homepage."""
    h = get("https://www.treccani.it/")
    i = h.find('"component":"Today"')
    if i < 0:
        raise RuntimeError("component Today non trovata in homepage")
    m = re.search(r'"url":"(https://www\.treccani\.it/vocabolario/[^"]+)"', h[i:i+8000])
    if not m:
        m = re.search(r'href="(/vocabolario/[^"?]+/)"', h[i-9000:i+100])
        if not m: raise RuntimeError("link parola non trovato")
        return "https://www.treccani.it" + m.group(1)
    return m.group(1)

def parse_entry(url):
    h = get(url)
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    data = json.loads(m.group(1))["props"]["pageProps"]["data"]
    c = data["content"]
    # etimologia grezza con markup -> separiamo prima della parte definita
    m = re.search(r"<b>(.+?)</b>\s*(agg\.|s\.m\.|s\.f\.|v\.|sm\.|s\.)\s*\[(.+?)\]", c)
    if m:
        lemma, pos, etimo_raw = m.group(1), m.group(2), m.group(3)
        tail = c[m.end():]
    else:
        mb = re.search(r"<b>(.+?)</b>", c)
        lemma = strip_html(mb.group(1))
        # l'etimologia e' la prima [...] dopo il lemma: i marcatori non sono un
        # elenco chiuso (es. "adattam. dell'ingl." per princisbécco) -> non fare
        # affidamento su keyword fisse, prendere il primo blocco quadre
        p = c.find("[", mb.end())
        q = c.find("]", p) if p >= 0 else -1
        while q >= 0:
            n = c.find("[", p + 1, q)
            if n >= 0:
                q = c.find("]", q + 1)
            else:
                break
        if p >= 0 and q >= 0:
            pos, etimo_raw = "", c[p:q + 1]
            tail = c[q + 1:]
        else:
            m2 = re.search(r"\[(dal|der\.|comp\.|var\.|lat\.|gr\.)", c)
            if m2:
                pos, etimo_raw = "", strip_html(c[m2.start():c.find("] –") if "] –" in c else m2.start()+400])
                tail = c[c.find("] –") + 3:] if "] –" in c else c
            else:
                pos, etimo_raw, tail = "", "", c
    # etimo: conserva i link testuali (es. rinvio a estravagante)
    etimo_links = re.findall(r'href="[^"]*/vocabolario/([^"/]+)/?"[^>]*>([^<]+)</a>', etimo_raw)
    etimo = strip_html(etimo_raw)
    # sensi: numeri + glossa tra parentesi quadre
    senses = []
    parts = re.split(r"<b>(\d+\.)</b>", tail)
    if len(parts) < 3:
        parts = re.split(r"(?:^|\s)(\d+\.)\s", strip_html(tail))
    labels = re.findall(r"(letter\. o raro\.|estroso|estensione)", "")
    for i in range(1, len(parts), 2):
        num = parts[i].rstrip(".")
        chunk = parts[i+1]
        txt = strip_html(chunk)
        g = re.search(r"\[([^\]]{15,200})\]", txt)
        qual = re.match(r"^\s*((?:letter|raro|estens|banch\.|non com\.)[^,\[]*?(?:o (?:raro|letter\.))?[^,\[]*)", strip_html(chunk))
        if g:
            gloss = g.group(1).strip()
        else:
            head = txt.lstrip()
            mcap = re.search(r"\b[A-ZÀ-Ù][^.;:]{14,190}", head)
            gloss = (mcap.group(0) if mcap else re.split(r"[:;]|\.\s", head)[0])[:190].strip()
        q = ""
        raw_head = strip_html(chunk)[:60]
        mq = re.match(r"^(letter\.\s+o\s+raro\.|letter\.|estroso|raro|non com\.)", raw_head)
        if mq: q = mq.group(1)
        senses.append({"num": num, "gloss": gloss, "qual": q})
    # forme derivate con sillabazione (per accento sul lemma)
    derived = re.findall(r"(\w+?)\s*\[([\w·]+(?:´|\b)[\w·]+[a-zéèìòùá][\w·]*)\]", strip_html(tail))
    derived = [(w, s) for w, s in derived if w.startswith(lemma.rstrip("e")) or lemma in w]
    return {"url": url, "lemma": lemma.strip(), "pos": pos.strip(),
            "etimo": etimo, "etimo_links": etimo_links,
            "senses": senses[:2], "derived": derived[:1],
            "opera": data.get("opera", ""), "fetched": datetime.datetime.now().isoformat()}

# --- struttura etimologia: lingua d'origine + parole componenti ---
LANG = r"(?:lat\. mediev\.|lat\. volg\.|lat\.|gr\.|fr\.|ant\.fr\.|altofr\.|ingl\.|spagn\.|tedesco|arab\.|neerl\.|gallo-|longob\.|franc\.)"
def etimo_parts(etimo):
    """lingua+forma d'origine, componenti (forma « glossa), eventuale rinvio."""
    lang = ""
    ml = re.search(LANG, etimo)
    if ml:
        lang = ml.group(0)
        rest = etimo[ml.end():]
        mf = re.match(r"\s*([A-Za-z\-À-Ùà-ù' ]+?)(?=[:,]|\s(?:comp\.|der\.|v\.|di )|$)", rest)
        form = mf.group(1).strip() if mf else ""
        source = (lang + (" " + form if form else "")).strip()
    else:
        source = etimo.split(",")[0][:120]
    comps = []
    mc = re.search(r"(?:comp\. di|der\. (?:da|di))\s+(.+?)$", etimo)
    if mc:
        body = mc.group(1)
        for piece in re.split(r"\s+e\s+", body):
            piece = piece.strip(" .")
            if not piece:
                continue
            mg = re.match(r"(.*?)[«]([^»»]+)[»]", piece)
            if mg:
                comps.append({"form": mg.group(1).strip(), "gloss": mg.group(2)})
            else:
                comps.append({"form": piece, "gloss": ""})
    xref = re.search(r"v\.\s+([A-Za-zà-ù]+)", etimo)
    return source, comps, (xref.group(1) if xref else "")

try:
    import pyphen
    _HAS_PYPHEN = True
except ImportError:
    _HAS_PYPHEN = False

if _HAS_PYPHEN:
    # sillabazione + accento verificati su it.wiktionary (16/17 esatti)
    _D = pyphen.Pyphen(lang="it")
    _V = "aeiou"
    _STRONG, _WEAK = "aeo", "iu"
    _ACC = {"à": "a", "è": "e", "é": "e", "ì": "i", "ò": "o", "ù": "u"}

    def _norm(w):
        return "".join(_ACC.get(c, c) for c in w.lower())

    def _chunks(w2):
        ch = _D.inserted(w2).split("-")
        out = []
        for c in ch:
            if out and c[:1] == "h" and out[-1][-1:] in _V:
                out[-1] += c          # digrammi ch/gh non separati
            else:
                out.append(c)
        return out

    def _vgroups(chunk, base):
        out, i = [], 0
        while i < len(chunk):
            if chunk[i] in _V:
                j = i
                while j + 1 < len(chunk) and chunk[j + 1] in _V:
                    j += 1
                out.append((base + i, base + j + 1))
                i = j + 1
            else:
                i += 1
        return out

    def tonic_in(chunk, base, final_syl):
        g = _vgroups(chunk, base)
        if not g:
            return -1
        g0, g1 = g[-1]
        if g1 - g0 == 1:
            return g0
        a, b = g0 - base, g1 - 1 - base
        va, vb = chunk[a], chunk[b]
        if va in _STRONG and vb in _WEAK:            # dittongo discendente
            return g0
        if (va in _WEAK and vb in _STRONG) or (va in _WEAK and vb in _WEAK and va != vb):
            if final_syl:                            # ascendente finale
                return g0
            return (b if vb in _STRONG else a) + base
        return g0

    _EXC = {"amico", "amica", "amici", "amiche", "intrico"}
    _IRREG = {"difficile": 2, "difficili": 2, "orrido": 0, "orridi": 0}

    def stressed_index(w):
        """Indice della vocale tonica in w; -1 se impossibile."""
        w2 = _norm(w)
        if not w2:
            return -1
        if w2 in _IRREG:
            return _IRREG[w2]
        ch = _chunks(w2)
        ns = len(ch)
        if w[-1:] in "àèéìòù":
            j = ns - 1                               # tronca
        elif ch[-1][-1:] not in _V:
            j = ns - 1
        elif re.search(r"(issimo|issima|issimi|issime|esimo|esima|esimi|esime)$", w2):
            j = ns - 3
        elif re.search(r"(imo|ima|imi|ime)$", w2) and ns >= 3:
            j = ns - 3
        elif w2 not in _EXC and re.search(r"(ibile|abili|abile|ico|ica|ici|iche|cile|tere|colo|cola)$", w2):
            j = ns - 3
        else:
            j = ns - 2
        j = max(0, min(ns - 1, j))
        base = 0
        for k, c in enumerate(ch):
            if k == j:
                return tonic_in(c, base, j == ns - 1)
            base += len(c)
        return -1

    ACCT = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú"}

    def syllabic(w):
        """'stra·va·gán·te' con vocale tonica accentata."""
        w2 = _norm(w)
        ch = _chunks(w2)
        vi = stressed_index(w)
        parts, pos = [], 0
        for c in ch:
            k = vi - pos if vi >= 0 else -1
            if 0 <= k < len(c):
                orig = w[pos + k]  # carattere originale: conserva àèéìòù esistenti
                parts.append(c[:k] + (orig if orig in "àèéìòù" else ACCT.get(c[k], c[k])) + c[k + 1:])
            else:
                parts.append(c)
            pos += len(c)
        return "·".join(parts), vi
else:
    # fallback euristico senza pyphen
    VOW = "aeiouòàèéìùá"

    def stressed_index(w):
        groups = [m.start() for m in re.finditer(f"[{VOW}]+", w)]
        if not groups:
            return -1
        if len(groups) >= 3 and re.search(r"(olo|ola|oli|ole|imo|ima|ile|ili|one|oni|are|ante|ente|ato|uto|ito|oso|osa)$", w):
            return groups[-3]
        if len(groups) >= 2:
            return groups[-2]
        return groups[-1]

    def syllabic(w):
        i = stressed_index(w)
        return w, i

if __name__ == "__main__":
    url = today_word_url()
    e = parse_entry(url)
    e["today"] = datetime.date.today().isoformat()
    src, comps, xref = etimo_parts(e["etimo"])
    e["etimo_source"], e["etimo_comps"], e["etimo_xref"] = src, comps, xref
    if xref and e["etimo_links"]:
        base_url = "https://www.treccani.it/vocabolario/" + e["etimo_links"][0][0] + "/"
        b = parse_entry(base_url)
        e["followed"] = e["etimo_links"][0][0]
        e["etimo_source"], e["etimo_comps"], _ = etimo_parts(b["etimo"])
        if not e["senses"] or len(e["senses"][0]["gloss"]) < 20:
            e["senses"] = b["senses"]
    syl = syllabic(e["lemma"])
    e["syllabic"] = syl[0] if isinstance(syl, tuple) else ""
    e["stress"] = syl[1] if isinstance(syl, tuple) else -1
    with open(os.path.join(ROOT, "word.json"), "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=2)
    print(json.dumps(e, ensure_ascii=False, indent=2))
