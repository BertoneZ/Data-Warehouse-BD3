import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Esto lee el archivo .env oculto en tu computadora
load_dotenv()

# Trae la URL completa desde el archivo .env (o desde GitHub Secrets si está en la nube)
DATABASE_URL = os.getenv("DATABASE_URL")

# Crea el motor directamente con la URL
engine = create_engine(DATABASE_URL)

#DIMENSIÓN SITIO WEB
# 1. Buscar el último ID en el DW
query_max_sitio = text("SELECT COALESCE(MAX(id_sitio_web), 0) FROM data_warehouse.dim_sitio_web;")
with engine.connect() as conn:
    max_id_sitio = conn.execute(query_max_sitio).scalar()

# 2. Extraer solo lo nuevo
query_sitio = f"SELECT id_sitio, url_sitio FROM operacional.sitio_web WHERE id_sitio > {max_id_sitio};"
df_sitio_web = pd.read_sql(query_sitio, engine)

# 3. aca lo que hago es indicar la "equivalencia" de nombres entre la BD y el DW, la regla es Origen : Destino
if not df_sitio_web.empty:
    df_sitio_web = df_sitio_web.rename(columns={
        'id_sitio': 'id_sitio_web',
        'url_sitio': 'url_sitio_web'
    })
    df_sitio_web.to_sql('dim_sitio_web', engine, schema='data_warehouse', if_exists='append', index=False)
    print(f"Dim_Sitio_Web: {len(df_sitio_web)} sitios web nuevos.")
else:
    print("Dim_Sitio_Web: No hay datos nuevos para cargar.")

# -- DIMENSIÓN CLIENTE --
try:
    with engine.connect() as conn:
        max_id_cliente = conn.execute(text("SELECT COALESCE(MAX(id_cliente), 0) FROM data_warehouse.dim_cliente;")).scalar()
except Exception:
    max_id_cliente = 0

df_cliente = pd.read_sql(f"SELECT id_cliente, nombre FROM operacional.cliente WHERE id_cliente > {max_id_cliente};", engine)
if not df_cliente.empty:
    df_cliente = df_cliente.rename(columns={'nombre': 'nombre_cliente'})
    df_cliente.to_sql('dim_cliente', engine, schema='data_warehouse', if_exists='append', index=False)
    print(f"Dim_Cliente: {len(df_cliente)} registros nuevos.")
else:
    print("Dim_Cliente: No hay datos nuevos para cargar.")

# -- DIMENSIÓN CAMPAÑA -- 
try:
    with engine.connect() as conn:
        max_id_camp = conn.execute(text("SELECT COALESCE(MAX(id_campania), 0) FROM data_warehouse.dim_campania;")).scalar()
except Exception:
    max_id_camp = 0

df_campania = pd.read_sql(f"SELECT id_campania, nombre FROM operacional.campania WHERE id_campania > {max_id_camp};", engine)
if not df_campania.empty:
    df_campania = df_campania.rename(columns={'nombre': 'nombre_campania'})
    df_campania.to_sql('dim_campania', engine, schema='data_warehouse', if_exists='append', index=False)
    print(f"Dim_Campania: {len(df_campania)} registros nuevos.")
else:
    print("Dim_Campania: No hay datos nuevos para cargar.")

# -- DIMENSIÓN EMPLAZAMIENTO --
try:
    with engine.connect() as conn:
        max_id_emp = conn.execute(text("SELECT COALESCE(MAX(id_emplazamiento), 0) FROM data_warehouse.dim_emplazamiento;")).scalar()
except Exception:
    max_id_emp = 0

df_emplazamiento = pd.read_sql(f"SELECT id_emplazamiento, url_emplazamiento FROM operacional.emplazamiento WHERE id_emplazamiento > {max_id_emp};", engine)
if not df_emplazamiento.empty:
   
    df_emplazamiento.to_sql('dim_emplazamiento', engine, schema='data_warehouse', if_exists='append', index=False)
    print(f"Dim_Emplazamiento: {len(df_emplazamiento)} registros nuevos.")
else:
    print("Dim_Emplazamiento: No hay datos nuevos para cargar.")

# -- DIMENSIÓN USUARIO --
try:
    with engine.connect() as conn:
        max_id_usu = conn.execute(text("SELECT COALESCE(MAX(id_usuario), 0) FROM data_warehouse.dim_usuario;")).scalar()
except Exception:
    max_id_usu = 0

df_usuario = pd.read_sql(f"SELECT id_usuario, sexo FROM operacional.usuario WHERE id_usuario > {max_id_usu};", engine)
if not df_usuario.empty:
    df_usuario.to_sql('dim_usuario', engine, schema='data_warehouse', if_exists='append', index=False)
    print(f"Dim_Usuario: {len(df_usuario)} registros nuevos.")
