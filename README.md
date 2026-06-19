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
