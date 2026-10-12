# La Tiendita

Aplicación Django para controlar productos y ventas. No se usa almacenamiento
de media; los estáticos se sirven con WhiteNoise.

## Desarrollo local

Crear y activar un entorno virtual, instalar `pip install -r requirements.txt`.
Copiar `.env.example` a `.env` y completar `SECRET_KEY` y las variables de
Postgres (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`), o usar
`DATABASE_URL`. Ejecutar `python manage.py migrate`,
`python manage.py createsuperuser` y opcionalmente
`python manage.py cargar_datos_demo`. Finalmente ejecutar
`python manage.py runserver`.

El administrador está en `/admin/`; el CRUD autenticado está en `/` y
`/ventas/`. Para validar: `python manage.py check` y `python manage.py test`.

## Vercel

Configurar en Vercel las variables de `.env.example`, incluyendo las
credenciales de Supabase y una `SECRET_KEY` segura. Conectar el repositorio;
`vercel.json` expone `core/wsgi.py` y ejecuta `collectstatic`. Aplicar las
migraciones contra Supabase antes de usar la aplicación y crear el superusuario
mediante una ejecución administrativa segura. Revisar los logs de Vercel:
Django y `ventas` escriben en consola.
