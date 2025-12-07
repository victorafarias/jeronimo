-- Adicionando colunas de suporte a tipos e mídia em chat_logs
ALTER TABLE chat_logs ADD COLUMN message_type VARCHAR;
ALTER TABLE chat_logs ADD COLUMN media_data TEXT;
ALTER TABLE chat_logs ADD COLUMN evolution_id VARCHAR;
