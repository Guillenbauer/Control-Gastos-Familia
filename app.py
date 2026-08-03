import streamlit as st
import pandas as pd
from datetime import datetime
import io
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. CONFIGURACIÓN Y LOGIN
# ==========================================
st.set_page_config(
    page_title="Control de Gastos Familiar", 
    page_icon="icono.png",  # <-- Aquí cambias el emoji por tu imagen
    layout="centered"  # Ajustado a centrado para mejorar la vista en móviles
)

# --- INYECCIÓN DE ICONO PARA MÓVILES ---
URL_MI_ICONO = "https://github.com/Guillenbauer/Control-Gastos-Familia/blob/main/Icono.png?raw=true"

st.markdown(
    f"""
    <head>
        <link rel="apple-touch-icon" sizes="180x180" href="{URL_MI_ICONO}">
        <link rel="icon" type="image/png" sizes="192x192" href="{URL_MI_ICONO}">
        <link rel="shortcut icon" href="{URL_MI_ICONO}">
    </head>
    """,
    unsafe_allow_html=True
)

def verificar_password():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.title("🔒 Acceso Restringido")
        pwd = st.text_input("Introduce la contraseña de acceso:", type="password")
        if st.button("Entrar", use_container_width=True):
            if pwd == "FamiliaGSPA2026":
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        return False
    return True

