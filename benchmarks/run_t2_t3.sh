#!/bin/zsh
# =============================================================================
# run_t2_t3.sh
# Automatisierte T2 Konstantlast + T3 Ramp-Testreihe
#
# T2: 3× Konstantlast je Framework (30 VU, 10 min) → Hauptmessung
# T3: 1× Ramp je Framework (0→30 VU, 12 min)
#
# DB wird vor jedem Run und vor T3 geleert → faire, reproduzierbare Bedingungen
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

T0_SCRIPT="tests/t0_baseline.js"
WARMUP_SCRIPT="tests/t1_warmup.js"
T2_SCRIPT="tests/t2_constant_load.js"
T3_SCRIPT="tests/t3_ramp.js"

MONGO_URI="mongodb+srv://nazirm10:nazirm10@vlp-benchmark-m10.bvhn2g.mongodb.net/"

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

reset_db() {
  local reason=$1
  echo "${YELLOW}  🗑  DB-Reset: ${reason}...${NC}"
  log "  DB-Reset: ${reason}"

  local result
  result=$(mongosh "$MONGO_URI" --quiet --eval \
    "db.getSiblingDB('vlp').vehicles.deleteMany({})" 2>&1)

  local count
  count=$(mongosh "$MONGO_URI" --quiet --eval \
    "db.getSiblingDB('vlp').vehicles.countDocuments({})" 2>&1)

  if [ "$count" = "0" ]; then
    echo "${GREEN}  ✅ DB geleert (0 Dokumente)${NC}"
    log "  DB-Reset erfolgreich – 0 Dokumente"
  else
    echo "${RED}  ⚠️  DB-Reset unsicher – ${count} Dokumente verbleiben${NC}"
    log "  DB-Reset Warnung – ${count} Dokumente verbleiben"
  fi
}

check_prerequisites() {
  log_section "Voraussetzungen prüfen"
  local ok=true

  command -v k6 &>/dev/null && \
    echo "${GREEN}  ✅ k6 gefunden${NC}" || \
    { echo "${RED}  ❌ k6 fehlt${NC}"; ok=false; }

  command -v mongosh &>/dev/null && \
    echo "${GREEN}  ✅ mongosh gefunden${NC}" || \
    { echo "${RED}  ❌ mongosh fehlt (brew install mongosh)${NC}"; ok=false; }

  for var in SAM_URL SLS_URL FAAS_URL; do
    if [ -z "${(P)var}" ]; then
      echo "${RED}  ❌ $var nicht gesetzt${NC}"; ok=false
    else
      echo "${GREEN}  ✅ $var gesetzt${NC}"
    fi
  done

  for script in "$T0_SCRIPT" "$WARMUP_SCRIPT" "$T2_SCRIPT" "$T3_SCRIPT"; do
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
run_t0_checks() {
  log_section "T0 Smoke-Test – alle Frameworks"

  local all_ok=true

  for entry in "sam:${SAM_URL}" "sls:${SLS_URL}" "faas:${FAAS_URL}"; do
    local name="${entry%%:*}"
    local url="${entry#*:}"
    local name_upper=$(echo "$name" | tr '[:lower:]' '[:upper:]')

    echo "${BLUE}  T0 → ${name_upper} (${url})${NC}"
    log "  T0 gestartet: ${name_upper}"

    local result
    result=$(k6 run \
      --env BASE_URL="$url" \
      --vus 1 --iterations 1 \
      "$T0_SCRIPT" 2>&1)

    local exit_code=$?
    local checks_ok=$(echo "$result" | grep -o "checks_succeeded.*" | head -1)
    local failed=$(echo "$result" | grep "checks_failed" | grep -v "0.00%" | head -1)

    if [ $exit_code -eq 0 ] && [ -z "$failed" ]; then
      echo "${GREEN}  ✅ T0 ${name_upper}: alle Checks bestanden${NC}"
      log "  T0 ${name_upper}: OK"
    else
      echo "${RED}  ❌ T0 ${name_upper}: Checks fehlgeschlagen!${NC}"
      echo "$result" | grep -E "✓|✗|status" | head -10
      log "  T0 ${name_upper}: FEHLER"
      all_ok=false
    fi
  done

  if [ "$all_ok" = false ]; then
    echo "\n${RED}${BOLD}  Abbruch: T0 fehlgeschlagen. Bitte Deployments prüfen.${NC}\n"
    exit 1
  fi

  echo "\n${GREEN}${BOLD}  ✅ T0 alle Frameworks OK – starte Haupttests.${NC}\n"
  log "T0 alle Frameworks bestanden."
}

run_t1_check() {
  local name=$1
  local url=$2
  local name_upper=$(echo "$name" | tr '[:lower:]' '[:upper:]')

  echo "${BLUE}  T1 Warm-up Check (${name_upper})...${NC}"
  log "  T1 Check gestartet: ${name_upper}"

  local result
  result=$(k6 run --env BASE_URL="$url" "$WARMUP_SCRIPT" 2>&1)
  local rate=$(echo "$result" | grep "http_req_failed" | grep -o "rate=[0-9.]*%" | head -1)

  echo "$result" | grep -E "✓|✗|rate=" | head -5
  echo "${GREEN}  ✅ T1 Warm-up ${name_upper} abgeschlossen (${rate})${NC}"
  log "  T1 ${name_upper} abgeschlossen: ${rate}"
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

    # DB vor jedem Run leeren
    reset_db "vor Run ${run}/${RUNS} (${name_upper})"

    # Warm-up via T1
    run_t1_check "$name" "$url"

    # T2 Konstantlast
    local outfile="${RESULTS_DIR}/t2_${name}_run${run}.json"
    local ts_start=$(date '+%Y-%m-%d %H:%M:%S')
    local ts_start_epoch=$(date +%s)
    echo "${BLUE}  [2/2] Konstantlast (10 min, 30 VU)...${NC}"
    echo "${YELLOW}  T2 Start-Timestamp: ${ts_start}${NC}"
    log "  T2 gestartet → $outfile"
    log "  TIMESTAMP_START t2_${name}_run${run}: ${ts_start} (epoch: ${ts_start_epoch})"

    k6 run \
      --env BASE_URL="$url" \
      --out "json=${outfile}" \
      "$T2_SCRIPT" || true

    local ts_end=$(date '+%Y-%m-%d %H:%M:%S')
    local ts_end_epoch=$(date +%s)
    echo "${GREEN}  ✅ Run ${run} gespeichert: ${outfile}${NC}"
    echo "${YELLOW}  T2 End-Timestamp:   ${ts_end}${NC}"
    log "  Run ${run} gespeichert: $outfile"
    log "  TIMESTAMP_END   t2_${name}_run${run}: ${ts_end} (epoch: ${ts_end_epoch})"

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

  # DB vor T3 leeren
  reset_db "vor T3 (${name_upper})"

  local outfile="${RESULTS_DIR}/t3_${name}.json"
  echo "${BLUE}  Ramp-Test läuft (0→30 VU, 12 min)...${NC}"
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
echo "  T2: 3× 10 min Konstantlast je Framework (30 VU, DB-Reset vor jedem Run)"
echo "  T3: 1× 12 min Ramp je Framework (0→30 VU, DB-Reset vor T3)"
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

# T0 Smoke-Test – alle Frameworks müssen antworten
run_t0_checks

# Initiales DB-Reset vor dem ersten Framework
reset_db "initialer Reset vor Testbeginn"

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
echo "${YELLOW}  Nächster Schritt: Auswertung mit analyze_all.py${NC}"
log "T2/T3 Testreihe vollständig abgeschlossen."
