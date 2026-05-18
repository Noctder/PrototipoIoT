# Green IoT: Agricultura Inteligente - ESP32 + MicroPython
# Ciclo: Despertar -> Medir -> Conectar -> Enviar -> Desconectar -> Deep Sleep
# Basado en concepto de PrototipoIoT (Noctder) con Deep Sleep y conexión breve

import machine
import dht
import utime
import network
import urequests
import struct

# Cargar configuración
try:
    import config_supabase as cfg

    SUPABASE_URL = cfg.SUPABASE_URL
    SUPABASE_API_KEY = cfg.SUPABASE_API_KEY
    SUPABASE_TABLE = cfg.SUPABASE_TABLE
    WIFI_SSID = cfg.WIFI_SSID
    WIFI_PASSWORD = cfg.WIFI_PASSWORD
    DEEP_SLEEP_MS = cfg.DEEP_SLEEP_MS
    TEMP_ALERTA_CALOR = cfg.TEMP_ALERTA_CALOR
    HUMEDAD_ALERTA_BAJA = cfg.HUMEDAD_ALERTA_BAJA
    HUMEDAD_SUELO_ALERTA_BAJA = cfg.HUMEDAD_SUELO_ALERTA_BAJA

    # Calibración opcional para sensor capacitivo de suelo.
    # SECO: lectura ADC con sonda al aire o suelo muy seco.
    # HUMEDO: lectura ADC con sonda en suelo húmedo.
    SUELO_ADC_SECO = getattr(cfg, "SUELO_ADC_SECO", 3000)
    SUELO_ADC_HUMEDO = getattr(cfg, "SUELO_ADC_HUMEDO", 1400)

    PIN_RELE = getattr(cfg, "PIN_RELE", 26)
    RELAY_ACTIVE_LOW = getattr(cfg, "RELAY_ACTIVE_LOW", True)
    RIEGO_HABILITADO = getattr(cfg, "RIEGO_HABILITADO", True)
    RIEGO_ACTIVAR_POR_DEBAJO_DE = getattr(cfg, "RIEGO_ACTIVAR_POR_DEBAJO_DE", 35)
    RIEGO_NO_REGAR_POR_ENCIMA_DE = getattr(cfg, "RIEGO_NO_REGAR_POR_ENCIMA_DE", 50)
    TIEMPO_RIEGO_MS = getattr(cfg, "TIEMPO_RIEGO_MS", 5000)
except ImportError:
    SUPABASE_URL = "https://TU_PROYECTO.supabase.co"
    SUPABASE_API_KEY = "TU_API_KEY"
    SUPABASE_TABLE = "agricultura_lecturas"
    WIFI_SSID = "TU_WIFI"
    WIFI_PASSWORD = "TU_PASSWORD"
    DEEP_SLEEP_MS = 300000  # 5 min
    TEMP_ALERTA_CALOR = 32
    HUMEDAD_ALERTA_BAJA = 25
    HUMEDAD_SUELO_ALERTA_BAJA = 30
    SUELO_ADC_SECO = 3000
    SUELO_ADC_HUMEDO = 1400
    PIN_RELE = 26
    RELAY_ACTIVE_LOW = True
    RIEGO_HABILITADO = True
    RIEGO_ACTIVAR_POR_DEBAJO_DE = 35
    RIEGO_NO_REGAR_POR_ENCIMA_DE = 50
    TIEMPO_RIEGO_MS = 5000

# ----- Hardware -----
led = machine.Pin(2, machine.Pin.OUT)
led.value(1)

# Buzzer opcional (GPIO 18)
try:
    buzzer_pwm = machine.PWM(machine.Pin(18))
    buzzer_pwm.duty(0)
except Exception:
    buzzer_pwm = None

# DHT11 (temperatura y humedad) - GPIO 4, pull-up 10kΩ
dht_pin = machine.Pin(4)
sensor_dht = dht.DHT11(dht_pin)

# BMP280 (presión) opcional - I2C
i2c_bmp = None
bmp_calib = {}
bmp_addr = 0x76

# Pin ADC para humedad de suelo (sensor capacitivo v1.2) - GPIO 33
PIN_HUMEDAD_SUELO_ADC = 33