if verificar_password():

    # Conexión con Google Sheets
    conn = st.connection("gsheets", type=GSheetsConnection)

    # ==========================================
    # 2. DICCIONARIOS Y OPCIONES
    # ==========================================
    OPCIONES_CONCEPTOS = {
        "Fijos_Básicos": [
            "Hipoteca", "Colegio (La Salle)", "Guardería", 
            "Comunidad", "Telefonía (O2)", "IBI"
        ],
        "Fijos_Opcionales": [
            "Extraescolares", "Suscripciones", "Seguro Médico", "Alquiler Garaje"
        ],
        "Variables_Básicos": [
            "Gasolina", "Luz", "Agua", "Gas", "Alimentación", 
            "Farmacia", "Seguro Hogar", "Seguro Coche"
        ],
        "Variables_Opcionales": [
            "Viajes", "Regalos", "Ocio (Cine, Bolera...)", "Restaurantes", 
            "Ropa", "Alimentación", "Peluquero", "Taller Coche", 
            "Caldera", "Electrodomésticos", "Parking", "Peaje", 
            "Otros", "Recon. Médico", "Gastos Heredado"
        ]
    }

    METODOS_PAGO = ["Tarjeta", "Efectivo", "Transferencia", "Bizum", "Recibo", "Otro"]

    # ==========================================
    # 3. NAVEGACIÓN LATERAL
    # ==========================================
    st.sidebar.title("📌 Menú")
    opcion_menu = st.sidebar.radio("Ir a:", ["Registrar Gasto", "Estadísticas y Histórico"])

    # ==========================================
    # PANTALLA 1: REGISTRO DE GASTOS (MÓVIL / 1 COLUMNA)
    # ==========================================
    if opcion_menu == "Registrar Gasto":
        st.title("📝 Registrar Gasto")

        # Formulario estructurado verticalmente en 1 sola columna
        fecha = st.date_input("Fecha", value=datetime.now(), format="DD/MM/YYYY")

        tipo_gasto = st.selectbox(
            "Tipo de Gasto", 
            list(OPCIONES_CONCEPTOS.keys()), 
            key="tipo_gasto_select"
        )

        conceptos_disponibles = OPCIONES_CONCEPTOS[tipo_gasto]
        concepto = st.selectbox("Concepto", conceptos_disponibles, key="concepto_select")

        metodo_pago = st.selectbox("Método de Pago", METODOS_PAGO, key="metodo_pago_select")

        with st.form("form_registro_gasto", clear_on_submit=True):
            importe = st.number_input("Importe (€)", min_value=0.0, step=0.01, format="%.2f")
            comentarios = st.text_area("Comentarios (Opcional)", height=80)
            
            submitted = st.form_submit_button("💾 Guardar Gasto", use_container_width=True)

        if submitted:
            if importe <= 0:
                st.warning("El importe debe ser mayor a 0 €.")
            else:
                nuevo_gasto = pd.DataFrame([{
                    "Fecha": fecha.strftime("%d/%m/%Y"),
                    "Tipo de Gasto": tipo_gasto,
                    "Concepto": concepto,
                    "Método de Pago": metodo_pago,
                    "Importe (€)": importe,
                    "Comentarios": comentarios
                }])
                
                try:
                    df_existente = conn.read(ttl=0)
                    df_actualizado = pd.concat([df_existente, nuevo_gasto], ignore_index=True)
                    conn.update(data=df_actualizado)
                    st.success("¡Gasto registrado con éxito!")
                except Exception as e:
                    st.error(f"Error al guardar los datos: {e}")

    # ==========================================
    # PANTALLA 2: ESTADÍSTICAS E HISTÓRICO
    # ==========================================
    elif opcion_menu == "Estadísticas y Histórico":
        st.title("📊 Estadísticas de Gastos")

        try:
            df_gastos = conn.read(ttl=0)

            if not df_gastos.empty and "Importe (€)" in df_gastos.columns:
                df_gastos["Importe (€)"] = pd.to_numeric(df_gastos["Importe (€)"], errors="coerce").fillna(0)
                df_gastos["Fecha_dt"] = pd.to_datetime(df_gastos["Fecha"], format="%d/%m/%Y", errors="coerce")

                # --- FILTRO POR FECHAS EN SIDEBAR ---
                st.sidebar.subheader("📅 Filtrar Fechas")
                fecha_min = df_gastos["Fecha_dt"].min()
                fecha_max = df_gastos["Fecha_dt"].max()

                if pd.notna(fecha_min) and pd.notna(fecha_max):
                    rango_fechas = st.sidebar.date_input(
                        "Selecciona intervalo",
                        value=(fecha_min, fecha_max),
                        format="DD/MM/YYYY"
                    )

                    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
                        f_inicio, f_fin = rango_fechas
                        mask = (df_gastos["Fecha_dt"].dt.date >= f_inicio) & (df_gastos["Fecha_dt"].dt.date <= f_fin)
                        df_filtrado = df_gastos[mask].copy()
                    else:
                        df_filtrado = df_gastos.copy()
                else:
                    df_filtrado = df_gastos.copy()

                # --- MÉTRICA PRINCIPAL Y DESCARGA ---
                st.metric("Total Gastado en Periodo", f"{df_filtrado['Importe (€)'].sum():.2f} €")

                # Exportador a Excel (.xlsx)
                output = io.BytesIO()
                df_export = df_filtrado.drop(columns=["Fecha_dt"], errors="ignore")
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_export.to_excel(writer, index=False, sheet_name='Gastos')
                excel_data = output.getvalue()

                st.download_button(
                    label="📥 Descargar Excel (.xlsx)",
                    data=excel_data,
                    file_name=f"gastos_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

                st.divider()

                # --- GRÁFICO CIRCULAR POR TIPO DE GASTO ---
                st.subheader("🥧 Distribución por Tipo de Gasto")
                if "Tipo de Gasto" in df_filtrado.columns and not df_filtrado.empty:
                    df_pie = df_filtrado.groupby("Tipo de Gasto")["Importe (€)"].sum().reset_index()
                    
                    fig = px.pie(
                        df_pie, 
                        values="Importe (€)", 
                        names="Tipo de Gasto",
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    # Muestra % y la cantidad total en € en la etiqueta
                    fig.update_traces(textinfo="percent+value", hovertemplate="%{label}: %{value:.2f} € (%{percent})")
                    fig.update_layout(margin=dict(t=20, b=20, l=10, r=10))
                    
                    st.plotly_chart(fig, use_container_width=True)

                st.divider()

                # --- TABLAS DE DESGLOSE POR CONCEPTO Y TIPO DE GASTO ---
                st.subheader("📋 Desglose por Concepto")
                
                if "Tipo de Gasto" in df_filtrado.columns and "Concepto" in df_filtrado.columns:
                    tipos_existentes = df_filtrado["Tipo de Gasto"].unique()

                    for tipo in tipos_existentes:
                        with st.expander(f"🔹 **{tipo}**", expanded=True):
                            df_sub = df_filtrado[df_filtrado["Tipo de Gasto"] == tipo]
                            resumen_concepto = df_sub.groupby("Concepto")["Importe (€)"].sum().reset_index()
                            resumen_concepto = resumen_concepto.sort_values(by="Importe (€)", ascending=False)
                            
                            # Formato moneda para la tabla
                            resumen_concepto["Importe (€)"] = resumen_concepto["Importe (€)"].map("{:.2f} €".format)
                            
                            st.dataframe(resumen_concepto, use_container_width=True, hide_index=True)

                st.divider()

                # --- HISTÓRICO Y ELIMINACIÓN DE REGISTROS ---
                st.subheader("🗂️ Histórico de Registros")
                st.caption("Selecciona una o varias filas si deseas eliminarlas.")

                df_tabla = df_filtrado.drop(columns=["Fecha_dt"], errors="ignore").copy()
                df_tabla.insert(0, "Eliminar", False)

                edited_df = st.data_editor(
                    df_tabla,
                    hide_index=True,
                    column_config={"Eliminar": st.column_config.CheckboxColumn("Eliminar", default=False)},
                    disabled=["Fecha", "Tipo de Gasto", "Concepto", "Método de Pago", "Importe (€)", "Comentarios"],
                    use_container_width=True
                )

                filas_a_eliminar = edited_df[edited_df["Eliminar"] == True]

                if not filas_a_eliminar.empty:
                    if st.button("🗑️ Eliminar seleccionados", type="primary", use_container_width=True):
                        indices_borrar = filas_a_eliminar.index
                        df_nuevo = df_gastos.drop(columns=["Fecha_dt"], errors="ignore").drop(index=indices_borrar)
                        
                        try:
                            conn.update(data=df_nuevo)
                            st.success("Registros eliminados correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar la base de datos: {e}")

            else:
                st.info("Aún no hay datos registrados en el historial.")

        except Exception as e:
            st.error(f"Error al cargar las estadísticas: {e}")
