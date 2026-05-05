$env:QT_OPENGL="software"
$env:QTWEBENGINE_DISABLE_SANDBOX="1"
$env:QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu --disable-gpu-compositing --disable-logging --log-level=3 --ignore-certificate-errors --no-sandbox --disable-features=VizDisplayCompositor"
$env:QT_LOGGING_RULES="qt.webenginecontext.debug=false;qt.webenginecontext.warning=false;qt.qpa.*=false"
python run_app_clean.py
