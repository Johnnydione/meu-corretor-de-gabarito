import streamlit as st
import cv2
import numpy as np
import pandas as pd

st.set_page_config(page_title="Corretor 90 Questões", layout="wide")
st.title("📝 Corretor Pro: 90 Questões + Planilha")

# --- INTERFACE ---
nome_aluno = st.text_input("Nome do Aluno:", placeholder="Digite o nome completo")
foto = st.camera_input("Tirar foto do Gabarito")

# Criar uma "memória" para guardar os resultados se não existir
if 'dados' not in st.session_state:
    st.session_state.dados = []

if foto and nome_aluno:
    # 1. Processar Imagem
    img_array = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img = cv2.imdecode(img_array, 1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # 2. Lógica para 90 questões
    # Vamos supor que seu gabarito tem 3 colunas de 30 questões
    questoes_total = 90
    respostas_aluno = []
    OPCOES = ['A', 'B', 'C', 'D', 'E']

    # Divisão simplificada (90 fatias horizontais)
    fatias = np.array_split(thresh, questoes_total)

    for i, fatia in enumerate(fatias):
        opcoes_v = np.array_split(fatia, 5, axis=1)
        pixels = [cv2.countNonZero(opt) for opt in opcoes_v]
        indice_marcado = np.argmax(pixels)
        respostas_aluno.append(OPCOES[indice_marcado])

    # 3. Salvar na Memória do Site
    resultado = {"Nome": nome_aluno}
    for i, resp in enumerate(respostas_aluno):
        resultado[f"Q{i+1}"] = resp
    
    # Adiciona à lista de resultados
    if st.button("Confirmar e Salvar na Planilha"):
        st.session_state.dados.append(resultado)
        st.success(f"Dados de {nome_aluno} salvos com sucesso!")

# --- PARTE DA PLANILHA ---
if st.session_state.dados:
    st.divider()
    st.subheader("📊 Planilha de Resultados")
    df = pd.DataFrame(st.session_state.dados)
    st.dataframe(df) # Mostra a tabela no site

    # Botão para baixar o arquivo Excel/CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Planilha Completa (Excel/CSV)",
        data=csv,
        file_name='resultados_simulado.csv',
        mime='text/csv',
    )
