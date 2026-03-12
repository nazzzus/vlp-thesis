#!/bin/zsh
# =============================================================================
# run_t4.sh
# Automatisierter T4 Cold-Start-Test
#
# Protokoll je Run:
#   1. T1 Warm-up (3 min, gestaffelt 0→30 VU)
#   2. 15 min Abkühlphase (kein Traffic)
#   3. 1 Einzelrequest → t_first messen
#
# 5 Runs je Framework, alle 3 Frameworks nacheinander.
# Gesamtdauer: ca. 4,5 Stunden
#
# Ausführung:
#   chmod +x run_t4.sh
#   ./run_t4.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

RUNS=5
COOLDOWN=900          # 15 min Abkühlphase
RESULTS_DIR="results"
LOG_FILE="${RESULTS_DIR}/t4_protokoll.log"

WARMUP_SCRIPT="tests/t1_warmup.js"
T4_SCRIPT="tests/t4_cold_start.js"

SAM_URL="${SAM_URL:-}"
SLS_URL="${SLS_URL:-}"
FAAS_URL="${FAAS_URL:-}"

# p50_warm aus T2-Ergebnissen (M10)
P50_WARM_SAM="48.5"
P50_WARM_SLS="53.0"
P50_WARM_FAAS="35.6"

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

# =============================================================================
run_t4_for_framework() {
  local name=$1
  local url=$2
  local p50_warm=$3
  local name_upper=$(echo "$name" | tr '[:lower:]' '[:upper:]')

  log_section "T4 Cold-Start – ${name_upper} (${RUNS}× Runs)"
  log "URL: $url | p50_warm: ${p50_warm}ms"

  for run in $(seq 1 $RUNS); do
    echo "\n${BOLD}  ── T4 Run ${run}/${RUNS} (${name_upper}) ────────────────────${NC}"
    log "  T4 Run ${run}/${RUNS} gestartet"

    # 1. Warm-up
    echo "${BLUE}  [1/3] Warm-up (3 min, 0→30 VU)...${NC}"
    k6 run --env BASE_URL="$url" "$WARMUP_SCRIPT" 2>&1 | \
      grep -E "rate=|✓|✗" | head -3 || true
    echo "${GREEN}  ✅ Warm-up abgeschlossen${NC}"
    log "  Warm-up abgeschlossen"

    # 2. Abkühlphase
    echo "${BLUE}  [2/3] Abkühlphase (15 min – kein Traffic)...${NC}"
    countdown $COOLDOWN "Abkühlphase Run ${run}/${RUNS}"

    # 3. Cold-Start-Messung
    local outfile="${RESULTS_DIR}/t4_${name}_run${run}.json"
    local ts=$(date '+%Y-%m-%d %H:%M:%S')
    local ts_epoch=$(date +%s)
    echo "${BLUE}  [3/3] Cold-Start-Messung...${NC}"
    log "  TIMESTAMP_T4 t4_${name}_run${run}: ${ts} (epoch: ${ts_epoch})"

    local output
    output=$(k6 run \
      --env BASE_URL="$url" \
      --out "json=${outfile}" \
      "$T4_SCRIPT" 2>&1)

    echo "$output" | grep -E "T4 Cold-Start|Timings|status" | head -5

    # t_first aus Output extrahieren
    local t_first
    t_first=$(echo "$output" | grep "T4 Cold-Start-Messung" | \
      grep -o "[0-9]* ms" | head -1 | tr -d ' ms')

    if [ -n "$t_first" ]; then
      local delta
      delta=$(python3 -c "print(f'{${t_first} - ${p50_warm}:.1f}')" 2>/dev/null || echo "?")
      echo "${GREEN}  ✅ t_first=${t_first}ms | p50_warm=${p50_warm}ms | Δt_cold=${delta}ms${NC}"
      log "  t4_${name}_run${run}: t_first=${t_first}ms | delta=${delta}ms"
    else
      echo "${YELLOW}  ⚠️  t_first konnte nicht extrahiert werden – prüfe ${outfile}${NC}"
      log "  t4_${name}_run${run}: Extraktion fehlgeschlagen"
    fi

    log "  Run ${run} gespeichert: ${outfile}"
  done

  log "T4 ${name_upper} abgeschlossen."
  echo "\n${GREEN}${BOLD}  ✅ T4 ${name_upper} fertig – alle ${RUNS} Runs gespeichert.${NC}\n"
}

