import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS (JÁ ATUALIZADO COM SEUS DADOS) ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Corretor Pro 3-Col", layout="wide")

# --- ESTILO PARA AUMENTAR A CÂMERA ---
st.markdown("""
    <style>
    div[data-testid="stCameraInput"] {
        width: 100% !important;
        max-width: 800px !important;
        margin: 0 auto;
    }
    div[data-testid="stCameraInput"] video {
        border: 8px solid #00ff00 !important;
        border-radius: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 Sistema de Correção (Gabarito 3-Colunas)")
st.info("Alinhe os 4 cantos pretos do papel nas bordas verdes da câmera.")

nome_aluno = st.text_input("Nome do Aluno:", placeholder="Digite o nome completo")
foto = st.camera_input("Tirar Foto")

if foto and nome_aluno:
    # 1. Converter imagem recebida
    img_array = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img = cv2.imdecode(img_array, 1)
    img_viz = img.copy() 
    
    # 2. Processamento para leitura (Preto e Branco)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # --- LÓGICA DE DETECÇÃO PARA 3 COLUNAS ---
    respostas_finais = {}
    OPCOES = ['A', 'B', 'C', 'D', 'E']
    altura_total, largura_total = thresh.shape

    # Desenha linhas azuis para mostrar onde o Python está dividindo as colunas
    w_col = int(largura_total / 3)
    cv2.line(img_viz, (w_col, 0), (w_col, altura_total), (255, 0, 0), 3)
    cv2.line(img_viz, (w_col * 2, 0), (w_col * 2, altura_total), (255, 0, 0), 3)

    # Processar cada uma das 3 colunas principais
    colunas_fatias = np.array_split(thresh, 3, axis=1)
    for c_idx, coluna in enumerate(colunas_fatias):
        start_q = (c_idx * 30) + 1 # Q1, Q31 ou Q61
        
        # Divide cada coluna em 30 questões (linhas)
        questoes = np.array_split(coluna, 30)
        
        for q_idx, questao in enumerate(questoes):
            q_num = start_q + q_idx
            
            # Divide cada questão em 5 alternativas (A, B, C, D, E)
            alternativas = np.array_split(questao, 5, axis=1)
            pixels = [cv2.countNonZero(alt) for alt in alternativas]
            
            # Identifica a opção com mais marcação
            indice_marcado = np.argmax(pixels)
            respostas_finais[q_num] = OPCOES[indice_marcado]

    # Transforma em uma única linha de texto separada por vírgula
    respostas_ordenadas = [respostas_finais[q] for q in range(1, 91)]
    texto_respostas = ", ".join(respostas_ordenadas)

    # Mostrar visualização do processamento
    st.subheader("Visualização do Alinhamento:")
    st.image(img_viz, caption="As linhas azuis devem ficar no espaço entre as colunas do seu papel", use_container_width=True)
    
    st.write(f"**Gabarito detectado:** {texto_respostas[:80]}...")

    # 4. Botão de Envio para o Google Forms
    if st.button("ENVIAR PARA PLANILHA"):
        dados_envio = {ID_NOME: nome_aluno, ID_RESPOSTAS: texto_respostas}
        try:
            r = requests.post(FORM_URL, data=dados_envio)
            if r.status_code == 200:
                st.balloons()
                st.success(f"✅ Feito! Os dados de {nome_aluno} já estão no Google Sheets.")
            else:
                st.error(f"Erro ao enviar. Código: {r.status_code}")
        except Exception as e:
            st.error(f"Erro de conexão: {e}")
