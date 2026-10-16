# Empresas como Pilou

Script que busca empresas parecidas a [Pilou](https://www.pilou.io), una fintech mexicana de inversión para mujeres y principiantes, y las guarda en CSV y Excel ordenadas por parecido (0-100).

## Uso local

```
pip install -r requirements.txt
python buscar_empresas_como_pilou.py
```

Opciones: `--resultados N` (resultados por búsqueda), `--minimo N` (parecido mínimo), `--busqueda "..."` (búsqueda propia, repetible), `--salida nombre`.

## Desde GitHub

Ve a la pestaña **Actions**, abre **Buscar empresas como Pilou** y pulsa **Run workflow**. Cuando termine, el CSV y el Excel quedan guardados en la carpeta `resultados/` del repo (y también en *Artifacts* de la ejecución).
