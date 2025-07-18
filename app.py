import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests

# --- Configuración de la URL de Google Drive ---
GOOGLE_SHEETS_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRuj5CR1pOwlDvQY7-LRrCO4l_XaNNUfzUTN_YXEO1zSuwG5W6s30HI6xhCuw-1m_w/pub?output=xlsx'

# --- Configuración inicial de la página de Streamlit ---
st.set_page_config(layout="wide")
st.title('📊 Inventario Camaras 1-2 y Reefers 1 al 10')
st.markdown("---")

# --- Función para Cargar Datos (Caché para eficiencia) ---
# @st.cache_data # Temporalmente desactivado para depuración, si no se actualiza con nuevos datos.
def load_and_process_data(url):
    try:
        st.info('Cargando y procesando datos desde Google Drive...')
        response = requests.get(url)
        response.raise_for_status() # Lanza un error para códigos de estado HTTP 4xx/5xx

        # Leer sin encabezado y asignar manualmente después
        # Se especifica el motor 'openpyxl' para la lectura del archivo Excel
        df_raw = pd.read_excel(io.BytesIO(response.content), header=None, engine='openpyxl')

        # --- SECCIONES DE DEPURACIÓN OCULTAS AL USUARIO FINAL ---
        # st.subheader("DataFrame leído directamente (con columnas numéricas si header=None):")
        # st.dataframe(df_raw.head())
        # st.write("Columnas originales leídas por Pandas:", df_raw.columns.tolist())
        # --- FIN SECCIONES DE DEPURACIÓN OCULTAS ---

        # Asignar nombres de columnas manualmente en el orden exacto de tu Excel
        # Ahora se esperan 5 columnas: FECHA VTO., MARCA, PRODUCTO, CAJA APROX, UBICACION
        # Basado en la imagen, el orden es: FECHA VTO., DESCRIPCION, CAJAS APROX, MARCA, UBICACION, UNIDADES
        # Ajustando a la imagen proporcionada:
        expected_excel_headers = ['FECHA VTO.', 'DESCRIPCION', 'CAJA APROX', 'MARCA', 'UBICACION', 'UNIDADES']
        
        # Verificar que el número de columnas leídas sea exactamente el esperado
        if len(df_raw.columns) != len(expected_excel_headers):
            st.error(f"Error: El archivo Excel tiene {len(df_raw.columns)} columnas, pero se esperaban exactamente {len(expected_excel_headers)}.")
            st.error(f"Asegúrate de que tu Excel contenga las columnas: {', '.join(expected_excel_headers)} en ese orden.")
            st.stop()
        
        # Asignar los nombres de columna de la lista `expected_excel_headers`
        df_raw.columns = expected_excel_headers
        
        # Ahora, la primera fila de df_raw es la que contenía los nombres de columna.
        # Los datos reales comienzan desde la segunda fila (índice 1).
        df = df_raw.iloc[1:].copy()
        
        # --- SECCIONES DE DEPURACIÓN OCULTAS AL USUARIO FINAL ---
        # st.info("Nombres de columnas asignados manualmente y datos separados de encabezados.")
        # --- FIN SECCIONES DE DEPURACIÓN OCULTAS ---

        # --- Mapeo de nombres de columnas a nombres internos de la aplicación ---
        column_mapping = {
            'FECHA VTO.': 'Fecha Vencimiento', # Nueva columna
            'DESCRIPCION': 'Producto',
            'CAJA APROX': 'Cajas disponibles',
            'MARCA': 'Marca',
            'UBICACION': 'Ubicacion',
            'UNIDADES': 'Unidades' # Nueva columna
        }
        df = df.rename(columns=column_mapping)

        # --- Verificación de columnas finales requeridas (ESTO SÍ ES CRÍTICO Y SE MUESTRA SI HAY ERROR) ---
        required_final_cols = ['Fecha Vencimiento', 'Producto', 'Cajas disponibles', 'Marca', 'Ubicacion', 'Unidades'] # Actualizado aquí
        missing_cols = [col for col in required_final_cols if col not in df.columns] # Corregido: eliminado 'col' duplicado
        if missing_cols:
            st.error(f"❌ ¡Faltan columnas esenciales después del procesamiento! Asegúrate de que tu Excel contenga los encabezados correctos: {', '.join(missing_cols)}")
            st.warning("Columnas detectadas en tu archivo y cómo se están mapeando:") # Se mantiene para ayuda en caso de error
            st.dataframe(pd.DataFrame(list(column_mapping.items()), columns=['En Excel', 'Esperado por App'])) # Se mantiene para ayuda en caso de error
            st.dataframe(df.columns.to_frame(name='Columnas Resultantes en App')) # Se mantiene para ayuda en caso de error
            st.stop()

        # --- Limpieza de datos y conversión a numérico/fecha ---
        # Elimina filas donde 'Producto', 'Marca', 'Ubicacion' o 'Cajas disponibles' sean nulos, ya que son esenciales
        df.dropna(subset=['Producto', 'Marca', 'Ubicacion', 'Cajas disponibles'], inplace=True) 
        if df.empty:
            st.warning('⚠️ El inventario está vacío después de limpiar filas sin Producto, Marca, Ubicación o Cajas disponibles.')
            st.stop()

        # Convertimos las columnas numéricas.
        df['Cajas disponibles'] = pd.to_numeric(df['Cajas disponibles'], errors='coerce').fillna(0).astype(int)
        df['Unidades'] = pd.to_numeric(df['Unidades'], errors='coerce').fillna(0).astype(int) # Convertir Unidades
        
        # Convertir 'Fecha Vencimiento' a datetime, manejando errores
        df['Fecha Vencimiento'] = pd.to_datetime(df['Fecha Vencimiento'], errors='coerce')
        # Eliminar filas donde la fecha de vencimiento sea inválida después de la conversión
        df.dropna(subset=['Fecha Vencimiento'], inplace=True)

        # Formatear la columna 'Fecha Vencimiento' para mostrar solo la fecha
        df['Fecha Vencimiento'] = df['Fecha Vencimiento'].dt.strftime('%Y-%m-%d')


        # Calcular el Total de Unidades
        df['Total de Unidades'] = df['Unidades'] # Asumiendo que 'Unidades' ya es el total por fila

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

