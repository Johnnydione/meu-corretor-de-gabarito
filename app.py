import streamlit as st
import cv2
import numpy as np
import requests

# CONFIG
ID_DO_FORM = "1FAIpQLSfDtXbWM__6tHs_fk-6IQSHJpuCmvKDDSArfFFfYrJEGuTLTQ"
ID_NOME = "entry.263979686"
ID_RESPOSTAS = "entry.630983224"
FORM_URL = f"https://docs.google.com/forms/d/e/{ID_DO_FORM}/formResponse"

st.title("Leitor Profissional de Gabarito")

nome = st.text_input("Nome")
img_file = st.file_uploader("Foto", type=["jpg","png","jpeg"])

if img_file and nome:

    file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)

    img = cv2.resize(img, (1000, 1400))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # DETECTAR CÍRCULOS (TODOS)
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=20,
        param1=100,
        param2=18,
        minRadius=5,
        maxRadius=20
    )

    if circles is None:
        st.error("Nenhum ponto detectado")
        st.stop()

    circles = np.round(circles[0]).astype(int)

    pontos = np.array([[x, y] for x,y,r in circles])

    # -----------------------------
    # AGRUPAR POR LINHAS
    # -----------------------------
    pontos = pontos[pontos[:,1].argsort()]

    linhas = []
    tolerancia = 15

    for p in pontos:
        colocado = False

        for linha in linhas:
            if abs(linha[0][1] - p[1]) < tolerancia:
                linha.append(p)
                colocado = True
                break

        if not colocado:
            linhas.append([p])

    # ordenar cada linha
    for linha in linhas:
        linha.sort(key=lambda x: x[0])

    # ordenar linhas
    linhas.sort(key=lambda l: l[0][1])

    # -----------------------------
    # FILTRAR LINHAS REAIS (questões)
    # -----------------------------
    linhas_validas = [l for l in linhas if len(l) >= 5]

    if len(linhas_validas) < 50:
        st.error("Poucas linhas detectadas")
        st.stop()

    OPCOES = ['A','B','C','D','E']
    respostas = {}

    for i, linha in enumerate(linhas_validas[:90]):

        # pegar apenas 5 primeiros pontos (alternativas)
        linha = linha[:5]

        linha = sorted(linha, key=lambda x: x[0])

        pixels = []

        for (x,y) in linha:
            r = 12

            y1 = max(y-r, 0)
            y2 = y+r
            x1 = max(x-r, 0)
            x2 = x+r

            roi = gray[y1:y2, x1:x2]

            _, th = cv2.threshold(roi, 0, 255,
                cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            pixels.append(cv2.countNonZero(th))

        v = sorted(pixels, reverse=True)
        p1, p2 = v[0], v[1]

        if p1 < 50:
            respostas[i+1] = "X"
        elif (p1 - p2) > p1 * 0.25:
            respostas[i+1] = OPCOES[np.argmax(pixels)]
        else:
            respostas[i+1] = "X"

    resultado = "".join([respostas.get(i,"X") for i in range(1,91)])

    st.image(img, caption="Imagem analisada")
    st.write("Respostas:", resultado)

    if st.button("ENVIAR"):
        requests.post(FORM_URL, data={
            ID_NOME: nome,
            ID_RESPOSTAS: resultado
        })
        st.success("Enviado!")
