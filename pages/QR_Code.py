import streamlit as st
import pandas as pd
import io
from auth import check_authentication
import qrcode
from PIL import Image

check_authentication()

st.set_page_config(
    page_title="Gerador de QR Code",
    page_icon=" ",
    layout="wide"
)
# Título da aplicação
st.title("Gerador de QR Code")

# Entrada para o nome do participante e o link do evento
nome = st.text_input("Digite o nome Evento:")
link = st.text_input("Digite o link do evento:")

# Gerar o QR Code quando o botão for pressionado
if st.button("Gerar QR Code"):
    if nome and link:
        # Criar um objeto QRCode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        # Adicionar o link ao QR Code
        qr.add_data(link)
        qr.make(fit=True)

        # Criar uma imagem do QR Code
        img = qr.make_image(fill_color="black", back_color="white")

        # Converter a imagem para um formato adequado para Streamlit
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()

        # Exibir a imagem do QR Code
        st.image(img_byte_arr, caption="QR Code Gerado", use_container_width=True)

        # Adicionar botão para download
        st.download_button(
            label="Baixar QR Code",
            data=img_byte_arr,
            file_name=f"QR_Code_{nome}.png",
            mime="image/png"
        )

        st.success(f"QR Code gerado e pronto para ser baixado.")
    else:
        st.warning("Por favor, insira o nome do participante e o link do evento.")