# --- NUEVA SECCIÓN DE DEPURACIÓN DE UBICACIONES (Visible para ti, puedes comentar si no la necesitas) ---
# st.subheader("📊 Depuración de Ubicaciones: Valores Únicos en tu Excel")
# st.info("Estos son los valores únicos detectados en la columna 'UBICACION' de tu archivo Excel.")
# st.dataframe(pd.DataFrame({'Valores Únicos de Ubicación': df['Ubicacion'].unique().tolist()}))
# st.markdown("---")
# --- FIN NUEVA SECCIÓN DE DEPURACIÓN ---


# --- Componentes Interactivos (Filtros en el cuerpo principal) ---
st.subheader('Filtros de Inventario')

# Crear columnas para organizar los selectbox horizontalmente
col1, col2, col3 = st.columns(3)

with col1:
    marcas_disponibles = ['Todas'] + sorted(df['Marca'].unique().tolist())
    marca_seleccionada = st.selectbox('Marca', marcas_disponibles)

with col2:
    ubicaciones_disponibles = ['Todas'] + sorted(df['Ubicacion'].unique().tolist())
    ubicacion_seleccionada = st.selectbox('Ubicación', ubicaciones_disponibles)

with col3:
    productos_disponibles = ['Todos'] + sorted(df['Producto'].unique().tolist())
    producto_seleccionado = st.selectbox('Producto', productos_disponibles)

