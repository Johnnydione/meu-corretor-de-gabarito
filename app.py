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

# --- CSS AJUSTADO PARA NÃO CORTAR A FOTO ---
st.markdown("""
    <style>
    div[data-testid="stCameraInput"] video {
        width: 100% !important;
        height: auto !important;
        border: 4px solid #00ff00 !important;
        border-radius: 10px;
        object-fit: contain !important; /* Garante que a imagem apareça inteira */
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 Corretor Digital 90Q")

nome_aluno = st.text_input("Nome do Aluno:")
foto = st.camera_input("Tire a foto com o celular EM PÉ")

if foto and nome_aluno:
    # 1. Converter imagem
    file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)

    # --- CORREÇÃO DE ROTAÇÃO ---
    # Se a largura for maior que a altura, a foto está deitada. Vamos girar.
    h, w = img.shape[:2]
    if w > h:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
    # Redimensiona para o padrão A4 vertical
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
        cv2.line(img_viz, (w_col * i, 0), (w_col * i, 1100), (255, 0, 0), 2)
    for i in range(30):
        cv2.line(img_viz, (0, h_row * i), (800, h_row * i), (0, 255, 0), 1)

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

    st.subheader("Conferência Visual (A foto deve aparecer inteira aqui):")
    st.image(img_viz, use_container_width=True)
    
    if st.button("ENVIAR PARA GOOGLE SHEETS"):
        dados = {ID_NOME: nome_aluno, ID_RESPOSTAS: texto_respostas}
        requests.post(FORM_URL, data=dados)
        st.balloons()
        st.success("Enviado!")