# Relé bomba de agua (GPIO configurable en config_supabase.py)
rele_pin = None
if PIN_RELE is not None and RIEGO_HABILITADO:
    try:
        rele_pin = machine.Pin(PIN_RELE, machine.Pin.OUT)
    except Exception as e:
        print("Relé no disponible:", e)
        rele_pin = None

# ---------------------------------------------------------------------------
# BMP280 (opcional)
# ---------------------------------------------------------------------------
def inicializar_bmp280():
    global i2c_bmp, bmp_calib, bmp_addr
    try:
        i2c_bmp = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=100000)
        devs = i2c_bmp.scan()
        if 0x76 not in devs and 0x77 not in devs:
            i2c_bmp = None
            return False
        bmp_addr = 0x76 if 0x76 in devs else 0x77
        i2c_bmp.writeto_mem(bmp_addr, 0xE0, b'\xB6')
        utime.sleep_ms(10)
        cal = i2c_bmp.readfrom_mem(bmp_addr, 0x88, 24)
        bmp_calib['T1'] = struct.unpack('<H', cal[0:2])[0]
        bmp_calib['T2'] = struct.unpack('<h', cal[2:4])[0]
        bmp_calib['T3'] = struct.unpack('<h', cal[4:6])[0]
        bmp_calib['P1'] = struct.unpack('<H', cal[6:8])[0]
        bmp_calib['P2'] = struct.unpack('<h', cal[8:10])[0]
        bmp_calib['P3'] = struct.unpack('<h', cal[10:12])[0]
        bmp_calib['P4'] = struct.unpack('<h', cal[12:14])[0]
        bmp_calib['P5'] = struct.unpack('<h', cal[14:16])[0]
        bmp_calib['P6'] = struct.unpack('<h', cal[16:18])[0]
        bmp_calib['P7'] = struct.unpack('<h', cal[18:20])[0]
        bmp_calib['P8'] = struct.unpack('<h', cal[20:22])[0]
        bmp_calib['P9'] = struct.unpack('<h', cal[22:24])[0]
        i2c_bmp.writeto_mem(bmp_addr, 0xF4, b'\x27')
        i2c_bmp.writeto_mem(bmp_addr, 0xF5, b'\xA0')
        utime.sleep_ms(200)
        return True
    except Exception as e:
        print("BMP280 no disponible:", e)
        i2c_bmp = None
        return False

def leer_presion_bmp280():
    global i2c_bmp, bmp_calib, bmp_addr
    if i2c_bmp is None or not bmp_calib:
        return None
    try:
        utime.sleep_ms(10)
        data = i2c_bmp.readfrom_mem(bmp_addr, 0xF7, 8)
        press_raw = (int(data[0]) << 12) | (int(data[1]) << 4) | (int(data[2]) >> 4)
        temp_raw = (int(data[3]) << 12) | (int(data[4]) << 4) | (int(data[5]) >> 4)
        # Compensación oficial BMP280 (datasheet), en punto flotante.
        var1 = (temp_raw / 16384.0 - bmp_calib['T1'] / 1024.0) * bmp_calib['T2']
        var2 = ((temp_raw / 131072.0 - bmp_calib['T1'] / 8192.0) *
                (temp_raw / 131072.0 - bmp_calib['T1'] / 8192.0)) * bmp_calib['T3']
        t_fine = var1 + var2

        var1_p = t_fine / 2.0 - 64000.0
        var2_p = var1_p * var1_p * bmp_calib['P6'] / 32768.0
        var2_p = var2_p + var1_p * bmp_calib['P5'] * 2.0
        var2_p = var2_p / 4.0 + bmp_calib['P4'] * 65536.0
        var1_p = (bmp_calib['P3'] * var1_p * var1_p / 524288.0 +
                  bmp_calib['P2'] * var1_p) / 524288.0
        var1_p = (1.0 + var1_p / 32768.0) * bmp_calib['P1']

        if abs(var1_p) < 1e-9:
            return None

        pressure = 1048576.0 - press_raw
        pressure = (pressure - var2_p / 4096.0) * 6250.0 / var1_p
        var1_p = bmp_calib['P9'] * pressure * pressure / 2147483648.0
        var2_p = pressure * bmp_calib['P8'] / 32768.0
        pressure = pressure + (var1_p + var2_p + bmp_calib['P7']) / 16.0
        pressure = pressure / 100.0  # hPa
        if 600.0 <= pressure <= 1200.0:
            return round(pressure, 2)
        return None
    except Exception:
        return None

