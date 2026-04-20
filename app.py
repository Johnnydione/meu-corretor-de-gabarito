import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/e/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor Inteligente 90Q", layout="centered")

st.title("🎯 Corretor Digital Pro")
st.write("Dica: Os 4 quadrados pretos devem estar visíveis para o alinhamento automático.")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Tire a foto ou escolha o arquivo", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    # 1. Carregar imagem
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    # 2. Corrigir orientação e redimensionar para trabalho
    h, w = img.shape[:2]
    if w > h: 
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # 3. LOCALIZAR QUADRADOS (ÂNCORAS)
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    quadrados = []
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            area = cv2.contourArea(c)
            if area > 400: # Filtra sujeira
                quadrados.append(c)

    # 4. DEFINIR ÁREA DE LEITURA (ROI) COM AJUSTE DE MARGEM
    if len(quadrados) >= 4:
        all_pts = np.concatenate(quadrados)
        x, y, w_box, h_box = cv2.boundingRect(all_pts)
        
        # --- AJUSTE DE PRECISÃO (OFFSETS) ---
        # Recuamos um pouco para a grade azul ignorar os quadrados e focar nas questões
        offset_y = int(h_box * 0.052) # Ajuste vertical (5.2%)
        offset_x = int(w_box * 0.035) # Ajuste horizontal (3.5%)
        
        x_final, y_final = x + offset_x, y + offset_y
        w_final, h_final = w_box - (2 * offset_x), h_box - (2 * offset_y)

        roi_thresh = thresh[y_final:y_final+h_final, x_final:x_final+w_final]
        img_viz_roi = img_viz[y_final:y_final+h_final, x_final:x_final+w_final]
        
        # Desenha o retângulo de leitura azul (Área Útil)
        cv2.rectangle(img_viz, (x_final, y_final), (x_final+w_final, y_final+h_final), (255, 0, 0), 3)
    else:
        st.warning("⚠️ Quadrados não detectados! Tente uma foto mais clara.")
        roi_thresh = thresh
        img_viz_roi = img_viz

    # 5. PROCESSAR GRADE (DENTRO DA ÁREA ÚTIL)
    alt_roi, larg_roi = roi_thresh.shape
    w_col = larg_roi // 3
    h_row = alt_roi // 30
    
    respostas_finais = {}
    OPCOES = ['A', 'B', 'C', 'D', 'E']
    
    for c_idx in range(3):
        coluna_img = roi_thresh[:, c_idx*w_col : (c_idx+1)*w_col]
        # Desenha divisórias de colunas
        cv2.line(img_viz_roi, (c_idx*w_col, 0), (c_idx*w_col, alt_roi), (255, 0, 0), 2)
        
        start_q = (c_idx * 30) + 1
        for q_idx in range(30):
            q_num = start_q + q_idx
            y_start = q_idx * h_row
            y_end = (q_idx + 1) * h_row
            
            # Desenha linha da questão (Verde)
            cv2.line(img_viz_roi, (c_idx*w_col, y_start), ((c_idx+1)*w_col, y_start), (0, 255, 0), 1)
            
            questao_crop = coluna_img[y_start:y_end, :]
            alternativas = np.array_split(questao_crop, 5, axis=1)
            
            pixels = [cv2.countNonZero(alt) for alt in alternativas]
            p_ord = sorted(pixels, reverse=True)
            
            if p_ord[0] < 35:
                respostas_finais[q_num] = "BRANCO"
            elif (p_ord[0] - p_ord[1]) < 30:
                respostas_finais[q_num] = "DUPLA"
            else:
                respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

    # 6. EXIBIR RESULTADOS
    st.subheader("3. Conferência Visual")
    st.image(img_viz, caption="O retângulo azul deve cercar apenas as bolinhas.", use_container_width=True)
    
    resultado_str = ", ".join([respostas_finais[q] for q in range(1, 91)])
    st.write(f"**Gabarito Lido:** {resultado_str[:120]}...")

    if st.button("ENVIAR PARA GOOGLE SHEETS"):
        with st.spinner("Enviando dados..."):
            dados = {ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str}
            res = requests.post(FORM_URL, data=dados)
            if res.status_code == 200:
                st.balloons()
                st.success(f"Enviado! Respostas de {nome_aluno} registradas.")
            else:
                st.error("Erro ao enviar. Verifique sua planilha.")
