-- Script SQL para solucionar el error de la columna faltante resolucion_77_line_id
-- Ejecutar como usuario postgres o con permisos de superusuario

-- Verificar si la columna existe
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'account_move' 
AND column_name = 'resolucion_77_line_id';

-- Si la columna NO existe, agregarla
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'account_move' 
        AND column_name = 'resolucion_77_line_id'
    ) THEN
        -- Agregar la columna
        ALTER TABLE account_move 
        ADD COLUMN resolucion_77_line_id integer;
        
        -- Crear índice para mejorar el rendimiento
        CREATE INDEX account_move_resolucion_77_line_id_idx 
        ON account_move(resolucion_77_line_id);
        
        -- Crear foreign key constraint
        ALTER TABLE account_move 
        ADD CONSTRAINT account_move_resolucion_77_line_id_fkey 
        FOREIGN KEY (resolucion_77_line_id) 
        REFERENCES resolucion_77_line(id) ON DELETE SET NULL;
        
        RAISE NOTICE 'Columna resolucion_77_line_id agregada exitosamente';
    ELSE
        RAISE NOTICE 'La columna resolucion_77_line_id ya existe';
    END IF;
END $$;

-- Verificar que la columna se creó correctamente
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'account_move' 
AND column_name = 'resolucion_77_line_id';

-- Verificar índices relacionados
SELECT indexname, indexdef
FROM pg_indexes 
WHERE tablename = 'account_move' 
AND indexname LIKE '%resolucion%';

-- Verificar foreign keys
SELECT 
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name = 'account_move'
AND kcu.column_name = 'resolucion_77_line_id'; 