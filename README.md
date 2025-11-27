# 🌡️ Monitor IoT - Sistema de Monitoreo Ambiental con ESP32

Sistema de monitoreo ambiental en tiempo real que utiliza un ESP32 para capturar datos de temperatura, humedad y presión atmosférica, almacenándolos en Supabase y enviando alertas por Telegram.

![ESP32](https://img.shields.io/badge/ESP32-MicroPython-blue)
![Supabase](https://img.shields.io/badge/Supabase-Database-green)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)

## 📋 Características

- ✅ **Monitoreo en tiempo real** de temperatura, humedad y presión atmosférica
- ✅ **Almacenamiento en la nube** mediante Supabase
- ✅ **Alertas automáticas** por Telegram cuando se detectan condiciones de calor
- ✅ **Interfaz web responsiva** con gráficas históricas
- ✅ **Progressive Web App (PWA)** instalable en dispositivos móviles
- ✅ **Actualización automática** de datos cada 5 segundos
- ✅ **Buzzer** para alertas sonoras locales
- ✅ **LED indicador** de estado del sistema

## 🛠️ Componentes Hardware

| Componente | Descripción | Conexión |
|------------|-------------|----------|
| **ESP32** | Microcontrolador principal | - |
| **DHT11** | Sensor de temperatura y humedad | GPIO 4 |
| **BMP280** | Sensor de presión atmosférica | I2C (SDA: GPIO 21, SCL: GPIO 22) |
| **Buzzer** | Alarma sonora | GPIO 18 (PWM) |
| **LED** | Indicador de estado | GPIO 2 (integrado) |
| **Resistencia 10kΩ** | Pull-up para DHT11 | Entre DATA y VCC |

### Diagrama de Conexiones

```
ESP32          DHT11          BMP280
------         -----          ------
GPIO 4  ────── DATA
3.3V    ────── VCC
GND     ────── GND

GPIO 21 ────────────────────── SDA
GPIO 22 ────────────────────── SCL
3.3V    ────────────────────── VCC
GND     ────────────────────── GND

GPIO 18 ────── Buzzer (PWM)
GPIO 2  ────── LED (integrado)
```

## 📦 Instalación

### 1. Requisitos Previos

- **MicroPython** instalado en el ESP32
- **Thonny IDE** o similar para cargar el código
- Cuenta en **Supabase** (gratuita)
- Bot de **Telegram** configurado

### 2. Configuración de Supabase

1. Crea un proyecto en [Supabase](https://supabase.com)
2. Crea una tabla con el siguiente esquema:

```sql
CREATE TABLE sensor_readings (
  id BIGSERIAL PRIMARY KEY,
  temperatura DECIMAL(4,1) NOT NULL,
  humedad DECIMAL(4,1) NOT NULL,
  presion DECIMAL(6,2),
  estado VARCHAR(10) NOT NULL,
  es_alerta BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Habilitar Realtime para actualizaciones en tiempo real
ALTER PUBLICATION supabase_realtime ADD TABLE sensor_readings;
```

3. Configura las políticas RLS (Row Level Security) según tus necesidades

### 3. Configuración de Telegram

1. Crea un bot con [@BotFather](https://t.me/BotFather)
2. Obtén tu **Chat ID** usando [@userinfobot](https://t.me/userinfobot)
3. Guarda el token del bot y tu Chat ID

### 4. Configuración del Código

1. Clona o descarga este repositorio
2. Edita `config_supabase.py` con tus credenciales:

```python
SUPABASE_URL = "https://tu-proyecto.supabase.co"
SUPABASE_API_KEY = "tu-api-key-aqui"
SUPABASE_TABLE = "sensor_readings"
```

3. Edita `main.py` y actualiza:

```python
# Configuración WiFi
WIFI_SSID = "tu-red-wifi"
WIFI_PASSWORD = "tu-contraseña"

# Configuración Telegram Bot
TELEGRAM_BOT_TOKEN = "tu-token-del-bot"
TELEGRAM_CHAT_ID = tu_chat_id  # Sin comillas
```

### 5. Cargar Código al ESP32

1. Conecta el ESP32 por USB
2. Abre Thonny IDE
3. Carga `main.py` y `config_supabase.py` al ESP32
4. Ejecuta `main.py`

## 🌐 Interfaz Web

La interfaz web está ubicada en la carpeta `web/` y puede ser desplegada en cualquier servidor web estático o servicio de hosting.

### Características de la Web

- **Diseño responsivo** - Funciona en móviles, tablets y desktop
- **Gráficas en tiempo real** - Visualización histórica de los datos
- **Actualización automática** - Sincronización con Supabase Realtime
- **PWA** - Instalable como aplicación nativa

### Despliegue

1. Sube los archivos de la carpeta `web/` a tu servidor
2. Asegúrate de que `index.html` esté en la raíz
3. Configura Supabase en el código JavaScript (línea ~50):

```javascript
const supabaseUrl = 'https://tu-proyecto.supabase.co';
const supabaseKey = 'tu-api-key';
```

4. Accede a la URL de tu servidor

## 📊 Funcionamiento

### Estados del Sistema

El sistema clasifica las lecturas en tres estados según la temperatura:

- **FRIO**: Temperatura < 15°C
- **NORMAL**: Temperatura entre 15°C y 27°C
- **CALOR**: Temperatura > 27°C

### Alertas

Cuando se detecta una condición de **CALOR**:
- 🔔 Se activa el buzzer (tono de 1.5kHz por 2 segundos)
- 📱 Se envía una alerta automática por Telegram
- 💾 Se marca el registro en Supabase como `es_alerta = true`

### Envío de Datos

Los datos se envían a Supabase **solo cuando hay cambios** en:
- Temperatura (redondeada a 1 decimal)
- Humedad (redondeada a 1 decimal)
- Presión (redondeada a 2 decimales)

Esto optimiza el uso de la base de datos y evita registros duplicados.

## 📁 Estructura del Proyecto

```
PropotipoIoT/
│
├── main.py                 # Código principal del ESP32
├── config_supabase.py      # Configuración de Supabase (crear con tus credenciales)
├── boot.py                 # Script de inicio (opcional)
│
└── web/                    # Interfaz web
    ├── index.html          # Página principal
    ├── manifest.json       # Configuración PWA
    ├── sw.js               # Service Worker para PWA
    └── icons/              # Iconos para PWA
        ├── icon.svg
        ├── icon-72x72.png
        ├── icon-96x96.png
        ├── icon-128x128.png
        ├── icon-144x144.png
        ├── icon-152x152.png
        ├── icon-192x192.png
        ├── icon-384x384.png
        └── icon-512x512.png
```

## 🔧 Tecnologías Utilizadas

### Hardware
- **ESP32** - Microcontrolador WiFi/Bluetooth
- **DHT11** - Sensor digital de temperatura y humedad
- **BMP280** - Sensor de presión atmosférica (I2C)

### Software
- **MicroPython** - Lenguaje de programación
- **Supabase** - Base de datos y backend
- **Telegram Bot API** - Notificaciones
- **Chart.js** - Gráficas interactivas
- **Progressive Web App (PWA)** - Aplicación web instalable

## 📝 Notas Importantes

- ⚠️ El **DHT11** requiere una resistencia pull-up de 10kΩ entre DATA y VCC
- ⚠️ El **BMP280** puede estar en dirección I2C `0x76` o `0x77` (el código detecta automáticamente)
- ⚠️ El sensor **BMP280** solo mide presión y temperatura, **NO humedad** (a diferencia del BME280)
- ⚠️ La humedad se obtiene únicamente del **DHT11**
- ⚠️ El código incluye manejo de errores y reintentos automáticos

## 🐛 Solución de Problemas

### El ESP32 no se conecta a WiFi
- Verifica que las credenciales WiFi sean correctas
- Asegúrate de que la red WiFi esté en 2.4GHz (ESP32 no soporta 5GHz)

### No se envían datos a Supabase
- Verifica las credenciales en `config_supabase.py`
- Revisa que la tabla exista y tenga el esquema correcto
- Verifica las políticas RLS en Supabase

### El sensor DHT11 no responde
- Verifica las conexiones (DATA, VCC, GND)
- Asegúrate de tener la resistencia pull-up de 10kΩ
- El DHT11 puede tardar hasta 2 segundos en responder

### El BMP280 no se detecta
- Verifica las conexiones I2C (SDA, SCL)
- Comprueba que el sensor esté alimentado (3.3V)
- El código detecta automáticamente la dirección I2C (0x76 o 0x77)

## 📄 Licencia

Este proyecto es de código abierto y está disponible para uso educativo y personal.

⭐ Si este proyecto te fue útil, ¡no olvides darle una estrella!

