import json, math, sys, subprocess, re, unicodedata, difflib
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

B = "/tmp/claude-0/-home-claude/345592a4-b47e-591b-b0fb-87c4679cee37/scratchpad"
FT = f"{B}/reels/fonts"
W, H, FPS = 1080, 1920, 30
def F(n, s): return ImageFont.truetype(f"{FT}/{n}.ttf", max(1, int(s)))
BG = (12, 15, 20); STEEL = (34, 40, 50); STEEL2 = (52, 60, 74); EDGE = (82, 92, 110)
GRN = (37, 153, 90); GRN2 = (92, 192, 140); GOLD = (232, 176, 74); RED = (226, 72, 72); WHITE = (245, 246, 248); GREY = (150, 158, 170)

LINES = ["Essa é a máquina do banco.", "Ela transforma 33 mil reais em 90 mil.", "Olha como funciona.",
         "Primeiro, você usa 33 mil reais no cartão.", "Atrasou? Entram juros, multa e IOF.",
         "Aí o banco oferece parcelar a fatura. Mais juros em cima de juros.",
         "No final, o app mostra a proposta: 90 mil reais em 24 vezes.", "Quase 3 vezes o que você usou.",
         "Mas tem um botão que o banco não te mostra: o valor alvo.", "É o que você usou, menos o que você já pagou.",
         "É dele que a negociação parte.", "Quer aprender a desligar essa máquina?",
         "Comenta o nome do banco que você deve, que eu te mando a aula gratuita."]

def norm(w):
    w = unicodedata.normalize("NFD", w.lower()); w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", w)

def align(words):
    """words: [[text,s,e],...] -> start time of each script line (last take wins)."""
    sw = []
    for li, l in enumerate(LINES):
        for w in l.split(): sw.append((norm(w), li))
    tw = [norm(w[0]) for w in words]
    sm = difflib.SequenceMatcher(None, [x[0] for x in sw], tw, autojunk=False)
    starts = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            li = sw[a + k][1]
            if li not in starts or (a + k == 0 or sw[a + k - 1][1] != li): starts.setdefault(li, words[b + k][1])
    T = []
    for li in range(len(LINES)):
        T.append(starts.get(li, T[-1] + 2.0 if T else 0.0))
    for i in range(1, len(T)): T[i] = max(T[i], T[i - 1] + 0.3)
    return T

def ease(x): x = max(0, min(1, x)); return 1 - (1 - x) ** 3
def eio(x): x = max(0, min(1, x)); return x * x * (3 - 2 * x)
def back(x):
    x = max(0, min(1, x)); c1 = 1.70158; c3 = c1 + 1; return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def fmt(v): return "R$ " + f"{int(round(v)):,}".replace(",", ".")

def rr(d, box, r, fill=None, outline=None, width=1): d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)

def text_c(d, xy, s, font, fill, anchor="mm"): d.text(xy, s, font=font, fill=fill, anchor=anchor)

def gear(img, cx, cy, r, ang, col, teeth=10):
    d = ImageDraw.Draw(img); pts = []
    for i in range(teeth * 2):
        a = ang + i * math.pi / teeth; rr_ = r if i % 2 == 0 else r * 0.78
        for da in (-0.12, 0.12):
            pts.append((cx + rr_ * math.cos(a + da), cy + rr_ * math.sin(a + da)))
    d.polygon(pts, fill=col); d.ellipse((cx - r * .32, cy - r * .32, cx + r * .32, cy + r * .32), fill=STEEL)

def glow(img, layer, rad=18, amt=1.0):
    g = layer.filter(ImageFilter.GaussianBlur(rad))
    if amt != 1.0: g = Image.eval(g, lambda v: int(v * amt))
    img.alpha_composite(g); img.alpha_composite(layer)

PRINT = Image.open(f"{B}/provas/ins/app_proposta_itau.jpg").convert("RGBA")
BGIMG = Image.new("RGBA", (W, H), BG + (255,))
_d = ImageDraw.Draw(BGIMG)
for y in range(H):
    k = y / H; _d.line([(0, y), (W, y)], fill=(int(12 + 10 * k), int(15 + 12 * k), int(20 + 16 * k), 255))
for x in range(0, W, 60): _d.line([(x, 0), (x, H)], fill=(255, 255, 255, 10))
for y in range(0, H, 60): _d.line([(0, y), (W, y)], fill=(255, 255, 255, 10))

