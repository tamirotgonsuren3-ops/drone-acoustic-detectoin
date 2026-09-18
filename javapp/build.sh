#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[BUILD]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }

check_prerequisites() {
    log "Checking prerequisites..."

    if ! command -v java &>/dev/null; then
        err "Java not found. Install JDK 17:"
        err "  sudo apt install openjdk-17-jdk"
        err "  or download from https://adoptium.net/"
        exit 1
    fi

    JAVA_VER=$(java -version 2>&1 | head -n1 | grep -oP '\d+' | head -1)
    log "Java version: $JAVA_VER"

    if ! command -v gradle &>/dev/null && [ ! -f "$PROJECT_DIR/gradlew" ]; then
        warn "Gradle not found, will download wrapper"
    fi
}

download_gradle_wrapper() {
    cd "$PROJECT_DIR"

    GRADLE_VER="8.5"
    WRAPPER_JAR="$PROJECT_DIR/gradle/wrapper/gradle-wrapper.jar"
    WRAPPER_URL="https://raw.githubusercontent.com/gradle/gradle/v${GRADLE_VER}.0/gradle/wrapper/gradle-wrapper.jar"

    mkdir -p gradle/wrapper

    if [ ! -f "$WRAPPER_JAR" ] || [ ! -s "$WRAPPER_JAR" ]; then
        log "Downloading gradle-wrapper.jar v${GRADLE_VER}..."
        if command -v curl &>/dev/null; then
            curl -fsSL -o "$WRAPPER_JAR" "$WRAPPER_URL" || true
        elif command -v wget &>/dev/null; then
            wget -q -O "$WRAPPER_JAR" "$WRAPPER_URL" || true
        fi

        if [ ! -s "$WRAPPER_JAR" ]; then
            warn "Direct download failed, trying alternate URL..."
            ALT_URL="https://github.com/gradle/gradle/raw/v${GRADLE_VER}.0/gradle/wrapper/gradle-wrapper.jar"
            if command -v curl &>/dev/null; then
                curl -fsSL -o "$WRAPPER_JAR" "$ALT_URL" || true
            fi
        fi
    fi

    cat > gradle/wrapper/gradle-wrapper.properties << EOF
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-${GRADLE_VER}-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
EOF

    if [ ! -f "$PROJECT_DIR/gradlew" ]; then
        cat > "$PROJECT_DIR/gradlew" << 'WRAPPER'
#!/bin/sh
# Gradle wrapper script
APP_BASE_NAME=$(basename "$0")
APP_HOME=$(cd "$(dirname "$0")" && pwd)
CLASSPATH="$APP_HOME/gradle/wrapper/gradle-wrapper.jar"
JAVACMD="java"
if [ -n "$JAVA_HOME" ] ; then
    JAVACMD="$JAVA_HOME/bin/java"
fi
exec "$JAVACMD" \
    -Xmx256m \
    "-Dorg.gradle.appname=$APP_BASE_NAME" \
    -classpath "$CLASSPATH" \
    org.gradle.wrapper.GradleWrapperMain "$@"
WRAPPER
        chmod +x "$PROJECT_DIR/gradlew"
    fi

    if [ -s "$WRAPPER_JAR" ]; then
        log "Gradle wrapper ready (jar: $(du -h "$WRAPPER_JAR" | cut -f1))"
    else
        err "Failed to download gradle-wrapper.jar"
        err "Download manually from: https://services.gradle.org/distributions/gradle-${GRADLE_VER}-bin.zip"
        err "Or install a newer gradle: https://gradle.org/install/"
        exit 1
    fi
}

build_debug() {
    log "Building debug APK..."
    cd "$PROJECT_DIR"

    if [ -f "./gradlew" ]; then
        ./gradlew assembleDebug --no-daemon
    else
        gradle assembleDebug --no-daemon
    fi

    APK_PATH="$PROJECT_DIR/app/build/outputs/apk/debug/app-debug.apk"
    if [ -f "$APK_PATH" ]; then
        cp "$APK_PATH" "$PROJECT_DIR/SoundSense-debug.apk"
        log "APK built: $PROJECT_DIR/SoundSense-debug.apk"
        log "Size: $(du -h "$PROJECT_DIR/SoundSense-debug.apk" | cut -f1)"
    else
        err "APK not found at expected path: $APK_PATH"
        exit 1
    fi
}

