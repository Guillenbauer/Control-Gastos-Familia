import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Configuración de la app
st.set_page_config(
    page_title="Control de Gastos", page_icon="💰", layout="centered"
)

# Estilo para ocultar cabeceras/menús de Streamlit en la vista móvil
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""",
    unsafe_allow_html=True,
)


# --- SISTEMA DE AUTENTICACIÓN / CONTRASEÑA ---
def check_password():
    """Devuelve True si el usuario introduce la contraseña correcta."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title("🔒 Acceso Restringido")
    pwd_input = st.text_input("Introduce la contraseña:", type="password")

    if st.button("Ingresar"):
        # Compara con la clave guardada en st.secrets
        if "APP_PASSWORD" in st.secrets and pwd_input == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Contraseña incorrecta")

    return False


# Si la contraseña no es correcta, detenemos la ejecución aquí
if not check_password():
    st.stop()

# --- A PARTIR DE AQUÍ SOLO ACCEDE USUARIO AUTENTICADO ---

# Botón para cerrar sesión en la barra lateral/arriba
if st.sidebar.button("🔒 Cerrar sesión"):
    st.session_state.authenticated = False
    st.rerun()

# Conexión directa a Google Sheets usando Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("💰 Mis Gastos")

# Formulario de alta
st.subheader("Registrar nuevo gasto")

with st.form(key="form_gasto", clear_on_submit=True):
    fecha = st.date_input("Fecha")
    concepto = st.text_input("Concepto (ej. Supermercado, Gasolina)")
    categoria = st.selectbox(
        "Categoría",
        [
            "Alimentación",
            "Hogar / Suministros",
            "Transporte",
            "Ocio y Entretenimiento",
            "Salud y Bienestar",
            "Otros",
        ],
    )
    metodo_pago = st.selectbox(
        "Método de Pago", ["Tarjeta", "Efectivo", "Bizum / Transferencia"]
    )
    importe = st.number_input(
        "Importe (€)", min_value=0.01, step=0.50, format="%.2f"
    )

    guardar = st.form_submit_button("➕ Guardar Gasto")

if guardar:
    if not concepto.strip():
        st.error("Por favor, introduce un concepto.")
    else:
        with st.spinner("Guardando gasto en Google Sheets..."):
            df_existente = conn.read(ttl=0)

            nuevo_gasto = pd.DataFrame(
                [
                    {
                        "Fecha": fecha.strftime("%Y-%m-%d"),
                        "Concepto": concepto,
                        "Categoría": categoria,
                        "Método de Pago": metodo_pago,
                        "Importe (€)": importe,
                    }
                ]
            )

            df_actualizado = pd.concat(
                [df_existente, nuevo_gasto], ignore_index=True
            )
            conn.update(data=df_actualizado)

            st.success("¡Gasto guardado correctamente en Google Sheets!")

# Visualización de datos guardados
st.divider()
st.subheader("Historial de Gastos")

try:
    df_gastos = conn.read(ttl=0)

    if not df_gastos.empty and "Importe (€)" in df_gastos.columns:
        df_gastos["Importe (€)"] = pd.to_numeric(
            df_gastos["Importe (€)"], errors="coerce"
        ).fillna(0)

        st.metric("Total Acumulado", f"{df_gastos['Importe (€)'].sum():.2f} €")
        st.dataframe(df_gastos, use_container_width=True)

        if "Categoría" in df_gastos.columns:
            resumen = (
                df_gastos.groupby("Categoría")["Importe (€)"]
                .sum()
                .reset_index()
            )
            st.bar_chart(data=resumen, x="Categoría", y="Importe (€)")
    else:
        st.info("Aún no hay gastos registrados.")
except Exception as e:
    st.info("Agrega tu primer gasto arriba para comenzar a sincronizar.")
    st.bar_chart(data=resumen, x="Categoría", y="Importe (€)")
    else:
        st.info("Aún no hay gastos registrados.")
except Exception as e:
    st.info("Agrega tu primer gasto arriba para comenzar a sincronizar.")
