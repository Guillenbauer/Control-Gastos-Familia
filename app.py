import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
import plotly.express as px
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Control de Gastos Familiar", layout="wide", page_icon="💰")

# --- CONTROL DE ACCESO / CONTRASEÑA ---
CONTRASEÑA_CORRECTA = "FamiliaGSPA2026"

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_login, _ = st.columns([1, 2])
    with col_login:
        with st.container(border=True):
            st.subheader("🔒 Acceso de la Familia")
            password_input = st.text_input("Introduce la contraseña para entrar:", type="password")
            boton_ingresar = st.button("Ingresar", type="primary", use_container_width=True)
            
            if boton_ingresar:
                if password_input == CONTRASEÑA_CORRECTA:
                    st.session_state["autenticado"] = True
                    st.success("✅ ¡Contraseña correcta!")
                    st.rerun()
                else:
                    st.error("⚠️ Contraseña incorrecta. Inténtalo de nuevo.")
    st.stop()

# --- CATEGORÍAS DE GASTOS ---
CATEGORIAS = {
    "Fijos Básicos": ["Hipoteca", "Colegio (La Salle)", "Guardería", "Comunidad", "Telefonía (O2)", "IBI"],
    "Fijos Opcionales": ["Extraescolares", "Suscripciones", "Seguro Médico", "Alquiler Garaje"],
    "Variables Básicos": ["Gasolina", "Luz", "Agua", "Gas", "Alimentación", "Farmacia", "Seguro Hogar", "Seguro Coche"],
    "Variables Opcionales": ["Viajes", "Regalos", "Ocio (Cine, Bolera…)", "Restaurantes", "Ropa", "Alimentación", "Peluquero", "Taller Coche", "Caldera", "Electrodomésticos", "Parking", "Peaje", "Otros", "Recon. Médico", "Gastos Heredado"]
}

# --- SISTEMA DE ALMACENAMIENTO FIJO ---
ARCHIVO_DATOS = "gastos_familia_datos.csv"

def obtener_gastos():
    # Si el archivo ya existe en tu almacenamiento del servidor, lo lee
    if os.path.exists(ARCHIVO_DATOS):
        try:
            df = pd.read_csv(ARCHIVO_DATOS)
            if not df.empty:
                df['fecha_dt'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y', errors='coerce')
                df['Importe'] = pd.to_numeric(df['Importe'], errors='coerce')
                return df
        except Exception:
            pass
    # Si es la primera vez o no existe, devuelve una tabla vacía estructurada
    return pd.DataFrame(columns=["Fecha", "Tipo de Gasto", "Concepto", "Importe", "Comentario"])

def guardar_gasto(fecha, tipo_gasto, concepto, importe, comentario):
    df_existente = obtener_gastos()
    if 'fecha_dt' in df_existente.columns:
        df_existente = df_existente.drop(columns=['fecha_dt'])
        
    nuevo_registro = pd.DataFrame([{
        "Fecha": fecha.strftime("%d/%m/%Y"),
        "Tipo de Gasto": tipo_gasto,
        "Concepto": concepto,
        "Importe": float(importe),
        "Comentario": comentario if comentario else ""
    }])
    
    df_actualizado = pd.concat([df_existente, nuevo_registro], ignore_index=True)
    # Guarda el archivo directamente en el almacenamiento persistente del contenedor
    df_actualizado.to_csv(ARCHIVO_DATOS, index=False)

st.title("💰 Control de Gastos de la Familia")
menu = st.sidebar.radio("Navegación", ["1. Registrar Gasto", "2. Estadísticas y Gráficos"])

if menu == "1. Registrar Gasto":
    st.header("📝 Registrar Nuevo Gasto")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha del Gasto", date.today(), format="DD/MM/YYYY")
        with col2:
            tipo_gasto = st.selectbox("Tipo de Gasto", list(CATEGORIAS.keys()))
            
        col3, col4 = st.columns(2)
        with col3:
            conceptos_disponibles = CATEGORIAS[tipo_gasto]
            concepto = st.selectbox("Concepto", conceptos_disponibles)
        with col4:
            importe = st.number_input("Importe (€)", min_value=0.0, step=0.01, format="%.2f", key="importe_input")
            
        comentario = st.text_input("Comentario / Detalle (Opcional)", key="comentario_input")
        boton_enviar = st.button("Añadir Gasto", type="primary")
        
        if boton_enviar:
            if importe > 0:
                try:
                    guardar_gasto(fecha, tipo_gasto, concepto, importe, comentario)
                    st.success(f"✅ ¡Gasto registrado y blindado en tu base de datos anual!")
                    st.toast("Guardado con éxito")
                except Exception:
                    st.error("Error al guardar el registro en el almacenamiento local.")
            else:
                st.error("⚠️ El importe debe ser mayor que 0")

elif menu == "2. Estadísticas y Gráficos":
    st.header("📊 Análisis de Gastos en Tiempo Real")
    df = obtener_gastos()
    
    if df.empty or 'fecha_dt' not in df or df['fecha_dt'].isna().all():
        st.info("Aún no hay gastos registrados visibles en tu base de datos. Registra tu primer gasto en la pestaña 1.")
    else:
        st.subheader("🔍 Filtros de Búsqueda")
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            fecha_min = min(df['fecha_dt']).date()
            fecha_max = max(df['fecha_dt']).date()
            rango_fechas = st.date_input("Rango de Fechas", [fecha_min, fecha_max], format="DD/MM/YYYY")
            
        with col_f2:
            tipos_seleccionados = st.multiselect("Filtrar por Tipo de Gasto", options=df["Tipo de Gasto"].unique(), default=df["Tipo de Gasto"].unique())
            
        with col_f3:
            conceptos_filtrados = df[df["Tipo de Gasto"].isin(tipos_seleccionados)]["Concepto"].unique()
            conceptos_seleccionados = st.multiselect("Filtrar por Concepto", options=conceptos_filtrados, default=conceptos_filtrados)
            
        if len(rango_fechas) == 2:
            inicio, fin = rango_fechas
            df_filtrado = df[(df['fecha_dt'].dt.date >= inicio) & (df['fecha_dt'].dt.date <= fin)]
        else:
            df_filtrado = df.copy()
            
        df_filtrado = df_filtrado[df_filtrado["Tipo de Gasto"].isin(tipos_seleccionados)]
        df_filtrado = df_filtrado[df_filtrado["Concepto"].isin(conceptos_seleccionados)]
        
        total_gastado = df_filtrado["Importe"].sum()
        st.metric(label="Total Gastado en Periodo Seleccionado", value=f"{total_gastado:,.2f} €")
        
        st.subheader("📈 Gráficos Visuales")
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("**Gasto por Tipo de Gasto**")
            fig_tipo = px.pie(df_filtrado, values="Importe", names="Tipo de Gasto", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_tipo, use_container_width=True)
            
        with col_g2:
            st.markdown("**Gasto por Concepto**")
            fig_concepto = px.bar(df_filtrado.groupby("Concepto")["Importe"].sum().reset_index(), 
                                  x="Concepto", y="Importe", color="Concepto", text_auto='.2s')
            st.plotly_chart(fig_concepto, use_container_width=True)
            
        st.subheader("📋 Historial de Datos Filtrados")
        df_vista = df_filtrado[['Fecha', "Tipo de Gasto", "Concepto", "Importe", "Comentario"]]
        st.dataframe(df_vista, use_container_width=True, hide_index=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_vista.to_excel(writer, index=False, sheet_name='Gastos_Familia')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 Exportar estos datos a Excel",
            data=excel_data,
            file_name=f"gastos_familia_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
