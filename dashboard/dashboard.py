import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

# Adiciona raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text
from app.core.config import settings

# Configuração da Página
st.set_page_config(page_title="Jeronimo Dashboard", layout="wide")

# Conexão DB
@st.cache_resource
def get_connection():
    return create_engine(settings.DATABASE_URL)

engine = get_connection()

# Autenticação Simples
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.subheader("Login")
    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        if user == settings.DASHBOARD_USER and pwd == settings.DASHBOARD_PASSWORD:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Credenciais inválidas")
    return False

if not check_password():
    st.stop()

# --- Dashboard Home ---
st.title("🚀 Jeronimo Dashboard Monitor")

# Métricas
col1, col2, col3, col4 = st.columns(4)

with engine.connect() as conn:
    # Fila Pendente
    pending_count = conn.execute(text("SELECT count(*) FROM request_queue WHERE status = 'pending'")).scalar()
    # Em Processamento
    processing_count = conn.execute(text("SELECT count(*) FROM request_queue WHERE status = 'processing'")).scalar()
    # Falhas (Total)
    failed_count = conn.execute(text("SELECT count(*) FROM request_queue WHERE status = 'failed'")).scalar()
    # Processados Hoje
    completed_today = conn.execute(text("SELECT count(*) FROM request_queue WHERE status = 'completed' AND created_at >= current_date")).scalar()

col1.metric("Fila Pendente", pending_count)
col2.metric("Processando", processing_count)
col3.metric("Falhas (Total)", failed_count)
col4.metric("Concluídos Hoje", completed_today)

st.divider()

# Gráficos
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("Status da Fila")
    df_status = pd.read_sql("SELECT status, count(*) as count FROM request_queue GROUP BY status", engine)
    if not df_status.empty:
        fig1 = px.pie(df_status, values='count', names='status', title='Distribuição de Status')
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Sem dados de fila ainda.")

with col_chart2:
    st.subheader("Logs de Processamento (Passos)")
    df_steps = pd.read_sql("SELECT step, count(*) as count FROM processing_logs GROUP BY step ORDER BY count DESC LIMIT 10", engine)
    if not df_steps.empty:
        fig2 = px.bar(df_steps, x='step', y='count', title='Passos Mais Comuns')
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sem logs de processamento.")

st.divider()

# Tabela de Falhas Recentes
st.subheader("⚠️ Falhas Recentes")
df_failures = pd.read_sql("""
    SELECT q.id, q.created_at, q.attempts, l.details as error_details
    FROM request_queue q
    LEFT JOIN processing_logs l ON q.id = l.queue_id AND l.status = 'error'
    WHERE q.status = 'failed'
    ORDER BY q.created_at DESC
    LIMIT 10
""", engine)
st.dataframe(df_failures, use_container_width=True)

if st.button("Atualizar Dados"):
    st.rerun()
