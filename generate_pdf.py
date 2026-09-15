import os
from fpdf import FPDF


class SoundsensePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("Arial", "", "C:\\Windows\\Fonts\\arial.ttf")
        self.add_font("Arial", "B", "C:\\Windows\\Fonts\\arialbd.ttf")
        self.add_font("Consolas", "", "C:\\Windows\\Fonts\\consola.ttf")
        self.add_font("Consolas", "B", "C:\\Windows\\Fonts\\consolab.ttf")
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() > 1:
            self.set_font("Arial", "", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 8, "SoundSense - Дуу таних систем", align="L")
            self.cell(0, 8, f"Хуудас {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(200, 200, 200)
            self.line(10, 16, 200, 16)
            self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, "12-р ангийн сурагчдад зориулсан заавар", align="C")

    def chapter_title(self, title):
        self.set_font("Arial", "B", 16)
        self.set_text_color(37, 99, 235)
        self.ln(5)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(37, 99, 235)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def section_title(self, title):
        self.set_font("Arial", "B", 13)
        self.set_text_color(30, 41, 59)
        self.ln(3)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def sub_title(self, title):
        self.set_font("Arial", "B", 11)
        self.set_text_color(71, 85, 105)
        self.ln(2)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font("Arial", "", 10)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def bullet(self, text):
        self.set_font("Arial", "", 10)
        self.set_text_color(51, 65, 85)
        x = self.get_x()
        self.cell(8, 6, chr(8226))
        self.multi_cell(0, 6, text)
        self.ln(1)

    def code_block(self, code, title=None):
        if title:
            self.set_font("Arial", "B", 9)
            self.set_text_color(100, 116, 139)
            self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
            self.ln(1)

        self.set_fill_color(241, 245, 249)
        self.set_draw_color(203, 213, 225)
        self.set_text_color(30, 41, 59)

        lines = code.strip().split("\n")
        line_h = 5
        block_h = len(lines) * line_h + 8

        if self.get_y() + block_h > 270:
            self.add_page()

        y_start = self.get_y()
        self.rect(10, y_start, 190, block_h, "DF")

        self.set_font("Consolas", "", 8)
        self.set_xy(14, y_start + 4)
        for line in lines:
            self.set_x(14)
            self.cell(0, line_h, line, new_x="LMARGIN", new_y="NEXT")
        self.set_y(y_start + block_h + 4)

    def info_box(self, text, color="blue"):
        colors = {
            "blue": (37, 99, 235, 239, 246, 254),
            "green": (22, 163, 74, 240, 253, 244),
            "yellow": (202, 138, 4, 254, 249, 195),
            "red": (220, 38, 38, 254, 226, 226),
        }
        border_r, border_g, border_b, bg_r, bg_g, bg_b = colors.get(color, colors["blue"])

        self.set_fill_color(bg_r, bg_g, bg_b)
        self.set_draw_color(border_r, border_g, border_b)
        self.set_text_color(border_r, border_g, border_b)

        self.set_font("Arial", "B", 9)
        y_start = self.get_y()
        self.rect(10, y_start, 190, 8, "DF")
        self.set_xy(14, y_start + 1)
        self.cell(0, 6, text)
        self.set_y(y_start + 10)

    def diagram_box(self, items, title=""):
        if title:
            self.set_font("Arial", "B", 10)
            self.set_text_color(30, 41, 59)
            self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

        box_w = 50
        box_h = 18
        gap = 8
        start_x = (210 - (len(items) * box_w + (len(items) - 1) * gap)) / 2
        y = self.get_y()

        for i, (label, color) in enumerate(items):
            x = start_x + i * (box_w + gap)
            if color == "blue":
                self.set_fill_color(37, 99, 235)
            elif color == "green":
                self.set_fill_color(22, 163, 74)
            elif color == "orange":
                self.set_fill_color(245, 158, 11)
            elif color == "purple":
                self.set_fill_color(139, 92, 246)
            elif color == "red":
                self.set_fill_color(220, 38, 38)

            self.set_draw_color(100, 100, 100)
            self.rect(x, y, box_w, box_h, "DF")
            self.set_fill_color(255, 255, 255)
            self.rect(x + 1, y + 1, box_w - 2, box_h - 2, "F")

            self.set_font("Arial", "B", 8)
            self.set_text_color(30, 41, 59)
            self.set_xy(x, y + 5)
            self.cell(box_w, 8, label, align="C")

        self.set_y(y + box_h + 8)

        arrow_y = y + box_h / 2
        for i in range(len(items) - 1):
            x1 = start_x + i * (box_w + gap) + box_w
            x2 = start_x + (i + 1) * (box_w + gap)
            self.set_draw_color(100, 100, 100)
            self.set_line_width(0.5)
            mid = (x1 + x2) / 2
            self.line(x1 + 1, arrow_y, x2 - 1, arrow_y)
            self.line(x2 - 3, arrow_y - 2, x2 - 1, arrow_y)
            self.line(x2 - 3, arrow_y + 2, x2 - 1, arrow_y)
        self.set_line_width(0.2)
        self.ln(4)


