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
BG_YELLOW='\033[43m'
BLACK='\033[0;30m'

# ── Version ───────────────────────────────────────────────────
# When you make a change worth pushing to users:
#   1. Bump this number (e.g. 2.0.1 → 2.0.2)
#   2. Update the VERSION file in your repo to the same number
#   3. Commit & push via GitHub Desktop as normal — done.
LOCAL_VERSION="2.0.0"

GITHUB_USER="watashiwatasha"
GITHUB_REPO="macos-diagnostic-tool"
GITHUB_RAW="https://raw.githubusercontent.com/${GITHUB_USER}/${GITHUB_REPO}/main"
GITHUB_VERSION_URL="${GITHUB_RAW}/VERSION"

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

# ── Auto-Update Check ─────────────────────────────────────────
check_for_updates() {
    echo -e "  ${DIM}Checking for updates...${RESET}"

    # Fetch the VERSION file directly from the repo.
    # curl is built into macOS — no install needed.
    # -s = silent, -f = fail quietly on HTTP errors, --max-time = don't hang forever.
    LATEST_VERSION=$(curl -sf --max-time 5 \
        "$GITHUB_VERSION_URL" 2>/dev/null \
        | tr -d '[:space:]')

    # If we couldn't reach GitHub (offline, API limit, etc.) — skip silently.
    if [ -z "$LATEST_VERSION" ]; then
        echo -e "  ${DIM}(Could not reach GitHub — skipping update check)${RESET}"
        echo ""
        return
    fi

    if [ "$LATEST_VERSION" = "$LOCAL_VERSION" ]; then
        echo -e "  ${GREEN}✓${RESET}  ${DIM}You're on the latest version (v${LOCAL_VERSION})${RESET}"
        echo ""
        return
    fi

    # A newer version exists — countdown then auto-update.
    echo ""
    echo -e "  ${BG_YELLOW}${BLACK} UPDATE AVAILABLE ${RESET}  ${YELLOW}${BOLD}v${LATEST_VERSION}${RESET}${YELLOW} is out  (you have v${LOCAL_VERSION})${RESET}"
    echo ""
    echo -e "  ${WHITE}✨ A new version is ready. Updating automatically in 10 seconds.${RESET}"
    echo -e "  ${DIM}   Your old reports are never touched — only the script files update.${RESET}"
    echo ""
    echo -e "  ${DIM}   → Press  N  then Enter  to skip and keep the current version.${RESET}"
    echo ""

    # Read with timeout. If user types N/n within 10 s, skip. Otherwise, update.
    SKIP_UPDATE=false
    for i in $(seq 10 -1 1); do
        printf "\r  ${CYAN}  Updating in ${BOLD}%2d${RESET}${CYAN} seconds...   (press N + Enter to skip)${RESET}  " "$i"
        # Non-blocking read: wait 1 second for input
        if read -r -t 1 USER_INPUT </dev/tty 2>/dev/null; then
            if [[ "$USER_INPUT" =~ ^[Nn]$ ]]; then
                SKIP_UPDATE=true
                break
            fi
        fi
    done
    echo ""  # newline after countdown line

    if [ "$SKIP_UPDATE" = true ]; then
        echo ""
        echo -e "  ${DIM}Skipping update — running current version.${RESET}"
        echo ""
    else
        do_update
    fi
}

do_update() {
    echo ""
    echo -e "  ${CYAN}⬇  Downloading update...${RESET}"

    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

    # Download both files into a temp location first,
    # then move them over only if the download succeeded.
    # This prevents a half-broken state if the connection drops mid-download.

    TMP_DIR=$(mktemp -d)

    if curl -sf --max-time 30 \
        "${GITHUB_RAW}/macos_diagnostic.py" -o "${TMP_DIR}/macos_diagnostic.py" && \
       curl -sf --max-time 30 \
        "${GITHUB_RAW}/run_diagnostic.sh" -o "${TMP_DIR}/run_diagnostic.sh"; then

        # Move new files over the old ones
        mv "${TMP_DIR}/macos_diagnostic.py" "${SCRIPT_DIR}/macos_diagnostic.py"
        mv "${TMP_DIR}/run_diagnostic.sh"   "${SCRIPT_DIR}/run_diagnostic.sh"
        chmod +x "${SCRIPT_DIR}/run_diagnostic.sh"
        rm -rf "$TMP_DIR"

        echo -e "  ${BG_GREEN}${BLACK} UPDATED ${RESET}  ${GREEN}${BOLD}Now on v${LATEST_VERSION}!${RESET}"
        echo ""
        echo -e "  ${YELLOW}Restarting with the new version...${RESET}"
        echo ""
        # Re-exec this script — the new version takes over from here.
        exec bash "${SCRIPT_DIR}/run_diagnostic.sh"

    else
        rm -rf "$TMP_DIR"
        echo -e "  ${BG_RED}${WHITE} DOWNLOAD FAILED ${RESET}  ${RED}Could not download update.${RESET}"
        echo -e "  ${DIM}Check your internet connection — continuing with current version.${RESET}"
        echo ""
    fi
}

# ── Clear & Banner ────────────────────────────────────────────
echo ""
echo -e "${YELLOW}  (\__/)  ${RESET}"
echo -e "${YELLOW}  ( •ᴗ•)⚡ ${WHITE}${BOLD}macOS Diagnostic v${LOCAL_VERSION}${RESET}"
echo -e "${YELLOW}  /つ💻\ ${RESET}"
echo ""

print_line
echo -e "  ${DIM}Health check for memory · disk · GPU · thermals · daemons${RESET}"
echo ""

# ── Run update check before anything else ────────────────────
check_for_updates

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
echo -e "  ${DIM}macOS System Diagnostic Tool v${LOCAL_VERSION} · by watashiwatasha 🌼${RESET}"
echo ""
