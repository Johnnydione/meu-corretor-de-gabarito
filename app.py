import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor 90Q Precision", layout="centered")
st.title("🎯 Corretor Digital Pro")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Envie o gabarito", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Threshold mais rigoroso para separar bem as linhas pretas do fundo
    thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)[1]

    # MUDANÇA AQUI: Usamos RETR_LIST para pegar todos os contornos e filtramos por formato
    cnts, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    colunas_cnts = []
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        area = cv2.contourArea(c)
        
        # Filtramos contornos que tenham formato de retângulo alto (área grande e 4 pontos)
        if area > 50000 and len(approx) == 4:
            colunas_cnts.append(c)

    # Ordenar da esquerda para a direita e pegar os 3 maiores
    colunas_cnts = sorted(colunas_cnts, key=lambda c: cv2.boundingRect(c)[0])[:3]

    if len(colunas_cnts) == 3:
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']
        
        for i, col_cnt in enumerate(colunas_cnts):
            x, y, w, h = cv2.boundingRect(col_cnt)
            # REFINAMENTO: Encolhemos 2 pixels de cada lado para garantir que não pegamos a borda preta
            x, y, w, h = x+2, y+2, w-4, h-4
            
            cv2.rectangle(img_viz, (x, y), (x+w, y+h), (0, 0, 255), 2)
            roi_col = thresh[y:y+h, x:x+w]
            start_q = [1, 31, 61][i]
            
            for q_idx in range(30):
                q_num = start_q + q_idx
                y1 = int(q_idx * (h / 30))
                y2 = int((q_idx + 1) * (h / 30))
                
                linha = roi_col[y1:y2, :]
                h_l, w_l = linha.shape
                
                # Dividir a coluna interna em 5 partes exatas
                fatias = np.array_split(linha, 5, axis=1)
                pixels = []
                for fatia in fatias:
                    hf, wf = fatia.shape
                    # Pegamos apenas o miolo (60% central) para fugir de qualquer ruído
                    miolo = fatia[int(hf*0.2):int(hf*0.8), int(wf*0.2):int(wf*0.8)]
                    pixels.append(cv2.countNonZero(miolo))
                
                p_ord = sorted(pixels, reverse=True)
                if p_ord[0] < 15: respostas_finais[q_num] = "BRANCO"
                elif (p_ord[0] - p_ord[1]) < 10: respostas_finais[q_num] = "DUPLA"
                else: respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

        st.image(img_viz, caption="Agora os retângulos devem estar internos às linhas pretas.")
        
        resultado_str = ", ".join([respostas_finais.get(q, "BRANCO") for q in range(1, 91)])
        st.write(f"**Gabarito Lido:** {resultado_str[:150]}...")

        if st.button("ENVIAR PARA GOOGLE SHEETS"):
            requests.post(FORM_URL, data={ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str})
            st.balloons()
            st.success("Enviado!")
    else:
        st.error(f"Detectei {len(colunas_cnts)} colunas. Garanta que os retângulos do Canva apareçam inteiros.")
