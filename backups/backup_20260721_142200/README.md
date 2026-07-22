# SGD - Base Django

## 1. Crear entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Migraciones y usuario admin

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

## 3. Ejecutar servidor

```powershell
python manage.py runserver
```

## Estructura principal

- `config/`: configuracion global del proyecto
- `apps/core/`: vistas base (inicio y dashboard)
- `apps/accounts/`: espacio para logica de usuarios
- `apps/documents/`: modelo y vistas de documentos
- `templates/`: plantillas HTML
- `static/`: recursos estaticos
- `media/`: archivos subidos

## Backups

El sistema tiene dos tipos de backup: **archivos del proyecto** y **base de datos PostgreSQL**.

### Backup manual

```powershell
# Archivos del proyecto
.\backup.ps1              # copia en carpeta
.\backup.ps1 -Compress    # comprimido en .zip

# Base de datos (PostgreSQL vía Docker)
.\backup_db.ps1
```

Guarda los archivos en:
- `backups/backup_<timestamp>/`  — archivos del proyecto
- `backups/db/db_backup_<timestamp>.sql.zip` — dump de la base de datos

Registra cada backup en `backups/backup.log`.  
Por defecto conserva los **últimos 7 backups** (configurable con `-KeepLast N`).

### Backup automático (diario)

Ejecuta **una sola vez** como Administrador:
```powershell
.\setup_backup_task.ps1                          # archivos 02:00 AM, DB 02:30 AM
.\setup_backup_task.ps1 -TimeFiles "20:00" -TimeDB "20:30"   # horario personalizado
.\setup_backup_task.ps1 -Compress               # archivos comprimidos
.\setup_backup_task.ps1 -KeepLast 14            # conservar 14 backups
```

Para eliminar ambas tareas programadas:
```powershell
.\setup_backup_task.ps1 -Remove
```

| Tarea | Hora por defecto | Destino |
|---|---|---|
| Archivos | 02:00 AM | `backups/backup_<ts>/` |
| Base de datos | 02:30 AM | `backups/db/db_backup_<ts>.zip` |
