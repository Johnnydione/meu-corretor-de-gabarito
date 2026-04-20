import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor Pro", layout="centered")

# --- CSS SIMPLIFICADO (PARA EVITAR CORTES DO NAVEGADOR) ---
st.markdown("""
    <style>
    div[data-testid="stCameraInput"] {
        width: 100% !important;
    }
    div[data-testid="stCameraInput"] video {
        border: 4px solid #00ff00 !important;
        border-radius: 10px;
        object-fit: contain !important; /* Mostra o feed inteiro, sem cortar */
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 Corretor Digital 90Q")

nome_aluno = st.text_input("Nome do Aluno:")
foto = st.camera_input("Tire a foto (pode ser com o celular deitado ou em pé)")

if foto and nome_aluno:
    # 1. Ler a imagem original
    file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    # 2. IDENTIFICAÇÃO AUTOMÁTICA DE ORIENTAÇÃO
    h, w = img.shape[:2]
    # Se a imagem for mais larga que alta, ela veio deitada. Vamos girar 90 graus.
    if w > h:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
    # 3. REDIMENSIONAMENTO FORÇADO PARA A4 (800x1100)
    # Isso resolve o problema de "comer" metade da foto, pois forçamos o padrão.
    img = cv2.resize(img, (800, 1100))
    img_viz = img.copy()
    
    # 4. Processamento de Imagem
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # --- DESENHO DA GRADE (Conferência) ---
    w_col = 800 // 3
    h_row = 1100 // 30
    # Linhas das Colunas (Azul)
    cv2.line(img_viz, (w_col, 0), (w_col, 1100), (255, 0, 0), 3)
    cv2.line(img_viz, (w_col*2, 0), (w_col*2, 1100), (255, 0, 0), 3)
    # Linhas das Questões (Verde)
    for i in range(31):
        y = i * h_row
        cv2.line(img_viz, (0, y), (800, y), (0, 255, 0), 1)

    # 5. Lógica de Leitura das 90 Questões
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

    # 6. Resultados e Envio
    st.subheader("Conferência de Alinhamento")
    # Aqui é onde você verá se a foto foi recuperada inteira!
    st.image(img_viz, caption="O gabarito deve aparecer inteiramente aqui dentro da grade", use_container_width=True)
    
    texto_respostas = ", ".join([respostas_finais[q] for q in range(1, 91)])
    
    if st.button("ENVIAR PARA PLANILHA"):
        dados = {ID_NOME: nome_aluno, ID_RESPOSTAS: texto_respostas}
        requests.post(FORM_URL, data=dados)
        st.balloons()
        st.success("Enviado com sucesso!")
