import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor Pro", layout="centered")

st.title("🎯 Corretor Inteligente 90Q")
st.write("O sistema agora localiza as marcas pretas nos cantos para alinhar a grade.")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Tire a foto ou escolha o arquivo", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    # 1. Rotação e Pré-processamento
    h, w = img.shape[:2]
    if w > h: img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
    img = cv2.resize(img, (1000, 1400)) # Aumentei um pouco a resolução de trabalho
    img_viz = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # 2. LOCALIZAR AS ÂNCORAS (OS QUADRADOS PRETOS)
    # Procuramos os contornos dos quadrados nos cantos
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    quadrados = []
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4: # Se tem 4 lados
            area = cv2.contourArea(c)
            if area > 500: # Se não for sujeira
                quadrados.append(c)

    # Se achamos pelo menos 4 marcas, vamos alinhar. 
    # Caso contrário, usamos a página toda (plano B)
    if len(quadrados) >= 4:
        # Pega os limites da área das questões baseada nos quadrados
        all_pts = np.concatenate(quadrados)
        x, y, w_box, h_box = cv2.boundingRect(all_pts)
        # Recorta apenas a área interna do gabarito (ajustando margens internas)
        roi_thresh = thresh[y:y+h_box, x:x+w_box]
        img_viz_roi = img_viz[y:y+h_box, x:x+w_box]
        # Desenha um retângulo vermelho onde ele "travou" a leitura
        cv2.rectangle(img_viz, (x,y), (x+w_box, y+h_box), (0,0,255), 5)
    else:
        st.warning("⚠️ Não detectei os 4 cantos. Tente tirar a foto mais de perto e com fundo contrastante.")
        roi_thresh = thresh
        img_viz_roi = img_viz

    # 3. DIVISÃO DA GRADE (DENTRO DA ÁREA DETECTADA)
    alt, larg = roi_thresh.shape
    w_col = larg // 3
    h_row = alt // 30
    
    respostas_finais = {}
    OPCOES = ['A', 'B', 'C', 'D', 'E']
    
    # Processar as 3 colunas
    for c_idx in range(3):
        coluna = roi_thresh[:, c_idx*w_col : (c_idx+1)*w_col]
        cv2.line(img_viz_roi, (c_idx*w_col, 0), (c_idx*w_col, alt), (255, 0, 0), 3)
        
        start_q = (c_idx * 30) + 1
        # Divide a coluna em 30 questões
        for q_idx in range(30):
            q_num = start_q + q_idx
            y_start = q_idx * h_row
            y_end = (q_idx + 1) * h_row
            
            # Desenha a linha verde da questão
            cv2.line(img_viz_roi, (c_idx*w_col, y_start), ((c_idx+1)*w_col, y_start), (0, 255, 0), 1)
            
            questao_img = coluna[y_start:y_end, :]
            # Divide em 5 alternativas
            alternativas = np.array_split(questao_img, 5, axis=1)
            pixels = [cv2.countNonZero(alt_img) for alt_img in alternativas]
            
            p_ord = sorted(pixels, reverse=True)
            if p_ord[0] < 30: # Ajuste de sensibilidade
                respostas_finais[q_num] = "BRANCO"
            elif (p_ord[0] - p_ord[1]) < 25:
                respostas_finais[q_num] = "DUPLA"
            else:
                respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

    # 4. EXIBIÇÃO
    st.subheader("3. Conferência de Alinhamento")
    st.image(img_viz, caption="O retângulo vermelho mostra a área que o sistema capturou", use_container_width=True)
    
    lista_respostas = [respostas_finais[q] for q in range(1, 91)]
    texto_respostas = ", ".join(lista_respostas)
    
    st.write(f"**Gabarito Detectado:** {texto_respostas[:120]}...")

    if st.button("ENVIAR PARA PLANILHA"):
        dados = {ID_NOME: nome_aluno, ID_RESPOSTAS: texto_respostas}
        r = requests.post(FORM_URL, data=dados)
        if r.status_code == 200:
            st.balloons()
            st.success("✅ Enviado!")
