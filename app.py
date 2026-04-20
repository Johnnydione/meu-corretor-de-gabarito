import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor 90Q Colunas", layout="centered")
st.title("🎯 Corretor Digital Pro")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Envie o gabarito (Design de Colunas)", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    
    # 1. Processamento para destacar os retângulos
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)[1]

    # 2. Localizar os 3 Retângulos das Colunas
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Pega os 3 maiores contornos (que devem ser suas colunas) e ordena da esquerda para a direita
    colunas_cnts = sorted([c for c in cnts if cv2.contourArea(c) > 5000], 
                          key=lambda c: cv2.boundingRect(c)[0])[:3]

    if len(colunas_cnts) == 3:
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']
        
        for i, col_cnt in enumerate(colunas_cnts):
            x, y, w, h = cv2.boundingRect(col_cnt)
            # Desenha o contorno da coluna detectada para conferência
            cv2.rectangle(img_viz, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Recorta a coluna
            roi_col = thresh[y:y+h, x:x+w]
            
            # Define o range de questões da coluna
            start_q = [1, 31, 61][i]
            
            for q_idx in range(30):
                q_num = start_q + q_idx
                
                # Divisão vertical exata (30 partes)
                y1 = int(q_idx * (h / 30))
                y2 = int((q_idx + 1) * (h / 30))
                
                # Recorte da linha da questão
                linha = roi_col[y1:y2, :]
                h_l, w_l = linha.shape
                
                # --- MARGEM DE SEGURANÇA ---
                # Ignora 10% de cada lado para não ler a borda do retângulo
                area_util = linha[:, int(w_l*0.1):int(w_l*0.9)]
                
                # Divide em 5 alternativas
                alternativas = np.array_split(area_util, 5, axis=1)
                pixels = []
                for alt in alternativas:
                    ha, wa = alt.shape
                    # Pega apenas o miolo central de cada alternativa
                    miolo = alt[int(ha*0.2):int(ha*0.8), int(wa*0.2):int(wa*0.8)]
                    pixels.append(cv2.countNonZero(miolo))
                
                # Lógica de decisão
                p_ord = sorted(pixels, reverse=True)
                if p_ord[0] < 10:
                    respostas_finais[q_num] = "BRANCO"
                elif (p_ord[0] - p_ord[1]) < 8:
                    respostas_finais[q_num] = "DUPLA"
                else:
                    respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

        st.image(img_viz, caption="Colunas detectadas em azul.")
        
        # Formata as respostas (1-90)
        resultado_str = ", ".join([respostas_finais.get(q, "BRANCO") for q in range(1, 91)])
        st.write(f"**Gabarito Lido:** {resultado_str[:150]}...")

        if st.button("ENVIAR PARA GOOGLE SHEETS"):
            with st.spinner("Enviando..."):
                res = requests.post(FORM_URL, data={ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str})
                if res.status_code == 200:
                    st.balloons()
                    st.success("Enviado com sucesso!")
                else:
                    st.error("Erro no envio.")
    else:
        st.error(f"Não consegui identificar as 3 colunas. Detectei {len(colunas_cnts)}. Verifique se os retângulos estão bem visíveis.")
