import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests

# --- Configuración de la URL de Google Drive ---
# 🚨 ¡IMPORTANTE! Pega aquí el enlace de descarga directa de tu archivo de Google Sheets.
# Debe ser el formato que termina en '/export?format=xlsx'
# Ejemplo: 'https://docs.google.com/sheets/d/1rVAFj9y7PAud_jPJLzh--xpUJMHxGBiI/export?format=xlsx'
GOOGLE_SHEETS_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRuj5CR1pOwlDvQY7-LRrCO4l_XaNNUfzUTnYXEO1zSuwG5W6s30HI6xhCuw-1m_w/pub?output=xlsx'

# --- Configuración inicial de la página de Streamlit ---
st.set_page_config(layout="wide")
st.title('📊 Dashboard Interactivo de Inventario')
st.markdown("---")

# --- Función para Cargar Datos (Caché para eficiencia) ---
@st.cache_data
def load_and_process_data(url):
    try:
        st.info('Cargando y procesando datos desde Google Drive...')
        response = requests.get(url)
        response.raise_for_status() # Lanza un error para códigos de estado HTTP 4xx/5xx

        # Leer sin encabezado y asignar manualmente después
        # Se especifica el motor 'openpyxl' para la lectura del archivo Excel
        df_raw = pd.read_excel(io.BytesIO(response.content), header=None, engine='openpyxl')

        # --- SECCIONES DE DEPURACIÓN OCULTAS AL USUARIO FINAL ---
        # Estas líneas se pueden eliminar o comentar si la depuración ya no es necesaria,
        # pero las mantengo comentadas por si necesitas reactivarlas para futuras depuraciones.
        # st.subheader("DataFrame leído directamente (con columnas numéricas si header=None):")
        # st.dataframe(df_raw.head())
        # st.write("Columnas originales leídas por Pandas:", df_raw.columns.tolist())
        # --- FIN SECCIONES DE DEPURACIÓN OCULTAS ---

        # Asignar nombres de columnas manualmente en el orden exacto de tu Excel
        # Asumiendo que la primera fila de df_raw contiene tus verdaderos encabezados
        # y que el orden es: DESCRIPCION, UNIDADES, UNID X CAJA, CAJAS APROX, MARCA, UBICACION
        expected_excel_headers = ['DESCRIPCION', 'UNIDADES', 'UNID X CAJA', 'CAJAS APROX', 'MARCA', 'UBICACION']
        
        # Verificar que el número de columnas leídas sea al menos el esperado
        if len(df_raw.columns) < len(expected_excel_headers):
            st.error(f"Error: El archivo Excel tiene menos columnas de las esperadas. Se esperaban al menos {len(expected_excel_headers)}.")
            st.stop()
        
        # Asignar los nombres de columna de la lista `expected_excel_headers`
        df_raw.columns = expected_excel_headers + list(range(len(expected_excel_headers), len(df_raw.columns)))
        
        # Ahora, la primera fila de df_raw es la que contenía los nombres de columna.
        # Los datos reales comienzan desde la segunda fila (índice 1).
        df = df_raw.iloc[1:].copy()
        
        # --- SECCIONES DE DEPURACIÓN OCULTAS AL USUARIO FINAL ---
        # st.info("Nombres de columnas asignados manualmente y datos separados de encabezados.")
        # --- FIN SECCIONES DE DEPURACIÓN OCULTAS ---

        # --- Mapeo de nombres de columnas a nombres internos de la aplicación ---
        column_mapping = {
            'DESCRIPCION': 'Producto',
            'UNIDADES': 'Unidades',
            'UNID X CAJA': 'Unidades x Caja',
            'CAJAS APROX': 'Cajas',
            'MARCA': 'Marca',
            'UBICACION': 'Ubicacion' # Añadir mapeo para Ubicacion
        }
        df = df.rename(columns=column_mapping)

        # --- Verificación de columnas finales requeridas (ESTO SÍ ES CRÍTICO Y SE MUESTRA SI HAY ERROR) ---
        required_final_cols = ['Producto', 'Cajas', 'Unidades x Caja', 'Unidades', 'Marca', 'Ubicacion']
        missing_cols = [col for col in required_final_cols if col not in df.columns]
        if missing_cols:
            st.error(f"❌ ¡Faltan columnas esenciales después del procesamiento! Asegúrate de que tu Excel contenga los encabezados correctos: {', '.join(missing_cols)}")
            st.warning("Columnas detectadas en tu archivo y cómo se están mapeando:") # Se mantiene para ayuda en caso de error
            st.dataframe(pd.DataFrame(list(column_mapping.items()), columns=['En Excel', 'Esperado por App'])) # Se mantiene para ayuda en caso de error
            st.dataframe(df.columns.to_frame(name='Columnas Resultantes en App')) # Se mantiene para ayuda en caso de error
            st.stop()

        # --- Limpieza de datos y conversión a numérico ---
        # Elimina filas donde 'Producto' o 'Marca' sean nulos, ya que son esenciales
        df.dropna(subset=['Producto', 'Marca'], inplace=True)
        if df.empty:
            st.warning('⚠️ El inventario está vacío después de limpiar filas sin Producto o Marca.')
            st.stop()

        # Convertimos las columnas numéricas.
        for col in ['Cajas', 'Unidades x Caja', 'Unidades']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        # 'Total de Unidades' ahora es simplemente 'Unidades'
        df['Total de Unidades'] = df['Unidades']

        st.success('✅ ¡Datos cargados y procesados con éxito!')
        return df

    except requests.exceptions.RequestException as req_err:
        st.error(f"❌ Error de conexión al cargar el archivo. Verifica el enlace y permisos de Drive.")
        st.error(f"Detalles: {req_err}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error inesperado al leer o procesar el archivo. Asegúrate que sea un Excel válido y la estructura de columnas sea la esperada.")
        st.error(f"Detalles: {e}")
        st.stop()

