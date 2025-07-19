import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests

# --- Configuración de la URL de Google Drive ---
GOOGLE_SHEETS_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSNRv2kzy2qIDvRbljlj5nHEqbzSYhcZF9oqklzmmt_1-hQfO8Mjf4ZdvmwSdXt9A/pub?output=xlsx'

# --- Configuración inicial de la página de Streamlit ---
st.set_page_config(layout="wide")
st.title('📊 Inventario Camaras 1-2 y Reefers 1 al 10')
st.markdown("---")

# --- Función para Cargar Datos (Caché para eficiencia) ---
# @st.cache_data # Considera activar esto una vez que todo funcione bien para mejorar el rendimiento
def load_and_process_data(url):
    try:
        st.info('Cargando y procesando datos desde Google Drive...')
        response = requests.get(url)
        response.raise_for_status() # Lanza un error para códigos de estado HTTP 4xx/5xx

        df_raw = pd.read_excel(io.BytesIO(response.content), header=None, engine='openpyxl')

        expected_excel_headers = ['FECHA VTO.', 'DESCRIPCION', 'CAJA APROX', 'MARCA', 'UBICACION', 'UNIDADES']
        
        if len(df_raw.columns) != len(expected_excel_headers):
            st.error(f"Error: El archivo Excel tiene {len(df_raw.columns)} columnas, pero se esperaban exactamente {len(expected_excel_headers)}.")
            st.error(f"Asegúrate de que tu Excel contenga las columnas: {', '.join(expected_excel_headers)} en ese orden.")
            st.stop()
        
        df_raw.columns = expected_excel_headers
        df = df_raw.iloc[1:].copy()
        
        column_mapping = {
            'FECHA VTO.': 'Fecha Vencimiento',
            'DESCRIPCION': 'Producto',
            'CAJA APROX': 'Cajas disponibles',
            'MARCA': 'Marca',
            'UBICACION': 'Ubicacion',
            'UNIDADES': 'Unidades'
        }
        df = df.rename(columns=column_mapping)

        required_final_cols = ['Fecha Vencimiento', 'Producto', 'Cajas disponibles', 'Marca', 'Ubicacion', 'Unidades']
        missing_cols = [col for col in required_final_cols if col not in df.columns]
        if missing_cols:
            st.error(f"❌ ¡Faltan columnas esenciales después del procesamiento! Asegúrate de que tu Excel contenga los encabezados correctos: {', '.join(missing_cols)}")
            st.warning("Columnas detectadas en tu archivo y cómo se están mapeando:")
            st.dataframe(pd.DataFrame(list(column_mapping.items()), columns=['En Excel', 'Esperado por App']))
            st.dataframe(df.columns.to_frame(name='Columnas Resultantes en App'))
            st.stop()

        df.dropna(subset=['Producto', 'Marca', 'Ubicacion', 'Cajas disponibles'], inplace=True) 
        if df.empty:
            st.warning('⚠️ El inventario está vacío después de limpiar filas sin Producto, Marca, Ubicación o Cajas disponibles.')
            st.stop()

        df['Cajas disponibles'] = pd.to_numeric(df['Cajas disponibles'], errors='coerce').fillna(0).astype(int)
        df['Unidades'] = pd.to_numeric(df['Unidades'], errors='coerce').fillna(0).astype(int)
        
        df['Fecha Vencimiento'] = pd.to_datetime(df['Fecha Vencimiento'], errors='coerce')
        df.dropna(subset=['Fecha Vencimiento'], inplace=True)

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


# --- Componentes Interactivos (Filtros en el cuerpo principal) ---
st.subheader('Filtros de Inventario')

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
if producto_seleccionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['Producto'] == producto_seleccionado]


# Mensaje si no hay datos después de filtrar
if df_filtrado.empty:
    st.warning("No hay datos para la combinación de filtros seleccionada.")
