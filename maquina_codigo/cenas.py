import json, math, sys, subprocess, re, unicodedata, difflib
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, "/tmp/claude-0/-home-claude/345592a4-b47e-591b-b0fb-87c4679cee37/scratchpad/maquina")
import maquina as M
from maquina import F, W, H, FPS, GRN, GRN2, GOLD, RED, WHITE, GREY, EDGE, STEEL, STEEL2, ease, eio, back, rr, text_c, glow, music, sfx, caption_chunks, norm


_orig_text = ImageDraw.ImageDraw.text
def _text(self, xy, text, fill=None, font=None, anchor=None, *args, **kw):
    if isinstance(fill, tuple) and len(fill) == 4 and fill[3] < 255 and self.im.mode == "RGB":
        if fill[3] <= 0: return
        im = self._image
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        _orig_text(ImageDraw.Draw(lay), xy, text, fill=fill[:3] + (255,), font=font, anchor=anchor, *args, **kw)
        al = lay.getchannel("A").point(lambda v: v * fill[3] // 255); lay.putalpha(al)
        im.paste(lay, (0, 0), lay); return
    return _orig_text(self, xy, text, fill=fill, font=font, anchor=anchor, *args, **kw)
ImageDraw.ImageDraw.text = _text
_orig_init = ImageDraw.ImageDraw.__init__
def _init(self, im, mode=None):
    _orig_init(self, im, mode); self._image = im
ImageDraw.ImageDraw.__init__ = _init

DARK = (17, 20, 26)
SPECS = json.load(open(f"{M.B}/maquina/temas5.json"))

def align(words, lines):
    sw = []
    for li, l in enumerate(lines):
        for w in l.split(): sw.append((norm(w), li))
    tw = [norm(w[0]) for w in words]
    sm = difflib.SequenceMatcher(None, [x[0] for x in sw], tw, autojunk=False)
    starts = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            li = sw[a + k][1]; starts.setdefault(li, words[b + k][1])
    T = []
    for li in range(len(lines)):
        T.append(starts.get(li, T[-1] + 1.5 if T else 0.0))
    for i in range(1, len(T)): T[i] = max(T[i], T[i - 1] + 0.3)
    return T

# ---------- primitives (draw on RGBA layer with alpha a 0..1)
def A(c, a): return c + (int(255 * max(0, min(1, a))),)

def wrap(d, s, font, mw):
    out, cur = [], ""
    for w in s.split():
        x = (cur + " " + w).strip()
        if d.textlength(x, font=font) <= mw: cur = x
        else: out.append(cur); cur = w
    if cur: out.append(cur)
    return out

def headline(L, s, y, a, col=WHITE, size=96, box=None, sc=1.0):
    d = ImageDraw.Draw(L, "RGBA"); fnt = F("anton", int(size * sc)); lines = wrap(d, s, fnt, 900)
    lh = int(size * sc * 1.12); h = lh * len(lines)
    if box: rr(d, (70, y - h / 2 - 40, W - 70, y + h / 2 + 40), 34, fill=A(box, a * 0.95))
    for i, l in enumerate(lines): text_c(d, (W // 2, y - h / 2 + lh * i + lh / 2), l, fnt, A(col, a))

def chip(L, cx, cy, s, a, col=GRN, size=46, sc=1.0):
    d = ImageDraw.Draw(L, "RGBA"); fnt = F("inter800", max(8, int(size * sc))); tw = d.textlength(s, font=fnt)
    w2 = (tw + 70) / 2; h2 = size * 1.05 * sc
    rr(d, (cx - w2, cy - h2, cx + w2, cy + h2), int(h2), fill=A(col, a)); text_c(d, (cx, cy), s, fnt, A(WHITE, a))

def card(L, box, a, fill=(26, 31, 40), outline=EDGE, r=30, width=4):
    d = ImageDraw.Draw(L, "RGBA"); rr(d, box, r, fill=A(fill, a), outline=A(outline, a), width=width)

def check(L, x, y, a, ok=True, s=34):
    d = ImageDraw.Draw(L, "RGBA")
    d.ellipse((x - s, y - s, x + s, y + s), fill=A(GRN if ok else RED, a))
    if ok: d.line([(x - s * .45, y), (x - s * .1, y + s * .38), (x + s * .5, y - s * .35)], fill=A(WHITE, a), width=8)
    else:
        d.line([(x - s * .4, y - s * .4), (x + s * .4, y + s * .4)], fill=A(WHITE, a), width=8)
        d.line([(x - s * .4, y + s * .4), (x + s * .4, y - s * .4)], fill=A(WHITE, a), width=8)

def arrow(L, x0, y0, x1, y1, a, col=GOLD, w=10):
    d = ImageDraw.Draw(L, "RGBA"); d.line([(x0, y0), (x1, y1)], fill=A(col, a), width=w)
    ang = math.atan2(y1 - y0, x1 - x0); s = 26
    d.polygon([(x1, y1), (x1 - s * math.cos(ang - .5), y1 - s * math.sin(ang - .5)), (x1 - s * math.cos(ang + .5), y1 - s * math.sin(ang + .5))], fill=A(col, a))

def warn(L, cx, cy, s, a, sc=1.0):
    d = ImageDraw.Draw(L, "RGBA")
    tri = [(cx, cy - 90 * sc), (cx - 100 * sc, cy + 80 * sc), (cx + 100 * sc, cy + 80 * sc)]
    d.polygon(tri, fill=A(RED, a)); text_c(d, (cx, cy + 15 * sc), "!", F("anton", int(120 * sc)), A(WHITE, a))

def equation(L, y, a1, a2, a3, labels=("Usou", "Já pagou", "ALVO")):
    d = ImageDraw.Draw(L, "RGBA")
    rr(d, (70, y - 85, W - 70, y + 85), 30, fill=A((10, 12, 16), a1 * .95), outline=A(GRN, a1), width=4)
    text_c(d, (215, y), labels[0], F("anton", 70), A(WHITE, a1)); text_c(d, (360, y), "−", F("inter800", 70), A(GOLD, a2))
    text_c(d, (525, y), labels[1], F("anton", 70), A(WHITE, a2)); text_c(d, (690, y), "=", F("inter800", 70), A(GOLD, a3))
    text_c(d, (850, y), labels[2], F("anton", 76), A(GRN2, a3))

def ap(t, t0, d=0.4): return ease((t - t0) / d)
def vis(t, T, a, b, END):  # alpha of a block shown from line a to before line b
    t0 = T[a]; t1 = T[b] if b < len(T) else END
    return min(ease((t - t0 + 0.05) / 0.35), 1 - ease((t - t1 + 0.25) / 0.25))

# ---------- scenes per video
def scene_V1(L, t, T, END):
    a = vis(t, T, 0, 2, END)
    if a > 0:
        q = back((t - T[0]) / 0.5)
        headline(L, "O GOVERNO VAI COMPRAR A SUA DÍVIDA?", 820, a, GOLD, 110, sc=max(.01, q))
        if t > T[1]: chip(L, W // 2, 1180, "CALMA: OLHA O QUE É VERDADE", min(a, ap(t, T[1])), RED, 44)
    a = vis(t, T, 2, 5, END)
    if a > 0:
        card(L, (70, 470, W - 70, 1380), a)
        d = ImageDraw.Draw(L, "RGBA"); text_c(d, (W // 2, 560), "QUEM ENTRA NO DESENROLA 3.0", F("anton", 60), A(GOLD, a))
        items = [("Cartão de crédito e crédito pessoal", 2), ("Até R$ 10 mil (valor original)", 3), ("De 2 a 4,5 anos de atraso", 4)]
        for i, (s, li) in enumerate(items):
            b = min(a, ap(t, T[li])); y = 740 + i * 210
            if b <= 0: continue
            check(L, 180, y, b); d.text((250, y), s, font=fitf(d, s, "inter800", 46, W - 70 - 250 - 40), fill=A(WHITE, b), anchor="lm")
    a = vis(t, T, 5, 7, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA"); nodes = [("BANCOS", 300), ("GOVERNO", 760), ("VOCÊ", 1220)]
        for i, (s, y) in enumerate(nodes):
            b = min(a, ap(t, T[5] + i * 0.5)) if i < 2 else min(a, ap(t, T[6]))
            card(L, (230, y - 110, W - 230, y + 110), b, fill=(GRN if s == "VOCÊ" else (26, 31, 40)), outline=(GRN2 if s == "VOCÊ" else EDGE))
            text_c(d, (W // 2, y), s, F("anton", 86), A(WHITE, b))
        arrow(L, W // 2, 420, W // 2, 630, min(a, ap(t, T[5] + 0.4)))
        arrow(L, W // 2, 880, W // 2, 1090, min(a, ap(t, T[6])))
        if t > T[6] + 0.3: chip(L, W // 2 + 290, 1360, "SÓ DEPOIS", min(a, ap(t, T[6] + 0.3)), GOLD, 36)
    a = vis(t, T, 7, 8, END)
    if a > 0:
        check(L, W // 2, 640, a, True, 110 * max(.01, back((t - T[7]) / .5)))
        headline(L, "HOJE VOCÊ NÃO PRECISA FAZER NADA", 1000, a, GRN2, 96)
    a = vis(t, T, 8, 9, END)
    if a > 0:
        warn(L, W // 2, 640, "", a, max(.01, back((t - T[8]) / .5)) * 1.6)
        headline(L, "COBROU TAXA PRA TE COLOCAR NO PROGRAMA? DESCONFIE.", 1060, a, WHITE, 82, box=RED)
    a = vis(t, T, 9, 10, END)
    if a > 0:
        headline(L, "SUA DÍVIDA NÃO SE ENCAIXA?", 720, a, WHITE, 96)
        headline(L, "DÁ PRA NEGOCIAR DO MESMO JEITO", 1000, min(a, ap(t, T[9] + 1.0)), GRN2, 96)

def scene_V2(L, t, T, END):
    a = vis(t, T, 0, 1, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA"); q = max(.01, back((t - T[0]) / .5))
        rr(d, (W // 2 - 260 * q, 560 - 260 * q, W // 2 + 260 * q, 560 + 230 * q), int(40 * q), fill=A(WHITE, a))
        rr(d, (W // 2 - 260 * q, 560 - 260 * q, W // 2 + 260 * q, 560 - 150 * q), int(40 * q), fill=A(RED, a))
        text_c(d, (W // 2, 560 - 205 * q), "NOVEMBRO", F("anton", int(60 * q)), A(WHITE, a))
        text_c(d, (W // 2, 560 + 45 * q), "30", F("anton", int(230 * q)), A(DARK, a))
        headline(L, "MUTIRÃO DE NEGOCIAÇÃO DE DÍVIDAS", 1050, min(a, ap(t, T[0] + .6)), GOLD, 84)
    a = vis(t, T, 1, 2, END)
    if a > 0:
        n = int(160 * ease((t - T[1]) / 1.0)); d = ImageDraw.Draw(L, "RGBA")
        text_c(d, (W // 2, 760), f"+{n}", F("anton", 300), A(GOLD, a)); headline(L, "INSTITUIÇÕES", 1010, a, WHITE, 90)
    a = vis(t, T, 2, 3, END)
    if a > 0:
        for i, (s, c) in enumerate([("Cartão de crédito", GRN), ("Cheque especial", GRN), ("Outras dívidas atrasadas", STEEL2)]):
            q = back((t - T[2] - i * 0.45) / .4)
            if q > 0: chip(L, W // 2, 620 + i * 200, s, a, c, 58, q)
    a = vis(t, T, 3, 4, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA")
        for i, s in enumerate(["App do banco", "Consumidor.gov"]):
            b = min(a, ap(t, T[3] + i * 0.7)); x0 = 90 + i * 470
            card(L, (x0, 560, x0 + 430, 1100), b)
            rr(d, (x0 + 135, 640, x0 + 295, 940), 26, outline=A(GREY, b), width=8)
            d.ellipse((x0 + 200, 905, x0 + 230, 925), fill=A(GREY, b))
            text_c(d, (x0 + 215, 1020), s, F("inter800", 44), A(WHITE, b))
    a = vis(t, T, 4, 6, END)
    if a > 0:
        warn(L, W // 2, 520, "", a, 1.1)
        headline(L, "CUIDADO COM A PRIMEIRA PROPOSTA", 760, a, GOLD, 84)
        if t > T[5]:
            b = min(a, ap(t, T[5])); d = ImageDraw.Draw(L, "RGBA")
            card(L, (110, 900, W - 110, 1330), b, fill=(10, 12, 16))
            d.text((160, 990), "Cobrado com juros", font=F("inter700", 42), fill=A(GREY, b), anchor="lm")
            d.text((W - 160, 990), "R$ 30.000", font=F("anton", 62), fill=A(RED, b), anchor="rm")
            d.text((160, 1100), "Desconto de 40%", font=F("inter700", 42), fill=A(GREY, b), anchor="lm")
            d.text((W - 160, 1100), "− R$ 12.000", font=F("anton", 62), fill=A(GOLD, b), anchor="rm")
            d.line([(160, 1170), (W - 160, 1170)], fill=A(EDGE, b), width=3)
            d.text((160, 1250), "Proposta", font=F("inter800", 46), fill=A(WHITE, b), anchor="lm")
            d.text((W - 160, 1250), "R$ 18.000", font=F("anton", 70), fill=A(WHITE, b), anchor="rm")
            text_c(d, (W // 2, 1400), "(exemplo)", F("inter500", 34), A(GREY, b))
    a = vis(t, T, 6, 8, END)
    if a > 0:
        headline(L, "ANTES DE ACEITAR, FAÇA A CONTA", 700, a, WHITE, 88)
        equation(L, 1050, min(a, ap(t, T[6] + .3)), min(a, ap(t, T[7])), min(a, ap(t, T[7] + .9)))
    a = vis(t, T, 8, 9, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA"); base = 1200; p = ease((t - T[8]) / .7)
        rr(d, (230, base - int(250 * p), 450, base), 18, fill=A(GRN, a)); rr(d, (630, base - int(720 * p), 850, base), 18, fill=A(RED, a))
        text_c(d, (340, base + 55), "Seu alvo", F("inter700", 40), A(GREY, a)); text_c(d, (740, base + 55), "Proposta", F("inter700", 40), A(GREY, a))
        q = back((t - T[8] - .8) / .4)
        if q > 0:
            st = Image.new("RGBA", (760, 140), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
            rr(sd, (0, 0, 759, 139), 18, outline=RED + (255,), width=9); text_c(sd, (380, 72), "NÃO É DESCONTO", F("anton", 90), RED + (255,))
            sc = max(.01, 2 - q); st = st.resize((int(760 * sc), int(140 * sc))).rotate(-7, expand=True, resample=Image.BICUBIC)
            st.putalpha(Image.eval(st.getchannel("A"), lambda v: int(v * a * min(1, q))))
            L.paste(st, (W // 2 - st.width // 2, 330 - st.height // 2), st)

BANKS = [("Itaú", (236, 112, 0)), ("Santander", (204, 0, 0)), ("Nubank", (130, 10, 209)), ("Bradesco", (204, 9, 47)), ("BB", (240, 200, 0)), ("Caixa", (0, 94, 168))]

def scene_V3(L, t, T, END):
    a = vis(t, T, 0, 2, END)
    if a > 0:
        for i, (s, c) in enumerate(BANKS):
            q = back((t - T[0] - i * 0.15) / .4)
            if q > 0: chip(L, 250 + (i % 2) * 580, 560 + (i // 2) * 190, s, a, c, 56, q)
        if t > T[1]: headline(L, "CADA BANCO TEM UM TEMPO", 1250, min(a, ap(t, T[1])), GOLD, 90)
    a = vis(t, T, 2, 6, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA"); text_c(d, (W // 2, 470), "QUANDO A PROPOSTA BOA COSTUMA VIR", F("anton", 54), A(GOLD, a))
        rows = [("Itaú", 90, 2, BANKS[0][1]), ("Santander", 90, 2, BANKS[1][1]), ("Nubank", 180, 3, BANKS[2][1]), ("Bradesco", 180, 3, BANKS[3][1]), ("BB", 365, 4, (200, 165, 0))]
        for i, (s, dd, li, c) in enumerate(rows):
            b = min(a, ap(t, T[li] + (i % 2) * 0.25)); y = 600 + i * 150
            if b <= 0: continue
            d.text((90, y), s, font=F("inter800", 44), fill=A(WHITE, b), anchor="lm")
            ln = int(560 * dd / 365 * ease((t - T[li]) / .8))
            rr(d, (330, y - 34, 330 + max(ln, 40), y + 34), 18, fill=A(c, b))
            d.text((330 + max(ln, 40) + 16, y), f"{dd} dias", font=F("anton", 52), fill=A(WHITE, b), anchor="lm")
        if t > T[5]:
            b = min(a, ap(t, T[5])); chip(L, W // 2, 1420, "O que vemos negociando · não é regra", b, STEEL2, 36)
    a = vis(t, T, 6, 7, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA"); q = max(.01, back((t - T[6]) / .5))
        d.ellipse((W // 2 - 170 * q, 700 - 170 * q, W // 2 + 170 * q, 700 + 170 * q), outline=A(GOLD, a), width=16)
        d.line([(W // 2, 700), (W // 2, 700 - 110 * q)], fill=A(GOLD, a), width=14); d.line([(W // 2, 700), (W // 2 + 80 * q, 700)], fill=A(GOLD, a), width=14)
        headline(L, "ESPERAR SOZINHO NÃO RESOLVE", 1050, a, WHITE, 92, box=RED)
    a = vis(t, T, 7, 8, END)
    if a > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); lg = ImageDraw.Draw(lay)
        r = int(110 * max(0, back((t - T[7] - .2) / .5)))
        rr(lg, (140, 600, W - 140, 900), 50, fill=A((6, 8, 10), a), outline=A(GRN2, a), width=6)
        if r > 0:
            lg.ellipse((300 - r, 750 - r, 300 + r, 750 + r), fill=A(GRN, a))
            text_c(lg, (640, 750), "VALOR ALVO", F("anton", 100), A(GRN2, a * (0.8 + 0.2 * math.sin(t * 6))))
        _g = lay.filter(ImageFilter.GaussianBlur(20)); L.paste(_g, (0, 0), _g); L.paste(lay, (0, 0), lay)
        headline(L, "NEGOCIE COM ELE NA MÃO", 1100, min(a, ap(t, T[7] + .6)), WHITE, 84)

def scene_V4(L, t, T, END):
    a = vis(t, T, 0, 8, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA")
        card(L, (80, 380, W - 80, 1480), a, fill=(245, 246, 248), outline=(200, 205, 212))
        rr(d, (80, 380, W - 80, 480), 30, fill=A((37, 99, 170), a)); d.rectangle((80, 450, W - 80, 480), fill=A((37, 99, 170), a))
        d.text((130, 430), "Sua reclamação", font=F("inter800", 44), fill=A(WHITE, a), anchor="lm")
        # phase 1: bad text
        if t < T[2]:
            s = "Quero um desconto."; n = int(len(s) * ease((t - T[0] - .3) / .8))
            d.text((130, 600), s[:n], font=F("inter700", 52), fill=A(DARK, a), anchor="lm")
            if t > T[1]:
                p = ease((t - T[1]) / .4); d.line([(120, 600), (120 + 520 * p, 600)], fill=A(RED, a), width=10)
                check(L, 820, 600, min(a, p), False, 46)
        else:
            text_c(d, (W // 2, 560), "3 INFORMAÇÕES", F("anton", 64), A((37, 99, 170), min(a, ap(t, T[2]))))
            fields = [("1. Quanto usei no cartão:", "R$ ......", 3), ("2. Quanto já paguei:", "R$ ......", 4), ("3. Cabe no meu bolso por mês:", "R$ ......", 5)]
            for i, (lab, val, li) in enumerate(fields):
                b = min(a, ap(t, T[li])); y = 690 + i * 175
                if b <= 0: continue
                d.text((130, y), lab, font=F("inter800", 42), fill=A(DARK, b), anchor="lm")
                rr(d, (130, y + 35, W - 130, y + 110), 14, outline=A((37, 99, 170), b), width=4)
                d.text((160, y + 72), val, font=F("inter700", 40), fill=A(GREY, b), anchor="lm")
                check(L, W - 180, y + 72, b * ease((t - T[li] - .8) / .3), True, 26)
            if t > T[6]:
                s = "Peço a proposta por escrito, sem juros."; n = int(len(s) * ease((t - T[6]) / 1.3)); b = a
                d.text((130, 1260), s[:n], font=F("inter800", 42), fill=A((20, 120, 70), b), anchor="lm")
                q = back((t - T[6] - 1.4) / .4)
                if q > 0:
                    rr(d, (W // 2 - 170 * q, 1330, W // 2 + 170 * q, 1330 + 100 * q), 20, fill=A(GRN, b))
                    text_c(d, (W // 2, 1330 + 50 * q), "ENVIAR", F("anton", int(52 * q)), A(WHITE, b))
    a = vis(t, T, 7, 8, END)
    if a > 0:
        _o = Image.new("RGBA", (W, H), (8, 10, 13, int(220 * a))); L.paste(_o, (0, 0), _o)
        chip(L, W // 2, 760, "O banco tem prazo pra responder", a, GRN, 50, max(.01, back((t - T[7]) / .4)))
        q = back((t - T[7] - 1.0) / .4)
        if q > 0: chip(L, W // 2, 980, "Fica tudo registrado", a, GOLD, 50, q)

def car(L, cx, cy, a, sc=1.0):
    d = ImageDraw.Draw(L, "RGBA")
    rr(d, (cx - 230 * sc, cy - 40 * sc, cx + 230 * sc, cy + 70 * sc), int(30 * sc), fill=A((60, 130, 210), a))
    d.polygon([(cx - 130 * sc, cy - 40 * sc), (cx - 80 * sc, cy - 120 * sc), (cx + 90 * sc, cy - 120 * sc), (cx + 150 * sc, cy - 40 * sc)], fill=A((60, 130, 210), a))
    d.polygon([(cx - 105 * sc, cy - 45 * sc), (cx - 70 * sc, cy - 102 * sc), (cx - 5 * sc, cy - 102 * sc), (cx - 5 * sc, cy - 45 * sc)], fill=A((180, 210, 240), a))
    d.polygon([(cx + 10 * sc, cy - 45 * sc), (cx + 10 * sc, cy - 102 * sc), (cx + 80 * sc, cy - 102 * sc), (cx + 125 * sc, cy - 45 * sc)], fill=A((180, 210, 240), a))
    for wx in (-130, 130): d.ellipse((cx + (wx - 55) * sc, cy + 15 * sc, cx + (wx + 55) * sc, cy + 125 * sc), fill=A((30, 32, 38), a), outline=A(GREY, a), width=int(8 * sc))

def scene_V5(L, t, T, END):
    a = vis(t, T, 0, 2, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA"); q = max(.01, back((t - T[0]) / .5))
        rr(d, (90, 560, W - 90, 1000), 40, fill=A(WHITE, a))
        d.ellipse((130, 600, 230, 700), fill=A((180, 186, 196), a))
        d.text((260, 650), "seguidor", font=F("inter800", 40), fill=A(DARK, a), anchor="lm")
        s = "Devo 100 mil no cartão e o gerente mandou vender o meu carro."
        n = int(len(s) * ease((t - T[1]) / 1.6)) if t > T[1] else 0
        for i, l in enumerate(wrap(d, s[:n], F("inter700", 50), 800)): d.text((140, 760 + i * 70), l, font=F("inter700", 50), fill=A(DARK, a))
        if t < T[1]: text_c(d, (W // 2, 820), "Respondendo o comentário", F("anton", 66), A(GOLD, a))
    a = vis(t, T, 2, 4, END)
    if a > 0:
        headline(L, "ANTES DE VENDER QUALQUER COISA", 700, a, WHITE, 90)
        if t > T[3]: headline(L, "QUANTO VOCÊ REALMENTE USOU?", 1050, min(a, ap(t, T[3])), GOLD, 90, box=(26, 31, 40))
    a = vis(t, T, 4, 6, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA")
        for i, (lab, v, c) in enumerate([("Usou", "R$ 45 mil", GRN2), ("Já pagou", "R$ 20 mil", GOLD)]):
            b = min(a, ap(t, T[4] + i * .9)); x0 = 90 + i * 470
            card(L, (x0, 520, x0 + 430, 820), b)
            text_c(d, (x0 + 215, 600), lab, F("inter700", 44), A(GREY, b)); text_c(d, (x0 + 215, 720), v, F("anton", 84), A(c, b))
        text_c(d, (W // 2, 880), "(exemplo)", F("inter500", 34), A(GREY, a))
        if t > T[5]:
            b = min(a, ap(t, T[5])); q = max(.01, back((t - T[5]) / .5))
            card(L, (90, 980, W - 90, 1360), b, fill=(10, 12, 16), outline=GRN2)
            text_c(d, (W // 2, 1060), "SEU VALOR ALVO", F("anton", 56), A(GRN2, b))
            text_c(d, (W // 2, 1200), "R$ 25 mil", F("anton", int(130 * q)), A(WHITE, b))
            text_c(d, (W // 2, 1310), "não R$ 100 mil", F("inter800", 44), A(RED, b))
    a = vis(t, T, 6, 7, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA"); p = ease((t - T[6]) / .8)
        text_c(d, (W // 2, 520), "OS R$ 100 MIL QUE O BANCO COBRA", F("anton", 60), A(WHITE, a))
        rr(d, (90, 620, 90 + int(900 * p), 820), 24, fill=A(RED, a))
        rr(d, (90, 620, 90 + int(225 * p), 820), 24, fill=A(GRN, a))
        if p > .9:
            text_c(d, (202, 720), "25", F("anton", 90), A(WHITE, a)); text_c(d, (650, 720), "75 = JUROS", F("anton", 96), A(WHITE, a))
        headline(L, "JUROS EM CIMA DE JUROS", 1050, min(a, ap(t, T[6] + .9)), GOLD, 96)
    a = vis(t, T, 7, 8, END)
    if a > 0:
        car(L, W // 2, 700, a, 1.3)
        q = ease((t - T[7] - .5) / .4)
        if q > 0:
            d = ImageDraw.Draw(L, "RGBA"); d.line([(W // 2 - 330, 520), (W // 2 - 330 + 660 * q, 520 + 380 * q)], fill=A(RED, a), width=26)
        headline(L, "VENDER O CARRO PRA PAGAR JUROS É PERDER DUAS VEZES", 1150, min(a, ap(t, T[7] + .8)), WHITE, 76, box=RED)
    a = vis(t, T, 8, 9, END)
    if a > 0:
        headline(L, "CADA CASO É UM CASO", 720, a, GREY, 80)
        headline(L, "MAS PRIMEIRO, O VALOR ALVO", 980, min(a, ap(t, T[8] + .8)), GRN2, 100)


PR = f"{M.B}/maquina/prints"
_pcache = {}
def pimg(name, maxw, maxh, card=True):
    k = (name, maxw, maxh, card)
    if k not in _pcache:
        im = Image.open(f"{PR}/{name}").convert("RGBA"); sc = min(maxw / im.width, maxh / im.height)
        im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
        if card:
            c = Image.new("RGBA", (im.width + 36, im.height + 36), (255, 255, 255, 255)); c.alpha_composite(im, (18, 18))
            m = Image.new("L", c.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, c.width - 1, c.height - 1), 22, fill=255); c.putalpha(m); im = c
        _pcache[k] = im
    return _pcache[k]

# (key) -> list of (print, line, offset, dur, y, maxw, maxh, card, dim)
OVL = {
 "V1": [("desenrola_arte.png", 0, 0.0, 2.3, 820, 980, 900, False, 0), ("g1_desenrola.png", 5, 0.0, 3.0, 1250, 980, 400, True, 0)],
 "V2": [("agbr_mutirao.png", 0, 0.1, 3.4, 1250, 980, 400, True, 0)],
 "V6": [("desenrola_logo.png", 3, 0.0, 2.2, 1250, 900, 380, True, 0)],
 "V7": [("desenrola_arte.png", 0, 0.0, 2.2, 1000, 900, 800, False, 0.6), ("criterios.png", 3, 0.2, 3.6, 1000, 760, 700, True, 0.75)],
 "V8": [("g1_desenrola.png", 1, 0.0, 3.6, 1250, 980, 400, True, 0)],
}
def overlays(img, key, t, T):
    for name, li, off, dur, y, mw, mh, card, dim in OVL.get(key, []):
        t0 = T[li] + off; t1 = t0 + dur
        if not (t0 <= t <= t1): continue
        a = min(ease((t - t0) / 0.25), 1 - ease((t - t1 + 0.25) / 0.25)); q = back((t - t0) / 0.45)
        if dim:
            o = Image.new("RGBA", (W, H), (8, 10, 13, int(255 * dim * a))); img.paste(o, (0, 0), o)
        im = pimg(name, mw, mh, card); sc = 0.85 + 0.15 * min(q, 1.1)
        im2 = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))))
        if a < 1: im2.putalpha(im2.getchannel("A").point(lambda v: int(v * a)))
        sh = Image.new("RGBA", (im2.width + 60, im2.height + 60), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((30, 40, im2.width + 30, im2.height + 40), 24, fill=(0, 0, 0, int(140 * a)))
        sh = sh.filter(ImageFilter.GaussianBlur(14)); img.paste(sh, (W // 2 - sh.width // 2, int(y - sh.height / 2)), sh)
        img.paste(im2, (W // 2 - im2.width // 2, int(y - im2.height / 2)), im2)


def fitf(d, s, name, size, maxw):
    while size > 20 and d.textlength(s, font=F(name, size)) > maxw: size -= 2
    return F(name, size)

def make_bg():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.zeros((H, W, 3), np.float32)
    top = np.array([16, 26, 46], np.float32); bot = np.array([6, 8, 14], np.float32)
    k = (y / H)[..., None]; base += top * (1 - k) + bot * k
    def blob(cx, cy, r, col, s):
        g = np.exp(-(((x - cx) ** 2 + (y - cy) ** 2) / (2 * r * r)))[..., None]; return g * np.array(col, np.float32) * s
    base += blob(W * 0.15, H * 0.12, 520, (37, 153, 90), 0.55)
    base += blob(W * 0.9, H * 0.55, 600, (40, 80, 200), 0.35)
    base += blob(W * 0.3, H * 0.95, 560, (232, 176, 74), 0.22)
    vig = 1 - 0.45 * (((x - W / 2) / (W * 0.75)) ** 2 + ((y - H / 2) / (H * 0.75)) ** 2)[..., None]
    base *= np.clip(vig, 0.4, 1)
    rng = np.random.default_rng(3); base += rng.normal(0, 2.2, base.shape)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")

BGRGB = make_bg()
SCENES = {"V1": scene_V1, "V2": scene_V2, "V3": scene_V3, "V4": scene_V4, "V5": scene_V5}

def frame(key, t, T, words, chunks, END):
    img = BGRGB.copy(); SCENES[key](img, t, T, END); overlays(img, key, t, T)
    d = ImageDraw.Draw(img, "RGBA"); TL = T[-1]
    title = SPECS[key]["title"]
    if t < T[1] + 0.2:
        a = 1 - ease((t - T[1]) / 0.25); fnt = F("inter800", 56); tw = d.textlength(title, font=fnt)
        rr(d, (W / 2 - tw / 2 - 50, 150, W / 2 + tw / 2 + 50, 290), 26, fill=A(WHITE, a)); text_c(d, (540, 220), title, fnt, A(DARK, a))
    if t > TL - 0.1:   # CTA
        p = ease((t - TL) / 0.5)
        _o = Image.new("RGBA", (W, H), (8, 10, 13, int(215 * p))); img.paste(_o, (0, 0), _o); d = ImageDraw.Draw(img, "RGBA")
        rr(d, (90, 520, 990, 760), 40, fill=A(WHITE, p))
        text_c(d, (540, 600), "Comenta o nome do banco", F("inter800", 58), A(DARK, p)); text_c(d, (540, 680), "que você deve", F("inter800", 58), A(DARK, p))
        for i, (bk, c) in enumerate(BANKS):
            q = back((t - TL - 0.5 - i * 0.18) / 0.4)
            if q <= 0: continue
            fnt = F("inter800", 44); tw = d.textlength(bk, font=fnt); s = q; w2 = (tw + 70) * s / 2; h2 = 50 * s
            cx = 230 + (i % 3) * 310; cyy = 880 + (i // 3) * 140
            rr(d, (cx - w2, cyy - h2, cx + w2, cyy + h2), int(48 * s), fill=GRN + (255,))
            if s > 0.6: text_c(d, (cx, cyy), bk, F("inter800", int(44 * min(1, s))), WHITE)
        a = ease((t - TL - 1.8) / 0.5)
        text_c(d, (540, 1210), "e receba a aula gratuita", F("inter700", 50), A(GOLD, a))
        text_c(d, (540, 1300), "@rafaell.financas", F("anton", 64), A(WHITE, a))
        text_c(d, (540, 1380), "Cada caso é um caso.", F("inter500", 34), A(GREY, a))
    if t < TL - 0.1:
        for ch in chunks:
            s0 = words[ch[0]][1]; e0 = words[ch[-1]][2] + 0.25
            if s0 - 0.05 <= t <= e0:
                fnt = F("montserrat700", 64); txt = [words[i][0] for i in ch]
                widths = [d.textlength(w + " ", font=fnt) for w in txt]; tot = sum(widths); x = (W - tot) / 2; y = 1640
                for i, w, wd in zip(ch, txt, widths):
                    if words[i][1] - 0.03 <= t <= words[i][2] + 0.03:
                        bw = d.textlength(w, font=fnt); rr(d, (x - 12, y - 46, x + bw + 12, y + 50), 14, fill=GOLD + (255,))
                        d.text((x, y), w, font=fnt, fill=DARK, anchor="lm")
                    else: d.text((x, y), w, font=fnt, fill=WHITE, anchor="lm", stroke_width=5, stroke_fill=(0, 0, 0))
                    x += wd
                break
    return img

def fix_words(words):
    out = []
    for w in words:
        s = w[0]
        if norm(s) == "ponto" and out and norm(out[-1][0]) in ("consumidor", "3"):
            out[-1][0] += "." if norm(out[-1][0]) == "consumidor" else ".0"; out[-1][2] = w[2]; continue
        if out and out[-1][0].endswith((".", ".0")) and norm(s) in ("gov", "0", "zero"):
            out[-1][0] = out[-1][0].rstrip(".") + ("." + s if norm(s) == "gov" else ".0" if out[-1][0].endswith(".") else ""); out[-1][2] = w[2]; continue
        out.append(list(w))
    return out

def render(key, voice_wav, words_json, out, still=None):
    import soundfile as sf
    words = fix_words(json.load(open(words_json))["words"]); lines = SPECS[key]["lines"]
    T = align(words, lines); print(key, "T", [round(x, 2) for x in T])
    chunks = caption_chunks(words)
    if still:
        for tt in still: frame(key, tt, T, words, chunks, 60).save(f"{M.B}/maquina/{key}_still_{tt}.png")
        return
    v, sr = sf.read(voice_wav, dtype="float32")
    if v.ndim > 1: v = v.mean(1)
    END = len(v) / sr + 2.6; N = int(END * sr); mix = np.zeros(N, np.float32); mix[:len(v)] += v
    mix += (music(END)[:N] * 0.10).astype(np.float32)
    np.random.seed(2)
    for i, tt in enumerate(T):
        s = sfx("whoosh" if i % 2 else "pop", sr).astype(np.float32) * 0.45; i0 = int(tt * sr); j = min(N, i0 + len(s))
        if i0 < N: mix[i0:j] += s[:j - i0]
    sf.write(out + ".wav", np.clip(mix, -1, 1), sr)
    p = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", out + ".wav", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.5", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(int(END * FPS)): p.stdin.write(frame(key, i / FPS, T, words, chunks, END).tobytes())
    p.stdin.close(); p.wait(); print("ok", out)


# ================= V6-V8 (Desenrola, mais animação)
def phone(L, cx, cy, a, sc=1.0, rot=0):
    lay = Image.new("RGBA", (520, 980), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    rr(d, (0, 0, 519, 979), 70, fill=(12, 12, 14, 255), outline=(70, 74, 84, 255), width=8)
    rr(d, (22, 22, 497, 957), 54, fill=(236, 229, 221, 255))
    rr(d, (190, 40, 330, 72), 16, fill=(12, 12, 14, 255))
    rr(d, (22, 90, 497, 190), 0, fill=(32, 44, 51, 255))
    d.ellipse((50, 112, 106, 168), fill=(150, 156, 166, 255))
    d.text((124, 124), "+55 11 9XXXX-XXXX", font=F("inter700", 28), fill=(240, 240, 240))
    d.text((124, 158), "online", font=F("inter500", 22), fill=(170, 180, 186))
    if sc != 1.0 or rot: lay = lay.resize((max(1, int(520 * sc)), max(1, int(980 * sc)))).rotate(rot, expand=True, resample=Image.BICUBIC)
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    L.paste(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)), lay)
    return (cx - 260 * sc, cy - 490 * sc, sc)

def stamp(L, s, cx, cy, q, a, col=RED, w=760, h=170, size=120, rot=-8):
    if q <= 0: return
    st = Image.new("RGBA", (w, h), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
    rr(sd, (0, 0, w - 1, h - 1), 20, outline=col + (255,), width=12); text_c(sd, (w // 2, h // 2 + 6), s, F("anton", size), col + (255,))
    sc = max(.01, 2.2 - 1.2 * min(q, 1.3)); st = st.resize((int(w * sc), int(h * sc))).rotate(rot, expand=True, resample=Image.BICUBIC)
    st.putalpha(st.getchannel("A").point(lambda v: int(v * a * min(1, q))))
    L.paste(st, (int(cx - st.width / 2), int(cy - st.height / 2)), st)

def flash(L, t, t0, col=RED, dur=0.35):
    k = 1 - (t - t0) / dur
    if 0 < k <= 1:
        o = Image.new("RGBA", (W, H), col + (int(110 * k),)); L.paste(o, (0, 0), o)

def bubble(L, x, y, w, s, a, n=None, col=(255, 255, 255)):
    d = ImageDraw.Draw(L, "RGBA"); fnt = F("inter700", 34); lines = wrap(d, s if n is None else s[:n], fnt, w - 50)
    h = 40 + 46 * max(1, len(lines))
    rr(d, (x, y, x + w, y + h), 22, fill=A(col, a))
    for i, l in enumerate(lines): d.text((x + 25, y + 22 + i * 46), l, font=fnt, fill=A(DARK, a))
    return h

def scene_V6(L, t, T, END):
    a = vis(t, T, 0, 3, END)
    if a > 0:
        up = eio((t - T[0]) / 0.7); vib = 10 * math.sin(t * 80) if T[0] + 0.7 < t < T[0] + 1.4 else 0
        wa = pimg("whats_golpe.png", 760, 1330, True)
        im = wa.crop((0, 0, wa.width, 900)) if True else wa
        cy = 2100 - (2100 - 820) * up
        im2 = im.copy(); im2.putalpha(im2.getchannel("A").point(lambda v: int(v * a)))
        L.paste(im2, (int(W // 2 - im2.width // 2 + vib), int(cy - im2.height // 2)), im2)
        if t > T[1]:
            d = ImageDraw.Draw(L, "RGBA"); b = min(a, ap(t, T[1] + 0.3)); y0 = cy - im2.height / 2
            rr(d, (W // 2 - 360, y0 + 470, W // 2 + 360, y0 + 610), 20, outline=A(GOLD, b), width=8)
            chip(L, W // 2, y0 + 660, "Pix com prazo de hoje", b, GOLD, 34)
        if t > T[2]:
            flash(L, t, T[2]); stamp(L, "GOLPE", W // 2, 900, back((t - T[2]) / 0.35), a, RED, 700, 220, 170, -10)
    a = vis(t, T, 3, 6, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA")
        headline(L, "A NEGOCIAÇÃO AINDA NEM COMEÇOU", 470, a, GOLD, 80)
        steps = [("Bancos oferecem as dívidas", 4), ("Governo compra (leilão)", 4), ("Negociação com você", 5)]
        for i, (s, li) in enumerate(steps):
            y = 720 + i * 230; b = min(a, ap(t, T[li] + (0.6 if i == 1 else 0)))
            active = (i < 2 and t > T[4]) or (i == 2 and t > T[5])
            d.ellipse((140, y - 50, 240, y + 50), fill=A(GRN if active else STEEL2, max(b, a * .5)))
            text_c(d, (190, y), str(i + 1), F("anton", 60), A(WHITE, max(b, a * .5)))
            d.text((280, y), s, font=F("inter800", 48), fill=A(WHITE if active else GREY, max(b, a * .5)), anchor="lm")
            if i < 2: d.line([(190, y + 55), (190, y + 175)], fill=A(STEEL2, a), width=8)
        mk = 720 if t < T[5] else 720 + 2 * 230 * ease((t - T[5]) / 0.8)
        chip(L, 850, mk - 95, "VOCÊ ESTÁ AQUI" if t < T[5] else "SÓ DEPOIS", a, RED if t < T[5] else GOLD, 30)
    a = vis(t, T, 6, 7, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA"); q = max(.01, back((t - T[6]) / .45))
        card(L, (140, 600, W - 140, 900), a, fill=(26, 31, 40))
        text_c(d, (W // 2, 750), "TAXA DE INSCRIÇÃO", F("anton", int(86 * q)), A(WHITE, a))
        p = ease((t - T[6] - 0.6) / 0.35)
        d.line([(170, 630), (170 + (W - 340) * p, 630 + 240 * p)], fill=A(RED, a), width=22)
        d.line([(W - 170, 630), (W - 170 - (W - 340) * p, 630 + 240 * p)], fill=A(RED, a), width=22)
        headline(L, "NINGUÉM COBRA PRA TE COLOCAR NO PROGRAMA", 1120, min(a, ap(t, T[6] + 0.8)), GOLD, 72)
    a = vis(t, T, 7, 8, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA"); q = max(.01, back((t - T[7]) / .5)); cx, cy = W // 2, 720
        s = 150 * q; d.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill=A((50, 188, 173), a))
        text_c(d, (cx, cy), "PIX", F("anton", int(90 * q)), A(WHITE, a))
        check(L, cx + 170, cy - 130, min(a, ap(t, T[7] + .6)), False, 60)
        headline(L, "NUNCA PAGUE ACORDO PRA CONTA DE PESSOA FÍSICA", 1120, min(a, ap(t, T[7] + .4)), WHITE, 72, box=RED)
    a = vis(t, T, 8, 9, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA"); p = ease((t - T[8]) / 1.2); x = 200 + 680 * p; y = 900 - 420 * p + 60 * math.sin(p * 6)
        d.polygon([(x - 90, y + 20), (x + 110, y - 70), (x - 20, y + 90)], fill=A(WHITE, a)); d.polygon([(x - 20, y + 90), (x + 110, y - 70), (x + 10, y + 40)], fill=A(GREY, a))
        headline(L, "MANDA PRA QUEM ESTÁ ESPERANDO O DESENROLA", 1150, a, GOLD, 78)

def flipcard(L, cx, cy, w, h, t0, t, a, front, ok=None):
    p = (t - t0) / 0.5
    if p < 0: sx, showf = 1, False
    elif p < 0.5: sx, showf = 1 - p * 2, False
    elif p < 1: sx, showf = (p - 0.5) * 2, True
    else: sx, showf = 1, True
    ww = max(4, int(w * sx)); d = ImageDraw.Draw(L, "RGBA")
    if not showf:
        rr(d, (cx - ww / 2, cy - h / 2, cx + ww / 2, cy + h / 2), 26, fill=A(STEEL2, a), outline=A(GOLD, a), width=5)
        if sx > .5: text_c(d, (cx, cy), "?", F("anton", 140), A(GOLD, a))
    else:
        rr(d, (cx - ww / 2, cy - h / 2, cx + ww / 2, cy + h / 2), 26, fill=A(WHITE, a))
        if sx > .7:
            fnt = F("inter800", 40); lines = wrap(d, front, fnt, w - 160)
            for i, l in enumerate(lines): d.text((cx - w / 2 + 40, cy - 24 * len(lines) + 48 * i + 24), l, font=fnt, fill=A(DARK, a), anchor="lm")
            if ok is not None and t > t0 + 0.9: check(L, cx + w / 2 - 70, cy, min(a, ease((t - t0 - 0.9) / .3)), ok, 40)

def scene_V7(L, t, T, END):
    a = vis(t, T, 0, 5, END)
    if a > 0:
        headline(L, "TESTE: 3 PERGUNTAS", 420, a, GOLD, 90)
        qs = [("É cartão de crédito ou crédito pessoal?", 1), ("Valor original de até R$ 10 mil?", 3), ("Atraso entre 2 e 4,5 anos?", 4)]
        for i, (s, li) in enumerate(qs):
            y0 = 640 + i * 270; dy = 40 * (1 - back((t - T[0] - i * 0.2) / .5)) if t < T[0] + 1 else 0
            flipcard(L, W // 2, y0 + dy, 900, 220, T[li], t, a, s, True)
        if T[2] - .05 < t < T[3] + .2:
            chip(L, W // 2 + 230, 790, "Consignado não entra", min(a, ap(t, T[2]), 1 - ap(t, T[3])), RED, 34)
        if t > T[4] + 0.6:
            d = ImageDraw.Draw(L, "RGBA"); b = min(a, ap(t, T[4] + .6)); y = 1420; p = ease((t - T[4] - .6) / .8)
            d.line([(140, y), (940, y)], fill=A(STEEL2, b), width=14)
            x2, x45 = 140 + 800 * 2 / 5, 140 + 800 * 4.5 / 5
            d.line([(x2, y), (x2 + (x45 - x2) * p, y)], fill=A(GRN2, b), width=22)
            for yr in range(6):
                x = 140 + 800 * yr / 5; d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=A(WHITE, b))
                text_c(d, (x, y + 45), f"{yr} ano" + ("s" if yr != 1 else ""), F("inter700", 26), A(GREY, b))
    a = vis(t, T, 5, 7, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA")
        for i in range(3):
            q = back((t - T[5] - i * .2) / .4)
            if q > 0: check(L, 300 + i * 240, 560, a, True, 80 * q)
        headline(L, "PODE ENTRAR", 820, min(a, ap(t, T[5] + .7)), GRN2, 140)
        if t > T[6]:
            stamp(L, "NÃO É GARANTIDO", W // 2, 1080, back((t - T[6] - .3) / .35), a, RED, 820, 170, 110, -6)
            headline(L, "O BANCO ESCOLHE QUAIS DÍVIDAS OFERECER", 1330, min(a, ap(t, T[6] + 1.2)), WHITE, 62)
    a = vis(t, T, 7, 8, END)
    if a > 0:
        check(L, W // 2, 620, a, False, 100 * max(.01, back((t - T[7]) / .4)))
        headline(L, "RESPONDEU NÃO?", 860, a, WHITE, 100)
        headline(L, "DÁ PRA NEGOCIAR DO MESMO JEITO", 1100, min(a, ap(t, T[7] + .8)), GRN2, 90)

def bill(L, x, y, a, rot=0, w=380, h=170):
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    rr(d, (0, 0, w - 1, h - 1), 14, fill=(46, 140, 88, 255), outline=(30, 100, 60, 255), width=5)
    d.ellipse((w / 2 - 50, h / 2 - 50, w / 2 + 50, h / 2 + 50), outline=(200, 235, 210, 255), width=5)
    text_c(d, (w / 2, h / 2), "R$", F("anton", 50), (220, 245, 228))
    text_c(d, (60, 36), "1.000", F("anton", 30), (220, 245, 228))
    if rot: lay = lay.rotate(rot, expand=True, resample=Image.BICUBIC)
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    L.paste(lay, (int(x - lay.width / 2), int(y - lay.height / 2)), lay)

def scene_V8(L, t, T, END):
    a = vis(t, T, 0, 1, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA"); p = ease((t - T[0]) / 1.2)
        d.arc((W // 2 - 300, 560, W // 2 + 300, 1160), -90, -90 + 324 * p, fill=A(GOLD, a), width=40)
        text_c(d, (W // 2, 860), f"{int(90 * p)}%", F("anton", 230), A(WHITE, a))
        headline(L, "DE ONDE VEM ESSE NÚMERO?", 1330, min(a, ap(t, T[0] + 1.3)), GOLD, 80)
    a = vis(t, T, 1, 3, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA")
        for i, (s, x) in enumerate([("BANCO", 270), ("GOVERNO", 810)]):
            b = min(a, ap(t, T[1] + i * .5))
            d.polygon([(x - 170, 640), (x, 540), (x + 170, 640)], fill=A(STEEL2, b))
            for k in range(4): d.rectangle((x - 140 + k * 80, 660, x - 100 + k * 80, 860), fill=A(EDGE, b))
            d.rectangle((x - 180, 870, x + 180, 900), fill=A(STEEL2, b)); text_c(d, (x, 960), s, F("anton", 60), A(WHITE, b))
        p = ease((t - T[1] - 1.0) / 1.0)
        if p > 0:
            x = 810 - 540 * p; rr(d, (x - 60, 720, x + 60, 800), 12, fill=A(GOLD, a)); text_c(d, (x, 760), "R$", F("anton", 40), A(DARK, a))
            text_c(d, (W // 2, 470), "compra dívidas antigas", F("inter700", 34), A(GREY, a))
        if t > T[2]: stamp(L, "−90% NO MÍNIMO", W // 2, 1200, back((t - T[2]) / .35), a, RED, 820, 180, 120, -5); flash(L, t, T[2], RED)
    a = vis(t, T, 3, 5, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA")
        for k in range(10):
            fly = ease((t - T[3] - 1.0 - k * 0.08) / 0.6) if k > 0 else 0
            x = W // 2 + fly * (600 if k % 2 else -600); y = 1060 - k * 34 - fly * 300
            bill(L, x, y, a * (1 - fly), (k * 7 % 11) - 5 + fly * 40)
        val = 10000 - 9000 * ease((t - T[3] - 1.0) / 1.4)
        text_c(d, (W // 2, 520), M.fmt(val), F("anton", 140), A(RED if val > 1500 else GRN2, a))
        text_c(d, (W // 2, 640), "dívida no papel" if val > 1500 else "o que o banco recebe", F("inter700", 40), A(GREY, a))
        if t > T[4]:
            b = min(a, ap(t, T[4]))
            card(L, (90, 1180, W - 90, 1460), b, fill=(10, 12, 16))
            d.text((140, 1260), "O banco te cobra", font=F("inter700", 42), fill=A(GREY, b), anchor="lm"); d.text((W - 140, 1260), "R$ 10.000", font=F("anton", 64), fill=A(RED, b), anchor="rm")
            d.text((140, 1380), "Mas vende por", font=F("inter700", 42), fill=A(GREY, b), anchor="lm"); d.text((W - 140, 1380), "R$ 1.000", font=F("anton", 64), fill=A(GRN2, b), anchor="rm")
    a = vis(t, T, 5, 7, END)
    if a > 0:
        d = ImageDraw.Draw(L, "RGBA"); base = 1150; p = ease((t - T[5]) / .8); p2 = ease((t - T[6]) / .8)
        rr(d, (210, base - int(80 * p), 450, base), 16, fill=A(GRN, a)); text_c(d, (330, base - 80 * p - 60), "10%", F("anton", 90), A(GRN2, a * p))
        text_c(d, (330, base + 60), "Banco aceita", F("inter700", 40), A(GREY, a))
        if p2 > 0:
            rr(d, (630, base - int(700 * p2), 870, base), 16, fill=A(RED, a)); text_c(d, (750, base - 700 * p2 - 60), "100%", F("anton", 90), A(RED, a * p2))
            text_c(d, (750, base + 60), "Você pagaria?", F("inter700", 40), A(GREY, a))
        headline(L, "POR QUE VOCÊ PAGARIA 100?", 1400, min(a, ap(t, T[6] + .6)), GOLD, 74)
    a = vis(t, T, 7, 9, END)
    if a > 0:
        headline(L, "É POR ISSO QUE DÁ PRA NEGOCIAR", 520, a, WHITE, 88)
        if t > T[8]:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); lg = ImageDraw.Draw(lay); b = min(a, ap(t, T[8]))
            r = int(110 * max(0, back((t - T[8] - .2) / .5)))
            rr(lg, (140, 800, W - 140, 1100), 50, fill=A((6, 8, 10), b), outline=A(GRN2, b), width=6)
            if r > 0:
                lg.ellipse((300 - r, 950 - r, 300 + r, 950 + r), fill=A(GRN, b))
                _orig_text(ImageDraw.Draw(lay), (640, 950), "VALOR ALVO", font=F("anton", 100), fill=A(GRN2, b * (0.8 + 0.2 * math.sin(t * 6))), anchor="mm")
            _g = lay.filter(ImageFilter.GaussianBlur(20)); L.paste(_g, (0, 0), _g); L.paste(lay, (0, 0), lay)

SCENES.update({"V6": scene_V6, "V7": scene_V7, "V8": scene_V8})

if __name__ == "__main__":
    if sys.argv[1] == "still":
        render(sys.argv[2], None, sys.argv[3], None, [float(x) for x in sys.argv[4:]])
    else:
        render(*sys.argv[1:5])
