#!/bin/bash
# ================================================
# screen_control.sh — Ekran timeout va uyqu boshqaruv skripti
# KDE Plasma + 21school (idletimed) uchun TO'G'RILANGAN VERSIYA
#
# Muallif: Zoltanma
# Foydalanish:
#   ./screen_control.sh timeout 15m   # 15 daqiqa timeout
#   ./screen_control.sh timeout 1h    # 1 soat timeout
#   ./screen_control.sh timeout 30s   # 30 soniya timeout
#   ./screen_control.sh sleep         # Hoziroq uyquga
#   ./screen_control.sh wake          # Ekranni yoqish
#   ./screen_control.sh status        # Hozirgi holat
#   ./screen_control.sh off           # Timeout o'chirish
#   ./screen_control.sh keep_alive    # idletimed ni aldash (fon)
#   ./screen_control.sh stop_alive    # keep_alive ni to'xtatish
# ================================================

DISPLAY=${DISPLAY:-:0}
export DISPLAY

# Log fayl
LOG_FILE="/tmp/screen_control.log"
KEEP_ALIVE_PID_FILE="/tmp/screen_keep_alive.pid"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Soniyaga o'girish funksiyasi
parse_time() {
    local input="$1"
    local number="${input//[^0-9]/}"
    local unit="${input//[0-9]/}"

    case "$unit" in
        s|sec|soniya)   echo $((number)) ;;
        m|min|daqiqa)   echo $((number * 60)) ;;
        h|soat)         echo $((number * 3600)) ;;
        *)              echo $((number * 60)) ;;  # default: daqiqa
    esac
}

# Daqiqaga o'girish funksiyasi (kscreenlocker uchun)
parse_time_minutes() {
    local input="$1"
    local number="${input//[^0-9]/}"
    local unit="${input//[0-9]/}"

    case "$unit" in
        s|sec|soniya)   echo $(( (number + 59) / 60 )) ;;  # min 1 daqiqa
        m|min|daqiqa)   echo $((number)) ;;
        h|soat)         echo $((number * 60)) ;;
        *)              echo $((number)) ;;
    esac
}

# === IDLE RESET (xprintidle ni nolga qaytarish) ===
# Bu funksiya idletimed.sh ni "aldaydi" - fake mouse input orqali
reset_idle() {
    # 1-usul: python3 XTest orqali (eng ishonchli)
    python3 -c "
import ctypes, ctypes.util, os
os.environ.setdefault('DISPLAY', ':0')
xlib = ctypes.cdll.LoadLibrary(ctypes.util.find_library('X11'))
xtst = ctypes.cdll.LoadLibrary(ctypes.util.find_library('Xtst'))
display = xlib.XOpenDisplay(None)
if display:
    xtst.XTestFakeRelativeMotionEvent(display, 1, 1, 0)
    xtst.XTestFakeRelativeMotionEvent(display, -1, -1, 0)
    xlib.XFlush(display)
    xlib.XCloseDisplay(display)
" 2>/dev/null && return 0

    # 2-usul: xdg-screensaver reset
    xdg-screensaver reset 2>/dev/null && return 0

    # 3-usul: xset (kam ishonchli lekin backup)
    xset s reset 2>/dev/null
    return 0
}

# === KDE KSCREENLOCKER TIMEOUT O'RNATISH ===
set_kde_timeout() {
    local minutes="$1"
    
    if [ "$minutes" = "0" ]; then
        # Timeout o'chirish = Autolock false
        kwriteconfig5 --file kscreenlockerrc --group Daemon --key Autolock --type bool false 2>/dev/null
        log "KDE screen lock DISABLED"
    else
        # Timeout belgilash
        kwriteconfig5 --file kscreenlockerrc --group Daemon --key Autolock --type bool true 2>/dev/null
        kwriteconfig5 --file kscreenlockerrc --group Daemon --key Timeout --type int "$minutes" 2>/dev/null
        log "KDE screen lock timeout: $minutes daqiqa"
    fi
    
    # kscreenlocker ni qayta yuklash (yangi sozlamalar qo'llanilishi uchun)
    qdbus org.kde.screensaver /ScreenSaver org.kde.screensaver.configure 2>/dev/null
}

# === KEEP ALIVE FUNKSIYASI ===
# Har 50 soniyada idle ni resetlaydi (idletimed har 60 sek tekshiradi)
start_keep_alive() {
    # Agar allaqachon ishlayotgan bo'lsa - to'xtatish
    stop_keep_alive 2>/dev/null
    
    (
        while true; do
            reset_idle
            sleep 50
        done
    ) &
    local pid=$!
    echo "$pid" > "$KEEP_ALIVE_PID_FILE"
    log "Keep-alive ishga tushdi (PID: $pid)"
    echo "✅ Keep-alive ishga tushdi (har 50 sek idle reset)"
}

