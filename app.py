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
# INPUT
# -----------------------------
if "img_bytes" not in st.session_state:
    st.session_state.img_bytes = None

nome_aluno = st.text_input("Nome do Aluno")

foto_upload = st.file_uploader("Envie a FOTO", type=["jpg","jpeg","png"])

if st.button("🔄 Limpar"):
    st.session_state.img_bytes = None
    st.rerun()

if foto_upload is not None and st.session_state.img_bytes is None:
    st.session_state.img_bytes = foto_upload.read()

# -----------------------------
# PROCESSAMENTO
# -----------------------------
if st.session_state.img_bytes is not None and nome_aluno:

    file_bytes = np.asarray(bytearray(st.session_state.img_bytes), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)

    if img is None:
        st.error("Erro ao ler imagem")
        st.stop()

    # resize
    h, w = img.shape[:2]
    if max(h,w) > 1200:
        scale = 1200 / max(h,w)
        img = cv2.resize(img, (0,0), fx=scale, fy=scale)

    st.image(img, caption="Original")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # threshold
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

    # -----------------------------
    # DETECTAR COLUNAS
    # -----------------------------
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    colunas = []
    for c in cnts:
        x,y,w,h = cv2.boundingRect(c)
        if h > 500 and w > 150:
            colunas.append((x,y,w,h))

    colunas = sorted(colunas, key=lambda x: x[0])[:3]

    debug = img.copy()
    for (x,y,w,h) in colunas:
        cv2.rectangle(debug,(x,y),(x+w,y+h),(0,255,0),3)

    st.image(debug, caption="Colunas")

    respostas_finais = {}
    OPCOES = ['A','B','C','D','E']

    # -----------------------------
    # LEITURA INTELIGENTE
    # -----------------------------
    if len(colunas) == 3:

        for i,(x,y,w,h) in enumerate(colunas):

            roi = gray[y:y+h, x:x+w]

            # threshold local
            _, roi_thresh = cv2.threshold(
                roi, 0,255,
                cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

            # 🔥 SOMA HORIZONTAL (detecta linhas reais)
            soma_linhas = np.sum(roi_thresh, axis=1)

            # normaliza
            soma_linhas = soma_linhas / np.max(soma_linhas)

            # encontra picos (linhas)
            linhas_idx = np.where(soma_linhas > 0.5)[0]

            # agrupar linhas próximas
            linhas = []
            atual = []

            for idx in linhas_idx:
                if not atual:
                    atual.append(idx)
                    continue

                if idx - atual[-1] < 5:
                    atual.append(idx)
                else:
                    linhas.append(atual)
                    atual = [idx]

            if atual:
                linhas.append(atual)

            # pega centro de cada linha
            centros = [int(np.mean(l)) for l in linhas]

            # limitar a 30 questões
            centros = centros[:30]

            for q, cy in enumerate(centros):
                q_num = i*30 + q + 1

                y1 = max(cy-10,0)
                y2 = min(cy+10, roi.shape[0])

                faixa = roi_thresh[y1:y2, :]

                alternativas = np.array_split(faixa, 5, axis=1)

                valores = []

                for alt in alternativas:
                    h_alt, w_alt = alt.shape

                    miolo = alt[
                        int(h_alt*0.3):int(h_alt*0.7),
                        int(w_alt*0.3):int(w_alt*0.7)
                    ]

                    valores.append(cv2.countNonZero(miolo))

                v = sorted(valores, reverse=True)
                p1, p2 = v[0], v[1]

                if p1 < 20:
                    respostas_finais[q_num] = "X"
                elif (p1 - p2) > (p1 * 0.2):
                    respostas_finais[q_num] = OPCOES[np.argmax(valores)]
                else:
                    respostas_finais[q_num] = "X"

        resultado = "".join([respostas_finais.get(i,"X") for i in range(1,91)])

        st.write(f"**Nome:** {nome_aluno}")
        st.write(f"**Respostas:** {resultado}")

        if st.button("ENVIAR"):
            requests.post(FORM_URL, data={
                ID_NOME: nome_aluno,
                ID_RESPOSTAS: resultado
            })
            st.success("Enviado!")
            st.balloons()

    else:
        st.error("Não detectei 3 colunas")
