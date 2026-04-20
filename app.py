import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

# 1. Configurar a página para ocupar a tela toda
st.set_page_config(page_title="Corretor Pro", layout="wide")

# 2. CSS para "Explodir" a câmera na tela
st.markdown("""
    <style>
    /* Remove as margens das laterais do Streamlit */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Faz o componente de câmera ocupar toda a largura disponível */
    div[data-testid="stCameraInput"] {
        width: 100% !important;
    }
    
    /* Ajusta o vídeo para ser grande e não cortar */
    div[data-testid="stCameraInput"] video {
        width: 100% !important;
        height: auto !important;
        border: 4px solid #00ff00 !important;
        border-radius: 10px;
    }

    /* Estiliza o botão de tirar foto para ficar mais fácil de clicar */
    button[data-testid="stBaseButton-secondary"] {
        width: 100% !important;
        height: 3rem !important;
        background-color: #00ff0022 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 Corretor 90Q")

nome_aluno = st.text_input("Nome do Aluno:")
foto = st.camera_input("Enquadre o Gabarito")

if foto and nome_aluno:
    # --- O RESTANTE DO CÓDIGO CONTINUA IGUAL ---
    file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    h, w = img.shape[:2]
    if w > h:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
    img = cv2.resize(img, (800, 1100))
    img_viz = img.copy()
    
    # Processamento e Grade
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    w_col = 800 // 3
    h_row = 1100 // 30
    cv2.line(img_viz, (w_col, 0), (w_col, 1100), (255, 0, 0), 3)
    cv2.line(img_viz, (w_col*2, 0), (w_col*2, 1100), (255, 0, 0), 3)
    for i in range(31):
        cv2.line(img_viz, (0, i * h_row), (800, i * h_row), (0, 255, 0), 1)

    # Lógica de Leitura
    respostas_finais = {}
    OPCOES = ['A', 'B', 'C', 'D', 'E']
    colunas_fatias = np.array_split(thresh, 3, axis=1)
    
    for c_idx, coluna in enumerate(colunas_fatias):
        start_q = (c_idx * 30) + 1
        questoes = np.array_split(coluna, 30)
        for q_idx, questao_img in enumerate(questoes):
            q_num = start_q + q_idx
            alternativas = np.array_split(questao_img, 5, axis=1)
            pixels = [cv2.countNonZero(alt) for alt in alternativas]
            p_ord = sorted(pixels, reverse=True)
            if p_ord[0] < 40:
                respostas_finais[q_num] = "BRANCO"
            elif (p_ord[0] - p_ord[1]) < 30:
                respostas_finais[q_num] = "DUPLA"
            else:
                respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

    st.subheader("Conferência")
    st.image(img_viz, use_container_width=True)
    
    texto_respostas = ", ".join([respostas_finais[q] for q in range(1, 91)])
    
    if st.button("ENVIAR PARA PLANILHA"):
        dados = {ID_NOME: nome_aluno, ID_RESPOSTAS: texto_respostas}
        requests.post(FORM_URL, data=dados)
        st.balloons()
        st.success("Enviado!")