# ---------------------------------------------------------------------------
# DHT11
# ---------------------------------------------------------------------------
def leer_dht11():
    try:
        sensor_dht.measure()
        t = sensor_dht.temperature()
        h = sensor_dht.humidity()
        return (t, h)
    except OSError as e:
        print("Error DHT11:", e)
        return (None, None)
    except Exception as e:
        print("Error leyendo DHT11:", e)
        return (None, None)

# ---------------------------------------------------------------------------
# Humedad de suelo (ADC opcional)
# ---------------------------------------------------------------------------
def leer_humedad_suelo():
    if PIN_HUMEDAD_SUELO_ADC is None:
        return None
    try:
        adc = machine.ADC(machine.Pin(PIN_HUMEDAD_SUELO_ADC))
        adc.atten(machine.ADC.ATTN_11DB)
        adc.width(machine.ADC.WIDTH_12BIT)
        # Promedio para estabilizar lectura del sensor capacitivo.
        muestras = 5
        suma = 0
        for _ in range(muestras):
            suma += adc.read()
            utime.sleep_ms(20)
        v = suma / muestras

        # Mapear con calibración real: SECO -> 0%, HUMEDO -> 100%.
        span = SUELO_ADC_SECO - SUELO_ADC_HUMEDO
        if span <= 0:
            return None
        pct = ((SUELO_ADC_SECO - v) * 100.0) / span
        return max(0, min(100, int(round(pct))))
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Relé / bomba de agua
# ---------------------------------------------------------------------------
def rele_encender():
    if rele_pin is None:
        return
    rele_pin.value(0 if RELAY_ACTIVE_LOW else 1)

def rele_apagar():
    if rele_pin is None:
        return
    rele_pin.value(1 if RELAY_ACTIVE_LOW else 0)

def debe_regar(humedad_suelo_pct):
    if not RIEGO_HABILITADO or humedad_suelo_pct is None:
        return False
    if humedad_suelo_pct >= RIEGO_NO_REGAR_POR_ENCIMA_DE:
        return False
    if humedad_suelo_pct < RIEGO_ACTIVAR_POR_DEBAJO_DE:
        return True
    return False

