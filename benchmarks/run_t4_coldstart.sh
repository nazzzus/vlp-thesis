#!/bin/zsh
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

RUNS=5
COOLDOWN=900
FRAMEWORK_PAUSE=600
RESULTS_DIR="results"
LOG_FILE="${RESULTS_DIR}/t4_protokoll.log"
WARMUP_SCRIPT="tests/t1_warmup.js"
COLDSTART_SCRIPT="tests/t4_cold_start.js"

SAM_URL="${SAM_URL:-}"
SLS_URL="${SLS_URL:-}"
FAAS_URL="${FAAS_URL:-}"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  echo "$msg"
  echo "$msg" >> "$LOG_FILE"
}

log_section() {
  local line="═══════════════════════════════════════════════════════"
  echo "\n${BOLD}${BLUE}${line}${NC}"
  echo "${BOLD}${BLUE}  $1${NC}"
  echo "${BOLD}${BLUE}${line}${NC}\n"
  echo "$line" >> "$LOG_FILE"
  echo "  $1" >> "$LOG_FILE"
  echo "$line" >> "$LOG_FILE"
}

countdown() {
  local seconds=$1
  local label=$2
  local end=$((SECONDS + seconds))
  while [ $SECONDS -lt $end ]; do
    local remaining=$((end - SECONDS))
    local minutes=$((remaining / 60))
    local secs=$((remaining % 60))
    printf "\r${YELLOW}  ⏳ %s – noch %02d:%02d verbleibend...${NC}" "$label" "$minutes" "$secs"
    sleep 1
  done
  printf "\r${GREEN}  ✅ %s abgeschlossen.                    ${NC}\n" "$label"
  log "  Wartezeit abgeschlossen: $label"
}

check_prerequisites() {
  log_section "Voraussetzungen prüfen"
  local ok=true
  if ! command -v k6 &>/dev/null; then
    echo "${RED}  ❌ k6 nicht gefunden.${NC}"; ok=false
  else
    echo "${GREEN}  ✅ k6 gefunden${NC}"
  fi
  for var in SAM_URL SLS_URL FAAS_URL; do
    if [ -z "${(P)var}" ]; then
      echo "${RED}  ❌ $var ist nicht gesetzt.${NC}"; ok=false
    else
      echo "${GREEN}  ✅ $var gesetzt${NC}"
    fi
  done
  for script in "$WARMUP_SCRIPT" "$COLDSTART_SCRIPT"; do
    if [ ! -f "$script" ]; then
      echo "${RED}  ❌ Script nicht gefunden: $script${NC}"; ok=false
    else
      echo "${GREEN}  ✅ $script gefunden${NC}"
    fi
  done
  mkdir -p "$RESULTS_DIR"
  if [ "$ok" = false ]; then
    echo "\n${RED}${BOLD}Abbruch.${NC}"; exit 1
  fi
  log "Alle Voraussetzungen erfüllt."
}

