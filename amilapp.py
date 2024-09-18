import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
from io import StringIO
import folium
from streamlit_folium import folium_static
import branca.colormap as cm
from folium.features import GeoJson, GeoJsonTooltip
import matplotlib.pyplot as plt
import plotly.express as px
import locale
import streamlit as st
from pinecone import Pinecone
from pinecone_plugins.assistant.models.chat import Message
import branca

st.set_page_config(layout="wide", page_title="Beranda Si Amil Zakatkuy", page_icon="static/logo.svg", initial_sidebar_state="collapsed")

locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')

st.header("Beranda Si Amil Zakatkuy", divider="green")

# Load data dari file CSV
data = pd.read_csv('data/data baznas.csv')

# Filter data kolom yang relevan
data = data[['provinsi', 'tahun', 'jumlah_pengumpulan', 'jumlah_penyaluran']]

# Hitung rasio penyaluran/penerimaan zakat
data['rasio'] = data['jumlah_penyaluran'] / data['jumlah_pengumpulan']

data['efektivitas'] = pd.cut(data['rasio'], bins=[0, 0.2, 0.5, 0.7, 0.9, 5], labels=['Tidak Efektif', 'Dibawah Efektif', 'Cukup Efektif', 'Efektif', 'Sangat Efektif'])

# efektiivitas dalam label 1-5
data['efektivitas code'] = pd.cut(data['rasio'], bins=[0, 0.2, 0.5, 0.7, 0.9, 5], labels=[1, 2, 3, 4, 5])

# Fetch the GeoJSON file from URL
url = 'https://raw.githubusercontent.com/ans-4175/peta-indonesia-geojson/master/indonesia-prov.geojson'
response = requests.get(url)
geojson_data = response.text

# Read GeoJSON into GeoDataFrame
gdf = gpd.read_file(StringIO(geojson_data))

# Mapping dari GeoDataFrame ke data zakat
provinsi_mapping = {
    'DI. ACEH': 'ACEH',
    'DAERAH ISTIMEWA YOGYAKARTA': 'DI YOGYAKARTA',
    'BANGKA BELITUNG': 'KEP. BANGKA BELITUNG',
    'NUSATENGGARA BARAT': 'NUSA TENGGARA BARAT',
    'NUSA TENGGARA TIMUR': 'NUSA TENGGARA TIMUR',
    'PAPUA BARAT': 'PAPUA BARAT',
}

# Terapkan mapping ke GeoDataFrame
gdf['Propinsi'] = gdf['Propinsi'].replace(provinsi_mapping)

# User selects year from a slider
selected_year = st.select_slider(
    'Pilih Tahun',
    options=sorted(data['tahun'].unique())
)

# Filter data berdasarkan tahun yang dipilih
data_filtered = data[data['tahun'] == selected_year]

# buat 2 st column
col1, col2, col3 = st.columns([3, 3, 2])

def format_nominal(nominal):
  """Memformat nominal menjadi string dengan akhiran 'juta' atau 'milyar'."""
  if nominal >= 1_000_000_000_000:
    return f"Rp {nominal / 1_000_000_000_000:.3f} triliun"
  elif nominal >= 1_000_000_000:
    return f"Rp {nominal / 1_000_000_000:.3f} miliar"
  elif nominal >= 1_000_000:
    return f"Rp {nominal / 1_000_000:.1f} juta"
  else:
    return f"Rp {locale.format_string('%d', nominal, grouping=True)}"

# Kolom 1 diisi st.container border true dengan st.metrics dari pengumpulan
with col1:
    total_pengumpulan = data_filtered['jumlah_pengumpulan'].sum()
    st.container(border=True)
    st.metric(
        label='Total Pengumpulan Zakat',
        value=format_nominal(total_pengumpulan)
    )

