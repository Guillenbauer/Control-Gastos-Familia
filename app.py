import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ==========================================
# 1. CONFIGURACIÓN Y LOGIN
# ==========================================
st.set_page_config(page_title="Control de Gastos Familiar", layout="wide")

def verificar_password():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.title("🔒 Acceso Restringido")
        pwd = st.text_input("Introduce la contraseña de acceso:", type="password")
        if st.button("Entrar"):
            if pwd == "FamiliaGSPA2026":
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        return False
    return True

if verificar_password():

    # Conexión con Google Sheets
    from streamlit_gsheets import GSheetsConnection

    conn = st.connection("gsheets", type=GSheetsConnection)

    # ==========================================
    # 2. DICCIONARIO DE CONCEPTOS CONDICIONALES (TUS DATOS REALES)
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

    # ==========================================
    # 3. NAVEGACIÓN LATERAL
    # ==========================================
    st.sidebar.title("Navegación")
    opcion_menu = st.sidebar.radio("Ir a:", ["Registrar Gasto", "Estadísticas y Histórico"])

    # ==========================================
    # PANTALLA 1: REGISTRO DE GASTOS (REACTIVO)
    # ==========================================
    if opcion_menu == "Registrar Gasto":
        st.title("📝 Registro de Gastos")

        col1, col2 = st.columns(2)

        with col1:
            fecha = st.date_input("Fecha", value=datetime.now(), format="DD/MM/YYYY")
            
            # Al estar fuera del form, este selectbox reactualiza la página al instante
            tipo_gasto = st.selectbox(
                "Tipo de Gasto", 
                list(OPCIONES_CONCEPTOS.keys()), 
                key="tipo_gasto_select"
            )
            
            # El concepto se actualiza en tiempo real según la elección
            conceptos_disponibles = OPCIONES_CONCEPTOS[tipo_gasto]
            concepto = st.selectbox("Concepto", conceptos_disponibles, key="concepto_select")

        with col2:
            # El resto de datos los metemos en un formulario para el envío final
            with st.form("form_importe_comentarios", clear_on_submit=True):
                importe = st.number_input("Importe (€)", min_value=0.0, step=0.01, format="%.2f")
                comentarios = st.text_area("Comentarios (Opcional)", height=100)
                submitted = st.form_submit_button("Guardar Gasto")

        if submitted:
            if importe <= 0:
                st.warning("El importe debe ser mayor a 0 €.")
            else:
                nuevo_gasto = pd.DataFrame([{
                    "Fecha": fecha.strftime("%d/%m/%Y"),
                    "Tipo de Gasto": tipo_gasto,
                    "Concepto": concepto,
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
        st.title("📊 Estadísticas e Histórico de Gastos")

        try:
            df_gastos = conn.read(ttl=0)

            if not df_gastos.empty and "Importe (€)" in df_gastos.columns:
                # Formateo de tipos de datos
                df_gastos["Importe (€)"] = pd.to_numeric(df_gastos["Importe (€)"], errors="coerce").fillna(0)
                df_gastos["Fecha_dt"] = pd.to_datetime(df_gastos["Fecha"], format="%d/%m/%Y", errors="coerce")

                # --- FILTRO POR RANGO DE FECHAS EN SIDEBAR ---
                st.sidebar.subheader("Filtrar Fechas")
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

                # --- TOTAL Y BOTÓN DE DESCARGA EN EXCEL ---
                col_metric, col_download = st.columns([2, 1])
                
                with col_metric:
                    st.metric("Total Gastado en el Periodo", f"{df_filtrado['Importe (€)'].sum():.2f} €")
                
                with col_download:
                    # Generar archivo Excel en memoria (.xlsx)
                    output = io.BytesIO()
                    df_export = df_filtrado.drop(columns=["Fecha_dt"], errors="ignore")
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='Gastos')
                    excel_data = output.getvalue()

                    st.download_button(
                        label="📥 Descargar Excel (.xlsx)",
                        data=excel_data,
                        file_name=f"historico_gastos_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                st.divider()

                # --- GRÁFICOS RESUMEN ---
                st.subheader("📈 Gráficos Resumen")
                col_g1, col_g2 = st.columns(2)

                with col_g1:
                    st.markdown("**Gastos por Tipo**")
                    if "Tipo de Gasto" in df_filtrado.columns:
                        resumen_tipo = df_filtrado.groupby("Tipo de Gasto")["Importe (€)"].sum().reset_index()
                        st.bar_chart(data=resumen_tipo, x="Tipo de Gasto", y="Importe (€)")

                with col_g2:
                    st.markdown("**Gastos por Concepto**")
                    if "Concepto" in df_filtrado.columns:
                        resumen_concepto = df_filtrado.groupby("Concepto")["Importe (€)"].sum().reset_index()
                        st.bar_chart(data=resumen_concepto, x="Concepto", y="Importe (€)")

                st.divider()

                # --- TABLA INTERACTIVA DE HISTÓRICO Y ELIMINACIÓN ---
                st.subheader("🗂️ Histórico de Gastos (Seleccionar para eliminar)")
                st.caption("Marca las casillas de los registros que quieras borrar y pulsa el botón de abajo.")

                # Preparar DataFrame para data_editor agregando columna de selección
                df_tabla = df_filtrado.drop(columns=["Fecha_dt"], errors="ignore").copy()
                df_tabla.insert(0, "Eliminar", False)

                edited_df = st.data_editor(
                    df_tabla,
                    hide_index=True,
                    column_config={"Eliminar": st.column_config.CheckboxColumn("Eliminar", default=False)},
                    disabled=["Fecha", "Tipo de Gasto", "Concepto", "Importe (€)", "Comentarios"],
                    use_container_width=True
                )

                # Procesar la eliminación de filas seleccionadas
                filas_a_eliminar = edited_df[edited_df["Eliminar"] == True]

                if not filas_a_eliminar.empty:
                    if st.button("🗑️ Eliminar registros seleccionados", type="primary"):
                        # Filtrar df_gastos original descartando las filas marcadas
                        indices_borrar = filas_a_eliminar.index
                        df_nuevo = df_gastos.drop(columns=["Fecha_dt"], errors="ignore").drop(index=indices_borrar)
                        
                        try:
                            conn.update(data=df_nuevo)
                            st.success("Registros eliminados correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar en la base de datos: {e}")

            else:
                st.info("Aún no hay datos registrados en el historial.")

        except Exception as e:
            st.error(f"Error al cargar las estadísticas: {e}")
