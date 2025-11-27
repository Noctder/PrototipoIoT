import machine
import dht
import utime
import network
import urequests
import struct

# Importar configuración de Supabase
try:
    from config_supabase import SUPABASE_URL, SUPABASE_API_KEY, SUPABASE_TABLE
except ImportError:
    # Si no existe config_supabase.py, usa valores por defecto
    SUPABASE_URL = "https://TU_PROYECTO_ID.supabase.co"
    SUPABASE_API_KEY = "TU_API_KEY_AQUI"
    SUPABASE_TABLE = "sensor_readings"

# Configuración LED integrado
led = machine.Pin(2, machine.Pin.OUT)
led.value(1)  # LED encendido al inicio y siempre

# Configuración del buzzer en GPIO 18
buzzer_pwm = machine.PWM(machine.Pin(18))  # GPIO18 para el buzzer con PWM

# Asegurar que el buzzer esté apagado al inicio
buzzer_pwm.duty(0)

# Configuración del sensor DHT11 (GPIO 4)
dht_pin = machine.Pin(4)
sensor_dht = dht.DHT11(dht_pin)

# Configuración del sensor BMP280 (I2C en GPIO 21 y 22) - solo para presión
i2c_bmp280 = None
bmp280_calib = {}
bmp280_addr = 0x76  # Dirección I2C del BMP280

def inicializar_bmp280():
    global i2c_bmp280, bmp280_calib, bmp280_addr
    try:
        i2c_bmp280 = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=100000)
        devices = i2c_bmp280.scan()
        
        # BMP280 puede estar en 0x76 o 0x77
        if 0x76 not in devices and 0x77 not in devices:
            print("⚠️ BMP280 no detectado en el bus I2C")
            i2c_bmp280 = None
            return False
        
        # Usar la dirección encontrada
        if 0x76 in devices:
            bmp280_addr = 0x76
        else:
            bmp280_addr = 0x77
        
        # Soft reset del sensor
        i2c_bmp280.writeto_mem(bmp280_addr, 0xE0, b'\xB6')
        utime.sleep_ms(10)
        
        # Leer coeficientes de calibración (temperatura y presión)
        calib_data = i2c_bmp280.readfrom_mem(bmp280_addr, 0x88, 24)
        
        # Parsear coeficientes de temperatura y presión
        bmp280_calib['T1'] = struct.unpack('<H', bytes(calib_data[0:2]))[0]
        bmp280_calib['T2'] = struct.unpack('<h', bytes(calib_data[2:4]))[0]
        bmp280_calib['T3'] = struct.unpack('<h', bytes(calib_data[4:6]))[0]
        bmp280_calib['P1'] = struct.unpack('<H', bytes(calib_data[6:8]))[0]
        bmp280_calib['P2'] = struct.unpack('<h', bytes(calib_data[8:10]))[0]
        bmp280_calib['P3'] = struct.unpack('<h', bytes(calib_data[10:12]))[0]
        bmp280_calib['P4'] = struct.unpack('<h', bytes(calib_data[12:14]))[0]
        bmp280_calib['P5'] = struct.unpack('<h', bytes(calib_data[14:16]))[0]
        bmp280_calib['P6'] = struct.unpack('<h', bytes(calib_data[16:18]))[0]
        bmp280_calib['P7'] = struct.unpack('<h', bytes(calib_data[18:20]))[0]
        bmp280_calib['P8'] = struct.unpack('<h', bytes(calib_data[20:22]))[0]
        bmp280_calib['P9'] = struct.unpack('<h', bytes(calib_data[22:24]))[0]
        
        # Configurar el sensor (modo normal, oversampling estándar)
        i2c_bmp280.writeto_mem(bmp280_addr, 0xF4, b'\x27')  # ctrl_meas: modo normal, oversampling x1
        i2c_bmp280.writeto_mem(bmp280_addr, 0xF5, b'\xA0')  # config: standby 1000ms, filter off
        
        # Esperar un poco para que el sensor se estabilice
        utime.sleep_ms(200)
        
        return True
    except Exception as e:
        print(f"⚠️ No se pudo inicializar el BMP280: {e}")
        i2c_bmp280 = None
        return False