else:
    print("Dim_Usuario: No hay datos nuevos para cargar.")

# -- DIMENSIÓN UBICACIONES -- 
# Se extraen las 3 tablas completas para cruzarlas en memoria
df_loc = pd.read_sql("SELECT id_localidad, nombre AS localidad, id_provincia FROM operacional.localidad;", engine)
df_prov = pd.read_sql("SELECT id_provincia, nombre AS provincia, id_pais FROM operacional.provincia;", engine)
df_pais = pd.read_sql("SELECT id_pais, nombre AS pais FROM operacional.pais;", engine)

# Cruces (JOINs)
df_ubi = pd.merge(df_loc, df_prov, on='id_provincia')
df_ubi = pd.merge(df_ubi, df_pais, on='id_pais')

# Filtramos columnas finales y renombramos la PK
df_ubi_final = df_ubi[['id_localidad', 'localidad', 'provincia', 'pais']].rename(columns={'id_localidad': 'id_ubicacion'})

# Lógica incremental para ubicaciones
try:
    with engine.connect() as conn:
        max_id_ubi = conn.execute(text("SELECT COALESCE(MAX(id_ubicacion), 0) FROM data_warehouse.dim_ubicaciones;")).scalar()
except Exception:
    max_id_ubi = 0

df_ubi_nueva = df_ubi_final[df_ubi_final['id_ubicacion'] > max_id_ubi]
if not df_ubi_nueva.empty:
    df_ubi_nueva.to_sql('dim_ubicaciones', engine, schema='data_warehouse', if_exists='append', index=False)
    print(f"Dim_Ubicaciones: {len(df_ubi_nueva)} registros nuevos.")
else:
    print("Dim_Ubicaciones: No hay datos nuevos para cargar.")

# -- DIMENSIÓN TIPO VISITA -- 
# Los visitantes llegan de forma orgánica o pagada 
try:
    with engine.connect() as conn:
        count_visitas = conn.execute(text("SELECT COUNT(*) FROM data_warehouse.dim_tipo_visita;")).scalar()
except Exception:
    count_visitas = 0

if count_visitas == 0:
    df_tipo_visita = pd.DataFrame({
        'id_tipo_visita': [1, 2],
        'tipo_visita': ['Orgánica', 'Pagada']
    })
    df_tipo_visita.to_sql('dim_tipo_visita', engine, schema='data_warehouse', if_exists='append', index=False)
    print("Dim_TipoVisita: Cargada desde cero.")
else:
    print("Dim_TipoVisita: No hay datos nuevos para cargar.")

# -- DIMENSIÓN RANGO ETARIO --
try:
    with engine.connect() as conn:
        count_rangos = conn.execute(text("SELECT COUNT(*) FROM data_warehouse.dim_rango_etario;")).scalar()
except Exception:
    count_rangos = 0

if count_rangos == 0:
    df_rango_etario = pd.DataFrame({
        'id_rango_etario': [1, 2, 3, 4],
        'rango_etario': ['0-20', '21-40', '41-60', '+60']
    })
    df_rango_etario.to_sql('dim_rango_etario', engine, schema='data_warehouse', if_exists='append', index=False)
    print("Dim_RangoEtario: Cargada desde cero.")
else:
    print("Dim_RangoEtario: No hay datos nuevos para cargar.")

# -- DIMENSIÓN TIEMPO --
try:
    with engine.connect() as conn:
        count_tiempo = conn.execute(text("SELECT COUNT(*) FROM data_warehouse.dim_tiempo;")).scalar()
except Exception:
    count_tiempo = 0

if count_tiempo == 0:
    # Generamos un calendario automático desde 2024 hasta 2026
    fechas = pd.date_range(start='2024-01-01', end='2026-12-31')
    df_tiempo = pd.DataFrame({'fecha': fechas})
    df_tiempo['id_tiempo'] = df_tiempo['fecha'].dt.strftime('%d%m%Y').astype(int) #le puse formato dia mes y año 
    df_tiempo['dia'] = df_tiempo['fecha'].dt.day
    df_tiempo['mes'] = df_tiempo['fecha'].dt.month
    df_tiempo['anio'] = df_tiempo['fecha'].dt.year
    
    # Asignar estación del año simplificada
    def obtener_estacion(mes):
        if mes in [12, 1, 2]: return 'Verano'
        elif mes in [3, 4, 5]: return 'Otoño'
        elif mes in [6, 7, 8]: return 'Invierno'
        else: return 'Primavera'
        
    df_tiempo['estacion'] = df_tiempo['mes'].apply(obtener_estacion)
    
    # Eliminar la columna fecha temporal
    df_tiempo = df_tiempo.drop(columns=['fecha'])
    
    df_tiempo.to_sql('dim_tiempo', engine, schema='data_warehouse', if_exists='append', index=False)
    print("Dim_Tiempo: Calendario generado y cargado.")
