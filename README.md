# La Tiendita

Aplicación Django para administrar productos y ventas. El CRUD web conserva
sus rutas existentes y requiere sesión. Los estáticos se sirven con WhiteNoise.

## Desarrollo local

1. Crear un entorno virtual e instalar dependencias:
   `pip install -r requirements.txt`.
2. Copiar `.env.example` a `.env` y completar variables locales sin
   versionar el archivo.
3. Ejecutar `python manage.py migrate`, crear un usuario con
   `python manage.py createsuperuser` y arrancar con `python manage.py runserver`.

El administrador está en `/admin/`; el CRUD web está en `/` y `/ventas/`.
La API usa JWT mediante el encabezado `Authorization: Bearer <access>`.

## API REST

La API está bajo `/api/`. Los endpoints de productos y ventas requieren un
token JWT; `/api/health/` es público.

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/token/` | Obtener access y refresh tokens |
| POST | `/api/token/refresh/` | Renovar el access token |
| GET | `/api/health/` | Comprobar disponibilidad sin autenticación |
| GET/POST | `/api/productos/` | Listar o crear productos |
| GET/PUT/PATCH/DELETE | `/api/productos/{id}/` | Consultar, editar o eliminar producto |
| GET/POST | `/api/ventas/` | Listar o crear ventas |
| GET/PUT/PATCH/DELETE | `/api/ventas/{id}/` | Consultar, reemplazar detalles o eliminar venta |

`detalles` es escribible al crear o editar una venta. Si se envía en una
edición, reemplaza la lista completa: primero se eliminan los detalles
anteriores (su `delete()` repone stock) y después se crean los nuevos (su
`save()` descuenta stock y recalcula el total), todo dentro de una transacción.

Ejemplo de creación de venta:

```http
POST /api/ventas/
Authorization: Bearer <access>
Content-Type: application/json

{
  "cliente": "Ana López",
  "detalles": [
    {"producto": 1, "cantidad": 2}
  ]
}
```

La respuesta incluye `total`, `precio_unitario` y `subtotal` calculados.
Producto inactivo o stock insuficiente devuelve `400`; intentar borrar un
producto con ventas devuelve `409` con el mensaje para desactivarlo.
Los errores JSON usan `detail` o `errors`; los errores de autenticación y
permisos usan el formato estándar de DRF.

### Filtros, búsqueda y orden

- Productos: `activo`, `precio_min`, `precio_max`, `stock_min`, `stock_max`.
- Ventas: `fecha_desde`, `fecha_hasta`, `cliente`.
- Búsqueda de productos: `search=texto` sobre nombre y descripción.
- Orden: `ordering=nombre`, `ordering=-precio`, `ordering=fecha` o
  `ordering=-total`.
- Paginación: `page` con 10 elementos por página.

Ejemplo: `/api/productos/?activo=true&precio_min=100&stock_max=20&search=pan`.

## Variables de entorno

Requeridas:

- `SECRET_KEY`: clave secreta de Django.
- `DEBUG`: `False` en producción.
- `ALLOWED_HOSTS`: incluir el dominio de Vercel, por ejemplo `.vercel.app`.
- `CSRF_TRUSTED_ORIGINS`: incluir `https://*.vercel.app`.
- `DATABASE_URL`: URL PostgreSQL de Supabase; en producción se recomienda el
  pooler de transacción en puerto `6543`.

Alternativamente, para desarrollo se pueden usar `DB_HOST`, `DB_PORT`,
`DB_NAME`, `DB_USER` y `DB_PASSWORD`. Para ejecutar migraciones con la conexión
directa o el session pooler (puerto `5432`), definir temporalmente
`DATABASE_URL_MIGRATIONS`; `manage.py migrate` la selecciona automáticamente.
`DB_SSLMODE` es opcional y por defecto vale `require`.

## Despliegue en Vercel y Supabase

1. Crear el proyecto PostgreSQL en Supabase.
2. Configurar en Vercel las variables anteriores, sin incluir valores reales en
   el repositorio. Usar el pooler de transacción para `DATABASE_URL`.
3. Ejecutar las migraciones desde un entorno administrativo usando
   `DATABASE_URL_MIGRATIONS` y `python manage.py migrate`.
4. Crear el superusuario mediante una ejecución segura de administración.
5. Desplegar Vercel. `vercel.json` expone `api/index.py`, que publica
   `core.wsgi.application`, y ejecuta `collectstatic` durante el build.

El filesystem de la función es efímero y de solo lectura durante la ejecución;
por eso no se guardan archivos subidos y `CONN_MAX_AGE=0` desactiva conexiones
persistentes. `DISABLE_SERVER_SIDE_CURSORS=True` evita cursores incompatibles
con el pooler de transacción.

### Row Level Security (SQL no ejecutado)

Supabase expone las tablas mediante su API REST cuando se habilita el acceso
correspondiente. Django se conecta como usuario de aplicación y no debe
confiar en la anon key para proteger filas. RLS añade una segunda barrera en
PostgreSQL. Este SQL es una plantilla para revisar y ejecutar con el rol
administrador de Supabase; no se ejecuta desde este proyecto:

```sql
do $$
declare
  tabla record;
begin
  for tabla in
    select schemaname, tablename
    from pg_tables
    where schemaname in ('public')
      and tablename not in ('spatial_ref_sys')
  loop
    execute format('alter table %I.%I enable row level security',
                   tabla.schemaname, tabla.tablename);
  end loop;
end $$;
```

Activar RLS sin crear políticas bloquea el acceso de roles sin bypass, por lo
que las políticas deben definirse según el modelo de autorización antes de
exponer tablas a la anon key. Nunca se debe conceder a la anon key el rol de
servicio ni credenciales de Django.

## Verificación

Ejecutar `python manage.py check` y `python manage.py test`. Si la base de
pruebas PostgreSQL ya existe, usar `python manage.py test --keepdb`.
