import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor 90Q Precision", layout="centered")
st.title("🎯 Corretor Digital Pro")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Envie o gabarito", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Threshold um pouco mais baixo para garantir que o "preto" seja bem detectado
    thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)[1]

    # Filtro morfológico para manter os retângulos
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
    mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    colunas = sorted([c for c in cnts if cv2.contourArea(c) > 50000], key=lambda x: cv2.boundingRect(x)[0])[:3]

    if len(colunas) == 3:
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']

        for i, c in enumerate(colunas):
            x, y, w, h = cv2.boundingRect(c)
            # Margem interna para não ler a borda do retângulo
            roi_col = thresh[y+5:y+h-5, x+3:x+w-3]
            h_roi, w_roi = roi_col.shape
            start_q = [1, 31, 61][i]

            for q_idx in range(30):
                q_num = start_q + q_idx
                y1 = int(q_idx * (h_roi / 30))
                y2 = int((q_idx + 1) * (h_roi / 30))
                
                linha = roi_col[y1:y2, :]
                fatias = np.array_split(linha, 5, axis=1)
                
                contagem = []
                for fatia in fatias:
                    hf, wf = fatia.shape
                    # Pega o miolo da bolinha
                    miolo = fatia[int(hf*0.25):int(hf*0.75), int(wf*0.25):int(wf*0.75)]
                    contagem.append(cv2.countNonZero(miolo))
                
                # --- LÓGICA DE SENSIBILIDADE AJUSTADA ---
                # Ordenamos para comparar o maior com o segundo maior
                votos_ordenados = sorted(contagem, reverse=True)
                maior_voto = votos_ordenados[0]
                segundo_maior = votos_ordenados[1]
                
                # 1. Critério de Branco: Se o maior voto for quase nada
                if maior_voto < 5: 
                    respostas_finais[q_num] = "BRANCO"
                
                # 2. Critério de Dupla: Se a diferença entre o 1º e o 2º for pequena
                # (Significa que duas bolinhas estão pintadas com força similar)
                elif (maior_voto - segundo_maior) < (maior_voto * 0.4):
                    respostas_finais[q_num] = "DUPLA"
                
                # 3. Resposta Única
                else:
                    respostas_finais[q_num] = OPCOES[np.argmax(contagem)]

        st.image(img_viz)
        resultado_str = ", ".join([respostas_finais.get(q, "BRANCO") for q in range(1, 91)])
        st.write(f"**Detectado:** {resultado_str[:200]}...")

        if st.button("ENVIAR"):
            requests.post(FORM_URL, data={ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str})
            st.balloons()
            st.success("Enviado!")
    else:
        st.error(f"Detectadas {len(colunas)} colunas. Verifique o enquadramento.")
