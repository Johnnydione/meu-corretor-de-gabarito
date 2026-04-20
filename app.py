import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS (COLE SEUS DADOS AQUI) ---
# Substitua o que está entre aspas pelos dados que você extraiu do seu link
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 

# Aqui o código monta o link de envio automaticamente
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Corretor Pro 90", layout="centered")
st.title("🎯 Corretor Automático (90 Questões)")

nome_aluno = st.text_input("Nome do Aluno:")
foto = st.camera_input("Tire a foto do Gabarito")

if foto and nome_aluno:
    # 1. Converter imagem
    img_array = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img = cv2.imdecode(img_array, 1)
    
    # 2. Processamento da imagem (Transforma em preto e branco)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # 3. Lógica de Leitura (Simulando 90 fatias)
    respostas = []
    OPCOES = ['A', 'B', 'C', 'D', 'E']
    
    # Divide a imagem em 90 linhas horizontais
    fatias = np.array_split(thresh, 90)
    
    for fatia in fatias:
        # Divide cada linha em 5 colunas
        opcoes_v = np.array_split(fatia, 5, axis=1)
        pixels = [cv2.countNonZero(opt) for opt in opcoes_v]
        indice_marcado = np.argmax(pixels)
        respostas.append(OPCOES[indice_marcado])
    
    # Junta as 90 respostas em um texto só separado por vírgula
    texto_respostas = ", ".join(respostas)

    st.success("Leitura concluída!")
    st.write(f"**Respostas detectadas:** {texto_respostas[:50]}...") # Mostra só o começo pra não poluir

    # 4. Botão de Envio
    if st.button("ENVIAR PARA PLANILHA"):
        # Monta os dados para o Google
        dados_para_envio = {
            ID_NOME: nome_aluno,
            ID_RESPOSTAS: texto_respostas
        }
        
        try:
            resposta = requests.post(FORM_URL, data=dados_para_envio)
            if resposta.status_code == 200:
                st.balloons()
                st.success(f"✅ Dados de {nome_aluno} enviados com sucesso!")
            else:
                st.error("Erro ao enviar. Verifique se o ID do Formulário está correto.")
        except:
            st.error("Erro de conexão. Tente novamente.")
