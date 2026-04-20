import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIGURAÇÃO ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor 90Q PRO", layout="centered")
st.title("🎯 Corretor Digital PRO")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Envie a FOTO", type=['jpg', 'jpeg', 'png'])

# --- FUNÇÃO PARA CORRIGIR PERSPECTIVA ---
def ordenar_pontos(pts):
    pts = pts.reshape(4, 2)
    soma = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    return np.array([
        pts[np.argmin(soma)],   # topo-esq
        pts[np.argmin(diff)],   # topo-dir
        pts[np.argmax(soma)],   # baixo-dir
        pts[np.argmax(diff)]    # baixo-esq
    ], dtype="float32")

def corrigir_perspectiva(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edged = cv2.Canny(blur, 50, 150)

    cnts, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    for c in cnts:
        peri = cv2.arcLength(c, True)
        aprox = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(aprox) == 4:
            pts = ordenar_pontos(aprox)
            (tl, tr, br, bl) = pts

            larguraA = np.linalg.norm(br - bl)
            larguraB = np.linalg.norm(tr - tl)
            alturaA = np.linalg.norm(tr - br)
            alturaB = np.linalg.norm(tl - bl)

            maxL = int(max(larguraA, larguraB))
            maxA = int(max(alturaA, alturaB))

            dst = np.array([
                [0, 0],
                [maxL - 1, 0],
                [maxL - 1, maxA - 1],
                [0, maxA - 1]
            ], dtype="float32")

            M = cv2.getPerspectiveTransform(pts, dst)
            warp = cv2.warpPerspective(img, M, (maxL, maxA))

            return warp

    return img  # fallback se não detectar

# --- PROCESSAMENTO ---
if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)

    # 🔥 NOVO: corrigir folha torta
    img = corrigir_perspectiva(img)

    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    colunas = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if h / w > 3:  # mais robusto
            colunas.append((x, y, w, h))

    colunas = sorted(colunas, key=lambda x: x[2]*x[3], reverse=True)[:3]
    colunas = sorted(colunas, key=lambda x: x[0])

    if len(colunas) == 3:
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']

        for i, (x, y, w, h) in enumerate(colunas):
            cv2.rectangle(img_viz, (x, y), (x+w, y+h), (0, 255, 0), 2)

            roi_col = thresh[y+5:y+h-5, x+5:x+w-5]
            h_roi, w_roi = roi_col.shape
            start_q = [1, 31, 61][i]

            for q_idx in range(30):
                q_num = start_q + q_idx

                y1 = int(q_idx * (h_roi / 30))
                y2 = int((q_idx + 1) * (h_roi / 30))

                fatia = roi_col[y1:y2, :]
                fatias = np.array_split(fatia, 5, axis=1)

                pixels = []
                for f in fatias:
                    hf, wf = f.shape
                    miolo = f[int(hf*0.1):int(hf*0.9), int(wf*0.1):int(wf*0.9)]
                    pixels.append(cv2.countNonZero(miolo))

                v_ord = sorted(pixels, reverse=True)
                p1, p2 = v_ord[0], v_ord[1]

                if p1 < 10:
                    respostas_finais[q_num] = "X"
                elif p1 > 50 and (p1 - p2) > (p1 * 0.2):
                    respostas_finais[q_num] = OPCOES[np.argmax(pixels)]
                else:
                    respostas_finais[q_num] = "X"

                # DEBUG visual
                cv2.putText(img_viz, respostas_finais[q_num],
                            (x+5, y + int((q_idx+0.5)*(h/30))),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,0,0), 1)

        st.image(img_viz)

        resultado_str = "".join([respostas_finais.get(q, "X") for q in range(1, 91)])

        st.write(f"**Nome:** {nome_aluno}")
        st.write(f"**Respostas:** {resultado_str}")

        if st.button("ENVIAR"):
            requests.post(FORM_URL, data={ID_NOME: nome_aluno, ID_RESPOSTAS: resultado_str})
            st.success("Enviado com sucesso!")
            st.balloons()

    else:
        st.error(f"Erro: detectei {len(colunas)} colunas. Tente melhorar a foto.")
