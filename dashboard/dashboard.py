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

# Alterado: Mapeamentos de tradução para português/Brasil
STATUS_TRADUCAO = {
    'pending': 'Pendente',
    'processing': 'Processando',
    'completed': 'Concluído',
    'failed': 'Falhou',
    'error': 'Erro'
}

PASSOS_TRADUCAO = {
    'START': 'Início',
    'STEP_1': 'Identificando Usuário',
    'EXTRACT': 'Extração de Dados',
    'TYPE_CHECK': 'Verificação de Tipo',
    'LEAD_RULE': 'Regra de Lead',
    'BLOCK_RULE': 'Regra de Bloqueio',
    'AI_PROCESS': 'Processamento IA',
    'RESPONSE': 'Resposta Enviada',
    'TIMEOUT': 'Tempo Esgotado',
    'AI_ERROR': 'Erro na IA',
    'ERROR': 'Erro Geral'
}

# Conexão DB
# Alterado: Configuração de pool para evitar erro "SSL SYSCALL error: EOF detected"
@st.cache_resource
def get_connection():
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10,
        connect_args={"options": "-c timezone=America/Sao_Paulo"}
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
    pending_count = conn.execute(text("SELECT count(*) FROM request_queue WHERE status = 'pending'")).scalar()
    processing_count = conn.execute(text("SELECT count(*) FROM request_queue WHERE status = 'processing'")).scalar()
    failed_count = conn.execute(text("SELECT count(*) FROM request_queue WHERE status = 'failed'")).scalar()
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
        # Alterado: Traduzindo status para português
        df_status['status_pt'] = df_status['status'].map(STATUS_TRADUCAO).fillna(df_status['status'])
        fig1 = px.pie(df_status, values='count', names='status_pt', title='Distribuição de Status')
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Sem dados de fila ainda.")

with col_chart2:
    st.subheader("Logs de Processamento (Passos)")
    df_steps = pd.read_sql("SELECT step, count(*) as count FROM processing_logs GROUP BY step ORDER BY count DESC LIMIT 10", engine)
    if not df_steps.empty:
        # Alterado: Traduzindo passos para português
        df_steps['step_pt'] = df_steps['step'].map(PASSOS_TRADUCAO).fillna(df_steps['step'])
        fig2 = px.bar(df_steps, x='step_pt', y='count', title='Passos Mais Comuns')
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sem logs de processamento.")

st.divider()

# Tabela de Requisições Detalhada
st.subheader("📋 Últimas Requisições (Detalhado)")

# Alterado: Ordenação por ID DESC (maior para menor)
df_requests = pd.read_sql("SELECT id, payload, status, created_at, updated_at, attempts FROM request_queue ORDER BY id DESC LIMIT 50", engine)

if not df_requests.empty:
    def extract_metadata(row):
        payload = row['payload']
        if not payload: return pd.Series([None, None])
        
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

    unique_phones = df_requests['user_phone'].dropna().unique().tolist()
    unique_evo_ids = df_requests['evolution_id'].dropna().unique().tolist()

    df_users = pd.DataFrame()
    df_logs = pd.DataFrame()

    if unique_phones:
        placeholders = ','.join([f"'{p}'" for p in unique_phones])
        df_users = pd.read_sql(f"SELECT phone as user_phone, name, is_client, is_blocked, is_compliant FROM users WHERE phone IN ({placeholders})", engine)

    if unique_evo_ids:
        placeholders = ','.join([f"'{eid}'" for eid in unique_evo_ids])
        df_logs = pd.read_sql(f"SELECT evolution_id, message_text, response_text, message_type FROM chat_logs WHERE evolution_id IN ({placeholders})", engine)

    df_final = pd.merge(df_requests, df_users, on='user_phone', how='left')
    df_final = pd.merge(df_final, df_logs, on='evolution_id', how='left')

    # Alterado: Formatação do tempo removendo "0 days" e mostrando só HH:MM:SS
    def calc_duration(row):
        if pd.isna(row['updated_at']):
            return "Em andamento"
        delta = row['updated_at'] - row['created_at']
        # Remove "0 days " e microsegundos, mantém apenas HH:MM:SS
        duration_str = str(delta).split('.')[0]
        if 'day' in duration_str:
            # Se tiver dias, extrai só a parte de tempo
            parts = duration_str.split(', ')
            if len(parts) > 1:
                return parts[1]  # Retorna só a parte HH:MM:SS
            return duration_str
        return duration_str

    df_final['duration'] = df_final.apply(calc_duration, axis=1)

    def format_created_at(row):
        if pd.isna(row['created_at']):
            return ""
        dt = row['created_at']
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    
    df_final['data_formatada'] = df_final.apply(format_created_at, axis=1)

    def format_message_type(row):
        msg_type = row.get('message_type', None)
        if pd.isna(msg_type) or not msg_type:
            return "Texto"
        if 'audio' in str(msg_type).lower():
            return "Áudio"
        return "Texto"
    
    df_final['tipo_mensagem'] = df_final.apply(format_message_type, axis=1)

    # Alterado: Traduzindo status para português
    df_final['status_pt'] = df_final['status'].map(STATUS_TRADUCAO).fillna(df_final['status'])

    df_display = df_final[[
        'user_phone', 'name', 'is_client', 'is_blocked', 'is_compliant',
        'tipo_mensagem', 'message_text', 'response_text', 'duration', 'status_pt', 'data_formatada'
    ]].copy()

    df_display.columns = [
        'Telefone', 'Nome', 'Cliente?', 'Bloqueado?', 'Adimplente?',
        'Tipo de Mensagem', 'Mensagem Usuário', 'Resposta IA', 'Tempo Processamento', 'Status', 'Data'
    ]

    st.dataframe(df_display, use_container_width=True)

else:
    st.info("Nenhuma requisição encontrada.")

st.divider()

# Tabela de Falhas Recentes (Legado/Técnico)
st.subheader("⚠️ Logs de Erros Técnicos")
# Alterado: Ordenação por ID DESC (maior para menor)
df_failures = pd.read_sql("""
    SELECT q.id, q.created_at, q.attempts, l.details as error_details
    FROM request_queue q
    LEFT JOIN processing_logs l ON q.id = l.queue_id AND l.status = 'error'
    WHERE q.status = 'failed'
    ORDER BY q.id DESC
    LIMIT 10
""", engine)
st.dataframe(df_failures, use_container_width=True)

if st.button("Atualizar Dados"):
    st.rerun()

