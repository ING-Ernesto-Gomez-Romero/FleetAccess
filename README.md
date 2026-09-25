# Fleet Access

Sistema de escritorio para registrar y consultar entradas de unidades en un
centro de distribucion. Es una demostracion educativa creada con datos
ficticios y sin relacion con ninguna empresa real.

## Funciones principales

- Registro de unidad, conductor, empresa, destino, carga y horario.
- Validacion de campos obligatorios y datos numericos.
- Busqueda por folio, placa, conductor o empresa.
- Filtros por estado de la unidad.
- Cambio de estado entre `En patio` y `Salida registrada`.
- Persistencia mediante SQLite.
- Exportacion de resultados a CSV y PDF.
- Interfaz con tabla desplazable y resumen operativo.

## Tecnologias

- Python 3
- Tkinter y ttk
- SQLite
- ReportLab

## Instalacion

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

En macOS o Linux, activa el entorno con `source .venv/bin/activate`.

La base de datos y los reportes se crean localmente y estan excluidos del
control de versiones.

## Estructura

```text
FleetAccess-Demo/
|-- app.py
|-- requirements.txt
|-- .gitignore
|-- LICENSE
|-- README.md
`-- exports/
```

## Autor

Ernesto Gomez Romero  
[LinkedIn](https://www.linkedin.com/in/ernesto-g%C3%B3mez-romero-4398a541a/)

