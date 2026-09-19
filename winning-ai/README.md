# Winning AI

Winning AI es un proyecto diseñado para calcular equipos probables que pueden ganar en la liga de fantasy de Winning de Argentina. El objetivo es proporcionar tres tipos de equipos basados en diferentes estrategias de selección de jugadores.

## Estructura del Proyecto

El proyecto está organizado de la siguiente manera:

- **src/**: Contiene el código fuente de la aplicación.
  - **index.ts**: Punto de entrada de la aplicación.
  - **config/**: Configuraciones del proyecto, incluyendo la conexión a la API de sofascore.
  - **data/**: Archivos que contienen datos sobre jugadores y partidos.
    - **players.ts**: Lista de jugadores con estadísticas relevantes.
    - **matches.ts**: Información sobre los partidos.
    - **sofascore.ts**: Manejo de datos desde la API de sofascore.
  - **scoring/**: Implementación del sistema de puntuación de Winning.
    - **winning-score.ts**: Cálculo de puntos para los jugadores.
  - **predictions/**: Funciones para calcular equipos.
    - **safe-team.ts**: Cálculo del equipo más seguro.
    - **risky-team.ts**: Cálculo del equipo más arriesgado.
    - **balanced-team.ts**: Cálculo de un equipo intermedio.
    - **lineup-validator.ts**: Validación de alineaciones.
  - **types/**: Tipos e interfaces utilizados en el proyecto.
  - **utils/**: Funciones utilitarias para cálculos estadísticos.

- **tests/**: Contiene pruebas unitarias para asegurar el correcto funcionamiento del código.
  - **scoring.test.ts**: Pruebas para el sistema de puntuación.
  - **predictions.test.ts**: Pruebas para las funciones de predicción.

- **package.json**: Configuración de npm, incluyendo dependencias y scripts.
- **tsconfig.json**: Configuración para TypeScript.

## Instalación

Para instalar las dependencias del proyecto, ejecute el siguiente comando:

```
npm install
```

## Ejecución

Para ejecutar la aplicación, utilice el siguiente comando:

```
npm start
```

## Contribuciones

Las contribuciones son bienvenidas. Si desea contribuir, por favor abra un issue o envíe un pull request.

## Licencia

Este proyecto está bajo la licencia MIT.