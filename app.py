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
        
        # *** NUEVO CAMBIO AQUÍ: Leer sin header y luego establecerlo manualmente ***
        # Esto es más robusto si 'header=N' no funciona como se espera
        full_df = pd.read_excel(io.BytesIO(response.content), header=None)
        
        # La imagen de tu Excel muestra que los encabezados están en la fila de Excel #4,
        # que es el índice 3 en Pandas (la indexación empieza en 0).
        
        # Captura los encabezados de la fila con índice 3
        headers = full_df.iloc[3].tolist()
        
        # Asigna los encabezados y toma los datos desde la fila siguiente (índice 4)
        df_loaded = full_df[4:].copy()
        df_loaded.columns = headers
        
        st.success('✅ ¡Datos cargados con éxito!')
        
        # Debugging: Muestra los encabezados después de la lectura y asignación manual
        st.write("Columnas leídas y asignadas (después de procesamiento en load_data):")
        st.write(df_loaded.columns.tolist())
        
        return df_loaded
    except requests.exceptions.RequestException as req_err:
        st.error(f"❌ Error de conexión al cargar el archivo. Verifica el enlace y permisos de Drive.")
        st.error(f"Detalles: {req_err}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error inesperado al leer el archivo. Asegúrate que sea un Excel válido y la estructura sea la esperada.")
        st.error(f"Detalles: {e}")
        st.stop()

df = load_data(GOOGLE_SHEETS_URL)

# --- Normalización de Nombres de Columnas y Verificación ---
# Primero, limpia los nombres de columna del DataFrame (elimina espacios extra y posibles nulos)
# Asegura que sean strings antes de strip, y maneja posibles NaN en los headers (ej. si hay celdas vacías)
df.columns = [str(col).strip() if pd.notna(col) else f"Unnamed_{i}" for i, col in enumerate(df.columns)]


# *** Nombres de columnas esperados que coinciden con tu Excel ***
# Y mapeamos los nombres de tu Excel a los nombres estandarizados esperados por el resto del script
column_mapping = {
    'DESCRIPCION': 'Producto',
    'UNIDADES': 'Unidades',
    'UNID X CAJA': 'Unidades x Caja',
    'CAJAS APROX': 'Cajas', # Mapeamos 'CAJAS APROX' a 'Cajas'
    'MARCA': 'Marca'
}

# Columnas que necesitamos para la lógica del dashboard
required_final_cols = ['Producto', 'Cajas', 'Unidades x Caja', 'Unidades', 'Marca']

# Renombra las columnas existentes en el DataFrame
# Esto permite que el resto del código use los nombres estandarizados
df = df.rename(columns=column_mapping)

# Ahora, verifica si todas las columnas REQUERIDAS después del mapeo existen
missing_cols_after_rename = [col for col in required_final_cols if col not in df.columns]

if missing_cols_after_rename:
    st.error(f"❌ ¡Faltan columnas esenciales después de intentar mapearlas! Asegúrate de que tu Excel contenga todas estas: DESCRIPCION, UNIDADES, UNID X CAJA, CAJAS APROX, MARCA")
    st.warning("Columnas detectadas en tu archivo y cómo se están mapeando:")
    st.dataframe(pd.DataFrame(list(column_mapping.items()), columns=['En Excel', 'Esperado por App']))
    st.dataframe(df.columns.to_frame(name='Columnas Resultantes en App'))
    st.stop()

if df.empty:
    st.warning('⚠️ El inventario está vacío. No se encontraron datos en el archivo de Excel o está vacía después de la lectura.')
    st.stop()

# Elimina filas donde 'Producto' o 'Marca' sean nulos, ya que son esenciales para los gráficos
df.dropna(subset=['Producto', 'Marca'], inplace=True)
if df.empty:
    st.warning('⚠️ El inventario está vacío después de limpiar filas sin Producto o Marca.')
    st.stop()

# Convertimos las columnas a tipo numérico para asegurar los cálculos
# 'errors='coerce'' convierte no-números a NaN, 'fillna(0)' los hace cero
try:
    df['Cajas'] = pd.to_numeric(df['Cajas'], errors='coerce').fillna(0).astype(int)
    df['Unidades x Caja'] = pd.to_numeric(df['Unidades x Caja'], errors='coerce').fillna(0).astype(int)
    df['Unidades'] = pd.to_numeric(df['Unidades'], errors='coerce').fillna(0).astype(int)
except Exception as e:
    st.error(f"❌ Error en la conversión de columnas numéricas. Revisa que 'UNIDADES', 'UNID X CAJA' y 'CAJAS APROX' contengan solo números en tu Excel.")
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
# Muestra las columnas originales del Excel más la calculada
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
