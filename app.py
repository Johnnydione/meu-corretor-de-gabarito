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

# --- CSS PARA FORÇAR FORMATO VERTICAL NA CÂMERA ---
st.markdown("""
    <style>
    /* Força o container da câmera a ser vertical */
    div[data-testid="stCameraInput"] {
        max-width: 450px !important;
        margin: 0 auto;
    }
    div[data-testid="stCameraInput"] video {
        border: 5px solid #00ff00 !important;
        border-radius: 15px;
        aspect-ratio: 3 / 4 !important; /* Proporção de papel */
        object-fit: cover !important;
    }
    /* Estiliza a imagem de visualização para não ficar gigante */
    .stImage img {
        border: 2px solid #333;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 Corretor Digital 90Q")

nome_aluno = st.text_input("Nome do Aluno:")
foto = st.camera_input("Enquadre o Gabarito (Papel em Pé)")

if foto and nome_aluno:
    # 1. Converter imagem
    file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)

    # Pegamos as dimensões reais
    h, w = img.shape[:2]

    # --- LÓGICA DE ROTAÇÃO INTELIGENTE ---
    # Se a foto estiver "deitada" (largura > altura), giramos
    if w > h:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
    # Agora redimensionamos para o padrão vertical fixo
    img = cv2.resize(img, (800, 1100))
    img_viz = img.copy() 
    
    # 2. Processamento
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    respostas_finais = {}
    OPCOES = ['A', 'B', 'C', 'D', 'E']
    
    # Grade de conferência
    w_col = 800 // 3
    h_row = 1100 // 30
    for i in range(1, 3):
        cv2.line(img_viz, (w_col * i, 0), (w_col * i, 1100), (255, 0, 0), 3) # Colunas em Azul
    for i in range(30):
        cv2.line(img_viz, (0, h_row * i), (800, h_row * i), (0, 255, 0), 1) # Linhas em Verde

    # 3. Lógica de Leitura
    colunas_fatias = np.array_split(thresh, 3, axis=1)
    for c_idx, coluna in enumerate(colunas_fatias):
        start_q = (c_idx * 30) + 1
        questoes = np.array_split(coluna, 30)
        for q_idx, questao_img in enumerate(questoes):
            q_num = start_q + q_idx
            alternativas = np.array_split(questao_img, 5, axis=1)
            pixels = [cv2.countNonZero(alt) for alt in alternativas]
            
            p_ordenados = sorted(pixels, reverse=True)
            if p_ordenados[0] < 40:
                respostas_finais[q_num] = "BRANCO"
            elif (p_ordenados[0] - p_ordenados[1]) < 30:
                respostas_finais[q_num] = "DUPLA"
            else:
                respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

    respostas_ordenadas = [respostas_finais[q] for q in range(1, 91)]
    texto_respostas = ", ".join(respostas_ordenadas)

    st.subheader("Conferência de Leitura")
    # Mostra a imagem processada (já em pé)
    st.image(img_viz, caption="As linhas azuis devem estar entre as colunas do papel", width=400)
    
    st.write(f"**Gabarito lido:** {texto_respostas[:80]}...")

    if st.button("ENVIAR PARA GOOGLE SHEETS"):
        try:
            dados = {ID_NOME: nome_aluno, ID_RESPOSTAS: texto_respostas}
            requests.post(FORM_URL, data=dados)
            st.balloons()
            st.success("Enviado com sucesso!")
        except:
            st.error("Erro na conexão.")
