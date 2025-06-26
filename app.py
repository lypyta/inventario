import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests # Necesario para leer archivos desde URL

    # --- Configuración de la URL de Google Drive ---
    # 🚨 ¡IMPORTANTE! Pega aquí el enlace de descarga directa de tu archivo de Google Sheets.
    # Debe ser el formato que termina en '/export?format=xlsx'
    # Ejemplo: 'https://docs.google.com/spreadsheets/d/1rVAFj9y7PAud_jPJLzh--xpUJMHxGBiI/export?format=xlsx'
GOOGLE_SHEETS_URL = 'https://docs.google.com/spreadsheets/d/1rVAFj9y7PAud_jPJLzh--xpUJMHxGBiI/export?format=xlsx'

    # --- Configuración inicial de la página de Streamlit ---
st.set_page_config(layout="wide") # Para que el dashboard ocupe todo el ancho de la pantalla
st.title('📊 Dashboard de Inventario Dinámico')
st.markdown("---")

    # --- Carga y depuración de datos ---
df = pd.DataFrame() # Inicializa un DataFrame vacío

@st.cache_data # Cacha los datos para mejorar el rendimiento
def load_data(url):
    try:
        st.info('Cargando datos desde Google Drive...')
        response = requests.get(url)
        response.raise_for_status()  # Lanza un error para códigos de estado HTTP 4xx/5xx
        df_loaded = pd.read_excel(io.BytesIO(response.content))
        st.success('✅ ¡Datos cargados con éxito!')
        return df_loaded
    except requests.exceptions.RequestException as req_err:
        st.error(f"❌ Error de conexión al cargar el archivo. Verifica el enlace y permisos de Drive.")
        st.error(f"Detalles: {req_err}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error inesperado al leer el archivo. Asegúrate que sea un Excel válido.")
        st.error(f"Detalles: {e}")
        st.stop()

df = load_data(GOOGLE_SHEETS_URL)

    # --- Verificación de Columnas y Limpieza de Datos ---
expected_cols = ['Producto', 'Cajas', 'Unidades x Caja', 'Unidades', 'Marca']
missing_cols = [col for col in expected_cols if col not in df.columns]

if missing_cols:
    st.error(f"❌ ¡Faltan columnas esenciales en tu archivo de Excel! Faltan: **{', '.join(missing_cols)}**")
    st.warning("Asegúrate de que los nombres de las columnas en tu Excel sean **exactamente** iguales a los esperados (mayúsculas, minúsculas, espacios).")
    st.dataframe(df.columns.to_frame(name='Columnas detectadas'))
    st.stop()

if df.empty:
    st.warning('⚠️ El inventario está vacío. No se encontraron datos en el archivo de Excel.')
    st.stop()

    # Convertimos las columnas a tipo numérico para asegurar los cálculos
    # 'errors='coerce'' convierte no-números a NaN, 'fillna(0)' los hace cero
try:
    df['Cajas'] = pd.to_numeric(df['Cajas'], errors='coerce').fillna(0).astype(int)
    df['Unidades x Caja'] = pd.to_numeric(df['Unidades x Caja'], errors='coerce').fillna(0).astype(int)
    df['Unidades'] = pd.to_numeric(df['Unidades'], errors='coerce').fillna(0).astype(int)
except Exception as e:
        st.error(f"❌ Error en la conversión de columnas numéricas. Revisa que 'Cajas', 'Unidades x Caja', 'Unidades' contengan solo números.")
        st.error(f"Detalles: {e}")
        st.stop()

    # Calcula la columna del stock total de unidades
df['Total de Unidades'] = (df['Cajas'] * df['Unidades x Caja']) + df['Unidades']

    # --- Visualizaciones y Gráficos ---

    # Gráfico de barras del stock total por producto
st.subheader('Stock Total por Producto (en Unidades)')
fig_bar = px.bar(
        df.sort_values('Total de Unidades', ascending=False),
        x='Producto',
        y='Total de Unidades',
        color='Marca',
        title='Stock Actual por Producto',
        labels={'Total de Unidades': 'Unidades Totales'},
        text='Total de Unidades',
        height=500
    )
fig_bar.update_layout(xaxis_title='Producto', yaxis_title='Unidades Totales', showlegend=True)
st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

    # Gráfico de torta para ver la distribución del stock por marca
st.subheader('Distribución del Stock por Marca')
df_marca_total = df.groupby('Marca')['Total de Unidades'].sum().reset_index()
fig_pie = px.pie(
        df_marca_total,
        values='Total de Unidades',
        names='Marca',
        title='Proporción de Unidades por Marca',
        hole=0.3
    )
st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

    # Tabla del inventario con la columna de unidades totales
st.subheader('Inventario Detallado')
st.dataframe(df[['Producto', 'Marca', 'Cajas', 'Unidades x Caja', 'Unidades', 'Total de Unidades']].sort_values('Total de Unidades', ascending=False), use_container_width=True)

    # Opcional: Agregar un filtro por marca en la barra lateral
st.sidebar.title('Filtros Rápidos')
marcas_disponibles = df['Marca'].unique().tolist()
marca_seleccionada = st.sidebar.selectbox('Selecciona una Marca', ['Todas'] + marcas_disponibles)

if marca_seleccionada != 'Todas':
    df_filtrado = df[df['Marca'] == marca_seleccionada]
st.subheader(f'Inventario para la Marca: {marca_seleccionada}')
st.dataframe(df_filtrado[['Producto', 'Cajas', 'Unidades x Caja', 'Unidades', 'Total de Unidades']], use_container_width=True)

st.markdown("---")
st.success("¡Dashboard de Inventario actualizado y listo para usar!") 