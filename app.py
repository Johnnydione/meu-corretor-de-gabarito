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
foto_upload = st.file_uploader("2. Envie a foto", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    # 1. Ajuste e Resize
    h, w = img.shape[:2]
    if w > h: img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    
    # 2. Processamento
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 115, 255, cv2.THRESH_BINARY_INV)[1]

    # 3. Localizar Âncoras
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted([c for c in cnts if cv2.contourArea(c) > 400], key=cv2.contourArea, reverse=True)[:4]

    if len(cnts) >= 4:
        all_pts = np.concatenate(cnts)
        x, y, w_box, h_box = cv2.boundingRect(all_pts)
        
        # OFFSETS MÁGICOS (Mantendo os seus 5.2% e 3.5%)
        off_y, off_x = int(h_box * 0.052), int(w_box * 0.035)
        x_f, y_f = x + off_x, y + off_y
        w_f, h_f = w_box - (2 * off_x), h_box - (2 * off_y)

        roi_thresh = thresh[y_f:y_f+h_f, x_f:x_f+w_f]
        img_viz_roi = img_viz[y_f:y_f+h_f, x_f:x_f+w_f]
        cv2.rectangle(img_viz, (x_f, y_f), (x_f+w_f, y_f+h_f), (255, 0, 0), 3)

        alt_roi, larg_roi = roi_thresh.shape
        w_col = larg_roi / 3
        
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']

        for c_idx in range(3):
            # AQUI ESTÁ O AJUSTE: Criamos uma pequena folga nas laterais da coluna
            x_start_col = int(c_idx * w_col) + 5  # Empurra 5px para a direita
            x_end_col = int((c_idx + 1) * w_col) - 5 # Puxa 5px para a esquerda
            
            for q_idx in range(30):
                q_num = (c_idx * 30) + 1 + q_idx
                y1 = int(q_idx * (alt_roi / 30))
                y2 = int((q_idx + 1) * (alt_roi / 30))
                
                # Desenha grade verde
                cv2.line(img_viz_roi, (x_start_col, y1), (x_end_col, y1), (0, 255, 0), 1)
                
                # Pega a linha da questão com a nova margem
                linha_q = roi_thresh[y1:y2, x_start_col:x_end_col]
                
                # Dividir em 5 e ler apenas o miolo CENTRAL de cada alternativa
                alternativas = np.array_split(linha_q, 5, axis=1)
                pixels = []
                for alt in alternativas:
                    ha, wa = alt.shape
                    if ha > 0 and wa > 0:
                        # Pega só o "coração" da bolinha (60% da área)
                        miolo = alt[int(ha*0.2):int(ha*0.8), int(wa*0.2):int(wa*0.8)]
                        pixels.append(cv2.countNonZero(miolo))
                    else:
                        pixels.append(0)
                
                p_ord = sorted(pixels, reverse=True)
                if p_ord[0] < 12: 
                    respostas_finais[q_num] = "BRANCO"
                elif (p_ord[0] - p_ord[1]) < 10: 
                    respostas_finais[q_num] = "DUPLA"
                else:
                    respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

        st.image(img_viz, use_container_width=True)
        resultado_str = ", ".join([respostas_finais[q] for q in range(1, 91)])
        st.write(f"**Lido:** {resultado_str[:150]}...")

        if st.button("ENVIAR"):
            requests.post(FORM_URL, data={ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str})
            st.balloons()
            st.success("Enviado!")
    else:
        st.error("Âncoras não encontradas.")