build_release() {
    log "Building release APK..."
    cd "$PROJECT_DIR"

    if [ -f "./gradlew" ]; then
        ./gradlew assembleRelease --no-daemon
    else
        gradle assembleRelease --no-daemon
    fi

    APK_PATH="$PROJECT_DIR/app/build/outputs/apk/release/app-release-unsigned.apk"
    if [ -f "$APK_PATH" ]; then
        cp "$APK_PATH" "$PROJECT_DIR/SoundSense-release-unsigned.apk"
        log "Release APK: $PROJECT_DIR/SoundSense-release-unsigned.apk"
        log ""
        log "To sign the release APK, run:"
        log "  jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \\"
        log "    -keystore release-key.jks \\"
        log "    SoundSense-release-unsigned.apk alias_name"
        log ""
        log "Then zipalign:"
        log "  zipalign -v 4 SoundSense-release-unsigned.apk SoundSense.apk"
    else
        err "Release APK not found"
        exit 1
    fi
}

clean() {
    log "Cleaning build..."
    cd "$PROJECT_DIR"
    if [ -f "./gradlew" ]; then
        ./gradlew clean --no-daemon
    fi
    rm -f "$PROJECT_DIR/SoundSense-debug.apk" "$PROJECT_DIR/SoundSense-release-unsigned.apk"
    log "Clean complete"
}

usage() {
    cat << EOF
SoundSense Android Build Script

Usage: $(basename "$0") [command]

Commands:
  debug     Build debug APK (default)
  release   Build release APK (unsigned)
  clean     Clean build artifacts
  setup     Setup Gradle wrapper only
  all       Build both debug and release
  help      Show this help

The debug APK can be installed directly on any Android device.
For release builds, you need to sign the APK.

Requirements:
  - JDK 17 or later
  - Android SDK (usually installed with Android Studio)
  - ANDROID_HOME environment variable set

EOF
}

setup_android_sdk() {
    if [ -z "${ANDROID_HOME:-}" ] && [ -z "${ANDROID_SDK_ROOT:-}" ]; then
        if [ -d "$HOME/Android/Sdk" ]; then
            export ANDROID_HOME="$HOME/Android/Sdk"
            log "Auto-detected ANDROID_HOME: $ANDROID_HOME"
        elif [ -d "$HOME/android-sdk" ]; then
            export ANDROID_HOME="$HOME/android-sdk"
            log "Auto-detected ANDROID_HOME: $ANDROID_HOME"
        elif [ -d "/opt/android-sdk" ]; then
            export ANDROID_HOME="/opt/android-sdk"
            log "Auto-detected ANDROID_HOME: $ANDROID_HOME"
        else
            err "Android SDK not found. Install Android Studio or set ANDROID_HOME"
            exit 1
        fi
    fi

    if [ -n "${ANDROID_HOME:-}" ]; then
        log "Android SDK: $ANDROID_HOME"
        if [ ! -f "$PROJECT_DIR/local.properties" ]; then
            echo "sdk.dir=$ANDROID_HOME" > "$PROJECT_DIR/local.properties"
            log "Created local.properties"
        fi
    fi
}

main() {
    local cmd="${1:-debug}"

    check_prerequisites
    download_gradle_wrapper
    setup_android_sdk

    case "$cmd" in
        debug)   build_debug ;;
        release) build_release ;;
        clean)   clean ;;
        setup)   log "Setup complete" ;;
        all)     build_debug; build_release ;;
        help|-h|--help) usage ;;
        *)
            err "Unknown command: $cmd"
            usage
            exit 1
            ;;
    esac
}

main "$@"