df = load_and_process_data(GOOGLE_SHEETS_URL)

# --- Componentes Interactivos (Filtros) ---
st.sidebar.title('Filtros')

# Filtro por Marca
marcas_disponibles = ['Todas'] + sorted(df['Marca'].unique().tolist())
marca_seleccionada = st.sidebar.selectbox('Selecciona una Marca', marcas_disponibles)

# Filtro por Ubicación
ubicaciones_disponibles = ['Todas'] + sorted(df['Ubicacion'].unique().tolist())
ubicacion_seleccionada = st.sidebar.selectbox('Selecciona una Ubicación', ubicaciones_disponibles)

# Nuevo filtro por Producto
productos_disponibles = ['Todos'] + sorted(df['Producto'].unique().tolist())
producto_seleccionado = st.sidebar.selectbox('Selecciona un Producto', productos_disponibles)


# Filtrar el DataFrame según las selecciones
df_filtrado = df.copy()
if marca_seleccionada != 'Todas':
    df_filtrado = df_filtrado[df_filtrado['Marca'] == marca_seleccionada]
if ubicacion_seleccionada != 'Todas':
    df_filtrado = df_filtrado[df_filtrado['Ubicacion'] == ubicacion_seleccionada]
if producto_seleccionado != 'Todos': # Aplicar el nuevo filtro de producto
    df_filtrado = df_filtrado[df_filtrado['Producto'] == producto_seleccionado]


# Mensaje si no hay datos después de filtrar
if df_filtrado.empty:
    st.warning("No hay datos para la combinación de filtros seleccionada.")