# Kolom 2 diisi st.container border true dengan st.metrics dari penyaluran
with col2:
    total_penyaluran = data_filtered['jumlah_penyaluran'].sum()
    st.container(border=True)
    st.metric(
        label='Total Penyaluran Zakat',
        value=format_nominal(total_penyaluran)
    )

# Kolom 3 diisi st.container border true dengan st.metrics dari rasio
with col3:
    rasio = total_penyaluran / total_pengumpulan
    st.container(border=True)
    st.metric(
        label='Allocation to Collection Ratio (ACR)',
        value=f"{rasio:.2%}"
    )
    

# Merge GeoDataFrame with filtered zakat data
merged = gdf.set_index('Propinsi').join(data_filtered.set_index('provinsi'))

# Reset index so that we can use the province names as a column
merged = merged.reset_index()

# Create a folium map centered around Indonesia
m = folium.Map(location=[-2.5, 118], zoom_start=4)

# Define custom color scale for efektivitas (with text labels)
color_scale = [
    (1, 'red', 'Tidak Efektif'),     
    (2, 'orange', 'Dibawah Efektif'),  
    (3, 'yellow', 'Cukup Efektif'), 
    (4, 'limegreen', 'Efektif'), 
    (5, 'green', 'Sangat Efektif')   
]

# Create a colormap using custom color scale (with text labels in caption)
colormap = branca.colormap.LinearColormap(
    colors=[color[1] for color in color_scale],
    index=[color[0] for color in color_scale],
    vmin=merged['efektivitas code'].min(),
    vmax=merged['efektivitas code'].max(),
    caption='Efektivitas'  
).to_step(n=len(color_scale))  

# Add GeoJson to folium map with dynamic color based on 'efektivitas code'
geojson = folium.GeoJson(
    merged,
    style_function=lambda feature: {
        'fillColor': colormap(feature['properties']['efektivitas code']) if feature['properties']['efektivitas code'] else '#gray',
        'color': 'black',
        'weight': 0.5,
        'fillOpacity': 0.7,
    },
    tooltip=GeoJsonTooltip(
        fields=['Propinsi', 'efektivitas', 'rasio', 'jumlah_pengumpulan', 'jumlah_penyaluran'],
        aliases=['Provinsi', 'Efektivitas', 'Allocation to Collection Ratio (ACR)', 'Jumlah Pengumpulan Zakat', 'Jumlah Penyaluran Zakat'],
        localize=True
    )
).add_to(m)

col1, col2 = st.columns([3, 2])

with col1:
    # Add the colormap to the map
    colormap.add_to(m)

    # title for map using st.markdown
    st.markdown(f"### Peta Rasio Alokasi ke Pengumpulan Zakat Tahun {selected_year}")

    # Display the map 
    folium_static(m)


# buat data yang berisi jumlah count agregasi efektivitas
data_agg_efektivitas = data.groupby(['tahun', 'efektivitas'])[['jumlah_pengumpulan', 'jumlah_penyaluran']].count().reset_index()

# Filter data berdasarkan tahun yang dipilih
data_filtered_efektivitas = data_agg_efektivitas[data_agg_efektivitas['tahun'] == selected_year]

# Define the order of effectiveness categories for sorting
effectiveness_order = ["Sangat Efektif", "Efektif", "Cukup Efektif", "Dibawah Efektif", "Tidak Efektif"]

# Sort the data_filtered_efektivitas DataFrame based on the effectiveness order
data_filtered_efektivitas['efektivitas'] = pd.Categorical(data_filtered_efektivitas['efektivitas'], categories=effectiveness_order, ordered=True)
data_filtered_efektivitas = data_filtered_efektivitas.sort_values('efektivitas')

# Define the color mapping for the effectiveness categories
color_mapping = {
    "Tidak Efektif": 'red',
    "Dibawah Efektif": 'orange',
    "Cukup Efektif": 'yellow',
    "Efektif": 'limegreen',
    "Sangat Efektif": 'green'
}

