import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/e/1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ/formResponse"

st.set_page_config(page_title="Corretor 90Q Final", layout="centered")
st.title("🎯 Corretor Digital Pro")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Envie o gabarito", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    
    # 1. Processamento simples e direto
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Threshold bem limpo para imagens digitais
    thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)[1]

    # 2. Localizar as Colunas (Sem filtros que apagam tudo)
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    colunas_encontradas = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        # Filtro: largura mínima de 100px e altura mínima de 500px
        # Isso ignora números e logos, mas pega os retângulos
        if w > 100 and h > 500:
            colunas_encontradas.append((x, y, w, h))

    # Ordenar da esquerda para a direita
    colunas_encontradas = sorted(colunas_encontradas, key=lambda x: x[0])[:3]

    if len(colunas_encontradas) == 3:
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']

        for i, (x, y, w, h) in enumerate(colunas_encontradas):
            # Desenha em azul para confirmar a detecção
            cv2.rectangle(img_viz, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Recorte interno da coluna (encolhe 4px para ignorar a borda preta)
            roi_col = thresh[y+4:y+h-4, x+4:x+w-4]
            h_roi, w_roi = roi_col.shape
            
            start_q = [1, 31, 61][i]

            for q_idx in range(30):
                q_num = start_q + q_idx
                y1 = int(q_idx * (h_roi / 30))
                y2 = int((q_idx + 1) * (h_roi / 30))
                
                fatia = roi_col[y1:y2, :]
                
                # Divide em 5 partes
                fatias = np.array_split(fatia, 5, axis=1)
                pixels = []
                for f in fatias:
                    hf, wf = f.shape
                    # Pega o miolo (centro da bolinha)
                    miolo = f[int(hf*0.2):int(hf*0.8), int(wf*0.2):int(wf*0.8)]
                    pixels.append(cv2.countNonZero(miolo))
                
                # --- LÓGICA DE DECISÃO ---
                v_ord = sorted(pixels, reverse=True)
                p1, p2 = v_ord[0], v_ord[1]
                
                if p1 < 5: 
                    respostas_finais[q_num] = "BRANCO"
                elif (p1 - p2) < (p1 * 0.35): # Se a diferença for pequena, é dupla
                    respostas_finais[q_num] = "DUPLA"
                else:
                    respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

        st.image(img_viz)
        resultado_str = ", ".join([respostas_finais.get(q, "BRANCO") for q in range(1, 91)])
        st.write(f"**Resultado:** {resultado_str[:200]}...")

        if st.button("ENVIAR"):
            requests.post(FORM_URL, data={ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str})
            st.balloons()
            st.success("Enviado!")
    else:
        st.error(f"Detectadas {len(colunas_encontradas)} colunas. Certifique-se de que as linhas dos retângulos no Canva não são muito finas ou claras.")
