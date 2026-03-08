#!/bin/zsh
# =============================================================================
# run_t2_t3.sh
# Automatisierte T2 Konstantlast + T3 Ramp-Testreihe
#
# T2: 3× Konstantlast je Framework (50 VU, 10 min) → Hauptmessung
# T3: 1× Ramp je Framework (0→50 VU, 12 min)
#
# KEINE manuelle Intervention nötig – einfach starten und schlafen.
# Alle Ergebnisse werden in results/ gespeichert.
#
# Ausführung:
#   chmod +x run_t2_t3.sh
#   ./run_t2_t3.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

RUNS=3
FRAMEWORK_PAUSE=600       # 10 min zwischen Frameworks
RUN_PAUSE=600             # 10 min zwischen T2-Runs
RESULTS_DIR="results"
LOG_FILE="${RESULTS_DIR}/t2_t3_protokoll.log"

WARMUP_SCRIPT="tests/t1_warmup.js"
T2_SCRIPT="tests/t2_constant_load.js"
T3_SCRIPT="tests/t3_ramp.js"

SAM_URL="${SAM_URL:-}"
SLS_URL="${SLS_URL:-}"
FAAS_URL="${FAAS_URL:-}"

# =============================================================================
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
    printf "\r${YELLOW}  ⏳ %s – noch %02d:%02d verbleibend...${NC}" \
      "$label" "$minutes" "$secs"
    sleep 1
  done
  printf "\r${GREEN}  ✅ %s abgeschlossen.                    ${NC}\n" "$label"
  log "  Wartezeit abgeschlossen: $label"
}

check_prerequisites() {
  log_section "Voraussetzungen prüfen"
  local ok=true

  command -v k6 &>/dev/null && \
    echo "${GREEN}  ✅ k6 gefunden${NC}" || \
    { echo "${RED}  ❌ k6 fehlt${NC}"; ok=false; }

  for var in SAM_URL SLS_URL FAAS_URL; do
    if [ -z "${(P)var}" ]; then
      echo "${RED}  ❌ $var nicht gesetzt${NC}"; ok=false
    else
      echo "${GREEN}  ✅ $var gesetzt${NC}"
    fi
  done

  for script in "$WARMUP_SCRIPT" "$T2_SCRIPT" "$T3_SCRIPT"; do
    if [ ! -f "$script" ]; then
      echo "${RED}  ❌ Nicht gefunden: $script${NC}"; ok=false
    else
      echo "${GREEN}  ✅ $script gefunden${NC}"
    fi
  done

  mkdir -p "$RESULTS_DIR"
  [ "$ok" = false ] && { echo "\n${RED}Abbruch.${NC}"; exit 1; }
  log "Alle Voraussetzungen erfüllt."
}

# =============================================================================
run_t2_for_framework() {
  local name=$1
  local url=$2
  local name_upper=$(echo "$name" | tr '[:lower:]' '[:upper:]')

  log_section "T2 Konstantlast – ${name_upper} (${RUNS}× 10 min)"
  log "URL: $url"

  for run in $(seq 1 $RUNS); do
    echo "\n${BOLD}  ── T2 Run ${run}/${RUNS} ─────────────────────────────────${NC}"
    log "  T2 Run ${run}/${RUNS} gestartet"

    # Warm-up
    echo "${BLUE}  [1/2] Warm-up (3 min)...${NC}"
    k6 run --env BASE_URL="$url" --quiet "$WARMUP_SCRIPT" >> "$LOG_FILE" 2>&1 || true
    echo "${GREEN}  ✅ Warm-up abgeschlossen${NC}"
    log "  Warm-up abgeschlossen"

    # T2 Konstantlast
    local outfile="${RESULTS_DIR}/t2_${name}_run${run}.json"
    echo "${BLUE}  [2/2] Konstantlast (10 min, 50 VU)...${NC}"
    log "  T2 gestartet → $outfile"

    k6 run \
      --env BASE_URL="$url" \
      --out "json=${outfile}" \
      "$T2_SCRIPT" || true

    echo "${GREEN}  ✅ Run ${run} gespeichert: ${outfile}${NC}"
    log "  Run ${run} gespeichert: $outfile"

    # Pause zwischen Runs (außer nach dem letzten)
    if [ "$run" -lt "$RUNS" ]; then
      echo "${BLUE}  Pause zwischen Runs (10 min)...${NC}"
      countdown $RUN_PAUSE "Pause vor Run $((run+1))"
    fi
  done

  log "T2 ${name_upper} abgeschlossen."
  echo "\n${GREEN}${BOLD}  ✅ T2 ${name_upper} fertig – alle ${RUNS} Runs gespeichert.${NC}\n"
}