# Create the Plotly donut chart with custom colors and sorted legend
fig2 = px.pie(data_filtered_efektivitas, 
             values='jumlah_penyaluran', 
             names='efektivitas', 
             title=f'Efektivitas Penyaluran Zakat Tahun {selected_year}',
             hole=0.4,
             color='efektivitas', 
             color_discrete_map=color_mapping,
             category_orders={"efektivitas": effectiveness_order}
             ) 

fig2.update_layout(
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True)
    )

with col2:
    # Display the chart in Streamlit
    st.plotly_chart(fig2, use_container_width=True)

# Tambahkan opsi 'Semua Provinsi'
provinsi_list = sorted(data['provinsi'].unique())
provinsi_list.insert(0, 'Semua Provinsi')

# Multiselect for provinces with 'Semua Provinsi' as default
selected_provinces = st.multiselect(
    'Pilih Provinsi',
    options=provinsi_list,
    default='Semua Provinsi'
)

# Filter data based on selected provinces
if 'Semua Provinsi' in selected_provinces:
    data_filtered_prov = data 
else:
    data_filtered_prov = data[data['provinsi'].isin(selected_provinces)]

# Aggregate data by year
data_agg = data_filtered_prov.groupby('tahun').agg({
    'jumlah_pengumpulan': 'sum',
    'jumlah_penyaluran': 'sum'
}).reset_index()

# Prepare the data for Plotly
data_melted = pd.melt(data_agg, id_vars=['tahun'], value_vars=['jumlah_pengumpulan', 'jumlah_penyaluran'], 
                      var_name='Jenis Zakat', value_name='Jumlah')

# penerimaan zakat per provinsi, line chart
data_penerimaan_provinsi = data.groupby(['provinsi', 'tahun'])['jumlah_pengumpulan'].sum().reset_index()


# Create the Plotly bar chart
fig = px.bar(data_melted, 
            x='tahun', 
            y='Jumlah', 
            color='Jenis Zakat', 
            barmode='group',
            labels={'Jumlah': 'Jumlah Zakat (Rupiah)', 'tahun': 'Tahun'},
            title='Penerimaan dan Penyaluran Zakat per Tahun')    

fig.update_layout(
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True)
    )

col1, col2 = st.columns(2)

with col1:
    # Display the chart in Streamlit
    st.plotly_chart(fig, use_container_width=True)

fig2 = px.line(data_penerimaan_provinsi, x='tahun', y='jumlah_pengumpulan', color='provinsi',
                labels={'jumlah_pengumpulan': 'Jumlah Penerimaan Zakat (Rupiah)', 'tahun': 'Tahun'},
                title='Penerimaan Zakat per Provinsi')

fig2.update_layout(
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True)
    )

with col2:
    st.plotly_chart(fig2, use_container_width=True)

import google.generativeai as genai

# Sidebar select box for model selection
model_option = st.sidebar.selectbox(
    "Pilih Model AI:",
    ("Pinecone", "Gemini")
)

# Initialize session state for messages
if "messages" not in st.session_state:
    st.session_state["messages"] = []

messages = st.session_state["messages"]

# Common opening message
if len(messages) == 0:
    opening_message = ""
    if model_option == "Pinecone":
        opening_message = "Assalamu'alaikum! Ana adalah Zaki, siap membantu antum dengan pertanyaan terkait laporan zakat BAZNAS. Silakan tanyakan apa yang ingin antum ketahui tentang laporan zakat BAZNAS, insyaAllah ana siap membantu!"
        messages.append({"role": "assistant", "content": opening_message})
    elif model_option == "Gemini":
        opening_message = "Assalamu'alaikum! Ana adalah ZakatKuy, siap membantu antum dengan pertanyaan terkait zakat. Silakan tanyakan apa yang ingin antum ketahui tentang zakat, insyaAllah ana siap membantu!"
        messages.append({"role": "assistant", "content": opening_message})

