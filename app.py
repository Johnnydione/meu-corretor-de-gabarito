import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor Profissional", layout="centered")

st.title("🎯 Corretor Digital 90Q")
st.write("Dica: Use a câmera nativa para melhor foco e enquadramento.")

nome_aluno = st.text_input("Nome do Aluno:")

# --- BOTÃO QUE ABRE A CÂMERA DO CELULAR EM TELA CHEIA ---
# O segredo está no 'label' e no tipo de arquivo
foto_upload = st.file_uploader("CLIQUE AQUI PARA TIRAR FOTO", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    # 1. Ler a imagem
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    # 2. Rotação Inteligente
    h, w = img.shape[:2]
    if w > h:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
    # 3. Redimensionamento Padrão
    img = cv2.resize(img, (800, 1100))
    img_viz = img.copy()
    
    # 4. Processamento
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Grade de Conferência
    w_col = 800 // 3
    h_row = 1100 // 30
    for i in range(1, 3):
        cv2.line(img_viz, (w_col * i, 0), (w_col * i, 1100), (255, 0, 0), 3)
    for i in range(31):
        cv2.line(img_viz, (0, i * h_row), (800, i * h_row), (0, 255, 0), 1)

    # 5. Lógica de Leitura
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

    st.subheader("Conferência de Alinhamento")
    st.image(img_viz, use_container_width=True)
    
    texto_respostas = ", ".join([respostas_finais[q] for q in range(1, 91)])
    
    if st.button("ENVIAR PARA PLANILHA"):
        dados = {ID_NOME: nome_aluno, ID_RESPOSTAS: texto_respostas}
        requests.post(FORM_URL, data=dados)
        st.balloons()
        st.success("Enviado com sucesso!")
