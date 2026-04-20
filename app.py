import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor 90Q Final", layout="centered")
st.title("🎯 Corretor Digital Pro")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Envie o gabarito", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    # Redimensionamos para 1000x1400 para travar a matemática das coordenadas
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Threshold ajustado para ser sensível (pega até cinzas escuros)
    thresh = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY_INV)[1]

    # --- MAPEAMENTO MILIMÉTRICO (Baseado na sua imagem do Canva) ---
    # x_inicio, x_fim de cada bloco de bolinhas
    # Ajustei para ignorar os números e focar só dentro dos retângulos
    colunas = [
        (138, 308),  # Coluna 1 (Q 1-30)
        (428, 598),  # Coluna 2 (Q 31-60)
        (718, 888)   # Coluna 3 (Q 61-90)
    ]
    
    y_topo = 238   # Onde começa a primeira bolinha
    y_base = 1315  # Onde termina a última bolinha
    
    respostas_finais = {}
    OPCOES = ['A', 'B', 'C', 'D', 'E']

    for i, (x1, x2) in enumerate(colunas):
        start_q = [1, 31, 61][i]
        larg_util = x2 - x1
        alt_util = y_base - y_topo
        
        # Desenha área de leitura (Verde para conferência)
        cv2.rectangle(img_viz, (x1, y_topo), (x2, y_base), (0, 255, 0), 2)

        for q_idx in range(30):
            q_num = start_q + q_idx
            
            # Calcula a posição vertical de cada questão
            y1_q = y_topo + int(q_idx * (alt_util / 30))
            y2_q = y_topo + int((q_idx + 1) * (alt_util / 30))
            
            # Recorta a linha da questão e divide em 5 (A, B, C, D, E)
            linha = thresh[y1_q:y2_q, x1:x2]
            
            # Margem interna lateral (5% para não encostar na linha preta do retângulo)
            margem_w = int(larg_util * 0.05)
            fatias = np.array_split(linha[:, margem_w : larg_util - margem_w], 5, axis=1)
            
            pixels = []
            for fatia in fatias:
                h_f, w_f = fatia.shape
                # Pega só o miolo da bolinha
                miolo = fatia[int(h_f*0.2):int(h_f*0.8), int(w_f*0.2):int(w_f*0.8)]
                pixels.append(cv2.countNonZero(miolo))
            
            p_ord = sorted(pixels, reverse=True)
            # Como a imagem é digital, o contraste é alto. 
            # 15 pixels de "miolo" preto já indicam uma marcação clara.
            if p_ord[0] < 15: 
                respostas_finais[q_num] = "BRANCO"
            elif (p_ord[0] - p_ord[1]) < 10: 
                respostas_finais[q_num] = "DUPLA"
            else:
                respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

    st.image(img_viz, caption="Visualização das Zonas de Leitura")
    
    resultado_str = ", ".join([respostas_finais.get(q, "BRANCO") for q in range(1, 91)])
    st.write(f"**Resultado Lido:** {resultado_str[:160]}...")

    if st.button("ENVIAR GABARITO"):
        requests.post(FORM_URL, data={ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str})
        st.balloons()
        st.success("Enviado com sucesso!")
