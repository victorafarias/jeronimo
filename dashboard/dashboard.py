import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
from datetime import date, timedelta

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
# Layout de Cabeçalho e Filtros
col_header, col_filters, col_auth = st.columns([2, 3, 1])

with col_header:
    st.title("🚀 Jeronimo Dashboard")

# Gerenciamento de Estado dos Filtros
def init_filters():
    if 'data_inicial' not in st.session_state:
        st.session_state['data_inicial'] = None
    if 'data_final' not in st.session_state:
        st.session_state['data_final'] = None

def set_date_range(days):
    st.session_state['data_final'] = date.today()
    st.session_state['data_inicial'] = date.today() - timedelta(days=days)

def reset_filters():
    st.session_state['data_inicial'] = None
    st.session_state['data_final'] = None

init_filters()

with col_filters:
    st.subheader("Filtros de Data")
    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    
    # Inputs de Data (interagem com session_state)
    # Alterado: Formato de data para DD/MM/YYYY
    start_val = st.date_input("Início", value=st.session_state['data_inicial'], key='input_inicio', format="DD/MM/YYYY",
                              on_change=lambda: st.session_state.update({'data_inicial': st.session_state.input_inicio}))
    end_val = st.date_input("Fim", value=st.session_state['data_final'], key='input_fim', format="DD/MM/YYYY",
                            on_change=lambda: st.session_state.update({'data_final': st.session_state.input_fim}))
    
    with c3:
        st.write("") # Espaçamento
        st.write("") 
        if st.button("7 Dias"):
            set_date_range(7)
            st.rerun()
            
    with c4:
        st.write("")
        st.write("")
        if st.button("30 Dias"):
            set_date_range(30)
            st.rerun()

    if st.button("Limpar Filtros"):
        reset_filters()
        st.rerun()

# Variáveis para uso nas queries
date_start = st.session_state['data_inicial']
date_end = st.session_state['data_final']

st.divider()

# Métricas
# Alterado: Aumentado para 6 colunas para incluir Clientes e Leads
col1, col2, col3, col4, col5, col6 = st.columns(6)

# Preparando cláusula de filtro de data
date_filter = ""
params = {}

