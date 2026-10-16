# Empresas como Pilou

Busca empresas parecidas a [Pilou](https://www.pilou.io), una fintech mexicana de inversión para mujeres y principiantes, y las publica en una página web con dos pestañas: **Mexicanas** e **Internacionales**.

## Cómo funciona

- Todos los días a las 7:00 (hora de Ciudad de México), una GitHub Action lanza la búsqueda, puntúa cada empresa de 0 a 100 según su parecido con Pilou y publica la página.
- Cada vez que recargas la página, ves los resultados de la última búsqueda. Las empresas encontradas en los últimos 7 días llevan la etiqueta **Nueva**.
- Los resultados se van acumulando en `site/data/empresas.json`, así que la lista crece con cada búsqueda.
- Para buscar en ese momento, ve a **Actions → Buscar empresas como Pilou → Run workflow**.

Una empresa cuenta como mexicana si su dominio termina en `.mx`, si su web habla sobre todo de México o si menciona la CNBV, la CONDUSEF o la CDMX.

## Uso local

```
pip install -r requirements.txt
python buscar_empresas_como_pilou.py --json site/data/empresas.json
```

Opciones: `--resultados N` (resultados por búsqueda), `--minimo N` (parecido mínimo), `--busqueda "..."` (búsqueda propia, se puede repetir), `--salida nombre`.
