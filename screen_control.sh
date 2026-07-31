#!/bin/bash
# ================================================
# screen_control.sh — Ekran timeout va uyqu boshqaruv skripti
# Muallif: Zoltanma
# Foydalanish:
#   ./screen_control.sh timeout 15m   # 15 daqiqa timeout
#   ./screen_control.sh timeout 1h    # 1 soat timeout
#   ./screen_control.sh timeout 30s   # 30 soniya timeout
#   ./screen_control.sh sleep         # Hoziroq uyquga
#   ./screen_control.sh wake          # Ekranni yoqish
#   ./screen_control.sh status        # Hozirgi holat
#   ./screen_control.sh off           # Timeout o'chirish
# ================================================

DISPLAY=${DISPLAY:-:0}
export DISPLAY

# Log fayl
LOG_FILE="/tmp/screen_control.log"

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

case "$1" in

    # --- TIMEOUT BELGILASH ---
    timeout)
        if [ -z "$2" ]; then
            echo "Xato: vaqt kiriting. Misol: timeout 15m yoki timeout 1h yoki timeout 30s"
            exit 1
        fi

        SECONDS_VAL=$(parse_time "$2")

        # GNOME idle delay
        gsettings set org.gnome.desktop.session idle-delay "$SECONDS_VAL" 2>/dev/null

        # xset orqali ekran timeout
        xset s "$SECONDS_VAL" "$SECONDS_VAL" 2>/dev/null
        xset +dpms 2>/dev/null
        xset dpms "$SECONDS_VAL" "$SECONDS_VAL" "$SECONDS_VAL" 2>/dev/null

        log "Timeout $2 ($SECONDS_VAL soniya) ga o'rnatildi"
        echo "✅ Ekran timeout: $2 ($SECONDS_VAL soniya)"
        ;;

    # --- EKRANNI QULFLASH ---
    lock)
        log "Ekran qulflandi"
        qdbus org.freedesktop.ScreenSaver /ScreenSaver org.freedesktop.ScreenSaver.Lock 2>/dev/null \
        || loginctl lock-session 2>/dev/null \
        || xdg-screensaver lock 2>/dev/null
        echo "🔒 Ekran qulflandi (parol so'raladi)"
        ;;

    # --- VAQTGA QULFLASH ---
    lock_timer)
        if [ -z "$2" ]; then
            echo "Xato: vaqt kiriting. Misol: lock_timer 4h"
            exit 1
        fi

        SECONDS_VAL=$(parse_time "$2")

        # Qulflash
        qdbus org.freedesktop.ScreenSaver /ScreenSaver org.freedesktop.ScreenSaver.Lock 2>/dev/null \
        || loginctl lock-session 2>/dev/null \
        || xdg-screensaver lock 2>/dev/null

        log "Ekran $2 ($SECONDS_VAL soniya) ga qulflandi, vaqt o'tgach logout"
        echo "🔒 Ekran $2 davomida qulflandi"
        echo "⏰ $2 dan keyin LOGOUT bo'lasiz (kompyuterdan chiqadi)"

        # Fon jarayonda: tizim auto-logout ni oldini olish + vaqt tugagach LOGOUT
        (
            END_TIME=$(( $(date +%s) + SECONDS_VAL ))
            while [ $(date +%s) -lt $END_TIME ]; do
                # Har 20 daqiqada idle vaqtni nollaymiz + session active bo'lib tursin
                DISPLAY=:0 xset s reset 2>/dev/null
                # loginctl ni "faol" deb belgilash (idle hint = no)
                loginctl set-idle-hint no 2>/dev/null
                sleep 1200  # 20 daqiqa
            done
            # Vaqt tugadi — LOGOUT
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
        # Qulfdan chiqish
        qdbus org.freedesktop.ScreenSaver /ScreenSaver org.freedesktop.ScreenSaver.SetActive false 2>/dev/null
        loginctl unlock-session 2>/dev/null
        DISPLAY=:0 xset dpms force on 2>/dev/null
        log "Qulf va logout timer bekor qilindi"
        echo "🔓 Qulf bekor qilindi, logout timer to'xtatildi"
        ;;

    # --- HOZIROQ UYQUGA ---
    sleep)
        log "Uyqu rejimi yoqildi"
        echo "😴 Uyqu rejimi..."
        # Ekranni o'chirish
        xset dpms force off 2>/dev/null
        # Yoki tizimni suspend qilish
        # systemctl suspend
        ;;

    # --- EKRANNI YOQISH ---
    wake)
        log "Ekran yoqildi"
        xset dpms force on 2>/dev/null
        xset s reset 2>/dev/null
        echo "☀️  Ekran yoqildi"
        ;;

    # --- TIMEOUT O'CHIRISH ---
    off)
        gsettings set org.gnome.desktop.session idle-delay 0 2>/dev/null
        xset s off 2>/dev/null
        xset -dpms 2>/dev/null
        log "Timeout o'chirildi"
        echo "🔴 Timeout o'chirildi (ekran hech o'chmaydi)"
        ;;

    # --- HOLAT ---
    status)
        IDLE=$(gsettings get org.gnome.desktop.session idle-delay 2>/dev/null | awk '{print $NF}')
        echo "📊 Hozirgi holat:"
        if [ "$IDLE" = "0" ]; then
            echo "   Timeout: O'chirilgan"
        else
            MINUTES=$((IDLE / 60))
            HOURS=$((IDLE / 3600))
            if [ "$IDLE" -lt 60 ]; then
                echo "   Timeout: ${IDLE} soniya"
            elif [ "$IDLE" -lt 3600 ]; then
                echo "   Timeout: ${MINUTES} daqiqa"
            else
                echo "   Timeout: ${HOURS} soat"
            fi
        fi
        xset q 2>/dev/null | grep -A3 "Screen Saver\|DPMS"
        ;;

    *)
        echo "Foydalanish:"
        echo "  $0 timeout 30s    # 30 soniya"
        echo "  $0 timeout 15m    # 15 daqiqa"
        echo "  $0 timeout 2h     # 2 soat"
        echo "  $0 lock           # Ekranni quflash"
        echo "  $0 sleep          # Hoziroq ekran o'chsin"
        echo "  $0 wake           # Ekranni yoq"
        echo "  $0 off            # Timeoutni o'chir"
        echo "  $0 status         # Hozirgi holat"
        ;;
esac