if date_start and date_end:
    # Ajusta final do dia para cobrir todo o dia selecionado
    end_datetime = pd.to_datetime(date_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    
    date_filter = " AND created_at BETWEEN :start AND :end"
    params = {"start": date_start, "end": end_datetime}

with engine.connect() as conn:
    pending_count = conn.execute(text(f"SELECT count(*) FROM request_queue WHERE status = 'pending'{date_filter}"), params).scalar()
    processing_count = conn.execute(text(f"SELECT count(*) FROM request_queue WHERE status = 'processing'{date_filter}"), params).scalar()
    failed_count = conn.execute(text(f"SELECT count(*) FROM request_queue WHERE status = 'failed'{date_filter}"), params).scalar()
    
    # Alterado: Contabilizando todos os concluídos (respeitando filtro global se houver)
    completed_total = conn.execute(text(f"SELECT count(*) FROM request_queue WHERE status = 'completed'{date_filter}"), params).scalar()
    
    # Alterado: Novas métricas de Clientes e Leads
    clients_count = conn.execute(text(f"SELECT count(*) FROM users WHERE is_client = true{date_filter}"), params).scalar()
    leads_count = conn.execute(text(f"SELECT count(*) FROM users WHERE is_client = false{date_filter}"), params).scalar()

col1.metric("Fila Pendente", pending_count)
col2.metric("Processando", processing_count)
col3.metric("Falhas (Total)", failed_count)
col4.metric("Concluídos", completed_total)
# Alterado: Exibindo novas métricas
col5.metric("Total de Clientes", clients_count)
col6.metric("Total de Leads", leads_count)

st.divider()

# Gráficos
col_chart1, col_chart2 = st.columns(2)

# Ajuste do filtro para queries que não começam com WHERE preexistente ou precisam de WHERE
# Para charts, o GROUP BY vem depois.
# Query 1: SELECT ... FROM request_queue [WHERE ...] GROUP BY status
where_clause_chart = f"WHERE 1=1 {date_filter}" # 1=1 facilita append

with col_chart1:
    st.subheader("Status da Fila")
    df_status = pd.read_sql(text(f"SELECT status, count(*) as count FROM request_queue {where_clause_chart} GROUP BY status"), engine, params=params)
    if not df_status.empty:
        # Alterado: Traduzindo status para português
        df_status['status_pt'] = df_status['status'].map(STATUS_TRADUCAO).fillna(df_status['status'])
        fig1 = px.pie(df_status, values='count', names='status_pt', title='Distribuição de Status')
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Sem dados de fila ainda.")

with col_chart2:
    st.subheader("Logs de Processamento (Passos)")
    # processing_logs tem timestamp
    # Preciso adaptar o filtro para usar 'timestamp' em vez de 'created_at' se o nome da coluna for diferente
    # Verifiquei schemas anteriormente: ProcessingLog tem 'timestamp'.
    
    date_filter_logs = ""
    if date_start and date_end:
        date_filter_logs = " AND timestamp BETWEEN :start AND :end"
        
    df_steps = pd.read_sql(text(f"SELECT step, count(*) as count FROM processing_logs WHERE 1=1 {date_filter_logs} GROUP BY step ORDER BY count DESC LIMIT 10"), engine, params=params)
    
    if not df_steps.empty:
        # Alterado: Traduzindo passos para português
        df_steps['step_pt'] = df_steps['step'].map(PASSOS_TRADUCAO).fillna(df_steps['step'])
        fig2 = px.bar(df_steps, x='step_pt', y='count', title='Passos Mais Comuns')
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sem logs de processamento.")

st.divider()

# Alterado: Novo gráfico de Top 10 Usuários
st.subheader("🏆 Top 10 Usuários com Mais Requisições")

# CTE precisa do filtro na tabela base request_queue
query_top_users = f"""
    WITH extracted_phones AS (
        SELECT 
            CASE 
                WHEN payload::jsonb #>> '{{body,data,key,remoteJid}}' IS NOT NULL 
                THEN split_part(payload::jsonb #>> '{{body,data,key,remoteJid}}', '@', 1)
                ELSE split_part(payload::jsonb #>> '{{data,key,remoteJid}}', '@', 1)
            END as phone
        FROM request_queue
        WHERE 1=1 {date_filter}
    )
    SELECT 
        COALESCE(u.name, ep.phone) as user_identifier,
        COUNT(*) as request_count
    FROM extracted_phones ep
    LEFT JOIN users u ON ep.phone = u.phone
    WHERE ep.phone IS NOT NULL AND ep.phone != ''
    GROUP BY user_identifier
    ORDER BY request_count DESC
    LIMIT 10
"""

# Nota: f-string com chaves duplas {{ }} para escapar o JSON
df_top_users = pd.read_sql(text(query_top_users), engine, params=params)

if not df_top_users.empty:
    fig_top_users = px.bar(
        df_top_users, 
        x='request_count', 
        y='user_identifier', 
        orientation='h',
        title='Top 10 Usuários por Volume de Requisições',
        labels={'request_count': 'Total de Requisições', 'user_identifier': 'Usuário'},
        text='request_count' # Mostra o valor na barra
    )
    fig_top_users.update_layout(yaxis=dict(autorange="reversed")) # Maior no topo
    st.plotly_chart(fig_top_users, use_container_width=True)
else:
    st.info("Dados insuficientes para gerar o ranking de usuários.")

st.divider()

# Tabela de Requisições Detalhada
st.subheader("📋 Últimas Requisições (Detalhado)")

# Alterado: Ordenação por ID DESC (maior para menor)
# Adicionando filtro
df_requests = pd.read_sql(text(f"SELECT id, payload, status, created_at, updated_at, attempts FROM request_queue WHERE 1=1 {date_filter} ORDER BY id DESC LIMIT 50"), engine, params=params)

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
        # Usando bind params para a lista IN é complexo com SQLalchemy text simples, manter f-string para lista
        # Mas as datas já estao em params
        placeholders_phones = ','.join([f"'{p}'" for p in unique_phones])
        # Aqui nao precisa de filtro de data, pois estamos buscando dados cadastrais dos usuarios encontrados
        df_users = pd.read_sql(f"SELECT phone as user_phone, name, is_client, is_blocked, is_compliant FROM users WHERE phone IN ({placeholders_phones})", engine)

    if unique_evo_ids:
        placeholders_ids = ','.join([f"'{eid}'" for eid in unique_evo_ids])
        df_logs = pd.read_sql(f"SELECT evolution_id, message_text, response_text, message_type FROM chat_logs WHERE evolution_id IN ({placeholders_ids})", engine)

    df_final = pd.merge(df_requests, df_users, on='user_phone', how='left')
    df_final = pd.merge(df_final, df_logs, on='evolution_id', how='left')

    # Alterado: Formatação do tempo removendo "0 days" e mostrando só HH:MM:SS
    def calc_duration(row):
        if pd.isna(row['updated_at']):
            return "Em andamento"
        delta = row['updated_at'] - row['created_at']
        # Remove microsegundos primeiro
        duration_str = str(delta).split('.')[0]
        # Alterado: Remove "0 days " usando replace (formato: "0 days 00:00:46")
        duration_str = duration_str.replace("0 days ", "")
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

# Alterado: Renomeando colunas para nomes amigáveis em português
if not df_failures.empty:
    df_failures.columns = ['id', 'Data', 'Tentativas', 'Detalhes do Erro']

st.dataframe(df_failures, use_container_width=True)

if st.button("Atualizar Dados"):
    st.rerun()