else:
    print("Dim_Tiempo: No hay datos nuevos para cargar.")

#CARGA DE LAS FACT TABLES   
def obtener_max_id_tiempo(nombre_tabla):
    try:
        with engine.connect() as conn:
            return conn.execute(text(f"SELECT COALESCE(MAX(id_tiempo), 0) FROM data_warehouse.{nombre_tabla};")).scalar()
    except Exception:
        return 0

def obtener_fact_existente(nombre_tabla, id_tiempos):
    if not id_tiempos:
        return pd.DataFrame()
    valores = ", ".join(str(int(valor)) for valor in sorted(set(id_tiempos)))
    query = text(f"SELECT * FROM data_warehouse.{nombre_tabla} WHERE id_tiempo IN ({valores});")
    return pd.read_sql(query, engine)

def conjuntos_iguales(df_izquierda, df_derecha, columnas):
    if df_izquierda.empty and df_derecha.empty:
        return True
    if df_izquierda.empty != df_derecha.empty:
        return False
    filas_izquierda = {tuple(fila) for fila in df_izquierda[columnas].itertuples(index=False, name=None)}
    filas_derecha = {tuple(fila) for fila in df_derecha[columnas].itertuples(index=False, name=None)}
    return filas_izquierda == filas_derecha

max_ft_pub_tiempo = obtener_max_id_tiempo('ft_publicaciones')
if max_ft_pub_tiempo:
    fecha_corte_pub = pd.to_datetime(str(max_ft_pub_tiempo), format='%d%m%Y').date()
    query_pub = text("""
SELECT p.id_publicacion, p.fecha, p.id_emplazamiento, p.con_conversion_si_no,
       a.id_tipo_aviso, a.id_campania,
       c.id_cliente,
       cli.id_localidad AS id_ubicacion_cliente,
       e.costo
FROM operacional.publicacion p
JOIN operacional.aviso a ON p.id_aviso = a.id_aviso
JOIN operacional.campania c ON a.id_campania = c.id_campania
JOIN operacional.cliente cli ON c.id_cliente = cli.id_cliente
JOIN operacional.emplazamiento e ON p.id_emplazamiento = e.id_emplazamiento
WHERE p.fecha >= :fecha_corte_pub;
""")
    df_pub = pd.read_sql(query_pub, engine, params={'fecha_corte_pub': fecha_corte_pub})
else:
    query_pub = text("""
SELECT p.id_publicacion, p.fecha, p.id_emplazamiento, p.con_conversion_si_no,
       a.id_tipo_aviso, a.id_campania,
       c.id_cliente,
       cli.id_localidad AS id_ubicacion_cliente,
       e.costo
FROM operacional.publicacion p
JOIN operacional.aviso a ON p.id_aviso = a.id_aviso
JOIN operacional.campania c ON a.id_campania = c.id_campania
JOIN operacional.cliente cli ON c.id_cliente = cli.id_cliente
JOIN operacional.emplazamiento e ON p.id_emplazamiento = e.id_emplazamiento;
""")
    df_pub = pd.read_sql(query_pub, engine)

if not df_pub.empty:
    df_pub['id_tiempo'] = pd.to_datetime(df_pub['fecha']).dt.strftime('%d%m%Y').astype(int)

    df_ft_pub = df_pub.groupby([
        'id_tiempo', 'id_campania', 'id_cliente', 'id_tipo_aviso', 'id_ubicacion_cliente'
    ]).agg(
        cantidad_publicaciones=('id_publicacion', 'count'),
        costo_publicacion=('costo', 'sum'),
        conversiones=('con_conversion_si_no', 'sum')
    ).reset_index()

    columnas_pub = df_ft_pub.columns.tolist()
    fact_pub_existente = obtener_fact_existente('ft_publicaciones', df_ft_pub['id_tiempo'].unique().tolist())

    if fact_pub_existente.empty or not conjuntos_iguales(df_ft_pub, fact_pub_existente[columnas_pub], columnas_pub):
        if not fact_pub_existente.empty:
            ids_pub = ", ".join(str(int(valor)) for valor in sorted(df_ft_pub['id_tiempo'].unique()))
            with engine.begin() as conn:
                conn.execute(text(f"DELETE FROM data_warehouse.ft_publicaciones WHERE id_tiempo IN ({ids_pub});"))

        df_ft_pub.to_sql('ft_publicaciones', engine, schema='data_warehouse', if_exists='append', index=False)
        print(f"FT_Publicaciones: {len(df_ft_pub)} registros cargados o actualizados.")
    else:
        print("FT_Publicaciones: No hay cambios para cargar.")
else:
    print("FT_Publicaciones: No hay datos nuevos para cargar.")

