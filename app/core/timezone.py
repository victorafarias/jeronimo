# Alterado: Novo módulo utilitário para gerenciamento de timezone
# Centraliza todas as operações de data/hora no timezone de Brasília (UTC-3)

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# Constante para o timezone de Brasília (America/Sao_Paulo = UTC-3)
TIMEZONE_BR = ZoneInfo("America/Sao_Paulo")


def now_br() -> datetime:
    """
    Retorna o datetime atual no timezone de Brasília (UTC-3).
    
    Returns:
        datetime: Data/hora atual com timezone de Brasília
    
    Exemplo:
        >>> from app.core.timezone import now_br
        >>> agora = now_br()
        >>> print(agora)  # Exibe: 2025-12-08 10:52:00-03:00
    """
    return datetime.now(TIMEZONE_BR)


def to_br(dt: datetime) -> datetime:
    """
    Converte um datetime para o timezone de Brasília.
    
    Se o datetime não tiver timezone (naive), assume que é UTC.
    Se tiver timezone, converte para Brasília.
    
    Args:
        dt: datetime a ser convertido
        
    Returns:
        datetime: Data/hora convertida para timezone de Brasília
    
    Exemplo:
        >>> from datetime import datetime
        >>> from app.core.timezone import to_br
        >>> dt_utc = datetime(2025, 12, 8, 13, 0, 0)  # 13:00 UTC
        >>> dt_br = to_br(dt_utc)
        >>> print(dt_br)  # Exibe: 2025-12-08 10:00:00-03:00
    """
    if dt is None:
        return None
    
    # Se o datetime não tem timezone (naive), assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Converte para timezone de Brasília
    return dt.astimezone(TIMEZONE_BR)


def format_br(dt: datetime, formato: str = "%d/%m/%Y %H:%M:%S") -> str:
    """
    Formata um datetime no padrão brasileiro.
    
    Args:
        dt: datetime a ser formatado
        formato: string de formato (padrão: dd/mm/yyyy HH:MM:SS)
        
    Returns:
        str: Data formatada como string
    
    Exemplo:
        >>> from app.core.timezone import now_br, format_br
        >>> print(format_br(now_br()))  # Exibe: 08/12/2025 10:52:00
    """
    if dt is None:
        return ""
    
    dt_br = to_br(dt)
    return dt_br.strftime(formato)
