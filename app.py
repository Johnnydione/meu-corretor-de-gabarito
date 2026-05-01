import streamlit as st
import cv2
import numpy as np
import requests

# --- CONFIG ---
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ"
ID_NOME = "entry.263979686"
ID_RESPOSTAS = "entry.630983224"
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.title("Leitor de Gabarito - Versão Grid Real")

nome = st.text_input("Nome do Aluno")
img_file = st.file_uploader("Envie a foto", type=["jpg","png","jpeg"])

if img_file and nome:

    # -----------------------------
    # CARREGAR
    # -----------------------------
    file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)

    img = cv2.resize(img, (1000, 1400))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # -----------------------------
    # BINARIZAÇÃO FORTE
    # -----------------------------
    blur = cv2.GaussianBlur(gray, (5,5), 0)

    thresh = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        15, 3
    )

    # limpa ruído
    kernel = np.ones((3,3), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    # -----------------------------
    # DETECTAR BOLINHAS (BLOBS)
    # -----------------------------
    contours, _ = cv2.findContours(
        thresh,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE
    )

    pontos = []

    for c in contours:
        area = cv2.contourArea(c)

        if 30 < area < 500:  # tamanho típico de bolinha
            (x,y),r = cv2.minEnclosingCircle(c)
            pontos.append((int(x), int(y)))

    if len(pontos) < 200:
        st.error(f"Poucos pontos detectados ({len(pontos)})")
        st.stop()

    pontos = np.array(pontos)

    # -----------------------------
    # AGRUPAR POR LINHAS
    # -----------------------------
    pontos = pontos[pontos[:,1].argsort()]

    linhas = []
    tol = 12

    for p in pontos:
        colocado = False

        for linha in linhas:
            if abs(linha[0][1] - p[1]) < tol:
                linha.append(p)
                colocado = True
                break

        if not colocado:
            linhas.append([p])

    # ordenar linhas
    linhas = [sorted(l, key=lambda x: x[0]) for l in linhas]
    linhas.sort(key=lambda l: l[0][1])

    # -----------------------------
    # FILTRAR LINHAS COM ALTERNATIVAS
    # -----------------------------
    linhas_validas = [l for l in linhas if len(l) >= 5]

    if len(linhas_validas) < 80:
        st.error("Não consegui identificar as linhas do gabarito")
        st.stop()

    OPCOES = ['A','B','C','D','E']
    respostas = {}

    # -----------------------------
    # LER QUESTÕES
    # -----------------------------
    for i, linha in enumerate(linhas_validas[:90]):

        # pega 5 mais à esquerda (alternativas)
        linha = sorted(linha, key=lambda x: x[0])[:5]

        pixels = []

        for (x,y) in linha:

            r = 10

            roi = thresh[y-r:y+r, x-r:x+r]

            pixels.append(cv2.countNonZero(roi))

        v = sorted(pixels, reverse=True)
        p1, p2 = v[0], v[1]

        if p1 < 40:
            respostas[i+1] = "X"
        elif (p1 - p2) > p1 * 0.25:
            respostas[i+1] = OPCOES[np.argmax(pixels)]
        else:
            respostas[i+1] = "X"

    resultado = "".join([respostas.get(i, "X") for i in range(1,91)])

    # -----------------------------
    # OUTPUT
    # -----------------------------
    st.image(thresh, caption="Processado")
    st.write("Respostas:", resultado)

    if st.button("ENVIAR"):
        requests.post(FORM_URL, data={
            ID_NOME: nome,
            ID_RESPOSTAS: resultado
        })
        st.success("Enviado com sucesso!")
