import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor Master", layout="centered")

st.title("🎯 Corretor Digital 90Q")

nome_aluno = st.text_input("1. Nome do Aluno:")

# O file_uploader funciona como o nosso "scanner"
foto_upload = st.file_uploader("2. Tire a foto ou escolha o arquivo", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    # 1. Carregar a imagem
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    # 2. Corrigir rotação e redimensionar
    h, w = img.shape[:2]
    if w > h:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
    img = cv2.resize(img, (800, 1100))
    img_viz = img.copy()
    
    # 3. Processamento para destacar as marcações
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Filtro para remover ruídos de fotos de alta resolução
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # 4. Desenhar a Grade de Conferência
    w_col = 800 // 3
    h_row = 1100 // 30
    # Colunas
    cv2.line(img_viz, (w_col, 0), (w_col, 1100), (255, 0, 0), 3)
    cv2.line(img_viz, (w_col*2, 0), (w_col*2, 1100), (255, 0, 0), 3)
    # Linhas
    for i in range(31):
        cv2.line(img_viz, (0, i * h_row), (800, i * h_row), (0, 255, 0), 1)

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
            # Ajuste de sensibilidade para fotos de alta qualidade
            if p_ord[0] < 50: 
                respostas_finais[q_num] = "BRANCO"
            elif (p_ord[0] - p_ord[1]) < 40:
                respostas_finais[q_num] = "DUPLA"
            else:
                respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

    # 6. Exibir Visualização e Botão
    st.subheader("3. Confira o Alinhamento")
    st.image(img_viz, use_container_width=True)
    
    lista_respostas = [respostas_finais[q] for q in range(1, 91)]
    texto_respostas = ", ".join(lista_respostas)
    
    st.write(f"**Gabarito Detectado:** {texto_respostas[:100]}...")

    # O BOTÃO DEVE FICAR AQUI, DENTRO DO BLOCO 'IF'
    if st.button("ENVIAR PARA PLANILHA AGORA"):
        with st.spinner('Enviando...'):
            dados = {ID_NOME: nome_aluno, ID_RESPOSTAS: texto_respostas}
            try:
                r = requests.post(FORM_URL, data=dados)
                if r.status_code == 200:
                    st.balloons()
                    st.success(f"✅ Sucesso! Respostas de {nome_aluno} enviadas.")
                else:
                    st.error(f"Erro no formulário: {r.status_code}")
            except:
                st.error("Erro de conexão com o Google.")
else:
    st.warning("Aguardando Nome e Foto para habilitar o envio.")
