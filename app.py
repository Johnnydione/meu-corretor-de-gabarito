import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor 90Q Precision", layout="centered")

st.title("🎯 Corretor Digital Pro")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Envie a foto", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    # 1. Ajuste de Orientação e Resize fixo
    h, w = img.shape[:2]
    if w > h: img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    
    # 2. Processamento
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 100, 255, cv2.THRESH_BINARY_INV)[1]

    # 3. Localizar Âncoras
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted([c for c in cnts if cv2.contourArea(c) > 400], key=cv2.contourArea, reverse=True)[:4]

    if len(cnts) >= 4:
        all_pts = np.concatenate(cnts)
        x, y, w_box, h_box = cv2.boundingRect(all_pts)
        
        # OFFSETS MÁGICOS
        offset_y = int(h_box * 0.052) 
        offset_x = int(w_box * 0.035) 
        
        x_f, y_f = x + offset_x, y + offset_y
        w_f, h_f = w_box - (2 * offset_x), h_box - (2 * offset_y)

        roi_thresh = thresh[y_f:y_f+h_f, x_f:x_f+w_f]
        img_viz_roi = img_viz[y_f:y_f+h_f, x_f:x_f+w_f]
        cv2.rectangle(img_viz, (x_f, y_f), (x_f+w_f, y_f+h_f), (255, 0, 0), 3)

        # 4. LEITURA COM DIVISÃO DE ALTA PRECISÃO
        alt_roi, larg_roi = roi_thresh.shape
        w_col = larg_roi / 3  # Usando float agora
        
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']
        
        for c_idx in range(3):
            for q_idx in range(30):
                q_num = (c_idx * 30) + 1 + q_idx
                
                # AQUI ESTÁ O SEGREDO: Calcular a posição baseada na altura total / 30
                # Isso evita que o erro de arredondamento se acumule
                y1 = int(q_idx * (alt_roi / 30))
                y2 = int((q_idx + 1) * (alt_roi / 30))
                
                x1 = int(c_idx * w_col)
                x2 = int((c_idx + 1) * w_col)
                
                # Desenha a grade verde (Agora matematicamente perfeita)
                cv2.line(img_viz_roi, (x1, y1), (x2, y1), (0, 255, 0), 1)
                
                # Recorte e leitura do miolo
                linha_q = roi_thresh[y1:y2, x1:x2]
                alt_imgs = np.array_split(linha_q, 5, axis=1)
                
                pixels = []
                for a in alt_imgs:
                    ha, wa = a.shape
                    if ha > 0 and wa > 0:
                        miolo = a[int(ha*0.2):int(ha*0.8), int(wa*0.2):int(wa*0.8)]
                        pixels.append(cv2.countNonZero(miolo))
                    else:
                        pixels.append(0)
                
                p_ord = sorted(pixels, reverse=True)
                if p_ord[0] < 12: respostas_finais[q_num] = "BRANCO"
                elif (p_ord[0]-p_ord[1]) < 10: respostas_finais[q_num] = "DUPLA"
                else: respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

        st.image(img_viz, caption="Conferência Precision: Grade milimétrica aplicada.")
        
        resultado_str = ", ".join([respostas_finais[q] for q in range(1, 91)])
        st.write(f"**Lido:** {resultado_str[:130]}...")

        if st.button("ENVIAR"):
            requests.post(FORM_URL, data={ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str})
            st.balloons()
            st.success("Enviado!")
    else:
        st.error("Âncoras não detectadas. Verifique a iluminação nos cantos.")
