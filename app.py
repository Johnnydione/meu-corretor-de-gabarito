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
st.title("🎯 Corretor Digital PRO (Estável)")

# -----------------------------
# 📤 INPUT ROBUSTO
# -----------------------------
if "img_bytes" not in st.session_state:
    st.session_state.img_bytes = None

nome = st.text_input("Nome")

foto = st.file_uploader("Envie a imagem", type=["jpg","jpeg","png"])

if st.button("🔄 Limpar"):
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

    if img is None:
        st.error("Erro ao ler imagem")
        st.stop()

    # resize padrão
    img = cv2.resize(img, (1000, 1400))

    st.image(img, caption="Imagem normalizada")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # threshold robusto
    _, thresh = cv2.threshold(gray, 0,255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    st.image(thresh, caption="Threshold")

    # -----------------------------
    # 🎯 POSIÇÃO APROXIMADA DAS COLUNAS
    # -----------------------------
    colunas_x = [150, 450, 750]  # posições base

    respostas = {}
    OPCOES = ['A','B','C','D','E']

    # -----------------------------
    # 🔥 AJUSTE AUTOMÁTICO (SCAN LOCAL)
    # -----------------------------
    for i, x_base in enumerate(colunas_x):

        # busca melhor posição horizontal
        melhor_x = x_base
        melhor_score = 0

        for dx in range(-40, 41, 5):
            x = x_base + dx
            roi = thresh[:, x:x+150]

            score = np.sum(roi)

            if score > melhor_score:
                melhor_score = score
                melhor_x = x

        x = melhor_x

        # agora leitura normal
        for q in range(30):
            q_num = i*30 + q + 1

            y1 = int(q * 1400 / 30)
            y2 = int((q+1) * 1400 / 30)

            linha = thresh[y1:y2, x:x+150]

            alternativas = np.array_split(linha, 5, axis=1)

            valores = []

            for alt in alternativas:
                h, w = alt.shape

                miolo = alt[
                    int(h*0.3):int(h*0.7),
                    int(w*0.3):int(w*0.7)
                ]

                valores.append(cv2.countNonZero(miolo))

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
        st.balloons()
