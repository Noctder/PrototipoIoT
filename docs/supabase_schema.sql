-- Tabla para Green IoT - Agricultura Inteligente
-- "Gemelo digital": la última fila por dispositivo es el estado actual (device shadow)

CREATE TABLE IF NOT EXISTS agricultura_lecturas (
  id BIGSERIAL PRIMARY KEY,
  temperatura DECIMAL(4,1) NOT NULL,
  humedad DECIMAL(4,1) NOT NULL,
  presion DECIMAL(6,2),
  humedad_suelo SMALLINT,
  estado VARCHAR(20) NOT NULL,
  es_alerta BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índice para consultar la última lectura rápido (sombra del dispositivo)
CREATE INDEX IF NOT EXISTS idx_agricultura_created_at ON agricultura_lecturas(created_at DESC);

-- Opcional: Realtime para actualizar la UI al llegar un nuevo envío
ALTER PUBLICATION supabase_realtime ADD TABLE agricultura_lecturas;

-- Políticas RLS: ajustar según si usas anon key o servicio
-- Ejemplo permitir INSERT con anon key:
CREATE POLICY "Allow insert" ON agricultura_lecturas FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow select" ON agricultura_lecturas FOR SELECT USING (true);
