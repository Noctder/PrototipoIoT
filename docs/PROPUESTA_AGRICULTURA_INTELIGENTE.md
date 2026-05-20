# Green IoT: Agricultura Inteligente con Mínima Energía

## Resumen

Sistema de monitoreo agrícola basado en la arquitectura de la infografía: **nodo sensor físico** con máximo ahorro (Deep Sleep + conexión breve) y **gemelo digital** en la nube (Supabase) para continuidad de datos y alertas. Pensado para ESP32 con MicroPython y carga desde Thonny.

---

## 1. Nodo sensor físico: máximo ahorro

### 1.1 Estrategia “Sueño profundo” (Deep Sleep)

- El ESP32 **se apaga casi por completo** entre mediciones.
- Solo **despierta** cada X minutos (configurable, ej. 5–15 min), toma medida, envía y vuelve a dormir.
- **Ventaja:** batería dura días/semanas en campo.

### 1.2 Conexión rápida y breve

- **No** hay conexión WiFi constante.
- Flujo: despertar → conectar WiFi → leer sensores → enviar un único POST a Supabase → (opcional) alerta Telegram → desconectar WiFi → entrar en Deep Sleep.
- WiFi encendido solo 10–30 segundos por ciclo.

### 1.3 Componentes de bajo consumo

- **ESP32** + sensores que consuman poco en activo.
- Misma base que [PrototipoIoT](https://github.com/Noctder/PrototipoIoT): DHT11 (temperatura/humedad), BMP280 opcional (presión). Opcional: sensor de humedad de suelo por ADC.

---

## 2. Gemelo digital: continuidad virtual

### 2.1 Sombra del dispositivo (Device Shadow)

- En **Supabase** se guarda cada envío del nodo (INSERT en tabla `agricultura_lecturas`).
- La **última fila** por dispositivo es la “sombra”: último estado conocido aunque el sensor esté dormido.
- La app/dashboard siempre muestra ese último valor (y opcionalmente histórico).

### 2.2 Datos siempre disponibles

- El usuario ve temperatura, humedad, etc. **sin cortes**: la nube muestra la última lectura + timestamp.
- Realtime de Supabase (opcional) permite actualizar la UI en cuanto llega un nuevo envío.

### 2.3 Alertas y predicciones

- **En el ESP32:** umbrales simples (ej. temperatura alta, humedad baja, suelo seco) → `es_alerta` y buzzer.
- **En la web (gemelo digital):** predicciones inteligentes con **datos externos de clima** (API Open-Meteo) + última humedad de suelo del sensor → estimación de riesgo de sequía y **alertas preventivas** en el dashboard.

---

## 3. Flujo funcional del firmware

```
[Despertar por temporizador]
        ↓
[Leer DHT11 + opcional BMP280 / humedad suelo]
        ↓
[Conectar WiFi (timeout 10–15 s)]
        ↓
[POST a Supabase → INSERT en agricultura_lecturas]
        ↓
[Si alerta (temp/humedad) → Telegram]
        ↓
[Apagar WiFi]
        ↓
[Deep Sleep 5–15 min]
        ↓
[Repetir al despertar]
```

---

## 4. Hardware sugerido (compatible con PrototipoIoT)

| Componente     | Uso                    | Conexión              |
|----------------|------------------------|------------------------|
| ESP32          | Microcontrolador       | -                      |
| DHT11          | Temperatura y humedad  | GPIO 4 (pull-up 10kΩ)  |
| BMP280 (opc.)  | Presión atmosférica    | I2C SDA 21, SCL 22     |
| Humedad suelo (opc.) | ADC              | GPIO 34 (ADC)          |
| LED            | Indicador de envío     | GPIO 2 (integrado)     |
| Buzzer (opc.)  | Alerta local           | GPIO 18 (PWM)          |

---

## 5. Software y servicios

- **MicroPython** en ESP32, edición/carga con **Thonny**.
- **Supabase:** tabla `agricultura_lecturas` (gemelo digital / device shadow).
- **Telegram:** alertas cuando se superan umbrales (opcional).
- **Web/PWA:** misma idea que PrototipoIoT; se consulta la “última fila” + histórico desde Supabase.

---

## 6. Diferencias clave frente a PrototipoIoT

| Aspecto        | PrototipoIoT        | Agricultura Inteligente (Green IoT)     |
|----------------|----------------------|-----------------------------------------|
| Energía        | Loop continuo        | Deep Sleep entre mediciones             |
| WiFi           | Siempre conectado    | Solo durante envío (segundos)           |
| Envío          | Cada 5 s si hay cambio| Un envío por ciclo de despertar         |
| Experiencia UI | Tiempo real continuo | Misma (nube muestra última lectura)     |
| Uso            | Interior/experimento  | Campo, batería, larga duración          |

Con esto tienes una propuesta funcional alineada con la imagen y lista para bajar al código en Thonny y cargarlo al ESP32.
