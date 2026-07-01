#!/usr/bin/env bash
# Deploy do Shadow Nexus Worklog.
# Uso:
#   ./deploy.sh          → verifica dependências e faz o deploy (não instala nada)
#   ./deploy.sh --install → tenta instalar dependências que faltam (Debian/Ubuntu), depois faz deploy
set -euo pipefail

INSTALL=false
[[ "${1:-}" == "--install" ]] && INSTALL=true

log()  { printf '\033[1;34m[deploy]\033[0m %s\n' "$1"; }
err()  { printf '\033[1;31m[erro]\033[0m %s\n' "$1" >&2; }

# --- 1. Verificação de dependências ---
missing=()
command -v git            >/dev/null 2>&1 || missing+=("git")
command -v docker         >/dev/null 2>&1 || missing+=("docker")
docker compose version    >/dev/null 2>&1 || missing+=("docker-compose-plugin")

if [[ ${#missing[@]} -gt 0 ]]; then
  err "Dependências ausentes: ${missing[*]}"
  if [[ "$INSTALL" == false ]]; then
    err "Instale-as manualmente, ou rode: ./deploy.sh --install (Debian/Ubuntu)"
    exit 1
  fi

  # --- 2. Instalação (só com --install, só o necessário) ---
  log "Instalando dependências ausentes (requer sudo)..."
  sudo apt-get update
  # git é trivial; Docker segue o método oficial (repo da Docker), não o pacote da distro
  for dep in "${missing[@]}"; do
    case "$dep" in
      git)
        sudo apt-get install -y git
        ;;
      docker|docker-compose-plugin)
        # Instala Docker Engine + Compose plugin pelo repositório oficial
        sudo apt-get install -y ca-certificates curl
        sudo install -m 0755 -d /etc/apt/keyrings
        sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
          -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
          | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
          docker-buildx-plugin docker-compose-plugin
        log "Docker instalado. Talvez seja preciso reabrir a sessão para usá-lo sem sudo."
        break  # o bloco docker cobre ambas as entradas
        ;;
    esac
  done
fi

# --- 3. Pré-condições de configuração ---
if [[ ! -f .env ]]; then
  err ".env não encontrado. Copie .env.example para .env e preencha os valores."
  err "  cp .env.example .env"
  exit 1
fi

# Garante que segredos placeholder não passem despercebidos.
# Ignora comentários (linhas iniciadas por #) e linhas em branco.
if grep -vE '^[[:space:]]*(#|$)' .env | grep -qE 'CHANGE_?ME|your_?secret|placeholder'; then
  err ".env ainda contém valores placeholder. Preencha antes de subir."
  exit 1
fi

# --- 4. Deploy ---
log "Atualizando código..."
git pull --ff-only

log "Subindo containers..."
docker compose up -d --build

log "Estado dos serviços:"
docker compose ps

log "Deploy concluído."
