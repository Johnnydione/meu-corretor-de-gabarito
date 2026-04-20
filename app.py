import streamlit as st
import cv2
import numpy as np
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Corretor Google Sheets", layout="wide")
st.title("Corretor Automático")

# --- CONEXÃO COM O GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/1eTdENl07I0w9M2BtspDJhz15c6Jrv0TxlXWF4SQLpjI/edit?gid=0#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- INTERFACE ---
nome_aluno = st.text_input("Nome do Aluno:")
foto = st.camera_input("Tirar foto do Gabarito")

if foto and nome_aluno:
    # 1. Processamento da Imagem (OMR)
    img_array = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img = cv2.imdecode(img_array, 1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    OPCOES = ['A', 'B', 'C', 'D', 'E']
    respostas_aluno = []

    # Fatiar em 90 questões
    fatias = np.array_split(thresh, 90)
    for fatia in fatias:
        opcoes_v = np.array_split(fatia, 5, axis=1)
        pixels = [cv2.countNonZero(opt) for opt in opcoes_v]
        respostas_aluno.append(OPCOES[np.argmax(pixels)])

    # 2. Preparar dados para o Google Sheets
    novo_dado = {"Nome": [nome_aluno]}
    for i, resp in enumerate(respostas_aluno):
        novo_dado[f"Q{i+1}"] = [resp]
    
    df_novo = pd.DataFrame(novo_dado)

    # 3. Enviar para o Google Sheets
    if st.button("ENVIAR RESULTADO PARA O GOOGLE SHEETS"):
        try:
            # Lê os dados atuais da planilha
            dados_existentes = conn.read(spreadsheet=url)
            # Junta o novo aluno com os antigos
            df_final = pd.concat([dados_existentes, df_novo], ignore_index=True)
            # Salva de volta na planilha
            conn.update(spreadsheet=url, data=df_final)
            st.success(f"✅ Dados de {nome_aluno} enviados para a planilha!")
        except Exception as e:
            st.error(f"Erro ao conectar: {e}. Verifique as permissões de compartilhamento da planilha.")

# Mostrar os últimos resultados na tela
if st.checkbox("Mostrar resultados da planilha"):
    df_atual = conn.read(spreadsheet=url)
    st.dataframe(df_atual)