run_t4_for_framework() {
  local name=$1
  local url=$2
  local name_upper=$(echo "$name" | tr '[:lower:]' '[:upper:]')

  log_section "Framework: ${name_upper} – T4 Cold-Start (${RUNS} Wiederholungen)"
  log "URL: $url"

  for run in $(seq 1 $RUNS); do
    echo "\n${BOLD}  ── Run ${run}/${RUNS} ──────────────────────────────────────${NC}"
    log "  Run ${run}/${RUNS} gestartet"

    echo "${BLUE}  [1/3] Warm-up...${NC}"
    k6 run --env BASE_URL="$url" --quiet "$WARMUP_SCRIPT" >> "$LOG_FILE" 2>&1 || true
    echo "${GREEN}  ✅ Warm-up abgeschlossen${NC}"
    log "  Warm-up abgeschlossen"

    echo "${BLUE}  [2/3] Abkühlphase (15 min)...${NC}"
    log "  Abkühlphase gestartet"
    countdown $COOLDOWN "Abkühlphase Run ${run}/${RUNS}"

    local outfile="${RESULTS_DIR}/t4_${name}_run${run}.json"
    echo "${BLUE}  [3/3] Cold-Start-Messung...${NC}"
    log "  Cold-Start-Messung → $outfile"
    k6 run --env BASE_URL="$url" --out "json=${outfile}" "$COLDSTART_SCRIPT" || true
    echo "${GREEN}  ✅ Run ${run} gespeichert: ${outfile}${NC}"
    log "  Run ${run} gespeichert: $outfile"

    if [ "$name" = "sam" ] || [ "$name" = "sls" ]; then
      echo "\n${YELLOW}  ════════════════════════════════════════════════${NC}"
      echo "${YELLOW}  📋 JETZT CloudWatch prüfen – Log Insights:${NC}"
      echo "${YELLOW}     filter @type = \"REPORT\"${NC}"
      echo "${YELLOW}     | fields @duration, @initDuration${NC}"
      echo "${YELLOW}     | sort @timestamp desc | limit 5${NC}"
      echo "${YELLOW}  → initDuration Run ${run} notieren!${NC}"
      echo "${YELLOW}  ════════════════════════════════════════════════${NC}\n"
    fi

    if [ "$name" = "faas" ]; then
      echo "\n${YELLOW}  ════════════════════════════════════════════════${NC}"
      echo "${YELLOW}  📋 JETZT kubectl Events prüfen:${NC}"
      echo "${YELLOW}     kubectl get events -n openfaas-fn \\${NC}"
      echo "${YELLOW}       --sort-by='.lastTimestamp' | tail -10${NC}"
      echo "${YELLOW}  → Pod-Startzeit Run ${run} notieren!${NC}"
      echo "${YELLOW}  ════════════════════════════════════════════════${NC}\n"
    fi

    if [ "$run" -lt "$RUNS" ]; then
      echo "${BLUE}  30s Pause vor nächstem Run...${NC}"
      sleep 30
    fi
  done

  log "Framework ${name_upper} abgeschlossen."
  echo "\n${GREEN}${BOLD}  ✅ ${name_upper} fertig.${NC}\n"
}

clear
echo "${BOLD}${BLUE}"
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║     VLP – T4 Cold-Start Testreihe (automatisiert)   ║"
echo "  ║     SAM → Serverless Framework → OpenFaaS           ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo "${NC}"
echo "  Gesamtdauer: ca. ${BOLD}2,5 Stunden${NC}"
echo "${YELLOW}  Starte in 10 Sekunden. Abbrechen mit Ctrl+C.${NC}"
sleep 10

mkdir -p "$RESULTS_DIR"
echo "VLP T4 Protokoll – $(date)" > "$LOG_FILE"
echo "SAM_URL:  $SAM_URL" >> "$LOG_FILE"
echo "SLS_URL:  $SLS_URL" >> "$LOG_FILE"
echo "FAAS_URL: $FAAS_URL" >> "$LOG_FILE"

check_prerequisites

run_t4_for_framework "sam" "$SAM_URL"

log_section "Pause: SAM → Serverless Framework (10 min)"
countdown $FRAMEWORK_PAUSE "Framework-Pause"

run_t4_for_framework "sls" "$SLS_URL"

log_section "Pause: Serverless Framework → OpenFaaS (10 min)"
countdown $FRAMEWORK_PAUSE "Framework-Pause"

run_t4_for_framework "faas" "$FAAS_URL"

log_section "Testreihe abgeschlossen"
echo "${GREEN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║        ✅ T4 Testreihe abgeschlossen!               ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo "${NC}"
echo "  Gespeicherte Dateien:"
ls -la "${RESULTS_DIR}"/t4_*.json 2>/dev/null | awk '{print "    " $NF}' || echo "    (keine)"
echo ""
echo "${YELLOW}  Nächster Schritt: T2 Konstantlast${NC}"
log "Testreihe vollständig abgeschlossen."
