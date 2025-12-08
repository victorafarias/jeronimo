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
# Alterado: Configuração de pool para evitar erro "SSL SYSCALL error: EOF detected"
# - pool_pre_ping: Verifica se a conexão está ativa antes de usar
# - pool_recycle: Recicla conexões a cada 5 minutos para evitar conexões ociosas
# - pool_size: Número máximo de conexões no pool
@st.cache_resource
def get_connection():
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Verifica conexão antes de usar
        pool_recycle=300,    # Recicla conexões a cada 5 minutos
        pool_size=5,         # Tamanho do pool
        max_overflow=10      # Conexões extras permitidas
    )

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

# Tabela de Requisições Detalhada
st.subheader("📋 Últimas Requisições (Detalhado)")

# 1. Busca Requisições Recentes
df_requests = pd.read_sql("SELECT id, payload, status, created_at, updated_at, attempts FROM request_queue ORDER BY created_at DESC LIMIT 50", engine)

if not df_requests.empty:
    # 2. Extração de Dados do Payload (Python Side)
    def extract_metadata(row):
        payload = row['payload']
        if not payload: return pd.Series([None, None])
        
        # Tenta extrair evolution id e phone
        # Path: body -> data -> key -> id ou data -> key -> id
        try:
            body = payload.get("body", {})
            data = body.get("data") if body else payload.get("data")
            if not data: return pd.Series([None, None])
            
            key = data.get("key", {})
            evo_id = key.get("id")
            remote_jid = key.get("remoteJid", "")
            phone = remote_jid.split("@")[0] if remote_jid else None
            
            return pd.Series([evo_id, phone])
        except:
            return pd.Series([None, None])

    df_requests[['evolution_id', 'user_phone']] = df_requests.apply(extract_metadata, axis=1)

    # 3. Busca Dados Relacionados (ChatLogs e Users)
    # Pegamos ids únicos para filtrar query (otimização)
    unique_phones = df_requests['user_phone'].dropna().unique().tolist()
    unique_evo_ids = df_requests['evolution_id'].dropna().unique().tolist()

    df_users = pd.DataFrame()
    df_logs = pd.DataFrame()

    if unique_phones:
        placeholders = ','.join([f"'{p}'" for p in unique_phones])
        df_users = pd.read_sql(f"SELECT phone as user_phone, name, is_client, is_blocked, is_compliant FROM users WHERE phone IN ({placeholders})", engine)

    if unique_evo_ids:
        placeholders = ','.join([f"'{eid}'" for eid in unique_evo_ids])
        df_logs = pd.read_sql(f"SELECT evolution_id, message_text, response_text FROM chat_logs WHERE evolution_id IN ({placeholders})", engine)

    # 4. Merge dos Dados
    # Merge Requests + Users
    df_final = pd.merge(df_requests, df_users, on='user_phone', how='left')
    
    # Merge + ChatLogs
    df_final = pd.merge(df_final, df_logs, on='evolution_id', how='left')

    # 5. Calculo de Tempo (Duration)
    # Se updated_at existe, duration = updated - created. Se não, "Em andamento"
    def calc_duration(row):
        if pd.isna(row['updated_at']):
            return "Em andamento"
        delta = row['updated_at'] - row['created_at']
        return str(delta).split('.')[0] # Remove microsegundos

    df_final['duration'] = df_final.apply(calc_duration, axis=1)

    # 6. Seleção e Renomeação de Colunas
    df_display = df_final[[
        'user_phone', 'name', 'is_client', 'is_blocked', 'is_compliant',
        'message_text', 'response_text', 'duration', 'status'
    ]].copy()

    df_display.columns = [
        'Telefone', 'Nome', 'Cliente?', 'Bloqueado?', 'Adimplente?',
        'Mensagem Usuário', 'Resposta IA', 'Tempo Processamento', 'Status'
    ]

    st.dataframe(df_display, use_container_width=True)

else:
    st.info("Nenhuma requisição encontrada.")

st.divider()

# Tabela de Falhas Recentes (Legado/Técnico)
st.subheader("⚠️ Logs de Erros Técnicos")
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