def regar_si_necesario(humedad_suelo_pct):
    if not debe_regar(humedad_suelo_pct):
        if humedad_suelo_pct is None:
            print("Riego: sin lectura de suelo, bomba apagada")
        elif humedad_suelo_pct >= RIEGO_NO_REGAR_POR_ENCIMA_DE:
            print("Riego: suelo húmedo ({}%), bomba apagada".format(humedad_suelo_pct))
        else:
            print("Riego: {}% en zona intermedia, bomba apagada".format(humedad_suelo_pct))
        rele_apagar()
        return False
    print("Riego: suelo seco ({}%), bomba ON {} s".format(
        humedad_suelo_pct, TIEMPO_RIEGO_MS // 1000))
    rele_encender()
    utime.sleep_ms(TIEMPO_RIEGO_MS)
    rele_apagar()
    print("Riego: bomba OFF")
    return True

# ---------------------------------------------------------------------------
# WiFi - conexión breve
# ---------------------------------------------------------------------------
def conectar_wifi(timeout_s=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    t0 = utime.time()
    while not wlan.isconnected() and (utime.time() - t0) < timeout_s:
        utime.sleep(0.5)
    if wlan.isconnected():
        print("WiFi OK")
        return wlan
    print("WiFi timeout")
    return None

def desconectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.disconnect()
    wlan.active(False)

# ---------------------------------------------------------------------------
# Envío a Supabase (gemelo digital: cada fila = último estado conocido)
# ---------------------------------------------------------------------------
def enviar_supabase(temperatura, humedad, estado, presion=None, humedad_suelo=None, es_alerta=False):
    if "TU_PROYECTO" in SUPABASE_URL or "TU_API" in SUPABASE_API_KEY:
        print("Configura Supabase en config_supabase.py")
        return False
    try:
        url = "{}/rest/v1/{}".format(SUPABASE_URL.rstrip('/'), SUPABASE_TABLE)
        data = {
            "temperatura": round(float(temperatura), 1),
            "humedad": round(float(humedad), 1),
            "estado": estado,
            "es_alerta": es_alerta
        }
        if presion is not None:
            data["presion"] = round(float(presion), 2)
        if humedad_suelo is not None:
            data["humedad_suelo"] = int(humedad_suelo)
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": "Bearer {}".format(SUPABASE_API_KEY),
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        r = urequests.post(url, json=data, headers=headers, timeout=10)
        ok = r.status_code in (200, 201)
        r.close()
        return ok
    except Exception as e:
        print("Error Supabase:", e)
        return False

def sonar_buzzer(freq=1500, ms=2000):
    if buzzer_pwm is None:
        return
    try:
        buzzer_pwm.freq(freq)
        buzzer_pwm.duty(512)
        utime.sleep_ms(ms)
        buzzer_pwm.duty(0)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Determinar estado y alertas (agricultura)
# ---------------------------------------------------------------------------
def procesar_estado(temp, hum):
    if temp is None:
        return "DESCONOCIDO", False
    if temp < 15:
        estado = "FRIO"
    elif temp <= 27:
        estado = "NORMAL"
    else:
        estado = "CALOR"
    es_alerta = (estado == "CALOR" and temp >= TEMP_ALERTA_CALOR) or (hum is not None and hum < HUMEDAD_ALERTA_BAJA)
    return estado, es_alerta

# ======================== PROGRAMA PRINCIPAL (un ciclo por despertar) ========================

print("=" * 50)
print("  Green IoT - Agricultura Inteligente")
print("  Ciclo: Medir -> Riego -> Enviar -> Deep Sleep")
print("=" * 50)

# Relé apagado al arranque (también tras despertar de Deep Sleep)
rele_apagar()

# 1) Inicializar BMP280 (opcional)
bmp_ok = inicializar_bmp280()

# 2) Leer sensores
temp, hum = leer_dht11()
if temp is None and hum is None:
    utime.sleep_ms(500)
    temp, hum = leer_dht11()
presion = leer_presion_bmp280() if bmp_ok else None
hum_suelo = leer_humedad_suelo()

estado, es_alerta = procesar_estado(temp, hum)
if hum_suelo is not None and hum_suelo < HUMEDAD_SUELO_ALERTA_BAJA:
    es_alerta = True

# Si no hay datos del DHT11, intentar deep sleep igual para no bloquear
if temp is None:
    temp = 0.0
if hum is None:
    hum = 0.0

hum_suelo_txt = "{}%".format(hum_suelo) if hum_suelo is not None else "N/A"
print("Temp: {} C  Hum: {}%  HumSuelo: {}  Pres: {}  Estado: {}  Alerta: {}".format(
    temp, hum, hum_suelo_txt, presion, estado, es_alerta))

# 3) Riego automático (bomba ~5 s si suelo seco; luego relé apagado)
regar_si_necesario(hum_suelo)

# 4) Conexión breve: WiFi
wlan = conectar_wifi(15)
if wlan is not None:
    # 5) Enviar a Supabase (gemelo digital)
    if enviar_supabase(temp, hum, estado, presion, hum_suelo, es_alerta):
        print("Enviado a Supabase OK")
        led.value(0)
        utime.sleep_ms(200)
        led.value(1)
    else:
        print("Fallo envío Supabase")

    # 6) Alertas
    if es_alerta:
        sonar_buzzer(1500, 2000)

    # 7) Desconectar WiFi antes de dormir
    desconectar_wifi()
else:
    print("Sin WiFi; no se enviaron datos")

# 8) Deep Sleep hasta próximo ciclo (bomba ya apagada)
rele_apagar()
print("Entrando en Deep Sleep {} s...".format(DEEP_SLEEP_MS // 1000))
led.value(0)
utime.sleep_ms(100)
machine.deepsleep(DEEP_SLEEP_MS)
