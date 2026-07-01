-- Marca quando uma recorrente foi desativada, para o dashboard (Grupo A)
-- contar slots apenas nos dias em que a tarefa esteve vigente.
-- Idempotente: ADD COLUMN IF NOT EXISTS. Roda depois da 001 (ordem numerica).
-- Linhas existentes ficam com deactivated_at = NULL (ativas = vigentes). Sem
-- backfill: nao inventamos datas de desativacao para o passado.
ALTER TABLE recurring_tasks ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMPTZ
