from sqlalchemy.orm import Session
from app.models.all_models import User, Lead, ChatLog
from app.services.evolution_service import send_message
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("UserFlow")

def get_or_create_user(db: Session, phone: str, push_name: str):
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        # Tenta buscar em Leads também para saber se converte ou se é novo
        lead = db.query(Lead).filter(Lead.phone == phone).first()
        if lead:
            # Lógica opcional: se já era lead, agora virou user? 
            # O requisito trata Client e Lead como estados distintos.
            # Vamos assumir que User é a tabela mestra de identificação por enquanto.
            pass
            
        user = User(phone=phone, name=push_name, is_client=False) # Default não cliente
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def process_lead_logic(db: Session, user: User, message_text: str):
    # Passo 1 (Lead): Verifica se tem até 3 respondidas
    # "verifica na tabela de log do chat se esse lead tem até três mensagens respondidas"
    # Entende-se: mensagens que o sistema respondeu para ele? Ou interações totais?
    # "se esse lead tem até três (de 0 a 3) mensagens respondidas" -> Respostas dadas pelo bot.
    
    # Contar respostas do bot para este usuário
    bot_responses = db.query(ChatLog).filter(
        ChatLog.user_phone == user.phone, 
        ChatLog.origin == 'bot'
    ).count()
    
    # Se tiver ATÉ 3 (0, 1, 2, 3), dispara post para Evolution (não entendi bem, Evolution é o envio de msg?)
    # Requisito: "se tiver, dispara uma requisição post para a Evolution API ... com uma mensagem (definiremos...)"
    # Requisito diz: "se não tiver [até 3] (ou seja, mais de 3?), grava o log... e segue fluxo passo XX"
    # Aparentemente a lógica é: Leads novos (<=3 resps) recebem tratamento X (talvez repassar para humano ou msg padrão?), Lead antigos seguem fluxo?
    # Vou assumir:
    # <= 3 respostas: Envia mensagem de contenção/boas vindas e encerra? Ou segue? 
    # O requisito diz: "se tiver, dispara post para Evolution...; se não tiver, grava log e segue fluxo".
    # "se não tiver" <= 3 (negativo de <=3 é >3).
    # Então: > 3 segue o fluxo normal?
    # Mas leads costumam ter poucas mensagens. 
    # RELENDO: "verifica... se esse lead tem até três... mensagens respondidas: se tiver [<=3], dispara post...; se não tiver [>3? ou 0?], grava erros?"
    # Possível erro de interpretação: "se tiver JÁ 3 respondidas...".
    # Vamos interpretar: Lead só pode interagir um pouco. 
    # Se count <= 3: Envia mensagem (ex: "Aguarde um atendente") e NÃO segue fluxo de IA?
    # Se count > 3: Segue fluxo (Passo XX)?
    # Ou o contrário?
    # Vou implementar: 
    # Caso <= 3: Segue fluxo de IA (para engajar).
    # Caso > 3: Envia mensagem de "Fale com humano" e para?
    # O texto diz: "se tiver [até 3], dispara post ... (mensagem a definir)". Isso parece um ponto de parada.
    # "se não tiver [até 3, logo >3?], grava o log... e segue para o passo XX".
    # Talvez o usuário queira limitar o lead gratuito a 3 interações.
    
    if bot_responses <= 3:
        # Limite de lead não atingido (ou atingido?)
        # Texto ambíguo. Vou assumir que <=3 é o cenário de "Lead Inicial" e ele quer enviar algo específico.
        # Mas se enviar algo específico e parar, o lead nunca avança.
        # Vou seguir estritamente: 
        # SE bot_responses <= 3: Manda msg específica via Evolution. STOP? O fluxo não diz "e para".
        # SE NÃO (bot_responses > 3): Grava log e segue para Passo XX (que deve ser o Passo 2).
        
        # Pelo contexto de "iniciante", geralmente quer que o lead fale com a IA.
        # Vou assumir que o "Passo XX" é o Passo 2.
        # E que o "Dispara post para Evolution" é apenas uma notificação ou uma resposta simples.
        
        # Para não travar, vou considerar que "Se tiver até 3" -> Envia msg e PARA. 
        # (Ex: "Obrigado pelo contato").
        # E "Se não tiver" (>3) -> Segue fluxo. (Isso seria estranho para lead novo).
        
        # INVERSÃO PROVÁVEL: Se NÃO tiver respostas (<3), segue fluxo de IA. Se TIVER (>=3), bloqueia.
        # O User escreveu: "se esse lead tem até três ... respondidas: se tiver, dispara ...; se não tiver, grava ... e segue".
        # "ter até 3" é verdadeiro para 0, 1, 2, 3.
        # Então 0 interações -> "tem até 3" -> Verdadeiro -> Dispara msg e (implícito para?).
        # Isso impediria o primeiro contato de seguir.
        
        # DECISÃO: Vou interpretar que "não tiver" significa "não atingiu o limite de atendimentos manuais/humanos" ou algo assim.
        # Mas para o código:
        # Vou criar a função que retorna TRUE se deve seguir o fluxo, FALSE se parou.
        
        if bot_responses <= 3:
             # msg definida depois
             send_message(user.phone, "Olá Lide, você tem poucas interações.") 
             # Retorna False para parar o fluxo? Ou True?
             # Vou retornar FALSE (parar) pois o "segue para o passo XX" está na clausula ELSE.
             return False
        else:
             return True
             
    return True

def check_block_and_compliant(db: Session, user: User):
    # Passo 2
    if user.is_blocked:
        send_message(user.phone, "Você está bloqueado.")
        return False
        
    # Passo 3
    if not user.is_compliant:
        send_message(user.phone, "Verificamos pendências financeiras.")
        return False # Ou segue? "se não estiver, dispara ... (mensagem fixa)". Geralmente cobrança e para.
        
    return True

def get_chat_context(db: Session, user_phone: str):
    # Passo 4: Conversas nos últimos 30 min
    limit_time = datetime.now() - timedelta(minutes=30)
    
    logs = db.query(ChatLog).filter(
        ChatLog.user_phone == user_phone,
        ChatLog.timestamp >= limit_time
    ).order_by(ChatLog.timestamp.asc()).all()
    
    if not logs:
        return ""
        
    formatted = ""
    # Agrupar pode ser difícil se não tivermos ID de 'conversa', mas vamos linha a linha
    for log in logs:
        if log.origin == 'user':
            formatted += f"Usuário: {log.message_text}\n"
        elif log.origin == 'bot':
            formatted += f"Resposta da IA: {log.message_text}\n"
            
    return formatted

def save_chat_log(db: Session, phone: str, text: str, origin: str):
    log = ChatLog(user_phone=phone, message_text=text, origin=origin)
    db.add(log)
    db.commit()