def generate():
    pdf = SoundsensePDF()

    # ============ TITLE PAGE ============
    pdf.add_page()
    pdf.set_font("Arial", "B", 28)
    pdf.set_text_color(37, 99, 235)
    pdf.ln(40)
    pdf.cell(0, 15, "SoundSense", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Arial", "", 14)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 10, "IoT Дуу Таних Систем", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(1)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(15)

    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 8, "Python + Flask + MQTT + Machine Learning", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "12-р ангийн сурагчдад зориулсан кодын тайлбар", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(30)

    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 7, "2026", align="C", new_x="LMARGIN", new_y="NEXT")

    # ============ TABLE OF CONTENTS ============
    pdf.add_page()
    pdf.chapter_title("Агуулга")
    toc = [
        ("1. Төслийн тухай ерөнхий мэдээлэл", 3),
        ("2. Дүр зураг (Architecture)", 3),
        ("3. Ямар технологи ашигласан бэ?", 4),
        ("4. Файлуудын жагсаалт", 4),
        ("5. app.py - Үндсэн сервер", 5),
        ("6. mqtt_bridge.py - MQTT холболт", 7),
        ("7. audio_ml.py - Machine Learning", 8),
        ("8. index.html - Гар утасны апп", 9),
        ("9. dashboard.html - Хяналтын самбар", 10),
        ("10. app.js - Гар утасны логик", 10),
        ("11. dashboard.js - Dashboard логик", 11),
        ("12. Ашиглах заавар", 12),
        ("13. MQTT мессежийн формат", 13),
        ("14. Асуулт - Хариулт", 14),
    ]
    for title, page in toc:
        pdf.set_font("Arial", "", 11)
        pdf.set_text_color(51, 65, 85)
        dots = "." * (60 - len(title))
        pdf.cell(0, 8, f"{title} {dots} {page}", new_x="LMARGIN", new_y="NEXT")

    # ============ CHAPTER 1: ABOUT ============
    pdf.add_page()
    pdf.chapter_title("1. Төслийн тухай")
    pdf.body_text(
        "SoundSense бол зөөврийн компьютер буюу гар утасны микрофоноор "
        "дуу авиаг таних, MQTT протоколоор илгээх IoT (Internet of Things) систем юм."
    )
    pdf.body_text("Энэ төрлийн систем нь дараах зүйлсийг хийдэг:")
    pdf.bullet("Гар утасны микрофоноор дуу чимээ сонсож, танина")
    pdf.bullet("Танисан дууг сервер рүү илгээнэ (MQTT ашиглаж)")
    pdf.bullet("Сервер дээр бүх илэрсэн дуунуудыг хүлээн авч хадгална")
    pdf.bullet("Хяналтын самбар (Dashboard) дээр real-time харуулна")

    pdf.info_box("Энэ төсөл нь их сургуулийн эцсийн төсөл эсвэл шинжлэх ухааны үзэсгэлэнд тохиромжтой!", "green")

    pdf.ln(3)
    pdf.body_text(
        "Жишээ нь: Хэрэв таны хашаанд нохой хашхирах эсвэл дроны дуу гарахад "
        "тэр дууг таньж, мессеж илгээдэг систем гэсэн үг. Энэ нь хяналтын "
        "камерын оронд аудиогоор хяналт хийх боломж юм."
    )

    # ============ CHAPTER 2: ARCHITECTURE ============
    pdf.chapter_title("2. Дүр зураг (Architecture)")
    pdf.body_text("Төсөл нь 4 гол хэсгээс бүрдэнэ:")

    pdf.diagram_box([
        ("Gar utas\n(App)", "blue"),
        ("Flask\nServer", "green"),
        ("MQTT\nBroker", "orange"),
        ("Dashboard", "purple"),
    ])

    pdf.body_text("Мөр бүрийн утгыг тайлбарлая:")
    pdf.bullet("Gar utas (App) - Таны гар утасны веб хуудас. Микрофоноор дуу сонсож, танина.")
    pdf.bullet("Flask Server - Python-н сервер. Бүх логик энд ажиллана: файл хадгалах, ML сургах, MQTT холбох.")
    pdf.bullet("MQTT Broker - Мессеж шилжүүлэгч сервер (HiveMQ, Mosquitto гэх мэт). Илэрсэн дууг бусад төхөөрөмжид хүргэнэ.")
    pdf.bullet("Dashboard - Хяналтын самбар. Бүх илэрсэн дууг хүснэгтэд харуулна.")

    pdf.ln(2)
    pdf.sub_title("Ажиллах явц:")
    pdf.body_text(
        "1. Хэрэглэгч гар утаснаа микрофоноо асаана\n"
        "2. Веб хуудас микрофоноос дуу чимээ авна (Web Audio API)\n"
        "3. Авсан дууг frequency буюу давтамжийн мэдээлэл болгоно\n"
        "4. ML модель тэр дууг танина (жнь: нохой, дрон, машин)\n"
        "5. Танисан дууг MQTT мессеж болгоод сервер рүү илгээнэ\n"
        "6. Сервер тэр мессежийг хүлээн авч Dashboard дээр харуулна"
    )

    # ============ CHAPTER 3: TECHNOLOGIES ============
    pdf.add_page()
    pdf.chapter_title("3. Ямар технологи ашигласан бэ?")
    pdf.body_text("Энд тус бүрийн технологийн талаар энгийнээр тайлбарлав:")

    pdf.sub_title("Python")
    pdf.body_text(
        "Програмчлалын хэл. Энэ төсөлд сервер бичихэд ашигласан. "
        "Энгийн, уншихад хялбар хэл тул эхлэгчдэд тохиромжтой."
    )

    pdf.sub_title("Flask")
    pdf.body_text(
        "Python-н веб сервер бичих ном (library). Веб хуудас үүсгэх, "
        "API бичихэд хэрэглэнэ. 'Hello World' бичихэд 3 мөр л хангалттай."
    )

    pdf.sub_title("MQTT (Message Queuing Telemetry Transport)")
    pdf.body_text(
        "Мессеж илгээх протокол. IoT төхөөрөмжүүд хоорондоо мессеж "
        "солилцоход зориулагдсан. Жишээ нь: Ухаалаг утаснаас температурын "
        "мэдээллийг эмнэлгийн сервер рүү илгээх."
    )

    pdf.sub_title("Machine Learning (Машин сургалт)")
    pdf.body_text(
        "Компьютерт өөрөө сурах боломж олгох арга. Энэ төсөлд дуу "
        "танихын тулд MFCC (Mel-Frequency Cepstral Coefficients) гэх "
        "аргаар дууг тоо болгон хувиргаж, neural network-д сургана."
    )

    pdf.sub_title("librosa")
    pdf.body_text(
        "Python-н аудио боловсруулах ном. Дуу файлыг уншиж, "
        "дүн шинжилгээ хийхэд хэрэглэнэ. Spotify-н инженерүүд бичсэн."
    )

    pdf.sub_title("Web Audio API")
    pdf.body_text(
        "Веб хуудаснаас микрофоноос дуу авах, боловсруулах стандарт. "
        "Браузэрт байрлагдсан JavaScript API."
    )

    # ============ CHAPTER 4: FILES ============
    pdf.add_page()
    pdf.chapter_title("4. Файлуудын жагсаалт")
    pdf.body_text("Төсөлд байгаа бүх файлуудын жагсаалт болон тэдгээрийн үүрэг:")

    files = [
        ("app.py", "120 мөр", "Үндсэн Flask сервер. REST API, SocketIO, MQTT холболт"),
        ("mqtt_bridge.py", "75 мөр", "MQTT брокертэй холбогдох, мессеж илгээх/хүлээх"),
        ("audio_ml.py", "180 мөр", "Дууны онцлог шинжүүрийг гаргаж, ML модель сургах"),
        ("index.html", "150 мөр", "Гар утасны веб аппын HTML загвар"),
        ("dashboard.html", "120 мөр", "Хяналтын самбарын HTML загвар"),
        ("app.js", "320 мөр", "Гар утасны бүх үйлдэл: MQTT, микрофон, upload"),
        ("dashboard.js", "220 мөр", "Dashboard: MQTT хүлээх, хүснэгт, шүүлтүүр"),
        ("styles.css", "400 мөр", "Бүх хуудасны загвар (background, өнгө, хэмжээ)"),
    ]

    pdf.set_font("Consolas", "B", 9)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(45, 8, " Файл", fill=True)
    pdf.cell(22, 8, " Хэмжээ", fill=True)
    pdf.cell(123, 8, " Тодорхойлолт", fill=True, new_x="LMARGIN", new_y="NEXT")

    for fname, size, desc in files:
        pdf.set_font("Consolas", "", 8)
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(45, 7, f" {fname}", fill=True)
        pdf.set_font("Arial", "", 8)
        pdf.cell(22, 7, f" {size}", fill=True)
        pdf.cell(123, 7, f" {desc}", fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    pdf.info_box("Нийт 1600+ мөр код бичигдсэн. Тус бүрийг доор дэлгэрүүлж тайлбарлав.", "blue")

    # ============ CHAPTER 5: app.py ============
    pdf.add_page()
    pdf.chapter_title("5. app.py - Үндсэн сервер")
    pdf.body_text('Энэ бол төслийн "тархи" юм. Бүх зүйл эндээс эхэлнэ.')

    pdf.section_title("5.1 Импорт болон тохиргоо")
    pdf.code_block('''import os, json, uuid
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from mqtt_bridge import MQTTBridge
from audio_ml import AudioMLTrainer''', "Эхлээд шаардлагатай номуудыг дуудаж байна:")

    pdf.body_text("eventlet - Олон зүйлийг нэгэн зэрэг (concurrently) ажиллуулах ном. Flask SocketIO-д хэрэгтэй.")
    pdf.body_text("Flask - Веб сервер бичих ном.")
    pdf.body_text("SocketIO - Реал цагийн мессеж илгээх (WebSocket). Dashboard дээр шууд харуулахад хэрэгтэй.")
    pdf.body_text("MQTTBridge, AudioMLTrainer - Бидний бичсэн файлууд.")

    pdf.section_title("5.2 Flask сервер үүсгэх")
    pdf.code_block('''app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24).hex()
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MODEL_FOLDER"] = "models"
socketio = SocketIO(app, cors_allowed_origins="*")''', "Серверийн тохиргоо:")

    pdf.bullet("SECRET_KEY - Серверийн нууц түлхүүр (аюулгүй байдлын тулд)")
    pdf.bullet("UPLOAD_FOLDER - Upload хийсэн дууны файлуудыг энд хадгална")
    pdf.bullet("MODEL_FOLDER - Сургасан ML модельийг энд хадгална")
    pdf.bullet("cors_allowed_origins=\"*\" - Бүх веб хуудаснаас хандаж болно гэсэн үг")

    pdf.section_title("5.3 REST API эндпоинтууд")
    pdf.body_text("REST API гэдэг нь сервертэй харилцах хаягууд юм. Тус бүрийг нь ойлгoyo:")

    pdf.sub_title("GET / - Гар утасны хуудас")
    pdf.code_block('''@app.route("/")
def index():
    return render_template("index.html")''')
    pdf.body_text("Энгийн. Хэрэглэгч сайт руу ороход index.html хуудсыг буцаана.")

    pdf.sub_title("POST /api/upload - Дууны файл upload")
    pdf.code_block('''@app.route("/api/upload", methods=["POST"])
def upload_audio():
    file = request.files["file"]
    sound_type = request.form.get("sound_type", "")
    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file.save(filepath)''')
    pdf.body_text("Энд юу болж байна: 1) Файлыг хүлээн авна. 2) Нэрээ давхардуулахгүйн тулд random үсэг нэмнэ. 3) uploads хавтанд хадгална.")

    pdf.section_title("5.4 MQTT мессеж хүлээх")
    pdf.code_block('''def on_mqtt_message(topic, payload):
    msg_data = json.loads(payload)
    mqtt_messages.append(msg_data)
    socketio.emit("mqtt_message", msg_data)''')
    pdf.body_text("MQTT-ээс мессеж ирэхэд: JSON болгоно -> хадгална -> Dashboard руу шууд илгээнэ.")

    # ============ CHAPTER 6: mqtt_bridge.py ============
    pdf.add_page()
    pdf.chapter_title("6. mqtt_bridge.py - MQTT холболт")
    pdf.body_text("Энэ файл нь MQTT брокертэй холбогдох, мессеж илгээх/хүлээх ажлыг хийнэ.")

    pdf.section_title("6.1 Класс үүсгэх")
    pdf.code_block('''class MQTTBridge:
    def __init__(self, server, port, username, password,
                 on_message_callback):
        self.client = mqtt.Client(client_id=...)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message''')
    pdf.body_text("MQTTBridge гэдэг нь MQTT-тэй харилцах 'багаж' юм. paho.mqtt номыг ашиглаж байна.")

    pdf.section_title("6.2 Холбогдох үйлдэл")
    pdf.code_block('''def connect(self):
    self.client.connect_async(self.server, self.port,
                              keepalive=60)
    self.client.loop_start()  # Мессеж хүлээх эхлүүлнэ
    return self.is_connected''')
    pdf.body_text("connect_async - Албан ёсоор холбогдох (хүлээхгүй). loop_start - Мессеж ирэхэд автоматаар хүлээн авна.")

    pdf.section_title("6.3 Мессеж илгээх")
    pdf.code_block('''def publish(self, topic, payload):
    if self.is_connected:
        self.client.publish(topic, payload, qos=1)
        return True
    return False''')
    pdf.body_text("topic гэдэг нь мессежний 'хаяг'. Жишээ нь: 'detected/sound/' руу дууны мессеж илгээнэ.")
    pdf.body_text("qos=1 гэдэг нь мессеж заавал хүрэхийг баталгаажуулна (Quality of Service level 1).")

    # ============ CHAPTER 7: audio_ml.py ============
    pdf.add_page()
    pdf.chapter_title("7. audio_ml.py - Machine Learning")
    pdf.body_text("Энэ файл бол төслийн хамгийн сонирхолтой хэсэг! Дууг танихыг сургана.")

    pdf.section_title("7.1 Онцлог шинжүүр гаргах (Feature Extraction)")
    pdf.code_block('''def extract_features(self, file_path):
    y, sr = librosa.load(file_path, sr=22050)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
    mfcc_mean = np.mean(mfcc, axis=1)  # Дундаж
    mfcc_std = np.std(mfcc, axis=1)    # Хамаарал
    features = np.concatenate([mfcc_mean, mfcc_std, ...])
    return features''')
    pdf.body_text("Энд юу болж байна:")
    pdf.bullet("librosa.load - Дууны файлыг уншиж, тоон мэдээлэл болгоно")
    pdf.bullet("MFCC - Машух тэгшитгэлийн дууны 'хураамж'. Дуу бүрийн 'хуруун хээ' гэж бодоорой")
    pdf.bullet("mean болон std - Дундаж болон стандарт хамаарал. Энэ нь дууг тодорхойлох тоонууд")
    pdf.bullet("features - Бүх тоонуудыг нийлүүлээд нэг 'тэмдэгт мөр' болгоно")

    pdf.info_box("MFCC гэдэг нь хүний чихэнд сонсогдох дууны онцлогыг тоогоор илэрхийлсэн зүйл. Чимэхийн өнгө, өндөр, чичиргээ гэх мэт.", "yellow")

    pdf.section_title("7.2 Модель сургах (Training)")
    pdf.code_block('''self.model = MLPClassifier(
    hidden_layer_sizes=(128, 64, 32),
    activation="relu",
    max_iter=epochs
)
self.model.fit(X_train, y_train)''')
    pdf.body_text("MLPClassifier гэдэг нь 'Neural Network' буюу хиймэл мэдрэлтэй сүлжээ юм.")
    pdf.bullet("hidden_layer_sizes=(128, 64, 32) - 3 давхарга, тус бүрд нь 128, 64, 32 'мэдрэл'")
    pdf.bullet("activation='relu' - Нэг функц. Эерэг утгуудыг өнгөрөөж, сөрөг утгуудыг 0 болгоно")
    pdf.bullet("max_iter - Хичнээн удаа 'сурах' вэ")
    pdf.bullet("model.fit() - Өгөгдлөөр сургах үйлдэл")

    pdf.section_title("7.3 Таамаглах (Prediction)")
    pdf.code_block('''features = self.extract_features(file_path)
features_scaled = scaler.transform(features.reshape(1, -1))
probabilities = model.predict_proba(features_scaled)[0]
predicted_class = le.inverse_transform([np.argmax(probabilities)])''')
    pdf.body_text("Дууны файлыг авч, онцлог шинжүүрийг нь гаргаж, сургасан модельд өгч таамаглуулна. predict_proba нь бүх төрөл бүрийн магадлалыг гаргана.")

    # ============ CHAPTER 8: index.html ============
    pdf.add_page()
    pdf.chapter_title("8. index.html - Гар утасны апп")
    pdf.body_text("Энэ файл нь гар утасны веб хуудасны загварыг агуулна. 4 tab-тай:")

    pdf.diagram_box([
        ("Register", "blue"),
        ("Upload", "green"),
        ("Train", "orange"),
        ("Detect", "red"),
    ], "Tabнууд:")

    pdf.sub_title("Register (Бүртгэл)")
    pdf.body_text("MQTT серверийн мэдээллийг бөглөнө: нэр, хаяг, нууц үг. connectMQTT() JS функц дуудагдана.")

    pdf.sub_title("Upload (Аудио upload)")
    pdf.body_text("MP3/MP4 файл сонгож, sound_type label бичнэ. Жишээ: 'dog', 'drone', 'car'. /api/upload руу илгээнэ.")

    pdf.sub_title("Train (Сургалт)")
    pdf.body_text("Upload хийсэн файлуудаар ML-г сургана. trainModel() функц /api/train руу хандана.")

    pdf.sub_title("Detect (Илрүүлэг)")
    pdf.body_text("MIC товч дарж микрофоноо асаана. Дуу танихад MQTT рүү мессеж илгээнэ. Дэлгэцээ унтраасан ч background-д ажиллана (Wake Lock API).")

    pdf.code_block('''<nav class="tab-nav">
    <button class="tab-btn active" data-tab="register">
        Register
    </button>
    <button class="tab-btn" data-tab="upload">Upload</button>
    ...
</nav>''', "Tab navigation жишээ:")

    pdf.body_text("data-tab = 'register' гэдэг нь тухайн товч ямар tab-г нээхийг заана.")

    # ============ CHAPTER 9: dashboard.html ============
    pdf.add_page()
    pdf.chapter_title("9. dashboard.html - Хяналтын самбар")
    pdf.body_text("Энэ хуудас дээр бүх илэрсэн дуунуудыг хүснэгтэд харна. Дараах хэсгүүдтэй:")

    pdf.bullet("MQTT холболтын хэсэг - Брокертэй холбогдох")
    pdf.bullet("Статистик - Нийт илрүүлэлт, төхөөрөмжийн тоо, дууны төрлийн тоо")
    pdf.bullet("Шүүлтүүр - Төхөөрөмж эсвэл дууны төрөлөөр шүүх")
    pdf.bullet("Хүснэгт - Бүх мэдээллийг хүснэгтэд харуулна")
    pdf.bullet("Real-time лог - MQTT мессежүүдийг шууд харуулна")

    pdf.code_block('''<table id="detectionTable">
    <thead>
        <tr>
            <th>#</th>
            <th>Time</th>
            <th>Device</th>
            <th>Sound</th>
            ...
        </tr>
    </thead>
</table>''', "Хүснэгтийн загвар:")

    # ============ CHAPTER 10: app.js ============
    pdf.chapter_title("10. app.js - Гар утасны логик")
    pdf.body_text("Энэ файлд бүх JavaScript код байна. Хамгийн чухал хэсгүүдийг тайлбарлая:")

    pdf.section_title("10.1 MQTT холболт")
    pdf.code_block('''function connectMQTT() {
    const connectUrl =
        `wss://${server}:${port}/mqtt`;
    mqttClient = mqtt.connect(connectUrl, {
        username: user,
        password: pass,
        clientId: clientId
    });
}''')
    pdf.body_text("wss:// = WebSocket Secure. Гар утаснаас MQTT рүү холбогдохын тулд WebSocket ашиглана.")

    pdf.section_title("10.2 Микрофон асаах")
    pdf.code_block('''async function startListening() {
    audioContext = new AudioContext();
    const stream = await navigator.mediaDevices
        .getUserMedia({ audio: true });
    analyser = audioContext.createAnalyser();
    microphone = audioContext.createMediaStreamSource(stream);
    microphone.connect(analyser);
}''')
    pdf.body_text("getUserMedia - Браузэрээс микрофоны зөвшөөрөл авна. Analyser - Дууны frequency-г шинжлэх хэрэгсэл.")

    pdf.section_title("10.3 Дуу таних цикл")
    pdf.code_block('''function detectLoop() {
    if (!isListening) return;
    analyser.getByteFrequencyData(dataArray);
    const avgVolume = dataArray.reduce(...) / bufferLength;
    if (avgVolume > 15) {
        analyzeAudio(dataArray);  // Дуу илэрлээ!
    }
    requestAnimationFrame(detectLoop);  // Дахин шалгана
}''')
    pdf.body_text("requestAnimationFrame - Дэлгэц шинэчлэх бүрт шалгана. ~60 удаа/секунд.")

    pdf.section_title("10.4 MQTT рүү илгээх")
    pdf.code_block('''function publishDetection(detection) {
    mqttClient.publish("detected/sound/",
        JSON.stringify(detection));
}''')
    pdf.body_text("Дуу илэрсэн бол: нэр, дууны төрөл, огноо, газрын зураг, чиглэл зэргийг JSON болгоод MQTT рүү илгээнэ.")

    # ============ CHAPTER 11: dashboard.js ============
    pdf.add_page()
    pdf.chapter_title("11. dashboard.js - Dashboard логик")

    pdf.section_title("11.1 MQTT мессеж хүлээх")
    pdf.code_block('''mqttClient.on("message", (topic, message) => {
    const data = JSON.parse(message.toString());
    detections.push(data);
    updateTable();      // Хүснэгтийг шинэчилнэ
    updateStats();      // Статистикийг шинэчилнэ
    updateFilters();    // Шүүлтүүрийг шинэчилнэ
});''')
    pdf.body_text("MQTT-ээс мессеж ирэхэд бүх хэсгийг автоматаар шинэчилнэ.")

    pdf.section_title("11.2 Хүснэгт шинэчлэх")
    pdf.code_block('''function updateTable() {
    const filtered = getFilteredDetections();
    tbody.innerHTML = filtered.map((d, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>${d.detected_sound}</td>
            <td>${d.lat}, ${d.long}</td>
            ...
        </tr>
    `).join("");
}''')
    pdf.body_text("Template literal ашиглаж мөр бүрийг HTML болгоод хүснэгтэд нэмнэ.")

    pdf.section_title("11.3 CSV файл татаж авах")
    pdf.code_block('''function exportCSV() {
    const csv = headers.join(",") + "\\n" + rows...;
    const blob = new Blob([csv], {type: "text/csv"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "detections.csv";
    a.click();
}''')
    pdf.body_text("Мэдээллийг CSV файл болгож татаж авна. Excel-д нээж болно.")

    # ============ CHAPTER 12: USAGE GUIDE ============
    pdf.add_page()
    pdf.chapter_title("12. Ашиглах заавар")

    pdf.section_title("Алхам 1: Сервер асаах")
    pdf.code_block('''# Терминалд:
python -m venv venv          # Виртуал орчин үүсгэх
venv\\Scripts\\activate       # Асаах (Windows)
pip install -r requirements.txt  # Номуудыг суулгах
python app.py                # Сервер асаах''')
    pdf.body_text("Дараа нь хөтөч дээр http://localhost:5000 нээнэ.")

    pdf.section_title("Алхам 2: MQTT бүртгүүлэх")
    pdf.bullet("Device Name: sensor-01 (ямар ч нэр)")
    pdf.bullet("MQTT Server: broker.hivemq.com (эсвэл өөрийнхөө broker)")
    pdf.bullet("Port: 1883 эсвэл 8884")
    pdf.bullet("Username/Password: broker-н мэдээлэл")

    pdf.section_title("Алхам 3: Дуу upload хийх")
    pdf.bullet("Upload tab руу орно")
    pdf.bullet("Sound Type label бичнэ: dog, drone, car гэх мэт")
    pdf.bullet("Файл сонгоно (MP3, MP4, WAV)")
    pdf.bullet("Upload товч дарна")
    pdf.bullet("Нэг төрөлд олон файл upload хийх нь илүү сайн!")

    pdf.section_title("Алхам 4: Сургах")
    pdf.bullet("Train tab руу орно")
    pdf.bullet("Epochs тоог тохируулна (50-100 санал болгоно)")
    pdf.bullet("Start Training дарна")
    pdf.bullet("1-2 минут хүлээнэ")
    pdf.bullet("Model Status: Trained болсон эсэхийг шалгана")

    pdf.section_title("Алхам 5: Дуу таних")
    pdf.bullet("Detect tab руу орно")
    pdf.bullet("MIC товч дарна")
    pdf.bullet("Микрофоны зөвшөөрөл өгнө")
    pdf.bullet("Дууг танихад автоматаар MQTT рүү илгээнэ!")
    pdf.bullet("Дэлгэцээ унтраасан ч ажиллана (Wake Lock)")

    # ============ CHAPTER 13: MQTT FORMAT ============
    pdf.add_page()
    pdf.chapter_title("13. MQTT мессежийн формат")

    pdf.body_text("Илэрсэн дуу бүрт MQTT рүу дараах JSON мессеж илгээнэ:")

    pdf.code_block('''{
    "name": "sensor-01",
    "detected_sound": "dog",
    "confidence": 0.87,
    "datetime": "2026-09-15T17:30:00.000Z",
    "lat": 47.9184,
    "long": 106.9177,
    "direction": "NE",
    "tilted_degree": 15.3
}''', "MQTT мессеж:")

    pdf.body_text("Талбар бүрийн утгыг тайлбарлая:")
    fields = [
        ("name", "Төхөөрөмжийн нэр. Бүртгэхдээ өгсөн нэр"),
        ("detected_sound", "Танисан дууны төрөл: dog, drone, car, cow гэх мэт"),
        ("confidence", "Итгэлцэл 0-1.0 хооронд. 0.87 = 87% итгэлтэй танисан"),
        ("datetime", "Илэрсэн цаг. ISO 8001 формат"),
        ("lat", "Өргөрөг (Latitude). Газрын зургийн координат"),
        ("long", "Уртраг (Longitude). Газрын зургийн координат"),
        ("direction", "Чиглэл: N, NE, E, SE, S, SW, W, NW"),
        ("tilted_degree", "Утасны налалтын хэмжээ. Gyro мэдрэгчээс"),
    ]
    for field, desc in fields:
        pdf.set_font("Consolas", "B", 9)
        pdf.set_text_color(37, 99, 235)
        pdf.cell(35, 6, f" {field}")
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(0, 6, desc, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    pdf.info_box("Topic: detected/sound/ - Энэ хаягаар бүх хүлээн авагчид мессеж авна.", "blue")

    # ============ CHAPTER 14: FAQ ============
    pdf.add_page()
    pdf.chapter_title("14. Асуулт - Хариулт")

    faqs = [
        ("Q: MQTT гэж юу вэ?",
         "A: Message Queuing Telemetry Transport буюу мессежийг нэг талаас нөгөө тал руу шилжүүлэх протокол. Энгийнээр хэлбэл: зурвас илгээх систем шүү дээ."),
        ("Q: Flask гэж юу вэ?",
         "A: Python-н веб сервер бичих ном (library). Бидний сайт хэрхэн ажилладгийг зохицуулна."),
        ("Q: ML (Machine Learning) гэж юу вэ?",
         "A: Машин сургалт. Компьютерт өөрөө мэдээллээс хууль гаргаж сурах боломж. Эндээс: олон дуу сонсож, тэр дууг танихад сургана."),
        ("Q: MFCC гэж юу вэ?",
         "A: Дууны файлыг тоо болгож хувиргах арга. Нүдний хараатай адил: хүн нүдээрээ зүйл хардаг бол компьютер MFCC-гоор дууг 'хардаг'."),
        ("Q: Wake Lock гэж юу вэ?",
         "A: Дэлгэцээ унтраасан ч веб хуудас ажилласаар байх технологи. Гар утасны микрофон идэвхтэй байхад хэрэгтэй."),
        ("Q: Web Audio API гэж юу вэ?",
         "A: Веб хуудаснаас микрофоноос дуу авах стандарт. Браузэрт байрладаг JavaScript-н нэмэлт."),
        ("Q: Нэг төхөөрөмжөөс олон дуу таних боломжтой юу?",
         "A: Тийм. Нэг дээр dog, drone, car гэх мэт олон төрөл сургаж болно."),
        ("Q: Илүү сайн танихын тулд юу хийх вэ?",
         "A: Нэг төрөлд олон файл upload хийх. Янз бүрийн орчинд бичсэн файл нэмэх. Жишээ нь: чимээгүй орчинд бичсэн нохойн дуу, чимээтэй орчинд бичсэн нохойн дуу."),
    ]

    for q, a in faqs:
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(37, 99, 235)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(w=190, h=6, text=q)
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(51, 65, 85)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(w=190, h=6, text=a)
        pdf.ln(4)

    # ============ FINAL PAGE ============
    pdf.add_page()
    pdf.chapter_title("Дүгнэлт")
    pdf.body_text(
        "Энэ төсөл нь олон технологийг хослуулсан: Python, Flask, MQTT, "
        "Machine Learning, Web Audio API, HTML/CSS/JavaScript."
    )
    pdf.body_text(
        "Та нар үүнийг сурахдаа дараах зүйлсийг мэдэж авсан байна:"
    )
    pdf.bullet("Веб сервер хэрхэн ажилладаг вэ (Flask)")
    pdf.bullet("MQTT протоколоор мессеж илгээх (IoT)")
    pdf.bullet("Дууг тоон мэдээлэл болгох (MFCC + librosa)")
    pdf.bullet("Machine Learning модель сургах (sklearn)")
    pdf.bullet("Браузэрээс микрофон ашиглах (Web Audio API)")
    pdf.bullet("Real-time хүснэгт үүсгэх (JavaScript)")

    pdf.ln(10)
    pdf.info_box("Мөнгөн шагналт тэмцээн, шинжлэх ухааны үзэсгэлэн, эсвэл их сургуулийн төсөлд ашиглахад тохиромжтой!", "green")

    # Save
    output_path = os.path.join(os.path.dirname(__file__), "SoundSense_Tutorial_MN.pdf")
    pdf.output(output_path)
    print(f"PDF created: {output_path}")
    print(f"Total pages: {pdf.pages_count}")


if __name__ == "__main__":
    generate()
