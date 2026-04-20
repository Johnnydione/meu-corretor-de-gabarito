import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor 90Q - Fix Âncoras", layout="centered")

st.title("🎯 Corretor Digital Pro")
st.write("Versão com Detecção de Âncoras por Massa (Mais Robusta)")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Envie a foto", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    # 1. Ajuste de Orientação
    h, w = img.shape[:2]
    if w > h: img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    
    # 2. Processamento agressivo para achar os quadrados
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    # Threshold mais forte para destacar o preto dos quadrados
    thresh = cv2.threshold(blur, 100, 255, cv2.THRESH_BINARY_INV)[1]

    # 3. Localizar Âncoras (Pega os maiores contornos)
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Filtra contornos por área e pega os 4 maiores que podem ser nossos quadrados
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10] 
    
    quadrados = []
    for c in cnts:
        area = cv2.contourArea(c)
        if area > 300: # Se for grande o suficiente para ser um quadrado
            quadrados.append(c)

    # 4. Forçar o uso da área das âncoras
    if len(quadrados) >= 4:
        # Pega todos os pontos dos 4 maiores contornos encontrados
        top_4_quads = quadrados[:4]
        all_pts = np.concatenate(top_4_quads)
        x, y, w_box, h_box = cv2.boundingRect(all_pts)
        
        # Desenha onde ele achou as âncoras para você conferir (Bolotas amarelas)
        for q in top_4_quads:
            (qx, qy, qw, qh) = cv2.boundingRect(q)
            cv2.rectangle(img_viz, (qx, qy), (qx+qw, qy+qh), (0, 255, 255), 2)

        # SEUS OFFSETS DE SUCESSO (5.2% e 3.5%)
        offset_y = int(h_box * 0.052) 
        offset_x = int(w_box * 0.035) 
        
        x_f, y_f = x + offset_x, y + offset_y
        w_f, h_f = w_box - (2 * offset_x), h_box - (2 * offset_y)

        roi_thresh = thresh[y_f:y_f+h_f, x_f:x_f+w_f]
        img_viz_roi = img_viz[y_f:y_f+h_f, x_f:x_f+w_f]
        
        # Retângulo AZUL de leitura
        cv2.rectangle(img_viz, (x_f, y_f), (x_f+w_f, y_f+h_f), (255, 0, 0), 3)

        # 5. Processamento das Questões
        alt_roi, larg_roi = roi_thresh.shape
        w_col = larg_roi // 3
        h_row = alt_roi // 30
        
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']
        
        for c_idx in range(3):
            for q_idx in range(30):
                q_num = (c_idx * 30) + 1 + q_idx
                y1, y2 = q_idx * h_row, (q_idx + 1) * h_row
                x_base = c_idx * w_col
                
                # Grade Verde
                cv2.line(img_viz_roi, (x_base, y1), (x_base + w_col, y1), (0, 255, 0), 1)
                
                # Leitura do miolo da bolinha
                alt_imgs = np.array_split(roi_thresh[y1:y2, x_base:x_base+w_col], 5, axis=1)
                pixels = []
                for a in alt_imgs:
                    h_a, w_a = a.shape
                    # Pega o centro para ignorar as letras impressas
                    miolo = a[int(h_a*0.2):int(h_a*0.8), int(w_a*0.2):int(w_a*0.8)]
                    pixels.append(cv2.countNonZero(miolo))
                
                p_ord = sorted(pixels, reverse=True)
                if p_ord[0] < 15: respostas_finais[q_num] = "BRANCO"
                elif (p_ord[0]-p_ord[1]) < 10: respostas_finais[q_num] = "DUPLA"
                else: respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

        st.image(img_viz, caption="Conferência: Amarelo (Âncora) | Azul (Área Útil) | Verde (Questão)")
        
        resultado_str = ", ".join([respostas_finais[q] for q in range(1, 91)])
        st.write(f"**Lido:** {resultado_str[:120]}...")

        if st.button("ENVIAR"):
            requests.post(FORM_URL, data={ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str})
            st.balloons()
            st.success("Enviado!")
    else:
        st.error(f"Opa! Achei apenas {len(quadrados)} âncoras. Preciso de 4.")
        st.image(thresh, caption="Visão do Computador (Tente deixar os quadrados bem visíveis)")
