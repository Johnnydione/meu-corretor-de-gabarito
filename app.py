import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor 90Q", layout="centered")
st.title("🎯 Corretor Digital")

# -----------------------------
# INPUT
# -----------------------------
if "img_bytes" not in st.session_state:
    st.session_state.img_bytes = None

nome_aluno = st.text_input("Nome do Aluno")
foto_upload = st.file_uploader("Envie a FOTO", type=['jpg','jpeg','png'])

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

    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        21, 5
    )

    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    colunas = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w > 80 and h > 400:
            colunas.append((x, y, w, h))

    colunas = sorted(colunas, key=lambda x: x[0])[:3]

    if len(colunas) == 3:

        respostas_finais = {}
        OPCOES = ['A','B','C','D','E']

        for i, (x, y, w, h) in enumerate(colunas):

            # 🔥 AJUSTE FINO AUTOMÁTICO (ESSA É A CORREÇÃO)
            melhor_x = x
            melhor_score = 0

            for dx in range(-15, 16, 3):
                x_teste = x + dx
                roi_teste = thresh[y:y+h, x_teste:x_teste+w]

                score = np.sum(roi_teste)

                if score > melhor_score:
                    melhor_score = score
                    melhor_x = x_teste

            x = melhor_x

            # corte corrigido
            roi_col = thresh[y+5:y+h-5, x+5:x+w-5]

            h_roi, w_roi = roi_col.shape
            start_q = [1, 31, 61][i]

            for q_idx in range(30):
                q_num = start_q + q_idx

                y1 = int(q_idx * (h_roi / 30))
                y2 = int((q_idx + 1) * (h_roi / 30))

                fatia = roi_col[y1:y2, :]
                fatias = np.array_split(fatia, 5, axis=1)

                pixels = []

                for f in fatias:
                    hf, wf = f.shape
                    miolo = f[int(hf*0.1):int(hf*0.9),
                              int(wf*0.1):int(wf*0.9)]
                    pixels.append(cv2.countNonZero(miolo))

                v_ord = sorted(pixels, reverse=True)
                p1, p2 = v_ord[0], v_ord[1]

                if p1 < 10:
                    respostas_finais[q_num] = "X"
                elif (p1 - p2) > (p1 * 0.3):
                    respostas_finais[q_num] = OPCOES[np.argmax(pixels)]
                else:
                    respostas_finais[q_num] = "X"

        st.image(img_viz)

        resultado_str = "".join([
            respostas_finais.get(q, "X") for q in range(1, 91)
        ])

        st.write(f"**Nome:** {nome_aluno}")
        st.write(f"**Respostas:** {resultado_str}")

        if st.button("ENVIAR"):
            requests.post(FORM_URL, data={
                ID_NOME: nome_aluno,
                ID_RESPOSTAS: resultado_str
            })
            st.success("Enviado com sucesso!")
            st.balloons()

    else:
        st.error(f"Erro: Encontradas {len(colunas)} colunas")
