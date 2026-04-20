import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIG ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor PRO", layout="centered")
st.title("🎯 Corretor Digital PRO")

# -----------------------------
# 📐 FUNÇÕES
# -----------------------------
def ordenar_pontos(pts):
    pts = pts.reshape(4, 2)
    soma = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    return np.array([
        pts[np.argmin(soma)],
        pts[np.argmin(diff)],
        pts[np.argmax(soma)],
        pts[np.argmax(diff)]
    ], dtype="float32")

def corrigir_perspectiva(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edged = cv2.Canny(blur, 50, 150)

    cnts, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    for c in cnts[:5]:
        peri = cv2.arcLength(c, True)
        aprox = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(aprox) == 4:
            pts = ordenar_pontos(aprox)

            largura = int(max(
                np.linalg.norm(pts[2] - pts[3]),
                np.linalg.norm(pts[1] - pts[0])
            ))
            altura = int(max(
                np.linalg.norm(pts[1] - pts[2]),
                np.linalg.norm(pts[0] - pts[3])
            ))

            if largura < 500 or altura < 800:
                continue

            destino = np.array([
                [0, 0],
                [largura-1, 0],
                [largura-1, altura-1],
                [0, altura-1]
            ], dtype="float32")

            M = cv2.getPerspectiveTransform(pts, destino)
            return cv2.warpPerspective(img, M, (largura, altura))

    return img

# -----------------------------
# 📤 INPUT (UPLOAD ROBUSTO)
# -----------------------------
if "img_bytes" not in st.session_state:
    st.session_state.img_bytes = None

nome_aluno = st.text_input("Nome do Aluno")

foto_upload = st.file_uploader(
    "Envie a FOTO do gabarito",
    type=["jpg", "jpeg", "png"],
    key="uploader"
)

if st.button("🔄 Limpar"):
    st.session_state.img_bytes = None
    st.rerun()

# salva imagem só uma vez
if foto_upload is not None and st.session_state.img_bytes is None:
    st.session_state.img_bytes = foto_upload.read()

# -----------------------------
# 🔄 PROCESSAMENTO
# -----------------------------
if st.session_state.img_bytes is not None and nome_aluno:

    file_bytes = np.asarray(bytearray(st.session_state.img_bytes), dtype=np.uint8)

    if len(file_bytes) < 1000:
        st.error("Imagem inválida.")
        st.stop()

    img = cv2.imdecode(file_bytes, 1)

    if img is None:
        st.error("Erro ao ler imagem.")
        st.stop()

    # 🔧 NORMALIZAÇÃO
    max_lado = 1200
    h, w = img.shape[:2]

    if max(h, w) > max_lado:
        scale = max_lado / max(h, w)
        img = cv2.resize(img, (0, 0), fx=scale, fy=scale)

    # corrige rotação básica
    if h > w:
        pass
    else:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

    st.image(img, caption="Imagem carregada")

    # perspectiva
    img = corrigir_perspectiva(img)

    img = cv2.resize(img, (1000, 1400))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # threshold inteligente
    _, thresh = cv2.threshold(gray, 0, 255,
                              cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    if np.mean(thresh) < 15:
        thresh = cv2.adaptiveThreshold(gray, 255,
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 21, 5)

    thresh = cv2.GaussianBlur(thresh, (5,5), 0)

    st.image(thresh, caption="Threshold")

    # -----------------------------
    # 🔍 DETECTAR BOLINHAS
    # -----------------------------
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bolhas = []

    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)

        if 15 < w < 80 and 15 < h < 80:
            if 0.7 < w/h < 1.3:
                bolhas.append((x, y, w, h))

    # debug
    debug = img.copy()
    for (x,y,w,h) in bolhas:
        cv2.rectangle(debug, (x,y), (x+w,y+h), (255,0,0), 1)

    st.image(debug, caption="Bolinhas detectadas")

    # -----------------------------
    # 🧠 AGRUPAR EM LINHAS
    # -----------------------------
    bolhas = sorted(bolhas, key=lambda x: x[1])

    linhas = []
    linha_atual = []

    for b in bolhas:
        if not linha_atual:
            linha_atual.append(b)
            continue

        if abs(b[1] - linha_atual[0][1]) < 20:
            linha_atual.append(b)
        else:
            linhas.append(linha_atual)
            linha_atual = [b]

    if linha_atual:
        linhas.append(linha_atual)

    # -----------------------------
    # 🎯 LER RESPOSTAS
    # -----------------------------
    respostas_finais = {}
    OPCOES = ['A', 'B', 'C', 'D', 'E']

    for i, linha in enumerate(linhas[:90]):
        linha = sorted(linha, key=lambda x: x[0])

        valores = []

        for (x, y, w, h) in linha[:5]:
            bolha = thresh[y:y+h, x:x+w]
            valores.append(cv2.countNonZero(bolha))

        if len(valores) < 5:
            respostas_finais[i+1] = "X"
            continue

        v = sorted(valores, reverse=True)
        p1, p2 = v[0], v[1]

        if p1 < 20:
            respostas_finais[i+1] = "X"
        elif (p1 - p2) > (p1 * 0.2):
            respostas_finais[i+1] = OPCOES[np.argmax(valores)]
        else:
            respostas_finais[i+1] = "X"

    # -----------------------------
    # 📊 RESULTADO
    # -----------------------------
    resultado_str = "".join([respostas_finais.get(q, "X") for q in range(1, 91)])

    st.write(f"**Nome:** {nome_aluno}")
    st.write(f"**Respostas:** {resultado_str}")

    if st.button("ENVIAR"):
        requests.post(FORM_URL, data={
            ID_NOME: nome_aluno,
            ID_RESPOSTAS: resultado_str
        })
        st.success("Enviado com sucesso!")
        st.balloons()
