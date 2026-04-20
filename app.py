import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor 90Q - Final", layout="centered")
st.title("🎯 Corretor Digital Pro")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Envie o gabarito", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Threshold para ignorar o cinza das bolinhas vazias e pegar só o preto forte
    thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)[1]

    # Localizar as Colunas
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    colunas_encontradas = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w > 100 and h > 500:
            colunas_encontradas.append((x, y, w, h))

    colunas_encontradas = sorted(colunas_encontradas, key=lambda x: x[0])[:3]

    if len(colunas_encontradas) == 3:
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']

        for i, (x, y, w, h) in enumerate(colunas_encontradas):
            cv2.rectangle(img_viz, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Margem interna para ignorar a borda do retângulo
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
                    # Pega o centro absoluto da bolinha
                    miolo = f[int(hf*0.3):int(hf*0.7), int(wf*0.3):int(wf*0.7)]
                    pixels.append(cv2.countNonZero(miolo))
                
                # --- LÓGICA UNIFICADA ---
                v_ord = sorted(pixels, reverse=True)
                p1, p2 = v_ord[0], v_ord[1]
                
                # Se o "mais votado" for muito baixo -> Branco (X)
                # Se a diferença entre o 1º e o 2º for pequena -> Dupla (X)
                if p1 < 8 or (p1 - p2) < (p1 * 0.4):
                    respostas_finais[q_num] = "X"
                else:
                    respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

        st.image(img_viz)
        resultado_str = ", ".join([respostas_finais.get(q, "X") for q in range(1, 91)])
        st.write(f"**Resultado Lido:** {resultado_str[:200]}...")

        if st.button("ENVIAR GABARITO"):
            requests.post(FORM_URL, data={ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str})
            st.balloons()
            st.success("Enviado com sucesso!")
    else:
        st.error(f"Detectadas {len(colunas_encontradas)} colunas. Ajuste o enquadramento.")