# Display previous chat messages
for message in messages:
    role = message.get("role", "")
    content = message.get("content", "") or "".join(message.get("parts", []))
    avatar = "static/user_icon.png" if role == "user" else "static/ai_icon.png"
    with st.chat_message(role, avatar=avatar):
        st.markdown(content)

# User input
chat_message = st.chat_input("Masukkan pesan Anda...")

if chat_message:
    st.chat_message("user", avatar="static/user_icon.png").markdown(chat_message)
    messages.append({"role": "user", "content": chat_message})

    if model_option == "Pinecone":
        # Pinecone API Key
        if "api_key" in st.secrets:
            api_key = st.secrets["api_key"]
        else:
            st.error("Missing API key. Please add your API key to the secrets.toml file to continue.")

        # Initialize Pinecone
        assistant_name = "zaki"
        pc = Pinecone(api_key=api_key)
        assistant = pc.assistant.Assistant(assistant_name=assistant_name)

        # Send message to Pinecone Assistant API
        chat_context = [Message(content=chat_message)]
        response = assistant.chat_completions(messages=chat_context)

        if response:
            assistant_reply = response.choices[0].message.content
            st.chat_message("assistant", avatar="static/ai_icon.png").markdown(assistant_reply)
            messages.append({"role": "assistant", "content": assistant_reply})
        else:
            st.error("Terjadi kesalahan saat menghubungi Assistant API.")

    elif model_option == "Gemini":
        # Fetch gold price
        def fetch_gold_price():
            url = "https://logam-mulia-api.vercel.app/prices/hargaemas-org"
            try:
                response = requests.get(url)
                data = response.json()
                return data["data"][0]["sell"]
            except Exception as e:
                st.error(f"Gagal mengambil harga emas: {e}")
                return None

        gold_price = fetch_gold_price()

        if gold_price is not None:
            # Configure API key for Gemini
            if "google_api_key" in st.secrets:
                genai.configure(api_key=st.secrets["google_api_key"])
            else:
                st.error("Missing Google API key. Please add your API key to the secrets.toml file to continue.")

            # Get response from Gemini
            def get_response(messages, gold_price):
                try:
                    generation_config = {
                        "temperature": 1,
                        "top_p": 0.95,
                        "top_k": 64,
                        "max_output_tokens": 8192,
                        "response_mime_type": "text/plain",
                    }

                    system_instruction = st.secrets["system_instruction"].format(gold_price=gold_price)

                    model = genai.GenerativeModel(
                        model_name="gemini-1.5-flash",
                        system_instruction=system_instruction,
                        tools='code_execution',
                    )

                    res = model.generate_content(
                        [msg["content"] for msg in messages if msg["role"] == "user"],
                        stream=True,
                        generation_config=generation_config
                    )
                    return res
                except Exception as e:
                    st.error(f"Error getting response from the model: {e}")
                    return []

            def extract_result_from_response(response_text):
                # Remove code blocks from response
                while '```' in response_text:
                    start_code_block = response_text.find('```')
                    end_code_block = response_text.find('```', start_code_block + 3)
                    if end_code_block == -1:
                        break
                    response_text = response_text[:start_code_block] + response_text[end_code_block + 3:]
                return response_text.strip()

            # Get the response from Gemini
            res = get_response(messages, gold_price)
            res_text = ""
            for chunk in res:
                if hasattr(chunk, "text"):
                    res_text += chunk.text

            # Process the response
            final_result = extract_result_from_response(res_text)

            # Display the assistant's reply
            st.chat_message("assistant", avatar="static/ai_icon.png").markdown(final_result)
            messages.append({"role": "assistant", "content": final_result})
        else:
            st.error("Gagal mengambil harga emas. Mohon periksa koneksi Anda.")

# Reset conversation button
if len(st.session_state["messages"]) > 1:
    if st.button("Reset Percakapan"):
        st.session_state.clear()
        st.rerun()