def obtener_presion_bmp280():
    """Lee la presión del BMP280"""
    global i2c_bmp280, bmp280_calib, bmp280_addr
    
    if i2c_bmp280 is None or not bmp280_calib:
        return None
    
    try:
        # Pequeño delay para asegurar que el sensor tenga datos frescos
        utime.sleep_ms(10)
        
        # Leer datos de presión y temperatura (necesaria para compensación de presión)
        data = i2c_bmp280.readfrom_mem(bmp280_addr, 0xF7, 8)
        
        # Extraer valores sin procesar
        press_raw = (int(data[0]) << 12) | (int(data[1]) << 4) | (int(data[2]) >> 4)
        temp_raw = (int(data[3]) << 12) | (int(data[4]) << 4) | (int(data[5]) >> 4)
        
        # Calcular temperatura compensada (necesaria para compensación de presión)
        var1 = ((temp_raw >> 3) - (bmp280_calib['T1'] << 1)) * (bmp280_calib['T2'] >> 11)
        var2 = ((((temp_raw >> 4) - bmp280_calib['T1']) * ((temp_raw >> 4) - bmp280_calib['T1'])) >> 12) * (bmp280_calib['T3'] >> 14)
        t_fine = var1 + var2
        
        # Calcular presión compensada (algoritmo BMP280)
        var1_p = (float(t_fine) / 2.0) - 64000.0
        var2_p = var1_p * var1_p * float(bmp280_calib['P6']) / 32768.0
        var2_p = var2_p + var1_p * float(bmp280_calib['P5']) * 2.0
        var2_p = (var2_p / 4.0) + (float(bmp280_calib['P4']) * 65536.0)
        var1_p = (float(bmp280_calib['P3']) * var1_p * var1_p / 524288.0 + float(bmp280_calib['P2']) * var1_p) / 524288.0
        var1_p = (1.0 + var1_p / 32768.0) * float(bmp280_calib['P1'])
        
        if abs(var1_p) < 0.0001:
            presion = None
        else:
            # Calcular presión en Pascales
            presion = 1048576.0 - float(press_raw)
            presion = (presion - (var2_p / 4096.0)) * 6250.0 / var1_p
            var1_p = float(bmp280_calib['P9']) * presion * presion / 2147483648.0
            var2_p = presion * float(bmp280_calib['P8']) / 32768.0
            presion = presion + (var1_p + var2_p + float(bmp280_calib['P7'])) / 16.0
            
            # El algoritmo del BMP280 devuelve presión directamente en Pascales
            # Convertir de Pascales a hectopascales (hPa): 1 hPa = 100 Pa
            presion_hpa = presion / 100.0
            
            # Validar rango razonable (600-1200 hPa)
            if presion_hpa < 600.0 or presion_hpa > 1200.0:
                print(f"⚠️ Presión fuera de rango: {presion_hpa:.2f} hPa")
                presion = None
            else:
                presion = round(presion_hpa, 2)
        
        return presion
    except Exception as e:
        print(f"⚠️ Error leyendo presión del BMP280: {e}")
        return None

# Configuración WiFi
WIFI_SSID = "AQUI_VA_EL_NOMBRE_DE_TU_RED_WIFI"
WIFI_PASSWORD = "AQUI_VA_LA_CONTRASEÑA_DE_TU_RED_WIFI"

# Configuración Telegram Bot
# Obtén el token creando un bot con @BotFather en Telegram
TELEGRAM_BOT_TOKEN = "AQUI_VA_EL_TOKEN_DE_TU_BOT_DE_TELEGRAM"
# Obtén tu Chat ID usando @userinfobot en Telegram
TELEGRAM_CHAT_ID = 0  # AQUI_VA_TU_CHAT_ID_DE_TELEGRAM (número sin comillas)

# Variables para rastrear últimos valores enviados
ultima_temp_enviada = None
ultima_hum_enviada = None
ultima_pres_enviada = None

# Función para conectar a WiFi
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Conectando a WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            utime.sleep(1)
    print("WiFi conectado:", wlan.ifconfig())
    return True

# Función para enviar mensaje por Telegram
def enviar_telegram(mensaje):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje
        }
        response = urequests.post(url, json=data, timeout=10)
        ok = response.status_code == 200
        response.close()
        return ok
    except Exception as e:
        print(f"⚠️ Error enviando mensaje a Telegram: {e}")
        return False

def probar_telegram():
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = urequests.get(url, timeout=10)
        ok = False
        if response.status_code == 200:
            try:
                data = response.json()
                ok = data.get("ok", False)
            except:
                pass
        response.close()
        return ok
    except Exception as e:
        print(f"⚠️ Error verificando Telegram: {e}")
        return False