else:
    # --- Vista Específica: Productos y Ubicaciones por Marca (cuando se selecciona una marca) ---
    if marca_seleccionada != 'Todas' and producto_seleccionado == 'Todos': # Solo muestra si se filtra por marca y no por producto específico
        with st.expander(f"📦 Ver Productos y Ubicaciones para '{marca_seleccionada}'"):
            st.dataframe(
                df_filtrado[['Producto', 'Ubicacion', 'Total de Unidades']]
                .sort_values('Total de Unidades', ascending=False)
                .reset_index(drop=True), # Reinicia el índice para una vista más limpia
                use_container_width=True
            )
            st.info("Esta tabla muestra los productos y su ubicación para la marca seleccionada.")
    elif producto_seleccionado != 'Todos': # Si se selecciona un producto específico
        st.info(f"Mostrando detalles para el producto: **{producto_seleccionado}**")

    # --- Nuevo Gráfico de Torta: Distribución por Ubicación para Producto Seleccionado ---
    if producto_seleccionado != 'Todos' and not df_filtrado.empty:
        st.subheader(f"Distribución de Unidades para '{producto_seleccionado}' por Ubicación")
        df_ubicacion_total_filtrado = df_filtrado.groupby('Ubicacion')['Total de Unidades'].sum().reset_index()
        if not df_ubicacion_total_filtrado.empty:
            fig_pie_ubicacion = px.pie(
                df_ubicacion_total_filtrado,
                values='Total de Unidades',
                names='Ubicacion',
                title=f"Unidades de '{producto_seleccionado}' por Ubicación",
                hole=0.3
            )
            st.plotly_chart(fig_pie_ubicacion, use_container_width=True)
        else:
            st.warning(f"No hay datos de ubicación para el producto '{producto_seleccionado}' con los filtros actuales.")


    # --- Visualizaciones Dinámicas ---

    # Gráfico de Barras: Stock Total por Producto (filtrado)
    st.subheader(f'Stock Total por Producto (en Unidades) - {marca_seleccionada} / {ubicacion_seleccionada} / {producto_seleccionado}')
    # Si se selecciona un producto específico, el gráfico de barras será solo para ese producto
    if producto_seleccionado != 'Todos':
        fig_bar = px.bar(
            df_filtrado,
            x='Producto',
            y='Total de Unidades',
            color='Marca',
            title=f'Stock del Producto: {producto_seleccionado}',
            labels={'Total de Unidades': 'Unidades Totales'},
            text='Total de Unidades',
            height=300 # Más pequeño para un solo producto
        )
    else: # Si no se selecciona producto, muestra el top 10
        fig_bar = px.bar(
            df_filtrado.sort_values('Total de Unidades', ascending=False).head(10),
            x='Producto',
            y='Total de Unidades',
            color='Marca',
            title='Top 10 Productos por Stock',
            labels={'Total de Unidades': 'Unidades Totales'},
            text='Total de Unidades',
            height=500
        )
    fig_bar.update_layout(xaxis_title='Producto', yaxis_title='Unidades Totales', showlegend=True)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # Gráfico de Torta: Distribución del Stock por Marca (filtrado)
    st.subheader(f'Distribución de Unidades por Marca - {ubicacion_seleccionada} / {producto_seleccionado}')
    df_marca_total_filtrado = df_filtrado.groupby('Marca')['Total de Unidades'].sum().reset_index()
    # Si se selecciona un producto específico, el gráfico de torta de marca solo tendrá una "rebanada" (la marca de ese producto)
    if producto_seleccionado != 'Todos' and not df_marca_total_filtrado.empty:
        fig_pie = px.pie(
            df_marca_total_filtrado,
            values='Total de Unidades',
            names='Marca',
            title=f"Distribución de Unidades para '{producto_seleccionado}'",
            hole=0.3
        )
    else:
        fig_pie = px.pie(
            df_marca_total_filtrado,
            values='Total de Unidades',
            names='Marca',
            title='Proporción de Unidades por Marca',
            hole=0.3
        )
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # Tabla del Inventario Detallado (filtrado)
    st.subheader(f'Inventario Detallado Completo - {marca_seleccionada} / {ubicacion_seleccionada} / {producto_seleccionado}')
    st.dataframe(df_filtrado[['Producto', 'Marca', 'Ubicacion', 'Cajas', 'Unidades x Caja', 'Unidades', 'Total de Unidades']].sort_values('Total de Unidades', ascending=False), use_container_width=True)

st.markdown("---")
st.success("¡Dashboard de Inventario actualizado y listo para usar!")