else:
    # --- Tabla del Inventario Detallado (filtrado y ordenado por Fecha Vencimiento) ---
    st.subheader(f'Inventario Detallado Completo - {marca_seleccionada} / {ubicacion_seleccionada} / {producto_seleccionado}')
    
    # DEBUG: Verificar el tipo de dato de la columna Fecha Vencimiento antes de ordenar
    st.write(f"Tipo de dato de 'Fecha Vencimiento' antes de ordenar: {df_filtrado['Fecha Vencimiento'].dtype}")

    # Ordenar por 'Fecha Vencimiento' (que sigue siendo datetime) de forma ascendente
    df_para_mostrar = df_filtrado.sort_values('Fecha Vencimiento', ascending=True).copy() 
    
    # Formatear la columna 'Fecha Vencimiento' SOLO AHORA para la visualización
    df_para_mostrar['Fecha Vencimiento'] = df_para_mostrar['Fecha Vencimiento'].dt.strftime('%d-%m-%Y')

    # Mostrar la tabla
    st.dataframe(df_para_mostrar[['Marca', 'Producto', 'Cajas disponibles', 'Unidades', 'Ubicacion', 'Fecha Vencimiento']], use_container_width=True, hide_index=True)
    st.markdown("---") 

    # --- Vista Específica: Productos y Ubicaciones por Marca (cuando se selecciona una marca) ---
    if marca_seleccionada != 'Todas' and producto_seleccionado == 'Todos':
        with st.expander(f"📦 Ver Productos y Ubicaciones para '{marca_seleccionada}'"):
            st.dataframe(
                df_filtrado[['Producto', 'Ubicacion', 'Cajas disponibles']]
                .sort_values('Cajas disponibles', ascending=False)
                .reset_index(drop=True),
                use_container_width=True
            )
            st.info("Esta tabla muestra los productos y su ubicación para la marca seleccionada.")
    elif producto_seleccionado != 'Todos':
        st.info(f"Mostrando detalles para el producto: **{producto_seleccionado}**")

    # --- Nuevo Gráfico de Torta: Distribución por Ubicación para Producto Seleccionado (por Cajas disponibles) ---
    if producto_seleccionado != 'Todos' and not df_filtrado.empty:
        st.subheader(f"Distribución de Cajas disponibles para '{producto_seleccionado}' por Ubicación")
        df_ubicacion_total_filtrado = df_filtrado.groupby('Ubicacion')['Cajas disponibles'].sum().reset_index()
        if not df_ubicacion_total_filtrado.empty:
            fig_pie_ubicacion = px.pie(
                df_ubicacion_total_filtrado,
                values='Cajas disponibles',
                names='Ubicacion',
                title=f"Cajas disponibles de '{producto_seleccionado}' por Ubicación",
                hole=0.3
            )
            st.plotly_chart(fig_pie_ubicacion, use_container_width=True)
        else:
            st.warning(f"No hay datos de ubicación para el producto '{producto_seleccionado}' con los filtros actuales.")


    # --- Visualizaciones Dinámicas ---

    # Gráfico de Barras: Stock Total por Producto (en Cajas disponibles)
   # Gráfico de Barras: Stock Total por Producto (en Cajas disponibles)
    st.subheader(f'Stock Total por Producto (en Cajas disponibles) - {marca_seleccionada} / {ubicacion_seleccionada} / {producto_seleccionado}')
    
    if producto_seleccionado != 'Todos':
        # Si se selecciona un producto específico, el gráfico de barras será solo para ese producto
        fig_bar = px.bar(
            df_filtrado,
            y='Producto', # Cambiado a eje Y para horizontal
            x='Cajas disponibles', # Cambiado a eje X para horizontal
            color='Marca',
            title=f'Stock del Producto: {producto_seleccionado}',
            labels={'Cajas disponibles': 'Total de Cajas disponibles'},
            text='Cajas disponibles',
            height=300
        )
    else: 
        # Si no se selecciona producto, muestra el top 10 por Cajas disponibles (sumadas por producto)
        df_top_products = df_filtrado.groupby('Producto')['Cajas disponibles'].sum().reset_index()
        # Asegúrate de que el top 10 esté ordenado de mayor a menor
        df_top_products = df_top_products.sort_values('Cajas disponibles', ascending=False).head(10)
        
        fig_bar = px.bar(
            df_top_products,
            y='Producto', # Cambiado a eje Y para horizontal
            x='Cajas disponibles', # Cambiado a eje X para horizontal
            title='Top 10 Productos por Stock (Cajas disponibles)',
            labels={'Cajas disponibles': 'Total de Cajas disponibles'},
            text='Cajas disponibles',
            height=500,
            # --- CAMBIO CLAVE AQUÍ: Asegurar el orden del eje Y según el DataFrame ---
            category_orders={'Producto': df_top_products['Producto'].tolist()} 
        )
    fig_bar.update_layout(xaxis_title='Total de Cajas disponibles', yaxis_title='Producto', showlegend=True)
    st.plotly_chart(fig_bar, use_container_width=True)
    
    # Gráfico de Torta: Distribución del Stock por Marca (filtrado - por Cajas disponibles)
    st.subheader(f'Distribución de Cajas disponibles por Marca - {ubicacion_seleccionada} / {producto_seleccionado}')
    df_marca_total_filtrado = df_filtrado.groupby('Marca')['Cajas disponibles'].sum().reset_index()
    if producto_seleccionado != 'Todos' and not df_marca_total_filtrado.empty:
        fig_pie = px.pie(
            df_marca_total_filtrado,
            values='Cajas disponibles',
            names='Marca',
            title=f"Distribución de Cajas disponibles para '{producto_seleccionado}'",
            hole=0.3
        )
    else:
        fig_pie = px.pie(
            df_marca_total_filtrado,
            values='Cajas disponibles',
            names='Marca',
            title='Proporción de Cajas disponibles por Marca',
            hole=0.3
        )
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    # --- NUEVA TABLA: Resumen de Cajas y Unidades por Producto ---
    st.subheader(f'📦 Resumen Total de Cajas y Unidades por Producto')
    st.info('Esta tabla muestra la cantidad total de cajas y unidades disponibles para cada producto, considerando los filtros aplicados.')
    
    # Agrupar por 'Producto' y sumar 'Cajas disponibles' y 'Unidades'
    df_resumen_producto = df_filtrado.groupby('Producto')[['Cajas disponibles', 'Unidades']].sum().reset_index()
    
    # Renombrar las columnas de suma para mayor claridad en la tabla
    df_resumen_producto.rename(columns={
        'Cajas disponibles': 'Cantidad Total de Cajas',
        'Unidades': 'Cantidad Total de Unidades'
    }, inplace=True)
    
    # Ordenar de mayor a menor cantidad de cajas
    df_resumen_producto = df_resumen_producto.sort_values('Cantidad Total de Cajas', ascending=False)
    
    # Mostrar la tabla
    st.dataframe(df_resumen_producto, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.success("¡Dashboard de Inventario actualizado !")

st.markdown("---")
st.success("¡Dashboard de Inventario actualizado y listo para usar!")