# Función para enviar datos a Supabase
def enviar_supabase(temperatura, humedad, estado, presion=None, es_alerta=False):
    """
    Envía datos del sensor a Supabase
    Args:
        temperatura: Temperatura en °C
        humedad: Humedad en %
        estado: 'FRIO', 'NORMAL' o 'CALOR'
        presion: Presión atmosférica en hPa (opcional)
        es_alerta: Boolean indicando si es una alerta
    """
    # Validar que las credenciales estén configuradas
    if SUPABASE_URL == "https://TU_PROYECTO_ID.supabase.co" or SUPABASE_API_KEY == "TU_API_KEY_AQUI":
        print("⚠️ Supabase no configurado. Actualiza las credenciales en config_supabase.py")
        return False
    
    try:
        # Construir URL del endpoint REST de Supabase
        url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
        
        # Preparar datos según el esquema de la tabla
        data = {
            "temperatura": float(temperatura),
            "humedad": float(humedad),
            "estado": estado,
            "es_alerta": es_alerta
        }
        
        # Agregar presión si está disponible
        if presion is not None:
            data["presion"] = float(presion)
        
        # Headers requeridos por Supabase
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        # Enviar POST request con timeout
        response = urequests.post(url, json=data, headers=headers, timeout=10)
        
        # Verificar respuesta
        if response.status_code in [200, 201]:
            exito = True
        else:
            print(f"⚠️ Supabase respondió con código: {response.status_code}")
            exito = False
        
        response.close()
        return exito
        
    except Exception as e:
        print(f"⚠️ Error enviando a Supabase: {e}")
        return False

def probar_supabase():
    try:
        url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?select=id&limit=1"
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json",
            "Range": "0-0"
        }
        response = urequests.get(url, headers=headers, timeout=10)
        ok = response.status_code == 200
        response.close()
        return ok
    except Exception as e:
        print(f"⚠️ Error verificando Supabase: {e}")
        return False

def verificar_servicios(max_intentos=5, espera_seg=5):
    wlan = network.WLAN(network.STA_IF)
    for intento in range(1, max_intentos + 1):
        print(f"🔁 Verificando servicios (intento {intento}/{max_intentos})...")
        if not wlan.isconnected():
            print("📶 WiFi desconectado, reintentando...")
            conectar_wifi()
        telegram_ok = probar_telegram()
        supabase_ok = probar_supabase()
        if telegram_ok and supabase_ok:
            print("✅ Servicios remotos disponibles")
            return True
        print(f"⏳ Reintentando en {espera_seg} segundos...")
        utime.sleep(espera_seg)
    print("⚠️ No se pudo verificar todos los servicios remotos")
    return False

# Función para hacer sonar el buzzer con tono
def sonar_buzzer(frecuencia=1000, duracion_ms=1000):
    buzzer_pwm.freq(frecuencia)  # Frecuencia del tono (Hz)
    buzzer_pwm.duty(512)  # 50% duty cycle para volumen medio
    utime.sleep_ms(duracion_ms)  # Duración del sonido
    buzzer_pwm.duty(0)  # Apagar el buzzer

# Función para obtener datos del sensor DHT11
def obtener_temperatura_humedad_dht11():
    """Obtiene temperatura y humedad del DHT11"""
    try:
        # El DHT11 puede tardar hasta 2 segundos en responder
        sensor_dht.measure()
        temp = sensor_dht.temperature()  # °C
        hum = sensor_dht.humidity()  # %
        return temp, hum
    except OSError as e:
        # Error específico de timeout o comunicación con DHT11
        print(f"⚠️ Error DHT11: {e}")
        return None, None
    except Exception as e:
        print(f"⚠️ Error leyendo sensor DHT11: {e}")
        return None, None

