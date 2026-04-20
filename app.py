import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

# Configuração da página (Deve ser a primeira coisa do script)
st.set_page_config(page_title="Corretor Pro 90", layout="wide")

# --- ESTILO PARA AUMENTAR A CÂMERA ---
st.markdown("""
    <style>
    div[data-testid="stCameraInput"] {
        width: 100% !important;
    }
    div[data-testid="stCameraInput"] video {
        border: 5px solid #00ff00 !important;
        border-radius: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 Corretor Inteligente (90 Q)")

nome_aluno = st.text_input("Nome do Aluno:")
foto = st.camera_input("Aponte para o Gabarito")

if foto and nome_aluno:
    # 1. Converter imagem
    img_array = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img = cv2.imdecode(img_array, 1)
    img_viz = img.copy() 
    
    # 2. Processamento
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Suaviza a imagem para evitar erros com sombras
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # 3. Lógica de Leitura
    respostas = []
    OPCOES = ['A', 'B', 'C', 'D', 'E']
    
    altura, largura = thresh.shape
    # Divide a altura total por 90 questões
    fatias_h = np.array_split(thresh, 90)
    
    for i, fatia in enumerate(fatias_h):
        # Desenha linhas horizontais na imagem de visualização
        y_pos = int((altura / 90) * i)
        cv2.line(img_viz, (0, y_pos), (largura, y_pos), (0, 255, 0), 2)
        
        # Divide a linha em 5 colunas (A, B, C, D, E)
        opcoes_v = np.array_split(fatia, 5, axis=1)
        # Conta pixels em cada coluna
        pixels = [cv2.countNonZero(opt) for opt in opcoes_v]
        indice_marcado = np.argmax(pixels)
        respostas.append(OPCOES[indice_marcado])

    # Mostrar a imagem com as marcações
    st.subheader("Visualização da Detecção:")
    st.image(img_viz, caption="As linhas verdes devem estar alinhadas com as questões do papel", use_container_width=True)
    
    texto_respostas = ", ".join(respostas)
    st.write(f"**Gabarito lido:** {texto_respostas[:80]}...")

    if st.button("ENVIAR PARA PLANILHA"):
        dados = {ID_NOME: nome_aluno, ID_RESPOSTAS: texto_respostas}
        try:
            r = requests.post(FORM_URL, data=dados)
            if r.status_code == 200:
                st.balloons()
                st.success(f"✅ Sucesso! Dados de {nome_aluno} enviados.")
            else:
                st.error(f"Erro no Google Forms (Status: {r.status_code})")
        except Exception as e:
            st.error(f"Erro de conexão: {e}")
