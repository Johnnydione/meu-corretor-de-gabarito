import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Corretor Master", layout="wide")

# --- CSS PARA CÂMERA EM TELA CHEIA E INTERFACE LIMPA ---
st.markdown("""
    <style>
    /* Faz a câmera ocupar a largura total e ser mais alta */
    div[data-testid="stCameraInput"] video {
        width: 100% !important;
        height: auto !important;
        max-height: 70vh !important;
        border: 4px solid #00ff00 !important;
        border-radius: 15px;
        object-fit: cover;
    }
    /* Esconde botões desnecessários do Streamlit para ganhar espaço */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .main {padding-top: 0rem;}
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 Corretor Digital")

nome_aluno = st.text_input("Nome do Aluno:")
foto = st.camera_input("Foque no papel")

if foto and nome_aluno:
    # 1. Converter imagem
    img_array = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img = cv2.imdecode(img_array, 1)
    
    # Redimensionar para um padrão fixo para evitar o "bug" de alinhamento
    # Isso garante que a grade de 90 questões sempre caiba no desenho
    img = cv2.resize(img, (800, 1100))
    img_viz = img.copy() 
    
    # 2. Processamento
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # --- LÓGICA DE DETECÇÃO ---
    respostas_finais = {}
    OPCOES = ['A', 'B', 'C', 'D', 'E']
    
    # Desenhar grade de conferência
    # Dividindo em 3 colunas (azul) e 30 linhas (verde)
    w_col = 800 // 3
    h_row = 1100 // 30
    
    for i in range(1, 3):
        cv2.line(img_viz, (w_col * i, 0), (w_col * i, 1100), (255, 0, 0), 2)
    
    for i in range(30):
        cv2.line(img_viz, (0, h_row * i), (800, h_row * i), (0, 255, 0), 1)

    # Processamento real
    colunas_fatias = np.array_split(thresh, 3, axis=1)
    for c_idx, coluna in enumerate(colunas_fatias):
        start_q = (c_idx * 30) + 1
        questoes = np.array_split(coluna, 30)
        for q_idx, questao in enumerate(questoes):
            q_num = start_q + q_idx
            alternativas = np.array_split(questao, 5, axis=1)
            pixels = [cv2.countNonZero(alt) for alt in alternativas]
            respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

    respostas_ordenadas = [respostas_finais[q] for q in range(1, 91)]
    texto_respostas = ", ".join(respostas_ordenadas)

    st.subheader("Conferência de Alinhamento:")
    # Aqui mostramos a imagem redimensionada para você ver a grade certinha
    st.image(img_viz, use_container_width=True)
    
    if st.button("ENVIAR PARA GOOGLE SHEETS"):
        dados = {ID_NOME: nome_aluno, ID_RESPOSTAS: texto_respostas}
        r = requests.post(FORM_URL, data=dados)
        if r.status_code == 200:
            st.balloons()
            st.success("✅ Enviado com sucesso!")
        else:
            st.error("Erro no envio.")
