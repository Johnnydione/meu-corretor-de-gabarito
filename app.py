import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

# --- TRUQUE PARA AUMENTAR A CÂMERA ---
st.markdown("""
    <style>
    div[data-testid="stCameraInput"] {
        width: 100% !important;
        max-width: 800px !important;
    }
    video {
        border: 3px solid #00ff00 !important;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_view_policy=True)

st.set_page_config(page_title="Corretor Pro 90", layout="wide")
st.title("🎯 Corretor Inteligente")

nome_aluno = st.text_input("Nome do Aluno:")
foto = st.camera_input("Aponte para o Gabarito")

if foto and nome_aluno:
    # 1. Converter imagem
    img_array = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img = cv2.imdecode(img_array, 1)
    img_viz = img.copy() # Cópia para desenhar em cima
    
    # 2. Processamento
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # 3. Lógica de Leitura e Desenho
    respostas = []
    OPCOES = ['A', 'B', 'C', 'D', 'E']
    
    altura, largura = thresh.shape
    fatias_h = np.array_split(thresh, 90)
    
    # Vamos desenhar retângulos para mostrar a detecção
    for i, fatia in enumerate(fatias_h):
        y_pos = int((altura / 90) * i)
        # Desenha uma linha verde fina para cada questão detectada
        cv2.line(img_viz, (0, y_pos), (largura, y_pos), (0, 255, 0), 1)
        
        opcoes_v = np.array_split(fatia, 5, axis=1)
        pixels = [cv2.countNonZero(opt) for opt in opcoes_v]
        indice_marcado = np.argmax(pixels)
        respostas.append(OPCOES[indice_marcado])

    # Mostrar a imagem com as marcações de detecção
    st.subheader("Visualização da Detecção:")
    st.image(img_viz, caption="Linhas verdes mostram onde o Python dividiu as 90 questões", use_column_width=True)
    
    texto_respostas = ", ".join(respostas)
    st.write(f"**Gabarito lido:** {texto_respostas[:60]}...")

    if st.button("ENVIAR PARA PLANILHA"):
        dados = {ID_NOME: nome_aluno, ID_RESPOSTAS: texto_respostas}
        try:
            r = requests.post(FORM_URL, data=dados)
            if r.status_code == 200:
                st.balloons()
                st.success("✅ Enviado!")
            else: st.error("Erro no ID do Form.")
        except: st.error("Erro de conexão.")
