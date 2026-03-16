#!/bin/bash
# macOS Diagnostic Tool - Easy Launcher
# Runs the diagnostic and auto-opens the HTML report.
# Usage: bash run_diagnostic.sh

set -e

# ── Colors & Styles ──────────────────────────────────────────
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'

BG_GREEN='\033[42m'
BG_RED='\033[41m'
BLACK='\033[0;30m'

# ── Helpers ───────────────────────────────────────────────────
print_line() {
    echo -e "${DIM}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

print_double_line() {
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${RESET}"
}

spinner() {
    local pid=$1
    local msg=$2
    local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
    local i=0
    while kill -0 "$pid" 2>/dev/null; do
        printf "\r  ${CYAN}${frames[$i]}${RESET}  ${WHITE}${msg}${RESET}  "
        i=$(( (i + 1) % ${#frames[@]} ))
        sleep 0.08
    done
    printf "\r  ${GREEN}✓${RESET}  ${WHITE}${msg}${RESET}  \n"
}

# ── Clear & Banner ────────────────────────────────────────────
echo ""
echo -e "${YELLOW}   /) (\ ${RESET}"
echo -e "${YELLOW}  ( •ᴗ• ) ${WHITE}${BOLD}⚡ macOS Diagnostic v1.0${RESET}"
echo -e "${YELLOW}   づ🖥${RESET}"
echo ""

print_line
echo -e "  ${DIM}Health check for memory · disk · GPU · thermals · daemons${RESET}"
echo ""

# ── Locate files ──────────────────────────────────────────────
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_SCRIPT="$SCRIPT_DIR/macos_diagnostic.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "  ${BG_RED}${WHITE} ERROR ${RESET}  ${RED}macos_diagnostic.py not found in:${RESET}"
    echo -e "         ${DIM}${SCRIPT_DIR}${RESET}"
    echo -e "  ${YELLOW}Make sure both files are in the same folder.${RESET}"
    echo ""
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo -e "  ${BG_RED}${WHITE} ERROR ${RESET}  ${RED}python3 not found on this system.${RESET}"
    echo -e "  ${YELLOW}Fix:${RESET} xcode-select --install"
    echo ""
    exit 1
fi

# ── Pre-flight info ───────────────────────────────────────────
MAC_USER=$(whoami)
MAC_HOST=$(hostname -s)
SCAN_TIME=$(date "+%H:%M:%S")
SCAN_DATE=$(date "+%A, %d %B %Y")

echo -e "  ${DIM}User   ${RESET}  ${WHITE}${MAC_USER}@${MAC_HOST}${RESET}"
echo -e "  ${DIM}Date   ${RESET}  ${WHITE}${SCAN_DATE}${RESET}"
echo -e "  ${DIM}Time   ${RESET}  ${WHITE}${SCAN_TIME}${RESET}"
echo -e "  ${DIM}Script ${RESET}  ${WHITE}${PYTHON_SCRIPT}${RESET}"
echo ""
print_line
echo ""

# ── Countdown ─────────────────────────────────────────────────
echo -e "  ${YELLOW}⚡ Starting scan in...${RESET}"
for i in 3 2 1; do
    echo -ne "  ${BOLD}${CYAN}  ${i}${RESET}\r"
    sleep 0.6
done
echo -e "  ${BOLD}${GREEN}  Go!${RESET}   "
echo ""

# ── Run diagnostic ────────────────────────────────────────────
print_line
echo -e "\n  ${BOLD}${WHITE}RUNNING FULL SCAN${RESET}\n"
print_line
echo ""

python3 "$PYTHON_SCRIPT" &
DIAG_PID=$!
spinner $DIAG_PID "Scanning system — this takes ~30 seconds..."
wait $DIAG_PID
DIAG_EXIT=$?

echo ""
print_line
echo ""

# ── Result ────────────────────────────────────────────────────
if [ $DIAG_EXIT -ne 0 ]; then
    echo -e "  ${BG_RED}${WHITE} FAILED ${RESET}  ${RED}Diagnostic exited with errors.${RESET}"
    echo -e "  ${DIM}Check the output above for details.${RESET}"
    echo ""
    exit $DIAG_EXIT
fi

echo -e "  ${BG_GREEN}${BLACK} DONE ${RESET}  ${GREEN}${BOLD}Scan complete!${RESET}"
echo ""

# ── Open report ───────────────────────────────────────────────
REPORT_DIR="$HOME/Desktop/diagnostic_reports"
if [ -d "$REPORT_DIR" ]; then
    LATEST_HTML=$(ls -t "$REPORT_DIR"/diagnostic_*.html 2>/dev/null | head -1)
    if [ -n "$LATEST_HTML" ]; then
        REPORT_NAME=$(basename "$LATEST_HTML")
        echo -e "  ${CYAN}📄 Report  ${RESET}${WHITE}${REPORT_NAME}${RESET}"
        echo -e "  ${CYAN}📁 Saved   ${RESET}${DIM}${REPORT_DIR}${RESET}"
        echo ""
        echo -e "  ${YELLOW}Opening in browser...${RESET}"
        open "$LATEST_HTML"
    fi
fi

echo ""
print_double_line
echo ""
echo -e "  ${DIM}Tip: Paste the report into Claude and ask${RESET}"
echo -e "  ${DIM}     \"What should I fix first?\" for AI analysis.${RESET}"
echo ""
echo -e "  ${DIM}Run again anytime:${RESET}  ${CYAN}bash ${BASH_SOURCE[0]}${RESET}"
echo ""
print_double_line
echo -e "  ${DIM}macOS System Diagnostic Tool v1.0 · by watashiwatasha 🌼${RESET}"
echo ""
