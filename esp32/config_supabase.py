# Configuración para Green IoT - Agricultura Inteligente
# Actualiza estos valores y súbelos al ESP32 junto con main.py

# ----- Supabase (Gemelo digital / Device shadow) -----
SUPABASE_URL = "https://qpvfjgmpyqqlmssqfkoh.supabase.co"  
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFwdmZqZ21weXFxbG1zc3Fma29oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0NTE4MjksImV4cCI6MjA4OTAyNzgyOX0.jC-okr8hx-8mHW9_cOvgOEenD-eCK2RUwnmMOdjbYMg"
SUPABASE_TABLE = "agricultura_lecturas"

# ----- WiFi -----
WIFI_SSID = "AQUI_VA_TU_RED_WIFI"
WIFI_PASSWORD = "AQUI_VA_TU_CONTRASEÑA"

# ----- Telegram (alertas; opcional) -----
# Desactivado por ahora. Cuando lo quieras habilitar:
# - pon el token del bot (string) y tu chat_id (número)
# - y descomenta estas dos líneas.
#
# TELEGRAM_BOT_TOKEN = "AQUI_VA_TU_BOT_TOKEN"   # Crear con @BotFather
# TELEGRAM_CHAT_ID = 0   # Tu Chat ID (número, sin comillas); obtener con @userinfobot

# ----- Deep Sleep: intervalo entre mediciones (milisegundos) -----
# 1 min = 60000, 5 min = 300000, 10 min = 600000, 15 min = 900000
DEEP_SLEEP_MS = 60000

# ----- Umbrales para alertas (agricultura) -----
TEMP_ALERTA_CALOR = 32       # °C - alerta si supera
HUMEDAD_ALERTA_BAJA = 25     # % - alerta si humedad del aire baja
HUMEDAD_SUELO_ALERTA_BAJA = 30  # % - si usas sensor de humedad suelo (0-100)

# ----- Calibración sensor humedad de suelo (Capacitive Soil Moisture v1.2 en GPIO 33) -----
# Ajusta estos valores tras medir en tu montaje real:
# - SUELO_ADC_SECO: lectura ADC con sonda seca/al aire
# - SUELO_ADC_HUMEDO: lectura ADC con sonda en suelo húmedo
SUELO_ADC_SECO = 3000
SUELO_ADC_HUMEDO = 1400

# ----- Relé + bomba de agua 5V -----
# Módulo relé en GPIO 26 (IN del relé -> GPIO 26, GND/VCC del módulo al ESP32).
# Muchos módulos activan el relé con LOW; si el tuyo es al revés, pon RELAY_ACTIVE_LOW = False.
PIN_RELE = 26
RELAY_ACTIVE_LOW = True
RIEGO_HABILITADO = True

# Histéresis de humedad de suelo (0-100 %):
# - Si humedad < RIEGO_ACTIVAR_POR_DEBAJO_DE  -> enciende bomba TIEMPO_RIEGO_MS y apaga.
# - Si humedad >= RIEGO_NO_REGAR_POR_ENCIMA_DE -> no riega (suelo ya húmedo).
# Entre ambos valores no riega (evita encender/apagar en bucle cada ciclo).
RIEGO_ACTIVAR_POR_DEBAJO_DE = 35
RIEGO_NO_REGAR_POR_ENCIMA_DE = 50
TIEMPO_RIEGO_MS = 5000