#CARGA DE FT_VISITAS
max_ft_vis_tiempo = obtener_max_id_tiempo('ft_visitas')
if max_ft_vis_tiempo:
    fecha_corte_vis = pd.to_datetime(str(max_ft_vis_tiempo), format='%d%m%Y').date()
    query_vis = text("""
SELECT v.id_sitio, v.fecha, v.id_usuario, v.id_publicacion,
       u.fecha_nacimiento, u.id_localidad AS id_ubicacion_usuario,
       s.id_cliente,
       cli.id_localidad AS id_ubicacion_cliente,
       p.id_emplazamiento,
       e.costo AS costo_visitas_pagadas
FROM operacional.visitas v
JOIN operacional.usuario u ON v.id_usuario = u.id_usuario
JOIN operacional.sitio_web s ON v.id_sitio = s.id_sitio
JOIN operacional.cliente cli ON s.id_cliente = cli.id_cliente
LEFT JOIN operacional.publicacion p ON v.id_publicacion = p.id_publicacion
LEFT JOIN operacional.emplazamiento e ON p.id_emplazamiento = e.id_emplazamiento
WHERE v.fecha >= :fecha_corte_vis;
""")
    df_vis = pd.read_sql(query_vis, engine, params={'fecha_corte_vis': fecha_corte_vis})
else:
    query_vis = text("""
SELECT v.id_sitio, v.fecha, v.id_usuario, v.id_publicacion,
       u.fecha_nacimiento, u.id_localidad AS id_ubicacion_usuario,
       s.id_cliente,
       cli.id_localidad AS id_ubicacion_cliente,
       p.id_emplazamiento,
       e.costo AS costo_visitas_pagadas
FROM operacional.visitas v
JOIN operacional.usuario u ON v.id_usuario = u.id_usuario
JOIN operacional.sitio_web s ON v.id_sitio = s.id_sitio
JOIN operacional.cliente cli ON s.id_cliente = cli.id_cliente
LEFT JOIN operacional.publicacion p ON v.id_publicacion = p.id_publicacion
LEFT JOIN operacional.emplazamiento e ON p.id_emplazamiento = e.id_emplazamiento;
""")
    df_vis = pd.read_sql(query_vis, engine)

if not df_vis.empty:
    df_vis['fecha_visita'] = pd.to_datetime(df_vis['fecha'])
    df_vis['fecha_nac'] = pd.to_datetime(df_vis['fecha_nacimiento'])
    df_vis['id_tiempo'] = df_vis['fecha_visita'].dt.strftime('%d%m%Y').astype(int)

    df_vis['edad'] = df_vis['fecha_visita'].dt.year - df_vis['fecha_nac'].dt.year
    def asignar_rango(edad):
        if edad <= 20: return 1
        elif edad <= 40: return 2
        elif edad <= 60: return 3
        else: return 4
    df_vis['id_rango_etario'] = df_vis['edad'].apply(asignar_rango)

    df_vis['id_tipo_visita'] = df_vis['id_publicacion'].apply(lambda x: 1 if pd.isna(x) else 2)
    df_vis['costo_visitas_pagadas'] = df_vis['costo_visitas_pagadas'].fillna(0)
    df_vis = df_vis.rename(columns={'id_sitio': 'id_sitioweb'})

    df_ft_vis = df_vis.groupby([
        'id_tiempo', 'id_tipo_visita', 'id_usuario', 'id_sitioweb',
        'id_ubicacion_usuario', 'id_emplazamiento', 'id_rango_etario',
        'id_ubicacion_cliente', 'id_cliente'
    ]).agg(
        cantidad_visitas=('id_usuario', 'count'),
        costo_visitas_pagadas=('costo_visitas_pagadas', 'sum')
    ).reset_index()

    columnas_vis = df_ft_vis.columns.tolist()
    fact_vis_existente = obtener_fact_existente('ft_visitas', df_ft_vis['id_tiempo'].unique().tolist())

    if fact_vis_existente.empty or not conjuntos_iguales(df_ft_vis, fact_vis_existente[columnas_vis], columnas_vis):
        if not fact_vis_existente.empty:
            ids_vis = ", ".join(str(int(valor)) for valor in sorted(df_ft_vis['id_tiempo'].unique()))
            with engine.begin() as conn:
                conn.execute(text(f"DELETE FROM data_warehouse.ft_visitas WHERE id_tiempo IN ({ids_vis});"))

        df_ft_vis.to_sql('ft_visitas', engine, schema='data_warehouse', if_exists='append', index=False)
        print(f"FT_Visitas: {len(df_ft_vis)} registros cargados o actualizados desde la base operativa.")
    else:
        print("FT_Visitas: No hay cambios para cargar.")
else:
    print("FT_Visitas: No hay datos nuevos para cargar.")


