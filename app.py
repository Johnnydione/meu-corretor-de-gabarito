import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO DO GOOGLE FORMS ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor Pro - Vértice a Vértice", layout="centered")

st.title("🎯 Corretor Digital Pro")
st.write("Alinhamento preciso pelos vértices internos das âncoras.")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Tire a foto ou escolha o arquivo", type=['jpg', 'jpeg', 'png'])

if foto_upload and nome_aluno:
    # 1. Carregar imagem
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    # 2. Corrigir orientação e redimensionar
    h, w = img.shape[:2]
    if w > h: 
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # 3. LOCALIZAR CENTROS DOS QUADRADOS
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centros = []
    for c in cnts:
        area = cv2.contourArea(c)
        if 400 < area < 10000: # Filtra tamanhos compatíveis com as âncoras
            M = cv2.moments(c)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                centros.append((cX, cY))

    # 4. DEFINIR ÁREA PELOS VÉRTICES (PONTOS MÉDIOS/INTERNOS)
    if len(centros) >= 4:
        # Ordenar centros para identificar: Topo-Esq, Topo-Dir, Base-Esq, Base-Dir
        centros = sorted(centros, key=lambda p: p[1]) # Ordena por Y
        topo = sorted(centros[:2], key=lambda p: p[0]) # Dois de cima ordenados por X
        base = sorted(centros[-2:], key=lambda p: p[0]) # Dois de baixo ordenados por X
        
        # PONTOS DE CORTE (Vértices internos aproximados pelos centros das âncoras)
        x_min = max(topo[0][0], base[0][0])
        x_max = min(topo[1][0], base[1][0])
        y_min = max(topo[0][1], topo[1][1])
        y_max = min(base[0][1], base[1][1])

        # Ajuste Fino: Para partir do vértice, tiramos metade da largura estimada da âncora (ex: 15px)
        margem_ancora = 20 
        x_start, y_start = x_min + margem_ancora, y_min + margem_ancora
        x_end, y_end = x_max - margem_ancora, y_max - margem_ancora

        roi_thresh = thresh[y_start:y_end, x_start:x_end]
        img_viz_roi = img_viz[y_start:y_end, x_start:x_end]
        
        # Desenha o retângulo de leitura azul PARTINDO DO CANTO INTERNO
        cv2.rectangle(img_viz, (x_start, y_start), (x_end, y_end), (255, 0, 0), 3)
        
        # 5. PROCESSAR GRADE (DENTRO DA ÁREA ÚTIL)
        alt_roi, larg_roi = roi_thresh.shape
        w_col = larg_roi // 3
        h_row = alt_roi // 30
        
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']
        
        for c_idx in range(3):
            coluna_img = roi_thresh[:, c_idx*w_col : (c_idx+1)*w_col]
            cv2.line(img_viz_roi, (c_idx*w_col, 0), (c_idx*w_col, alt_roi), (255, 0, 0), 2)
            
            start_q = (c_idx * 30) + 1
            for q_idx in range(30):
                q_num = start_q + q_idx
                y_start_q = q_idx * h_row
                y_end_q = (q_idx + 1) * h_row
                
                cv2.line(img_viz_roi, (c_idx*w_col, y_start_q), ((c_idx+1)*w_col, y_start_q), (0, 255, 0), 1)
                
                questao_crop = coluna_img[y_start_q:y_end_q, :]
                alternativas = np.array_split(questao_crop, 5, axis=1)
                pixels = [cv2.countNonZero(alt) for alt in alternativas]
                p_ord = sorted(pixels, reverse=True)
                
                if p_ord[0] < 30:
                    respostas_finais[q_num] = "BRANCO"
                elif (p_ord[0] - p_ord[1]) < 25:
                    respostas_finais[q_num] = "DUPLA"
                else:
                    respostas_finais[q_num] = OPCOES[np.argmax(pixels)]

        # 6. EXIBIR RESULTADOS
        st.subheader("3. Conferência Visual")
        st.image(img_viz, use_container_width=True)
        
        resultado_str = ", ".join([respostas_finais[q] for q in range(1, 91)])
        st.write(f"**Gabarito Lido:** {resultado_str[:120]}...")

        if st.button("ENVIAR PARA GOOGLE SHEETS"):
            dados = {ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str}
            res = requests.post(FORM_URL, data=dados)
            if res.status_code == 200:
                st.balloons()
                st.success("Enviado com sucesso!")
            else:
                st.error("Erro ao enviar.")
    else:
        st.warning("⚠️ Localizei apenas {} de 4 âncoras. Garanta que os cantos estão visíveis.".format(len(centros)))
        st.image(img_viz, caption="Âncora(s) detectada(s).", use_container_width=True)
