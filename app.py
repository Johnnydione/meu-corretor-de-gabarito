import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIG ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ" 
ID_NOME = "entry.263979686"    
ID_RESPOSTAS = "entry.630983224" 
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.set_page_config(page_title="Corretor PRO", layout="centered")
st.title("🎯 Corretor Digital PRO")

nome_aluno = st.text_input("1. Nome do Aluno:")
foto_upload = st.file_uploader("2. Envie a FOTO", type=['jpg', 'jpeg', 'png'])

# -----------------------------
# 📐 CORREÇÃO DE PERSPECTIVA
# -----------------------------
def ordenar_pontos(pts):
    pts = pts.reshape(4, 2)
    soma = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    return np.array([
        pts[np.argmin(soma)],
        pts[np.argmin(diff)],
        pts[np.argmax(soma)],
        pts[np.argmax(diff)]
    ], dtype="float32")

def corrigir_perspectiva(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edged = cv2.Canny(blur, 50, 150)

    cnts, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    for c in cnts[:5]:  # tenta só os maiores
        peri = cv2.arcLength(c, True)
        aprox = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(aprox) == 4:
            pts = ordenar_pontos(aprox)
            (tl, tr, br, bl) = pts

            largura = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
            altura = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))

            # ⚠️ validação básica (evita pegar coisa errada)
            if largura < 500 or altura < 800:
                continue

            dst = np.array([
                [0, 0],
                [largura-1, 0],
                [largura-1, altura-1],
                [0, altura-1]
            ], dtype="float32")

            M = cv2.getPerspectiveTransform(pts, dst)
            warp = cv2.warpPerspective(img, M, (largura, altura))

            return warp

    return img  # fallback

# -----------------------------
# 🔄 PROCESSAMENTO
# -----------------------------
if foto_upload and nome_aluno:
    file_bytes = np.asarray(bytearray(foto_upload.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)

    # perspectiva segura
    img = corrigir_perspectiva(img)

    img = cv2.resize(img, (1000, 1400))
    img_viz = img.copy()

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # -----------------------------
    # 🧠 THRESHOLD INTELIGENTE
    # -----------------------------
    _, thresh = cv2.threshold(gray, 0, 255,
                              cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # fallback se imagem ruim
    if np.mean(thresh) < 15:
        thresh = cv2.adaptiveThreshold(gray, 255,
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 21, 5)

    # DEBUG (pode comentar depois)
    st.image(thresh, caption="Threshold")

    # -----------------------------
    # 🔍 CONTORNOS
    # -----------------------------
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    colunas = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)

        # filtro mais flexível
        if h > 300 and w > 50:
            colunas.append((x, y, w, h))

    # pega maiores áreas
    colunas = sorted(colunas, key=lambda x: x[2]*x[3], reverse=True)[:5]

    # ordena da esquerda pra direita
    colunas = sorted(colunas, key=lambda x: x[0])

    # pega só 3 melhores
    colunas = colunas[:3]

    # DEBUG contornos
    img_debug = img.copy()
    for (x,y,w,h) in colunas:
        cv2.rectangle(img_debug, (x,y), (x+w,y+h), (0,255,0), 2)

    st.image(img_debug, caption="Colunas detectadas")

    # -----------------------------
    # 🎯 LEITURA
    # -----------------------------
    if len(colunas) == 3:
        respostas_finais = {}
        OPCOES = ['A', 'B', 'C', 'D', 'E']

        for i, (x, y, w, h) in enumerate(colunas):
            roi = thresh[y+5:y+h-5, x+5:x+w-5]
            h_roi, w_roi = roi.shape

            start_q = [1, 31, 61][i]

            for q_idx in range(30):
                q_num = start_q + q_idx

                y1 = int(q_idx * (h_roi / 30))
                y2 = int((q_idx + 1) * (h_roi / 30))

                fatia = roi[y1:y2, :]
                partes = np.array_split(fatia, 5, axis=1)

                pixels = []
                for p in partes:
                    hp, wp = p.shape
                    miolo = p[int(hp*0.2):int(hp*0.8),
                              int(wp*0.2):int(wp*0.8)]
                    pixels.append(cv2.countNonZero(miolo))

                v = sorted(pixels, reverse=True)
                p1, p2 = v[0], v[1]

                if p1 < 15:
                    respostas_finais[q_num] = "X"
                elif p1 > 50 and (p1 - p2) > (p1 * 0.2):
                    respostas_finais[q_num] = OPCOES[np.argmax(pixels)]
                else:
                    respostas_finais[q_num] = "X"

                # debug visual
                cv2.putText(img_viz, respostas_finais[q_num],
                            (x+5, y + int((q_idx+0.5)*(h/30))),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,0,0), 1)

        st.image(img_viz, caption="Resultado final")

        resultado_str = "".join([respostas_finais.get(q, "X") for q in range(1, 91)])

        st.write(f"**Nome:** {nome_aluno}")
        st.write(f"**Respostas:** {resultado_str}")

        if st.button("ENVIAR"):
            requests.post(FORM_URL, data={
                ID_NOME: nome_aluno,
                ID_RESPOSTAS: resultado_str
            })
            st.success("Enviado!")
            st.balloons()

    else:
        st.error(f"Detectei {len(colunas)} colunas. Tente melhorar a foto.")