stop_keep_alive() {
    if [ -f "$KEEP_ALIVE_PID_FILE" ]; then
        local pid=$(cat "$KEEP_ALIVE_PID_FILE")
        kill "$pid" 2>/dev/null
        rm -f "$KEEP_ALIVE_PID_FILE"
        log "Keep-alive to'xtatildi (PID: $pid)"
        echo "🛑 Keep-alive to'xtatildi"
    else
        echo "ℹ️  Keep-alive ishlamayapti"
    fi
}

case "$1" in

    # --- TIMEOUT BELGILASH (KDE + xset + gsettings) ---
    timeout)
        if [ -z "$2" ]; then
            echo "Xato: vaqt kiriting. Misol: timeout 15m yoki timeout 1h yoki timeout 30s"
            exit 1
        fi

        SECONDS_VAL=$(parse_time "$2")
        MINUTES_VAL=$(parse_time_minutes "$2")

        # 1. KDE kscreenlocker timeout (ASOSIY!)
        set_kde_timeout "$MINUTES_VAL"

        # 2. GNOME idle delay (backup)
        gsettings set org.gnome.desktop.session idle-delay "$SECONDS_VAL" 2>/dev/null

        # 3. xset (backup)
        xset s "$SECONDS_VAL" "$SECONDS_VAL" 2>/dev/null
        xset +dpms 2>/dev/null
        xset dpms "$SECONDS_VAL" "$SECONDS_VAL" "$SECONDS_VAL" 2>/dev/null

        # 4. Keep-alive avtomatik yoqish (idletimed ni aldash)
        # Agar timeout > 30 daqiqa bo'lsa, keep_alive kerak (chunki idletimed 30 min da o'chiradi)
        if [ "$SECONDS_VAL" -gt 1800 ]; then
            stop_keep_alive 2>/dev/null
            start_keep_alive
            log "Keep-alive avtomatik yoqildi (timeout > 30 min)"
        fi

        log "Timeout $2 ($SECONDS_VAL sek / $MINUTES_VAL daqiqa) ga o'rnatildi"
        echo "✅ Ekran timeout: $2 ($MINUTES_VAL daqiqa)"
        echo "   KDE kscreenlocker: $MINUTES_VAL daqiqa"
        if [ "$SECONDS_VAL" -gt 1800 ]; then
            echo "   🟢 Keep-alive: avtomatik yoqildi (idletimed aldanadi)"
        fi
        ;;

    # --- EKRANNI QULFLASH ---
    lock)
        log "Ekran qulflandi"
        qdbus org.kde.screensaver /ScreenSaver org.freedesktop.ScreenSaver.Lock 2>/dev/null \
        || qdbus org.freedesktop.ScreenSaver /ScreenSaver org.freedesktop.ScreenSaver.Lock 2>/dev/null \
        || loginctl lock-session 2>/dev/null \
        || xdg-screensaver lock 2>/dev/null
        echo "🔒 Ekran qulflandi (parol so'raladi)"
        ;;

    # --- VAQTGA QULFLASH (keep_alive bilan) ---
    lock_timer)
        if [ -z "$2" ]; then
            echo "Xato: vaqt kiriting. Misol: lock_timer 4h"
            exit 1
        fi

        SECONDS_VAL=$(parse_time "$2")

        # Tugash vaqtini faylga yozish (bot status uchun)
        END_TS=$(( $(date +%s) + SECONDS_VAL ))
        echo "$END_TS" > /tmp/screen_lock_timer_end.txt

        # Qulflash
        qdbus org.kde.screensaver /ScreenSaver org.freedesktop.ScreenSaver.Lock 2>/dev/null \
        || qdbus org.freedesktop.ScreenSaver /ScreenSaver org.freedesktop.ScreenSaver.Lock 2>/dev/null \
        || loginctl lock-session 2>/dev/null \
        || xdg-screensaver lock 2>/dev/null

        log "Ekran $2 ($SECONDS_VAL soniya) ga qulflandi, vaqt o'tgach logout"
        echo "🔒 Ekran $2 davomida qulflandi"
        echo "⏰ $2 dan keyin LOGOUT bo'lasiz (kompyuterdan chiqadi)"

        # Fon jarayonda: idle ni aldash + vaqt tugagach LOGOUT
        (
            END_TIME=$(( $(date +%s) + SECONDS_VAL ))
            while [ $(date +%s) -lt $END_TIME ]; do
                # Har 50 soniyada idle resetlash (idletimed har 60 sek tekshiradi)
                reset_idle
                sleep 50
            done
            # Vaqt tugadi — LOGOUT
            rm -f /tmp/screen_lock_timer_end.txt
            loginctl terminate-user "$USER" 2>/dev/null
            log "Qulf vaqti tugadi ($2), LOGOUT qilindi"
        ) &
        disown
        ;;

    # --- QULFNI VA LOGOUT TIMERNI BEKOR QILISH ---
    unlock)
        # Fon jarayonini o'ldirish (logout timer)
        pkill -f "screen_control.sh lock_timer" 2>/dev/null
        pkill -f "loginctl terminate-user" 2>/dev/null
        # Lock timer faylini tozalash
        rm -f /tmp/screen_lock_timer_end.txt
        # Qulfdan chiqish
        qdbus org.kde.screensaver /ScreenSaver org.freedesktop.ScreenSaver.SetActive false 2>/dev/null \
        || qdbus org.freedesktop.ScreenSaver /ScreenSaver org.freedesktop.ScreenSaver.SetActive false 2>/dev/null
        loginctl unlock-session 2>/dev/null
        DISPLAY=:0 xset dpms force on 2>/dev/null
        log "Qulf va logout timer bekor qilindi"
        echo "🔓 Qulf bekor qilindi, logout timer to'xtatildi"
        ;;

    # --- HOZIROQ UYQUGA ---
    sleep)
        log "Uyqu rejimi yoqildi"
        echo "😴 Uyqu rejimi..."
        xset dpms force off 2>/dev/null
        ;;

    # --- EKRANNI YOQISH ---
    wake)
        log "Ekran yoqildi"
        xset dpms force on 2>/dev/null
        reset_idle
        echo "☀️  Ekran yoqildi"
        ;;

    # --- TIMEOUT O'CHIRISH ---
    off)
        # KDE kscreenlocker off
        set_kde_timeout 0
        
        # GNOME backup
        gsettings set org.gnome.desktop.session idle-delay 0 2>/dev/null
        
        # xset backup
        xset s off 2>/dev/null
        xset -dpms 2>/dev/null

        # Keep-alive to'xtatish (timeout yo'q = keep_alive kerak emas)
        stop_keep_alive 2>/dev/null
        
        log "Timeout o'chirildi"
        echo "🔴 Timeout o'chirildi (ekran hech o'chmaydi)"
        echo "   🛑 Keep-alive ham to'xtatildi"
        ;;

    # --- KEEP ALIVE (idletimed ni aldash) ---
    keep_alive)
        start_keep_alive
        ;;

    # --- KEEP ALIVE TO'XTATISH ---
    stop_alive)
        stop_keep_alive
        ;;

    # --- HOLAT ---
    status)
        # KDE kscreenlocker timeout
        KDE_AUTOLOCK=$(kreadconfig5 --file kscreenlockerrc --group Daemon --key Autolock 2>/dev/null)
        KDE_TIMEOUT=$(kreadconfig5 --file kscreenlockerrc --group Daemon --key Timeout 2>/dev/null)
        
        echo "📊 Hozirgi holat:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [ "$KDE_AUTOLOCK" = "true" ]; then
            echo "   🔒 KDE Screen Lock: YOQIQ ($KDE_TIMEOUT daqiqa)"
        else
            echo "   🔓 KDE Screen Lock: O'CHIQ"
        fi
        
        # GNOME idle
        IDLE=$(gsettings get org.gnome.desktop.session idle-delay 2>/dev/null | awk '{print $NF}')
        if [ "$IDLE" = "0" ]; then
            echo "   🔴 GNOME idle: O'chirilgan"
        else
            echo "   ⏱  GNOME idle: ${IDLE} soniya"
        fi
        
        # xprintidle
        IDLE_MS=$(xprintidle 2>/dev/null || echo "?")
        if [ "$IDLE_MS" != "?" ]; then
            IDLE_SEC=$((IDLE_MS / 1000))
            IDLE_MIN=$((IDLE_SEC / 60))
            echo "   ⏳ Hozirgi idle: ${IDLE_MIN}m ${IDLE_SEC}s (${IDLE_MS}ms)"
        fi
        
        # Keep-alive holati
        if [ -f "$KEEP_ALIVE_PID_FILE" ] && kill -0 "$(cat "$KEEP_ALIVE_PID_FILE")" 2>/dev/null; then
            echo "   🟢 Keep-alive: ISHLAYAPTI"
        else
            echo "   🔴 Keep-alive: O'CHIQ"
        fi
        
        # idletimed holati
        if pgrep -f "idletimed" > /dev/null 2>&1; then
            echo "   ⚠️  idletimed: ISHLAYAPTI (30 min idle = auto-logout)"
        else
            echo "   ✅ idletimed: ISHLAMAYAPTI"
        fi
        
        # xset holati
        xset q 2>/dev/null | grep -A3 "Screen Saver\|DPMS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ;;

    *)
        echo "Foydalanish:"
        echo "  $0 timeout 30s     # 30 soniya"
        echo "  $0 timeout 15m     # 15 daqiqa"
        echo "  $0 timeout 2h      # 2 soat"
        echo "  $0 lock            # Ekranni quflash"
        echo "  $0 lock_timer 4h   # Vaqtga quflash (keyin logout)"
        echo "  $0 unlock          # Qulfni ochish"
        echo "  $0 sleep           # Hoziroq ekran o'chsin"
        echo "  $0 wake            # Ekranni yoq"
        echo "  $0 off             # Timeoutni o'chir"
        echo "  $0 keep_alive      # idletimed ni aldash (auto-logout yo'q)"
        echo "  $0 stop_alive      # keep_alive ni to'xtatish"
        echo "  $0 status          # Hozirgi holat"
        ;;
esac
