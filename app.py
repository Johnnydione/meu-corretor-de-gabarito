import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor Master Pro", layout="wide")

# --- CSS PARA CÂMERA GRANDE ---
st.markdown("""
    <style>
    div[data-testid="stCameraInput"] video {
        width: 100% !important;
        border: 6px solid #00ff00 !important;
        border-radius: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 Corretor Digital 90Q")

nome_aluno = st.text_input("Nome do Aluno:")
foto = st.camera_input("Aponte para o Gabarito")

if foto and nome_aluno:
    img_array = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img = cv2.imdecode(img_array, 1)
    
    # Redimensiona para o padrão A4 digital (800x1100)
    img = cv2.resize(img, (800, 1100))
    img_viz = img.copy() 
    
    # Processamento de imagem
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    respostas_finais = {}
    OPCOES = ['A', 'B', 'C', 'D', 'E']
    
    # Desenhar Grade de Conferência (Azul para colunas, Verde para linhas)
    w_col = 800 // 3
    h_row = 1100 // 30
    for i in range(1, 3):
        cv2.line(img_viz, (w_col * i, 0), (w_col * i, 1100), (255, 0, 0), 2)
    for i in range(30):
        cv2.line(img_viz, (0, h_row * i), (800, h_row * i), (0, 255, 0), 1)

    # --- LÓGICA DE LEITURA COM FILTRO DE ERRO ---
    colunas_fatias = np.array_split(thresh, 3, axis=1)
    
    for c_idx, coluna in enumerate(colunas_fatias):
        start_q = (c_idx * 30) + 1
        questoes_da_coluna = np.array_split(coluna, 30)
        
        for q_idx, questao_img in enumerate(questoes_da_coluna):
            q_num = start_q + q_idx
            alternativas = np.array_split(questao_img, 5, axis=1)
            
            # Conta pixels pretos em cada uma das 5 alternativas
            pixels = [cv2.countNonZero(alt) for alt in alternativas]
            
            # Ordena para comparar a maior marcação com a segunda maior
            p_ordenados = sorted(pixels, reverse=True)
            maior = p_ordenados[0]
            segundo_maior = p_ordenados[1]
            
            # VALIDAÇÃO:
            # Se o mais votado tiver menos de 40 pixels, ninguém pintou nada (ajustável)
            if maior < 40:
