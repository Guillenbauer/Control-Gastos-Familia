import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
import plotly.express as px
import os

# --- CONFIGURACIÓN DE LA PÁGINA (CON EMOJI SEGURO) ---
st.set_page_config(page_title="Gastos", layout="centered", page_icon="icono_familia.png")

# --- FORZAR TAMAÑO PEQUEÑO MEDIANTE ETIQUETA HTML OFICIAL ---
st.html("""
    <style>
        html, body, [data-testid="stWidgetLabel"], .stMarkdown p {
            font-size: 13px !important;
        }
        h1 { font-size: 1.5rem !important; margin: 0 !important; padding: 0 !important; }
        h2 { font-size: 1.2rem !important; margin: 5px 0 !important; }
        h3 { font-size: 1.0rem !important; }
        .block-container { padding: 10px !important; }
        .stButton button { width: 100% !important; padding: 5px !important; }
    </style>
""")

# --- CONTROL DE ACCESO / CONTRASEÑA ---
CONTRASEÑA_CORRECTA = "FamiliaGSPA2026"

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔒 Acceso Familia")
    password_input = st.text_input("Contraseña:", type="password")
    boton_ingresar = st.button("Ingresar", type="primary")
    
    if boton_ingresar:
        if password_input == CONTRASEÑA_CORRECTA:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("⚠️ Incorrecta")
    st.stop()

# --- CATEGORÍAS DE GASTOS ---
CATEGORIAS = {
    "Fijos Básicos": ["Hipoteca", "Colegio (La Salle)", "Guardería", "Comunidad", "Telefonía (O2)", "IBI"],
    "Fijos Opcionales": ["Extraescolares", "Suscripciones", "Seguro Médico", "Alquiler Garaje"],
    "Variables Básicos": ["Gasolina", "Luz", "Agua", "Gas", "Alimentación", "Farmacia", "Seguro Hogar", "Seguro Coche"],
    "Variables Opcionales": ["Viajes", "Regalos", "Ocio (Cine, Bolera…)", "Restaurantes", "Ropa", "Alimentación", "Peluquero", "Taller Coche", "Caldera", "Electrodomésticos", "Parking", "Peaje", "Otros", "Recon. Médico", "Gastos Heredado"]
}

ARCHIVO_DATOS = "gastos_familia_datos.csv"

def obtener_gastos():
    if os.path.exists(ARCHIVO_DATOS):
        try:
            df = pd.read_csv(ARCHIVO_DATOS)
            if not df.empty:
                df['fecha_dt'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y', errors='coerce')
                df['Importe'] = pd.to_numeric(df['Importe'], errors='coerce')
                return df
        except Exception:
            pass
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
    df_actualizado.to_csv(ARCHIVO_DATOS, index=False)

def eliminar_gasto_por_indice(indice):
    df_existente = obtener_gastos()
    if not df_existente.empty:
        df_actualizado = df_existente.drop(indice).reset_index(drop=True)
        if 'fecha_dt' in df_actualizado.columns:
            df_actualizado = df_actualizado.drop(columns=['fecha_dt'])
        df_actualizado.to_csv(ARCHIVO_DATOS, index=False)

st.title("💰 Control de Gastos")
menu = st.sidebar.radio("Menú", ["1. Registrar Gasto", "2. Estadísticas"])

if menu == "1. Registrar Gasto":
    st.header("📝 Nuevo Gasto")
    
    with st.container(border=True):
        fecha = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        tipo_gasto = st.selectbox("Tipo de Gasto", list(CATEGORIAS.keys()))
        conceptos_disponibles = CATEGORIAS[tipo_gasto]
        concepto = st.selectbox("Concepto", conceptos_disponibles)
        importe = st.number_input("Importe (€)", min_value=0.0, step=0.01, format="%.2f")
        comentario = st.text_input("Comentario (Opcional)")
        boton_enviar = st.button("Añadir Gasto", type="primary")
        
        if boton_enviar:
            if importe > 0:
                try:
                    guardar_gasto(fecha, tipo_gasto, concepto, importe, comentario)
                    st.success(f"✅ ¡Registrado!")
                    st.toast("Guardado")
                    st.rerun()
                except Exception:
                    st.error("Error al guardar.")
            else:
                st.error("⚠️ Introduce un importe")

elif menu == "2. Estadísticas":
    st.header("📊 Análisis")
    df = obtener_gastos()
    
    if df.empty or 'fecha_dt' not in df or df['fecha_dt'].isna().all():
        st.info("No hay gastos.")
    else:
        st.subheader("🔍 Filtros")
        rango_fechas = st.date_input("Fechas", [min(df['fecha_dt']).date(), max(df['fecha_dt']).date()], format="DD/MM/YYYY")
        tipos_seleccionados = st.multiselect("Tipo", options=df["Tipo de Gasto"].unique(), default=df["Tipo de Gasto"].unique())
        conceptos_filtrados = df[df["Tipo de Gasto"].isin(tipos_seleccionados)]["Concepto"].unique()
        conceptos_seleccionados = st.multiselect("Concepto", options=conceptos_filtrados, default=conceptos_filtrados)
        
        if len(rango_fechas) == 2:
            df_filtrado = df[(df['fecha_dt'].dt.date >= rango_fechas[0]) & (df['fecha_dt'].dt.date <= rango_fechas[1])]
        else:
            df_filtrado = df.copy()
            
        df_filtrado = df_filtrado[df_filtrado["Tipo de Gasto"].isin(tipos_seleccionados)]
        df_filtrado = df_filtrado[df_filtrado["Concepto"].isin(conceptos_seleccionados)]
        
        st.metric(label="Total Gastado", value=f"{df_filtrado['Importe'].sum():,.2f} €")
        
        st.subheader("📈 Gráficos")
        fig_tipo = px.pie(df_filtrado, values="Importe", names="Tipo de Gasto", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_tipo.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=250)
        st.plotly_chart(fig_tipo, use_container_width=True)
        
        fig_concepto = px.bar(df_filtrado.groupby("Concepto")["Importe"].sum().reset_index(), x="Concepto", y="Importe")
        fig_concepto.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=250)
        st.plotly_chart(fig_concepto, use_container_width=True)
            
        st.subheader("📋 Historial")
        df_vista = df_filtrado[['Fecha', "Tipo de Gasto", "Concepto", "Importe", "Comentario"]]
        
        gasto_editado = st.data_editor(df_vista, use_container_width=True, num_rows="dynamic", disabled=list(df_vista.columns))
        
        if len(gasto_editado) < len(df_vista):
            indice_borrado = list(set(df_vista.index) - set(gasto_editado.index))
            if indice_borrado:
                eliminar_gasto_por_indice(indice_borrado)
                st.rerun()
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_vista.to_excel(writer, index=False, sheet_name='Gastos')
        
        st.download_button(label="📥 Exportar a Excel", data=output.getvalue(), file_name="gastos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