st.markdown("---") # Separador visual


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
    # --- Métrica de Total de Unidades en Inventario ---
    # total_unidades_inventario = df_filtrado['Unidades'].sum() # Eliminado
    # st.metric(label="Total de Unidades en Inventario (filtrado)", value=f"{total_unidades_inventario:,.0f}") # Eliminado
    # st.markdown("---") # Eliminado si no hay métrica


    # --- Tabla del Inventario Detallado (filtrado - ordenar por Cajas disponibles) - MOVIDA AL PRINCIPIO ---
    st.subheader(f'Inventario Detallado Completo - {marca_seleccionada} / {ubicacion_seleccionada} / {producto_seleccionado}')
    # La tabla ahora muestra las columnas en el orden solicitado: Marca, Producto, Cajas disponibles, Unidades, Ubicacion, Fecha Vencimiento
    st.dataframe(df_filtrado[['Marca', 'Producto', 'Cajas disponibles', 'Unidades', 'Ubicacion', 'Fecha Vencimiento']].sort_values('Cajas disponibles', ascending=False), use_container_width=True, hide_index=True) # Ordenar por Cajas disponibles y ocultar índice
    st.markdown("---") # Separador visual después de la tabla

    # --- Vista Específica: Productos y Ubicaciones por Marca (cuando se selecciona una marca) ---
    if marca_seleccionada != 'Todas' and producto_seleccionado == 'Todos': # Solo muestra si se filtra por marca y no por producto específico
        with st.expander(f"📦 Ver Productos y Ubicaciones para '{marca_seleccionada}'"):
            st.dataframe(
                df_filtrado[['Producto', 'Ubicacion', 'Cajas disponibles']] # Mostrar Cajas disponibles aquí también
                .sort_values('Cajas disponibles', ascending=False) # Ordenar por Cajas disponibles
                .reset_index(drop=True), # Reinicia el índice para una vista más limpia
                use_container_width=True
            )
            st.info("Esta tabla muestra los productos y su ubicación para la marca seleccionada.")
    elif producto_seleccionado != 'Todos': # Si se selecciona un producto específico
        st.info(f"Mostrando detalles para el producto: **{producto_seleccionado}**")

    # --- Nuevo Gráfico de Torta: Distribución por Ubicación para Producto Seleccionado (por Cajas disponibles) ---
    if producto_seleccionado != 'Todos' and not df_filtrado.empty:
        st.subheader(f"Distribución de Cajas disponibles para '{producto_seleccionado}' por Ubicación") # Actualizado aquí
        df_ubicacion_total_filtrado = df_filtrado.groupby('Ubicacion')['Cajas disponibles'].sum().reset_index() # Agrupar por Cajas disponibles
        if not df_ubicacion_total_filtrado.empty:
            fig_pie_ubicacion = px.pie(
                df_ubicacion_total_filtrado,
                values='Cajas disponibles', # Valores basados en Cajas disponibles
                names='Ubicacion',
                title=f"Cajas disponibles de '{producto_seleccionado}' por Ubicación", # Actualizado aquí
                hole=0.3
            )
            st.plotly_chart(fig_pie_ubicacion, use_container_width=True)
        else:
            st.warning(f"No hay datos de ubicación para el producto '{producto_seleccionado}' con los filtros actuales.")


    # --- Visualizaciones Dinámicas ---

    # Gráfico de Barras: Stock Total por Producto (filtrado - por Cajas disponibles)
    st.subheader(f'Stock Total por Producto (en Cajas disponibles) - {marca_seleccionada} / {ubicacion_seleccionada} / {producto_seleccionado}') # Actualizado aquí
    
    if producto_seleccionado != 'Todos':
        # Si se selecciona un producto específico, el gráfico de barras será solo para ese producto
        fig_bar = px.bar(
            df_filtrado,
            y='Producto', # Cambiado a eje Y para horizontal
            x='Cajas disponibles', # Cambiado a eje X para horizontal
            color='Marca',
            title=f'Stock del Producto: {producto_seleccionado}',
            labels={'Cajas disponibles': 'Total de Cajas disponibles'}, # Etiqueta actualizada
            text='Cajas disponibles', # Texto sobre barras basado en Cajas disponibles
            height=300 # Más pequeño para un solo producto
        )
    else: 
        # Si no se selecciona producto, muestra el top 10 por Cajas disponibles (sumadas por producto)
        df_top_products = df_filtrado.groupby('Producto')['Cajas disponibles'].sum().reset_index()
        df_top_products = df_top_products.sort_values('Cajas disponibles', ascending=False).head(10) # Ordenar por Cajas disponibles (descendente para el top)
        
        # st.subheader("DEBUG: Datos usados para el gráfico Top 10 Productos") # DEBUG
        # st.dataframe(df_top_products) # DEBUG

        fig_bar = px.bar(
            df_top_products,
            y='Producto', # Cambiado a eje Y para horizontal
            x='Cajas disponibles', # Cambiado a eje X para horizontal
            # No se usa 'color' por 'Marca' aquí porque estamos agrupando por 'Producto'.
            # Si se quisiera el color por marca, se necesitaría una lógica de agregación más compleja o un gráfico diferente.
            title='Top 10 Productos por Stock (Cajas disponibles)', # Título actualizado
            labels={'Cajas disponibles': 'Total de Cajas disponibles'}, # Etiqueta actualizada
            text='Cajas disponibles', # Texto sobre barras basado en Cajas disponibles
            height=500
        )
    fig_bar.update_layout(xaxis_title='Total de Cajas disponibles', yaxis_title='Producto', showlegend=True) # Ejes X e Y actualizados
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # Gráfico de Torta: Distribución del Stock por Marca (filtrado - por Cajas disponibles)
    st.subheader(f'Distribución de Cajas disponibles por Marca - {ubicacion_seleccionada} / {producto_seleccionado}') # Título actualizado
    df_marca_total_filtrado = df_filtrado.groupby('Marca')['Cajas disponibles'].sum().reset_index() # Agrupar por Cajas disponibles
    # Si se selecciona un producto específico, el gráfico de torta de marca solo tendrá una "rebanada" (la marca de ese producto)
    if producto_seleccionado != 'Todos' and not df_marca_total_filtrado.empty:
        fig_pie = px.pie(
            df_marca_total_filtrado,
            values='Cajas disponibles', # Valores basados en Cajas disponibles
            names='Marca',
            title=f"Distribución de Cajas disponibles para '{producto_seleccionado}'", # Título actualizado
            hole=0.3
        )
    else:
        fig_pie = px.pie(
            df_marca_total_filtrado,
            values='Cajas disponibles', # Valores basados en Cajas disponibles
            names='Marca',
            title='Proporción de Cajas disponibles por Marca', # Título actualizado
            hole=0.3
        )
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

st.markdown("---")
st.success("¡Dashboard de Inventario actualizado y listo para usar!")




