import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor 90Q Auto-Align", layout="centered")
st.title("🎯 Corretor Digital Pro")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Envie o gabarito", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    
    # 1. Transformar em Preto e Branco bem contrastado
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)[1]

    # 2. ACHAR AS COLUNAS (O segredo está aqui)
    # Vamos procurar por contornos, mas filtrar apenas os 3 que parecem retângulos de colunas
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    colunas_encontradas = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        aspect_ratio = h / float(w)
        # Uma coluna de 30 questões é muito mais alta que larga (proporção > 3)
        if h > 400 and aspect_ratio > 3:
            colunas_encontradas.append((x, y, w, h))

    # Ordena as colunas da esquerda para a direita (X)
    colunas_encontradas = sorted(colunas_encontradas, key=lambda x: x[0])

    if len(colunas_encontradas) == 3:
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']

        for i, (x, y, w, h) in enumerate(colunas_encontradas):
            # Desenha o retângulo detectado para você ver que ele achou certo
            cv2.rectangle(img_viz, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Recorta a coluna e encolhe 4 pixels de cada lado (margem de segurança)
            # Isso garante que a linha preta do retângulo não seja lida como marcação
            roi_col = thresh[y+4:y+h-4, x+4:x+w-4]
            h_roi, w_roi = roi_col.shape
            
            start_q = [1, 31, 61][i]

            for q_idx in range(30):
                q_num = start_q + q_idx
                
                # Divide a altura em 30 fatias exatas
                y1 = int(q_idx * (h_roi / 30))
                y2 = int((q_idx + 1) * (h_roi / 30))
                
                fatia_questao = roi_col[y1:y2, :]
                
                # Divide a largura em 5 partes (A, B, C, D, E)
                alternativas = np.array_split(fatia_questao, 5, axis=1)
                
                contagem_pixels = []
                for alt in alternativas:
                    # Pega só o centro da bolinha para evitar bordas
                    ha, wa = alt.shape
                    miolo = alt[int(ha*0.2):int(ha*0.8), int(wa*0.2):int(wa*0.8)]
                    contagem_pixels.append(cv2.countNonZero(miolo))
                
                maior = max(contagem_pixels)
                if maior < 10:
                    respostas_finais[q_num] = "BRANCO"
                else:
                    respostas_finais[q_num] = OPCOES[np.argmax(contagem_pixels)]

        st.image(img_viz, caption="Retângulos detectados automaticamente.")
        
        resultado_str = ", ".join([respostas_finais.get(q, "BRANCO") for q in range(1, 91)])
        st.write(f"**Lido:** {resultado_str[:150]}...")

        if st.button("ENVIAR"):
            requests.post(FORM_URL, data={ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str})
            st.balloons()
            st.success("Enviado!")
    else:
        st.error(f"Erro: Encontrei {len(colunas_encontradas)} colunas. Certifique-se de que os 3 retângulos pretos do Canva estão bem visíveis na imagem.")
