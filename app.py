import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor Master Pro", layout="centered")

st.title("🎯 Corretor Digital 90Q")
st.write("Ajustado para alinhar pelos vértices internos dos quadrados.")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Tire a foto ou escolha o arquivo", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    # 1. Carregar e Pré-processar
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    h, w = img.shape[:2]
    if w > h: 
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # 2. Localizar Contornos dos Quadrados
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    quadrados = []
    for c in cnts:
        area = cv2.contourArea(c)
        if area > 500:
            quadrados.append(c)

    if len(quadrados) >= 4:
        # Pega a borda externa total
        all_pts = np.concatenate(quadrados)
        x, y, w_box, h_box = cv2.boundingRect(all_pts)
        
        # --- AJUSTE MANUAL DOS VÉRTICES ---
        # Aumente estes números para a grade azul "encolher" mais para dentro
        # Diminua se a grade azul estiver muito longe dos números
        margem_topo_base = int(h_box * 0.055) # Recuo vertical
        margem_laterais = int(w_box * 0.040)  # Recuo horizontal
        
        x_final = x + margem_laterais
        y_final = y + margem_topo_base
        w_final = w_box - (2 * margem_laterais)
        h_final = h_box - (2 * margem_topo_base)

        roi_thresh = thresh[y_final:y_final+h_final, x_final:x_final+w_final]
        img_viz_roi = img_viz[y_final:y_final+h_final, x_final:x_final+w_final]
        
        # Desenha o retângulo AZUL que define onde as questões começam
        cv2.rectangle(img_viz, (x_final, y_final), (x_final+w_final, y_final+h_final), (255, 0, 0), 3)

        # 3. Processar Grade
        alt_roi, larg_roi = roi_thresh.shape
        w_col = larg_roi // 3
        h_row = alt_roi // 30
        
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']
        
        for c_idx in range(3):
            coluna_img = roi_thresh[:, c_idx*w_col : (c_idx+1)*w_col]
            cv2.line(img_viz_roi, (c_idx*w_col, 0), (c_idx*w_col, alt_roi), (255, 0, 0), 2)
            
            start_q = (c_idx * 30) + 1
            for q_idx in range(30):
                q_num = start_q + q_idx
                y_pos = q_idx * h_row
                
                # Linha verde da questão
                cv2.line(img_viz_roi, (c_idx*w_col, y_pos), ((c_idx+1)*w_col, y_pos), (0, 255, 0), 1)
                
                questao_crop = coluna_img[y_pos : y_pos + h_row, :]
                alternativas = np.array_split(questao_crop, 5, axis=1)
                pixels = [cv2.countNonZero(alt) for alt in alternativas]
                
                p_ord = sorted(pixels, reverse=True)
                if p_ord[0] < 35:
                    respostas_finais[q_num] = "BRANCO"
                elif (p_ord[0] - p_ord[1]) < 30:
                    respostas_finais[q_num] = "DUPLA"
                else:
                    respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

        # 4. Exibir e Enviar
        st.subheader("3. Conferência de Leitura")
        st.image(img_viz, use_container_width=True)
        
        resultado_str = ", ".join([respostas_finais[q] for q in range(1, 91)])
        st.write(f"**Detectado:** {resultado_str[:120]}...")

        if st.button("ENVIAR PARA PLANILHA"):
            dados = {ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str}
            requests.post(FORM_URL, data=dados)
            st.balloons()
            st.success("Enviado!")
    else:
        st.warning("Não detectei as âncoras. Tente outra foto.")
