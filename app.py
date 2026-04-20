import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIG ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor Scanner", layout="centered")
st.title("📄 Corretor estilo Scanner")

# -----------------------------
# 📐 FUNÇÃO SCANNER REAL
# -----------------------------
def escanear_folha(img):

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)

    edged = cv2.Canny(blur, 50, 150)

    cnts, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    folha = None

    for c in cnts[:10]:
        peri = cv2.arcLength(c, True)
        aprox = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(aprox) == 4:
            folha = aprox
            break

    if folha is None:
        return img

    pts = folha.reshape(4,2)

    soma = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    tl = pts[np.argmin(soma)]
    br = pts[np.argmax(soma)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]

    largura = int(max(
        np.linalg.norm(br-bl),
        np.linalg.norm(tr-tl)
    ))

    altura = int(max(
        np.linalg.norm(tr-br),
        np.linalg.norm(tl-bl)
    ))

    destino = np.array([
        [0,0],
        [largura-1,0],
        [largura-1,altura-1],
        [0,altura-1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(
        np.array([tl,tr,br,bl], dtype="float32"),
        destino
    )

    warp = cv2.warpPerspective(img, M, (largura, altura))

    return warp

# -----------------------------
# 📤 INPUT
# -----------------------------
if "img_bytes" not in st.session_state:
    st.session_state.img_bytes = None

nome = st.text_input("Nome")

foto = st.file_uploader("Envie a imagem", type=["jpg","png","jpeg"])

if st.button("Limpar"):
    st.session_state.img_bytes = None
    st.rerun()

if foto is not None and st.session_state.img_bytes is None:
    st.session_state.img_bytes = foto.read()

# -----------------------------
# 🔄 PROCESSAMENTO
# -----------------------------
if st.session_state.img_bytes is not None and nome:

    file_bytes = np.asarray(bytearray(st.session_state.img_bytes), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)

    # resize leve
    h, w = img.shape[:2]
    if max(h,w) > 1500:
        scale = 1500/max(h,w)
        img = cv2.resize(img,(0,0),fx=scale,fy=scale)

    st.image(img, caption="Original")

    # 🔥 SCANNER
    scan = escanear_folha(img)

    # normaliza tamanho fixo
    scan = cv2.resize(scan, (1000, 1400))

    st.image(scan, caption="Scan corrigido")

    gray = cv2.cvtColor(scan, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(gray, 0,255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    st.image(thresh, caption="Threshold")

    # -----------------------------
    # 🔍 DETECTAR COLUNAS
    # -----------------------------
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    colunas = []
    for c in cnts:
        x,y,w,h = cv2.boundingRect(c)

        if h > 600 and w > 150:
            colunas.append((x,y,w,h))

    colunas = sorted(colunas, key=lambda x: x[0])[:3]

    debug = scan.copy()
    for (x,y,w,h) in colunas:
        cv2.rectangle(debug,(x,y),(x+w,y+h),(0,255,0),3)

    st.image(debug, caption="Colunas")

    # -----------------------------
    # 🎯 LEITURA SIMPLES (AGORA FUNCIONA)
    # -----------------------------
    respostas = {}
    OPCOES = ['A','B','C','D','E']

    if len(colunas) == 3:

        for i,(x,y,w,h) in enumerate(colunas):

            roi = thresh[y:y+h, x:x+w]

            for q in range(30):
                q_num = i*30 + q + 1

                y1 = int(q * h / 30)
                y2 = int((q+1) * h / 30)

                linha = roi[y1:y2, :]
                alternativas = np.array_split(linha, 5, axis=1)

                valores = [cv2.countNonZero(a) for a in alternativas]

                v = sorted(valores, reverse=True)
                p1, p2 = v[0], v[1]

                if p1 < 20:
                    respostas[q_num] = "X"
                elif (p1 - p2) > (p1 * 0.2):
                    respostas[q_num] = OPCOES[np.argmax(valores)]
                else:
                    respostas[q_num] = "X"

        resultado = "".join([respostas.get(i,"X") for i in range(1,91)])

        st.write("Resultado:")
        st.write(resultado)

        if st.button("ENVIAR"):
            requests.post(FORM_URL, data={
                ID_NOME: nome,
                ID_RESPOSTAS: resultado
            })
            st.success("Enviado!")

    else:
        st.error("Não detectei as 3 colunas")