MX0, MY0, MX1, MY1 = 150, 520, 930, 1230   # machine body

def counter_val(t, T):
    if t < T[3]: return None
    if t < T[4]: return 33000
    if t < T[5]: return 33000 + (52000 - 33000) * ease((t - T[4] - 0.6) / 2.2)
    if t < T[8]: return 52000 + (90000 - 52000) * ease((t - T[5] - 0.4) / 2.5)
    return 90000

def caption_chunks(words):
    ch, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        if len(cur) >= 3 or w[0][-1:] in ".,?:!" or (i + 1 < len(words) and words[i + 1][1] - w[2] > 0.35):
            ch.append(cur); cur = []
    if cur: ch.append(cur)
    return ch

def frame(t, T, words, chunks, END):
    img = BGIMG.copy(); d = ImageDraw.Draw(img)
    on = ease((t - T[0] - 0.1) / 0.8)              # power on
    off = ease((t - T[11] - 0.8) / 0.6)             # switched off
    power = on * (1 - 0.75 * off)
    shake = 0
    if T[4] + 0.3 < t < T[5]: shake = 4 * math.sin(t * 60) * (1 if (t - T[4]) % 1.0 < 0.25 else 0)
    if T[5] + 0.3 < t < T[5] + 2.8: shake = 6 * math.sin(t * 70)
    ox = int(shake)
    speed = 1.0 + (2.5 if T[5] < t < T[8] else 0) - (1.0 if t > T[11] + 0.8 else 0) * 1.0
    # ----- neon sign
    sign = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sign)
    flick = 1.0 if (t - T[0]) > 1.0 else (0.3 if int(t * 14) % 3 == 0 else 1.0)
    a = int(255 * power * flick)
    rr(sd, (MX0 + 40 + ox, 330, MX1 - 40 + ox, 470), 26, outline=GOLD + (a,), width=6)
    text_c(sd, (W // 2 + ox, 400), "MÁQUINA DO BANCO", F("anton", 76), GOLD + (a,))
    glow(img, sign, 22)
    d = ImageDraw.Draw(img)
    # ----- machine body
    rr(d, (MX0 + ox, MY0, MX1 + ox, MY1), 40, fill=STEEL + (255,), outline=EDGE + (255,), width=5)
    for i in range(6): d.line([(MX0 + 30 + ox, MY0 + 330 + i * 18), (MX0 + 230 + ox, MY0 + 330 + i * 18)], fill=STEEL2 + (255,), width=6)
    for i in range(6): d.line([(MX1 - 230 + ox, MY0 + 330 + i * 18), (MX1 - 30 + ox, MY0 + 330 + i * 18)], fill=STEEL2 + (255,), width=6)
    # bolts
    for bx, by in [(MX0 + 30, MY0 + 30), (MX1 - 30, MY0 + 30), (MX0 + 30, MY1 - 30), (MX1 - 30, MY1 - 30)]:
        d.ellipse((bx - 10 + ox, by - 10, bx + 10 + ox, by + 10), fill=EDGE + (255,))
    # display
    dx0, dy0, dx1, dy1 = MX0 + 80 + ox, MY0 + 70, MX1 - 80 + ox, MY0 + 270
    rr(d, (dx0, dy0, dx1, dy1), 24, fill=(6, 8, 10, 255), outline=EDGE + (255,), width=4)
    cv = counter_val(t, T)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    if cv is not None and power > 0.2:
        col = GRN2 if cv < 40000 else (GOLD if cv < 70000 else RED)
        text_c(ld, ((dx0 + dx1) // 2, (dy0 + dy1) // 2 + 8), fmt(cv), F("anton", 120), col + (int(255 * power),))
        text_c(ld, ((dx0 + dx1) // 2, dy0 + 26), "SALDO DA DÍVIDA", F("inter700", 26), GREY + (int(255 * power),))
    elif power > 0.2:
        blink = 255 if int(t * 2) % 2 == 0 else 120
        text_c(ld, ((dx0 + dx1) // 2, (dy0 + dy1) // 2), "LIGADA", F("anton", 90), GRN2 + (int(blink * power),))
    glow(img, lay, 14, 0.8); d = ImageDraw.Draw(img)
    # gears
    ang = t * 1.4 * speed if t < T[11] + 0.8 else (T[11] + 0.8) * 1.4 * 3.5
    gear(img, MX0 + 300 + ox, MY0 + 470, 95, ang, EDGE + (255,), 12)
    gear(img, MX0 + 445 + ox, MY0 + 410, 62, -ang * 1.5 + 0.3, STEEL2 + (255,), 9)
    gear(img, MX1 - 250 + ox, MY0 + 480, 80, ang * 1.2, EDGE + (255,), 11)
    d = ImageDraw.Draw(img)
    # lights row
    for i in range(7):
        lx = MX0 + 150 + i * 80 + ox; ly = MY1 - 70
        lit = power > 0.3 and (int(t * 6) + i) % 3 == 0
        c = (RED if T[5] < t < T[8] else GRN2) if lit else (40, 46, 56)
        d.ellipse((lx - 14, ly - 14, lx + 14, ly + 14), fill=c + (255,))
    # input hopper (left) and output slot (right)
    d.polygon([(MX0 - 10 + ox, MY0 + 560), (MX0 - 120 + ox, MY0 + 470), (MX0 - 120 + ox, MY0 + 640), (MX0 - 10 + ox, MY0 + 620)], fill=STEEL2 + (255,))
    rr(d, (MX1 - 6 + ox, MY0 + 560, MX1 + 40 + ox, MY0 + 640), 8, fill=(6, 8, 10, 255))
    # lever (right)
    lp = ease((t - T[5] - 0.2) / 0.5) if t < T[8] else 1
    la = -0.9 + 1.8 * lp
    lx0, ly0 = MX1 + 10 + ox, MY0 + 230
    lx1, ly1 = lx0 + 110 * math.cos(la), ly0 + 110 * math.sin(la)
    d.line([(lx0, ly0), (lx1, ly1)], fill=EDGE + (255,), width=16); d.ellipse((lx1 - 24, ly1 - 24, lx1 + 24, ly1 + 24), fill=RED + (255,))
    # conveyor
    cy = MY1 + 70
    rr(d, (40, cy - 34, W - 40, cy + 34), 34, fill=(24, 28, 34, 255), outline=EDGE + (255,), width=4)
    off_px = (t * 140 * (0 if t > T[11] + 0.8 else 1)) % 70
    for x in range(-70, W, 70):
        xx = x + off_px
        if 70 < xx < W - 70: d.line([(xx, cy - 20), (xx - 24, cy + 20)], fill=STEEL2 + (255,), width=6)
    for wx in (80, W - 80): d.ellipse((wx - 28, cy - 28, wx + 28, cy + 28), outline=EDGE + (255,), width=5)

    # ===== scene overlays
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    # L1: 33 mil -> 90 mil teaser
    if T[1] - 0.1 < t < T[3]:
        p = ease((t - T[1]) / 0.5); q = ease((t - T[1] - 1.0) / 0.5); fade = 1 - ease((t - T[2] - 0.6) / 0.4)
        a = int(255 * fade)
        rr(od, (110, 1380, 970, 1500), 30, fill=(10, 12, 16, int(225 * p * fade)))
        text_c(od, (330, 1440), "R$ 33 mil", F("anton", 86), GRN2 + (int(a * p),))
        od.polygon([(500,1428),(560,1428),(560,1408),(592,1440),(560,1472),(560,1452),(500,1452)], fill=WHITE + (int(a * q),))
        text_c(od, (750, 1440), "R$ 90 mil", F("anton", 86), RED + (int(a * q),))
    # L3: card on conveyor into hopper
    if T[3] - 0.1 < t < T[4] + 0.4:
        p = eio((t - T[3]) / 1.6)
        x = -260 + (MX0 - 160 + 260) * p; y = MY1 + 70 - 115 - 140 * ease((t - T[3] - 1.6) / 0.5)
        fa = 1 - ease((t - T[3] - 1.9) / 0.4)
        if fa > 0:
            card = Image.new("RGBA", (300, 190), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
            rr(cd, (0, 0, 299, 189), 22, fill=GRN + (255,))
            cd.rectangle((0, 40, 299, 72), fill=(20, 90, 54, 255))
            rr(cd, (24, 92, 74, 132), 8, fill=GOLD + (255,))
            cd.text((24, 145), "R$ 33.000 usados", font=F("inter800", 26), fill=WHITE)
            card.putalpha(Image.eval(card.getchannel("A"), lambda v: int(v * fa)))
            ov.alpha_composite(card, (int(x), int(y)))
        if t > T[3] + 0.2:
            la = int(255 * min(ease((t - T[3] - 0.2) / 0.4), 1 - ease((t - T[4] + 0.2) / 0.3)))
            rr(od, (180, 1400, 900, 1490), 26, fill=(10, 12, 16, int(la * .88)))
            text_c(od, (540, 1445), "Você usou R$ 33 mil", F("inter800", 52), WHITE + (la,))
    # L4: stamps JUROS MULTA IOF
    if T[4] < t < T[5] + 0.6:
        labels = [("JUROS", 0.5), ("MULTA", 1.2), ("IOF", 1.9)]
        for i, (lab, dt) in enumerate(labels):
            p = (t - T[4] - dt)
            if p < 0: continue
            drop = ease(p / 0.45); fade = 1 - ease((p - 0.9) / 0.35)
            if fade <= 0: continue
            x = 270 + i * 270; y = 380 + (MY0 + 520 - 380) * drop if p > 0.45 else 380 + (MY0 + 160 - 380) * drop
            y = 600 + 300 * drop
            tag = Image.new("RGBA", (240, 110), (0, 0, 0, 0)); tg = ImageDraw.Draw(tag)
            rr(tg, (0, 0, 239, 109), 18, fill=RED + (255,)); text_c(tg, (120, 56), lab, F("anton", 64), WHITE)
            tag = tag.rotate((-8 + i * 8), expand=True, resample=Image.BICUBIC)
            tag.putalpha(Image.eval(tag.getchannel("A"), lambda v: int(v * fade)))
            ov.alpha_composite(tag, (int(x - tag.width / 2), int(y - tag.height / 2)))
    # L5: parcelamento tag
    if T[5] + 0.2 < t < T[6]:
        a = int(255 * min(ease((t - T[5] - 0.2) / 0.4), 1 - ease((t - T[6] + 0.3) / 0.3)))
        rr(od, (130, 1390, 950, 1500), 28, fill=RED + (int(a * .95),))
        text_c(od, (540, 1445), "PARCELAR A FATURA = + JUROS", F("anton", 64), WHITE + (a,))
    # L6: print ejected from slot then centered
    if T[6] - 0.1 < t < T[7] + 0.2:
        p = ease((t - T[6]) / 0.5); z = eio((t - T[6] - 0.7) / 0.6)
        fade = 1 - ease((t - T[7]) / 0.25)
        bw = int(220 + (920 - 220) * z); bh = int(bw * PRINT.height / PRINT.width)
        sx = MX1 + 20 + int(80 * p); sy = MY0 + 600
        cx = sx + (W // 2 - sx) * z; cyy = sy + (900 - sy) * z
        im = PRINT.resize((bw, bh), Image.LANCZOS)
        fr = Image.new("RGBA", (bw + 24, bh + 24), WHITE + (255,)); fr.alpha_composite(im, (12, 12))
        fr.putalpha(Image.eval(fr.getchannel("A"), lambda v: int(v * fade)))
        if z > 0: ov.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(170 * z * fade))))
        ov.alpha_composite(fr, (int(cx - fr.width / 2), int(cyy - fr.height / 2)))
        if z > 0.5:
            a = int(255 * min(1, (z - 0.5) * 2) * fade)
            rr(od, (130, 1390, 950, 1500), 28, fill=(10, 12, 16, int(a * .9)))
            text_c(od, (540, 1445), "App: R$ 90 mil em 24x", F("anton", 70), RED + (a,))
            od = ImageDraw.Draw(ov)
    # L7: bars
    if T[7] - 0.05 < t < T[8] + 0.3:
        p = ease((t - T[7]) / 0.8); fade = 1 - ease((t - T[8]) / 0.3)
        ov.alpha_composite(Image.new("RGBA", (W, H), (8, 10, 13, int(230 * min(1, (t - T[7]) * 4) * fade))))
        od = ImageDraw.Draw(ov); a = int(255 * fade); base = 1250
        h1 = int(300 * p); h2 = int(820 * p)
        rr(od, (230, base - h1, 450, base), 18, fill=GRN + (a,)); rr(od, (630, base - h2, 850, base), 18, fill=RED + (a,))
        text_c(od, (340, base + 60), "Você usou", F("inter700", 40), GREY + (a,)); text_c(od, (740, base + 60), "Banco quer", F("inter700", 40), GREY + (a,))
        text_c(od, (340, base - h1 - 50), "R$ 33 mil", F("anton", 64), GRN2 + (a,)); text_c(od, (740, base - h2 - 50), "R$ 90 mil", F("anton", 64), RED + (a,))
        q = back((t - T[7] - 0.6) / 0.5)
        if q > 0: text_c(od, (540, 1420), "QUASE 3x", F("anton", int(40 + 90 * q)), GOLD + (a,))
    # L8: hidden green button
    if T[8] < t < T[11] + 0.6:
        p = ease((t - T[8] - 0.5) / 0.6)
        pulse = 0.75 + 0.25 * math.sin(t * 6)
        fade = 1 - ease((t - T[11]) / 0.5)
        bx, by = W // 2 + ox, MY0 + 470
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); lg = ImageDraw.Draw(layer)
        rr(lg, (bx - 330, by - 120, bx + 330, by + 120), 40, fill=(6, 8, 10, int(240 * p * fade)), outline=GRN2 + (int(255 * p * fade),), width=5)
        r = int(78 * back((t - T[8] - 0.9) / 0.5))
        if r > 0:
            lg.ellipse((bx - 230 - r, by - r, bx - 230 + r, by + r), fill=GRN + (int(255 * fade),), outline=GRN2 + (int(255 * fade),), width=6)
            text_c(lg, (bx + 70, by), "VALOR ALVO", F("anton", 92), GRN2 + (int(255 * pulse * fade),))
        glow(ov, layer, 20); od = ImageDraw.Draw(ov)
    # L9: equation
    if T[9] < t < T[11]:
        fade = 1 - ease((t - T[11] + 0.3) / 0.3)
        a1 = ease((t - T[9]) / 0.4); a2 = ease((t - T[9] - 0.9) / 0.4); a3 = ease((t - T[9] - 1.8) / 0.4)
        rr(od, (70, 1360, 1010, 1520), 30, fill=(10, 12, 16, int(235 * a1 * fade)), outline=GRN + (int(255 * a1 * fade),), width=4)
        text_c(od, (215, 1440), "Usou", F("anton", 70), WHITE + (int(255 * a1 * fade),))
        text_c(od, (360, 1440), "−", F("inter800", 70), GOLD + (int(255 * a2 * fade),))
        text_c(od, (525, 1440), "Já pagou", F("anton", 70), WHITE + (int(255 * a2 * fade),))
        text_c(od, (690, 1440), "=", F("inter800", 70), GOLD + (int(255 * a3 * fade),))
        text_c(od, (850, 1440), "ALVO", F("anton", 76), GRN2 + (int(255 * a3 * fade),))
    # L10: stamp
    if T[10] + 0.2 < t < T[11]:
        q = back((t - T[10] - 0.2) / 0.35); fade = 1 - ease((t - T[11] + 0.2) / 0.2)
        st = Image.new("RGBA", (760, 120), (0, 0, 0, 0)); sdd = ImageDraw.Draw(st)
        rr(sdd, (0, 0, 759, 119), 16, outline=GRN2 + (255,), width=8)
        text_c(sdd, (380, 62), "PONTO DE PARTIDA DA NEGOCIAÇÃO", F("anton", 52), GRN2 + (255,))
        sc = max(0.01, 2.2 - 1.2 * q); st = st.resize((int(760 * sc), int(120 * sc))).rotate(-6, expand=True, resample=Image.BICUBIC)
        st.putalpha(Image.eval(st.getchannel("A"), lambda v: int(v * fade * min(1, q))))
        ov.alpha_composite(st, (W // 2 - st.width // 2, 215 - st.height // 2))
    # L11: switch off
    if T[11] < t < T[12] + 0.3:
        p = ease((t - T[11] - 0.4) / 0.4); fade = 1 - ease((t - T[12]) / 0.3)
        sx, sy = W // 2, 1440
        rr(od, (sx - 200, sy - 70, sx + 200, sy + 70), 70, fill=(10, 12, 16, int(240 * fade)), outline=EDGE + (int(255 * fade),), width=5)
        kx = sx + 120 - 240 * p
        od.ellipse((kx - 58, sy - 58, kx + 58, sy + 58), fill=((GRN if p < 0.5 else RED) + (int(255 * fade),)))
        text_c(od, (sx + (60 if p > 0.5 else -60), sy), "OFF" if p > 0.5 else "ON", F("anton", 56), WHITE + (int(255 * fade),))
    img.alpha_composite(ov)
    # L12: CTA
    if t > T[12] - 0.1:
        p = ease((t - T[12]) / 0.5)
        img.alpha_composite(Image.new("RGBA", (W, H), (8, 10, 13, int(215 * p))))
        d = ImageDraw.Draw(img)
        rr(d, (90, 520, 990, 760), 40, fill=WHITE + (int(255 * p),))
        text_c(d, (540, 600), "Comenta o nome do banco", F("inter800", 58), (17, 20, 26, int(255 * p)))
        text_c(d, (540, 680), "que você deve", F("inter800", 58), (17, 20, 26, int(255 * p)))
        banks = ["Itaú", "Nubank", "Bradesco", "Santander", "BB", "Caixa"]
        for i, bk in enumerate(banks):
            q = back((t - T[12] - 0.5 - i * 0.18) / 0.4)
            if q <= 0: continue
            cx = 230 + (i % 3) * 310; cyy = 880 + (i // 3) * 140
            fnt = F("inter800", 44); tw = d.textlength(bk, font=fnt)
            s = q; w2 = (tw + 70) * s / 2; h2 = 50 * s
            rr(d, (cx - w2, cyy - h2, cx + w2, cyy + h2), int(48 * s), fill=GRN + (255,))
            if s > 0.6: text_c(d, (cx, cyy), bk, F("inter800", int(44 * min(1, s))), WHITE)
        a = int(255 * ease((t - T[12] - 1.8) / 0.5))
        text_c(d, (540, 1210), "e receba a aula gratuita", F("inter700", 50), GOLD + (a,))
        text_c(d, (540, 1300), "@rafaell.financas", F("anton", 64), WHITE + (a,))
        text_c(d, (540, 1380), "Cada caso é um caso.", F("inter500", 34), GREY + (a,))
    d = ImageDraw.Draw(img)
    # title box at start
    if t < T[1] + 0.2:
        a = int(255 * (1 - ease((t - T[1]) / 0.25)))
        fnt = F("inter800", 58)
        rr(d, (110, 150, 970, 290), 26, fill=WHITE + (a,))
        text_c(d, (540, 220), "A máquina do banco", fnt, (17, 20, 26, a))
    # karaoke captions
    if t < T[12] - 0.1:
        for ch in chunks:
            s0 = words[ch[0]][1]; e0 = words[ch[-1]][2] + 0.25
            if s0 - 0.05 <= t <= e0:
                fnt = F("montserrat700", 64); txt = [words[i][0] for i in ch]
                widths = [d.textlength(w + " ", font=fnt) for w in txt]; tot = sum(widths)
                x = (W - tot) / 2; y = 1640
                for i, w, wd in zip(ch, txt, widths):
                    act = words[i][1] - 0.03 <= t <= words[i][2] + 0.08
                    if act:
                        bw = d.textlength(w, font=fnt)
                        rr(d, (x - 12, y - 46, x + bw + 12, y + 50), 14, fill=GOLD + (255,))
                        d.text((x, y), w, font=fnt, fill=(17, 20, 26), anchor="lm")
                    else:
                        d.text((x, y), w, font=fnt, fill=WHITE, anchor="lm", stroke_width=5, stroke_fill=(0, 0, 0))
                    x += wd
                break
    return img.convert("RGB")

def music(dur, sr=48000):
    t = np.arange(int(dur * sr)) / sr; out = np.zeros_like(t)
    bpm = 100; beat = 60 / bpm
    notes = [57, 60, 64, 67, 64, 60, 62, 65]  # hypnotic arp
    for k in range(int(dur / (beat / 2)) + 1):
        t0 = k * beat / 2; n = notes[k % len(notes)]; f = 440 * 2 ** ((n - 69) / 12)
        i0 = int(t0 * sr); L = int(0.45 * sr); seg = np.arange(L) / sr
        env = np.exp(-seg * 7) * (1 - np.exp(-seg * 200))
        tone = (np.sin(2 * np.pi * f * seg) + 0.3 * np.sin(2 * np.pi * 2 * f * seg)) * env * 0.16
        j = min(len(out), i0 + L); out[i0:j] += tone[:j - i0]
    pad = 0.06 * (np.sin(2 * np.pi * 110 * t) + 0.5 * np.sin(2 * np.pi * 164.8 * t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.1 * t))
    kick = np.zeros_like(t)
    for k in range(int(dur / beat) + 1):
        i0 = int(k * beat * sr); L = int(0.25 * sr); seg = np.arange(L) / sr
        s = np.sin(2 * np.pi * (50 + 80 * np.exp(-seg * 30)) * seg) * np.exp(-seg * 14) * 0.35
        j = min(len(kick), i0 + L); kick[i0:j] += s[:j - i0]
    m = out + pad + kick
    return m / np.max(np.abs(m)) * 0.9

def sfx(kind, sr=48000):
    if kind == "whoosh":
        L = int(0.45 * sr); n = np.random.randn(L); env = np.sin(np.linspace(0, np.pi, L)) ** 2
        return np.convolve(n, np.ones(30) / 30, "same") * env * 0.5
    if kind == "thud":
        L = int(0.3 * sr); s = np.arange(L) / sr
        return np.sin(2 * np.pi * (70 + 120 * np.exp(-s * 25)) * s) * np.exp(-s * 12) * 0.8
    if kind == "ding":
        L = int(0.6 * sr); s = np.arange(L) / sr
        return (np.sin(2 * np.pi * 1320 * s) + 0.5 * np.sin(2 * np.pi * 1980 * s)) * np.exp(-s * 6) * 0.35
    if kind == "click":
        L = int(0.05 * sr); s = np.arange(L) / sr
        return np.random.randn(L) * np.exp(-s * 120) * 0.6
    if kind == "pop":
        L = int(0.12 * sr); s = np.arange(L) / sr
        return np.sin(2 * np.pi * (500 + 900 * s * 8) * s) * np.exp(-s * 30) * 0.4

def main(voice_wav, words_json, out):
    import soundfile as sf
    words = json.load(open(words_json))["words"]
    T = align(words); print("T", [round(x, 2) for x in T])
    v, sr = sf.read(voice_wav, dtype="float32")
    if v.ndim > 1: v = v.mean(1)
    END = len(v) / sr + 2.6
    N = int(END * sr); mix = np.zeros(N, np.float32); mix[:len(v)] += v
    m = music(END); mix += (m[:N] * 0.10).astype(np.float32)
    ev = [(T[0], "click"), (T[1] + 1.0, "whoosh"), (T[3], "whoosh"), (T[3] + 1.9, "thud")]
    ev += [(T[4] + dt + 0.45, "thud") for dt in (0.5, 1.2, 1.9)]
    ev += [(T[5] + 0.2, "click"), (T[6], "whoosh"), (T[6] + 0.7, "whoosh"), (T[7] + 0.6, "pop"), (T[8] + 0.9, "ding"),
           (T[9], "pop"), (T[9] + 0.9, "pop"), (T[9] + 1.8, "pop"), (T[10] + 0.3, "thud"), (T[11] + 0.5, "click")]
    ev += [(T[12] + 0.5 + i * 0.18, "pop") for i in range(6)]
    for tt, k in ev:
        s = sfx(k, sr).astype(np.float32) * 0.5; i0 = int(tt * sr); j = min(N, i0 + len(s))
        if i0 < N: mix[i0:j] += s[:j - i0]
    mix = np.clip(mix, -1, 1); sf.write(out + ".wav", mix, sr)
    chunks = caption_chunks(words)
    p = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", out + ".wav", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.5", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(int(END * FPS)):
        p.stdin.write(frame(i / FPS, T, words, chunks, END).tobytes())
    p.stdin.close(); p.wait(); print("ok", out)

if __name__ == "__main__":
    if sys.argv[1] == "still":
        words = json.load(open(sys.argv[2]))["words"]; T = align(words); ch = caption_chunks(words)
        for tt in sys.argv[3:]:
            frame(float(tt), T, words, ch, 60).save(f"{B}/maquina/still_{tt}.png")
    else:
        main(*sys.argv[1:4])