# =============================================================================
clear
echo "${BOLD}${BLUE}"
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║   VLP – T4 Cold-Start-Test (automatisiert)          ║"
echo "  ║   SAM → Serverless Framework → OpenFaaS             ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo "${NC}"
echo "  Protokoll: Warmup (3 min) → Pause (15 min) → 1 Request"
echo "  5 Runs je Framework, Gesamtdauer: ca. ${BOLD}4,5 Stunden${NC}"
echo ""
echo "${YELLOW}  Keine manuelle Intervention nötig.${NC}"
echo "${YELLOW}  Starte in 10 Sekunden. Abbrechen mit Ctrl+C.${NC}"
sleep 10

mkdir -p "$RESULTS_DIR"
echo "VLP T4 Protokoll – $(date)" > "$LOG_FILE"
echo "SAM_URL:  $SAM_URL"  >> "$LOG_FILE"
echo "SLS_URL:  $SLS_URL"  >> "$LOG_FILE"
echo "FAAS_URL: $FAAS_URL" >> "$LOG_FILE"
echo "p50_warm: SAM=${P50_WARM_SAM}ms | SLS=${P50_WARM_SLS}ms | FaaS=${P50_WARM_FAAS}ms" >> "$LOG_FILE"

# Voraussetzungen prüfen
command -v k6 &>/dev/null || { echo "${RED}❌ k6 fehlt${NC}"; exit 1; }
[ -f "$WARMUP_SCRIPT" ] || { echo "${RED}❌ ${WARMUP_SCRIPT} fehlt${NC}"; exit 1; }
[ -f "$T4_SCRIPT" ]     || { echo "${RED}❌ ${T4_SCRIPT} fehlt${NC}"; exit 1; }
[ -n "$SAM_URL" ]  || { echo "${RED}❌ SAM_URL nicht gesetzt${NC}"; exit 1; }
[ -n "$SLS_URL" ]  || { echo "${RED}❌ SLS_URL nicht gesetzt${NC}"; exit 1; }
[ -n "$FAAS_URL" ] || { echo "${RED}❌ FAAS_URL nicht gesetzt${NC}"; exit 1; }
echo "${GREEN}✅ Alle Voraussetzungen erfüllt${NC}"
log "Voraussetzungen erfüllt. T4 startet."

# ── Tests ─────────────────────────────────────────────────────────────────────
run_t4_for_framework "sam"  "$SAM_URL"  "$P50_WARM_SAM"
run_t4_for_framework "sls"  "$SLS_URL"  "$P50_WARM_SLS"
run_t4_for_framework "faas" "$FAAS_URL" "$P50_WARM_FAAS"

# ── Abschluss ─────────────────────────────────────────────────────────────────
log_section "T4 Testreihe abgeschlossen"

echo "${GREEN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║      ✅ T4 Testreihe abgeschlossen!                 ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo "${NC}"
echo "  Ergebnisse:"
ls -1 "${RESULTS_DIR}"/t4_*.json 2>/dev/null | awk '{print "    " $0}' || true
echo ""
echo "${YELLOW}  Nächster Schritt: Δt_cold Auswertung mit analyze_t4.py${NC}"
log "T4 Testreihe vollständig abgeschlossen."

# ── Zusammenfassung aus Log ───────────────────────────────────────────────────
echo "\n${BOLD}  Zusammenfassung aus Protokoll:${NC}"
grep "t_first\|delta" "$LOG_FILE" | grep -v "^VLP\|^SAM\|^SLS\|^FAAS\|^p50" | \
  awk '{print "  " $0}'