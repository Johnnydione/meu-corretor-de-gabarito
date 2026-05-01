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
st.title("📄 Corretor Inteligente (nível scanner)")

# -----------------------------
# INPUT
# -----------------------------
if "img_bytes" not in st.session_state:
    st.session_state.img_bytes = None

nome_aluno = st.text_input("Nome do Aluno")
foto_upload = st.file_uploader("Envie a FOTO", type=['jpg','jpeg','png'])

if foto_upload is not None:
    st.session_state.img_bytes = foto_upload.read()

# -----------------------------
# PROCESSAMENTO
# -----------------------------
if st.session_state.img_bytes and nome_aluno:

    file_bytes = np.asarray(bytearray(st.session_state.img_bytes), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)

    img = cv2.resize(img, (1000, 1400))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # -----------------------------
    # DETECTAR BOLINHAS (CÍRCULOS)
    # -----------------------------
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=50,
        param1=100,
        param2=30,
        minRadius=8,
        maxRadius=25
    )

    if circles is None:
        st.error("Não detectei as bolinhas de referência 😢")
        st.stop()

    circles = np.round(circles[0, :]).astype("int")

    # pega centros
    pontos = np.array([[x, y] for (x, y, r) in circles])

    # -----------------------------
    # ENCONTRAR OS 4 CANTOS
    # -----------------------------
    soma = pontos.sum(axis=1)
    diff = np.diff(pontos, axis=1)

    topo_esq = pontos[np.argmin(soma)]
    baixo_dir = pontos[np.argmax(soma)]
    topo_dir = pontos[np.argmin(diff)]
    baixo_esq = pontos[np.argmax(diff)]

    pts1 = np.float32([topo_esq, topo_dir, baixo_esq, baixo_dir])

    largura = 800
    altura = 1200

    pts2 = np.float32([
        [0,0],
        [largura,0],
        [0,altura],
        [largura,altura]
    ])

    # -----------------------------
    # CORRIGIR PERSPECTIVA
    # -----------------------------
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    warp = cv2.warpPerspective(img, matrix, (largura, altura))

    gray_warp = cv2.cvtColor(warp, cv2.COLOR_BGR2GRAY)

    thresh = cv2.adaptiveThreshold(
        gray_warp, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        25, 5
    )

    # -----------------------------
    # ÁREA DO GABARITO (AJUSTÁVEL)
    # -----------------------------
    roi = thresh[200:1100, 100:700]

    h, w = roi.shape

    QUESTOES = 90
    COLUNAS = 3
    OPCOES = ['A','B','C','D','E']

    respostas = {}

    quest_por_col = int(QUESTOES / COLUNAS)

    col_width = w // COLUNAS

    for c in range(COLUNAS):
        x1 = c * col_width
        x2 = (c + 1) * col_width

        col = roi[:, x1:x2]

        for q in range(quest_por_col):
            q_num = c * quest_por_col + q + 1

            y1 = int(q * (h / quest_por_col))
            y2 = int((q + 1) * (h / quest_por_col))

            linha = col[y1:y2, :]

            alternativas = np.array_split(linha, 5, axis=1)

            pixels = []

            for alt in alternativas:
                h_a, w_a = alt.shape
                miolo = alt[int(h_a*0.2):int(h_a*0.8),
                            int(w_a*0.2):int(w_a*0.8)]
                pixels.append(cv2.countNonZero(miolo))

            v = sorted(pixels, reverse=True)
            p1, p2 = v[0], v[1]

            if p1 < 40:
                respostas[q_num] = "X"
            elif (p1 - p2) > (p1 * 0.2):
                respostas[q_num] = OPCOES[np.argmax(pixels)]
            else:
                respostas[q_num] = "X"

    resultado = "".join([respostas.get(i, "X") for i in range(1, 91)])

    st.image(warp, caption="Gabarito corrigido")

    st.write(f"**Nome:** {nome_aluno}")
    st.write(f"**Respostas:** {resultado}")

    if st.button("ENVIAR"):
        requests.post(FORM_URL, data={
            ID_NOME: nome_aluno,
            ID_RESPOSTAS: resultado
        })
        st.success("Enviado com sucesso!")
