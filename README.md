# Green IoT: Agricultura Inteligente

Sistema de monitoreo agrícola con **mínimo consumo**: ESP32 en **Deep Sleep**, **conexión breve** solo para enviar datos, y **gemelo digital** en Supabase para que la app muestre siempre el último estado.

Basado en la arquitectura [Green IoT / Agricultura Inteligente](docs/PROPUESTA_AGRICULTURA_INTELIGENTE.md) y en el código de [PrototipoIoT](https://github.com/Noctder/PrototipoIoT).

---

## Características

- **Nodo sensor:** Deep Sleep entre mediciones; solo despierta para medir y enviar.
- **Conexión breve:** WiFi encendido unos segundos por ciclo; luego se apaga y el ESP32 duerme.
- **Gemelo digital:** Supabase guarda cada envío; la “sombra” es la última fila (siempre visible para el usuario).
- **Sensores:** DHT11 (temperatura y humedad), BMP280 opcional (presión), ADC opcional (humedad de suelo).
- **Alertas:** Telegram (y buzzer local) cuando se superan umbrales (calor, humedad baja).

---

## Hardware sugerido

| Componente        | Uso                    | Conexión                 |
|-------------------|------------------------|--------------------------|
| ESP32             | Microcontrolador        | -                        |
| DHT11             | Temperatura y humedad   | GPIO 4 (pull-up 10kΩ)    |
| BMP280 (opc.)     | Presión atmosférica     | I2C SDA 21, SCL 22       |
| Humedad suelo (opc.) | Sensor capacitivo ADC | GPIO 34 (ADC)            |
| LED               | Indicador de envío      | GPIO 2 (integrado)       |
| Buzzer (opc.)     | Alerta sonora           | GPIO 18 (PWM)            |

---

## Configuración en Thonny y carga al ESP32

### 1. Requisitos

- MicroPython instalado en el ESP32 (firmware oficial o compatible).
- Thonny IDE.
- Proyecto en [Supabase](https://supabase.com) y tabla `agricultura_lecturas` (ver más abajo).
- Opcional: bot de Telegram para alertas.

### 2. Crear tabla en Supabase

En el SQL Editor de tu proyecto Supabase ejecuta el contenido de:

- [docs/supabase_schema.sql](docs/supabase_schema.sql)

Así tendrás la tabla `agricultura_lecturas` con columnas: `temperatura`, `humedad`, `presion`, `humedad_suelo`, `estado`, `es_alerta`, `created_at`.

### 3. Editar configuración

En tu PC, en la carpeta `esp32/`:

1. Abre **config_supabase.py**.
2. Completa:
   - `SUPABASE_URL` y `SUPABASE_API_KEY` (Settings → API en Supabase).
   - `WIFI_SSID` y `WIFI_PASSWORD`.
   - `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` si quieres alertas (si no, déjalos en `""` y `0`).
   - `DEEP_SLEEP_MS`: intervalo entre mediciones (ej. `300000` = 5 minutos).

### 4. Cargar archivos al ESP32 con Thonny

1. Conecta el ESP32 por USB y abre **Thonny**.
2. En Thonny: **Herramientas → Opciones → Intérprete** → selecciona el puerto del ESP32 y el intérprete **MicroPython (ESP32)**.
3. En el explorador de archivos (panel izquierdo), navega a la carpeta local `AgriculturaInteligente/esp32/`.
4. Sube al ESP32 (clic derecho → “Subir a /”) estos archivos:
   - **main.py**
   - **config_supabase.py**
   - **boot.py** (opcional; puede estar vacío o mínimo)
5. Comprueba que en la raíz del dispositivo aparezcan `main.py` y `config_supabase.py`.

### 5. Ejecutar

- En Thonny: **Ejecutar** (F5). El ESP32 hará un ciclo: medir → conectar WiFi → enviar a Supabase → (alertas si aplica) → desconectar → **Deep Sleep**.
- Tras el tiempo definido en `DEEP_SLEEP_MS`, el ESP32 despertará solo y repetirá el ciclo (vuelve a ejecutar `main.py` desde el inicio).

**Nota:** Si abres la consola de Thonny después de que entre en Deep Sleep, dejarás de ver salida hasta que lo reconectes y vuelva a ejecutarse. Para depurar sin Deep Sleep, comenta la línea final de `main.py` (`machine.deepsleep(...)`) y añade un `while True: utime.sleep(60)` para que no se reinicie.

---

## Estructura del proyecto

```
AgriculturaInteligente/
├── README.md
├── esp32/
│   ├── main.py           # Código principal (Deep Sleep + envío)
│   ├── config_supabase.py
│   └── boot.py
└── docs/
    ├── PROPUESTA_AGRICULTURA_INTELIGENTE.md
    └── supabase_schema.sql
```

---

## Cómo se ve el “gemelo digital”

- Cada vez que el ESP32 despierta, envía **una fila** a `agricultura_lecturas`.
- En tu app o dashboard, para mostrar el “estado actual” del nodo (sombra del dispositivo), consulta la **última fila** por dispositivo, por ejemplo:

  ```sql
  SELECT * FROM agricultura_lecturas ORDER BY created_at DESC LIMIT 1;
  ```

- Así el usuario siempre ve el último valor conocido aunque el sensor esté dormido.

---

## Licencia

Uso educativo y personal. Código del ESP32 basado en ideas de [Noctder/PrototipoIoT](https://github.com/Noctder/PrototipoIoT).