# Función para determinar estado y procesar datos
def procesar_datos(temp, hum, presion=None):
    global ultima_temp_enviada, ultima_hum_enviada, ultima_pres_enviada
    
    # Determinar estado actual
    if temp < 15:
        estado_actual = "FRIO"
    elif temp >= 15 and temp <= 27:
        estado_actual = "NORMAL"
    else:
        estado_actual = "CALOR"
    
    # Redondear valores para evitar envíos idénticos por cambios mínimos
    temp_enviar = round(float(temp), 1)
    hum_enviar = round(float(hum), 1)
    pres_enviar = round(float(presion), 2) if presion is not None else None
    
    # Verificar si hay cambios en temperatura, humedad o presión
    hay_cambio = (
        ultima_temp_enviada is None
        or ultima_hum_enviada is None
        or (presion is not None and ultima_pres_enviada is None)
        or temp_enviar != ultima_temp_enviada
        or hum_enviar != ultima_hum_enviada
        or (presion is not None and pres_enviar != ultima_pres_enviada)
    )
    
    # Verificar si hay una alerta (cada vez que detecta CALOR)
    es_alerta = False
    if estado_actual == "CALOR":
        print("🔥 ¡ALERTA DE CALOR! Sonando buzzer...")
        sonar_buzzer(1500, 2000)  # Tono agudo de 1.5kHz por 2 segundos
        
        # Enviar mensaje de alerta a Telegram
        if presion is not None:
            mensaje = f"ALERTA: Temperatura alta {temp_enviar:.1f}°C - Humedad {hum_enviar:.1f}% - Presión {presion:.2f} hPa"
        else:
            mensaje = f"ALERTA: Temperatura alta {temp_enviar:.1f}°C - Humedad {hum_enviar:.1f}% - Presión N/A"
        enviar_telegram(mensaje)
        
        es_alerta = True
    
    # Enviar datos a Supabase solo cuando cambie alguna lectura
    if hay_cambio:
        if enviar_supabase(temp_enviar, hum_enviar, estado_actual, presion, es_alerta):
            ultima_temp_enviada = temp_enviar
            ultima_hum_enviada = hum_enviar
            if presion is not None:
                ultima_pres_enviada = pres_enviar
        else:
            print("⚠️ No se pudo enviar a Supabase en esta lectura")
    else:
        print("ℹ️ Lectura sin cambios (temp, hum y pres sin variación), no se envía a Supabase")
    
    # Mostrar en consola
    if presion is not None:
        print(f"🌡️  Temp: {temp_enviar:.1f}°C | 💧 Hum: {hum_enviar:.1f}% | 📊 Pres: {presion:.2f}hPa | Estado: {estado_actual}")
    else:
        print(f"🌡️  Temp: {temp_enviar:.1f}°C | 💧 Hum: {hum_enviar:.1f}% | 📊 Estado: {estado_actual}")

# ========== INICIO DEL PROGRAMA ==========

print("=" * 50)
print("  🚀 ESP32 IoT - Sensor DHT11 + BMP280 + Supabase")
print("=" * 50)

# Conectar a WiFi
print("\n📡 Iniciando conexión WiFi...")
conectar_wifi()

print("\n🔧 Inicializando sensor BMP280...")
bmp280_ok = inicializar_bmp280()
if bmp280_ok:
    print("✅ BMP280 listo para leer presión")
else:
    print("⚠️ BMP280 no disponible, las lecturas de presión no estarán disponibles")

print("Verificando servicios remotos...")
servicios_ok = verificar_servicios()
if not servicios_ok:
    print("⚠️ Continuando sin verificar todos los servicios")
else:
    print("✅ Servicios verificados")

# Mensaje de inicio
print("\n✅ Sistema iniciado correctamente")
print("📊 Lectura de datos cada 5 segundos...\n")
print("-" * 50)

# Bucle principal
contador = 0
wlan = network.WLAN(network.STA_IF)
while True:
    try:
        # Verificar estado WiFi y mantener LED siempre encendido
        if not wlan.isconnected():
            # Si se desconectó, intentar reconectar
            print("⚠️ WiFi desconectado, intentando reconectar...")
            conectar_wifi()
        led.value(1)  # LED siempre encendido
        
        # Leer temperatura y humedad del DHT11
        temperatura, humedad = obtener_temperatura_humedad_dht11()
        
        # Leer presión del BMP280
        presion = obtener_presion_bmp280()
        
        if temperatura is not None and humedad is not None:
            contador += 1
            print(f"\n📝 Lectura #{contador}")
            procesar_datos(temperatura, humedad, presion)
        else:
            print("⚠️ Error leyendo sensor DHT11")
        
        print("-" * 50)
        
        # Sleep reducido a 3 segundos con heartbeat muy frecuente para mantener actividad constante
        # Esto evita que la batería se apague por detectar inactividad
        # Mantener actividad cada 100ms para máxima detección por la batería
        for i in range(30):  # 30 ciclos de 100ms = 3 segundos
            utime.sleep_ms(100)
            # Parpadeo muy frecuente del LED para mantener actividad constante
            led.value(0)  # Apagar momentáneamente
            utime.sleep_ms(30)
            led.value(1)  # Volver a encender
            # Actividad periódica para mantener el sistema activo
            if i % 5 == 0:  # Cada 500ms verificar WiFi
                _ = wlan.isconnected()
            if i % 10 == 0:  # Cada 1 segundo mantener variables activas
                _ = contador
                _ = temperatura if temperatura else None
        
    except OSError as e:
        print(f"❌ Error OSError en bucle: {e}")
        led.value(1)  # LED siempre encendido
        utime.sleep_ms(500)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        utime.sleep(1)

