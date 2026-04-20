import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor Inteligente 90Q", layout="centered")

st.title("🎯 Corretor Digital Pro")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Tire a foto ou escolha o arquivo", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    h, w = img.shape[:2]
    if w > h: img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    quadrados = [c for c in cnts if cv2.contourArea(c) > 400]

    if len(quadrados) >= 4:
        all_pts = np.concatenate(quadrados)
        x, y, w_box, h_box = cv2.boundingRect(all_pts)
        
        # VOLTAMOS PARA OS SEUS NÚMEROS MÁGICOS
        offset_y = int(h_box * 0.052) 
        offset_x = int(w_box * 0.035) 
        
        x_f, y_f = x + offset_x, y + offset_y
        w_f, h_f = w_box - (2 * offset_x), h_box - (2 * offset_y)

        roi_thresh = thresh[y_f:y_f+h_f, x_f:x_f+w_f]
        img_viz_roi = img_viz[y_f:y_f+h_f, x_f:x_f+w_f]
        cv2.rectangle(img_viz, (x_f, y_f), (x_f+w_f, y_f+h_f), (255, 0, 0), 3)

        alt_roi, larg_roi = roi_thresh.shape
        w_col = larg_roi // 3
        h_row = alt_roi // 30
        
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']
        
        for c_idx in range(3):
            start_q = (c_idx * 30) + 1
            for q_idx in range(30):
                q_num = start_q + q_idx
                y1, y2 = q_idx * h_row, (q_idx + 1) * h_row
                x_base = c_idx * w_col
                
                # Desenha a grade verde de conferência
                cv2.line(img_viz_roi, (x_base, y1), (x_base + w_col, y1), (0, 255, 0), 1)
                
                # Pega a linha da questão
                linha_q = roi_thresh[y1:y2, x_base:x_base+w_col]
                
                # DIVISÃO EM 5 ALTERNATIVAS
                alternativas = np.array_split(linha_q, 5, axis=1)
                pixels = []
                for alt in alternativas:
                    # O PULO DO GATO: Em cada alternativa, ignoramos as bordas
                    # Pegamos apenas o centro (40% a 60%) para não ler a letra A,B,C...
                    ha, wa = alt.shape
                    centro = alt[int(ha*0.25):int(ha*0.75), int(wa*0.25):int(wa*0.75)]
                    pixels.append(cv2.countNonZero(centro))
                
                p_ord = sorted(pixels, reverse=True)
                # Como a área é menor, o número de pixels cai. Ajustei os limites:
                if p_ord[0] < 10: 
                    respostas_finais[q_num] = "BRANCO"
                elif (p_ord[0] - p_ord[1]) < 8:
                    respostas_finais[q_num] = "DUPLA"
                else:
                    respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

        st.subheader("3. Conferência")
        st.image(img_viz, use_container_width=True)
        resultado_str = ", ".join([respostas_finais[q] for q in range(1, 91)])
        st.write(f"**Lido:** {resultado_str[:120]}...")

        if st.button("ENVIAR"):
            requests.post(FORM_URL, data={ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str})
            st.balloons()