run_t3_for_framework() {
  local name=$1
  local url=$2
  local name_upper=$(echo "$name" | tr '[:lower:]' '[:upper:]')

  log_section "T3 Ramp – ${name_upper} (1× ~12 min)"
  log "URL: $url"

  local outfile="${RESULTS_DIR}/t3_${name}.json"
  echo "${BLUE}  Ramp-Test läuft (0→50 VU, 12 min)...${NC}"
  log "  T3 gestartet → $outfile"

  k6 run \
    --env BASE_URL="$url" \
    --out "json=${outfile}" \
    "$T3_SCRIPT" || true

  echo "${GREEN}  ✅ T3 gespeichert: ${outfile}${NC}"
  log "  T3 ${name_upper} gespeichert: $outfile"
}

# =============================================================================
clear
echo "${BOLD}${BLUE}"
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║   VLP – T2 Konstantlast + T3 Ramp (automatisiert)  ║"
echo "  ║   SAM → Serverless Framework → OpenFaaS             ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo "${NC}"
echo "  T2: 3× 10 min Konstantlast je Framework"
echo "  T3: 1× 12 min Ramp je Framework"
echo "  Gesamtdauer: ca. ${BOLD}3 Stunden${NC}"
echo ""
echo "${YELLOW}  Keine manuelle Intervention nötig.${NC}"
echo "${YELLOW}  Starte in 10 Sekunden. Abbrechen mit Ctrl+C.${NC}"
sleep 10

mkdir -p "$RESULTS_DIR"
echo "VLP T2/T3 Protokoll – $(date)" > "$LOG_FILE"
echo "SAM_URL:  $SAM_URL"  >> "$LOG_FILE"
echo "SLS_URL:  $SLS_URL"  >> "$LOG_FILE"
echo "FAAS_URL: $FAAS_URL" >> "$LOG_FILE"

check_prerequisites

# ── AWS SAM ───────────────────────────────────────────────────────────────────
run_t2_for_framework "sam" "$SAM_URL"
run_t3_for_framework "sam" "$SAM_URL"

log_section "Pause: SAM → Serverless Framework (10 min)"
countdown $FRAMEWORK_PAUSE "Framework-Pause"

# ── Serverless Framework ──────────────────────────────────────────────────────
run_t2_for_framework "sls" "$SLS_URL"
run_t3_for_framework "sls" "$SLS_URL"

log_section "Pause: Serverless Framework → OpenFaaS (10 min)"
countdown $FRAMEWORK_PAUSE "Framework-Pause"

# ── OpenFaaS ──────────────────────────────────────────────────────────────────
run_t2_for_framework "faas" "$FAAS_URL"
run_t3_for_framework "faas" "$FAAS_URL"

# ── Abschluss ─────────────────────────────────────────────────────────────────
log_section "Testreihe abgeschlossen"

echo "${GREEN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║      ✅ T2 + T3 Testreihe abgeschlossen!           ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo "${NC}"

echo "  Gespeicherte Dateien:"
ls -1 "${RESULTS_DIR}"/t2_*.json 2>/dev/null | awk '{print "    " $0}' || true
ls -1 "${RESULTS_DIR}"/t3_*.json 2>/dev/null | awk '{print "    " $0}' || true

echo ""
echo "${YELLOW}  Nächster Schritt: Auswertung mit analyze_t2.py${NC}"
log "T2/T3 Testreihe vollständig abgeschlossen."
