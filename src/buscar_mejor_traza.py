"""
Traza de Ruptura Au-Au — Figura calidad poster A0
Mejoras aplicadas:
  - Fuentes más grandes (22pt etiquetas, 20pt ticks)
  - Título más limpio sin nombre de archivo
  - Sombreado de plateaus más visible
  - Líneas de referencia más gruesas y claras
  - Leyenda mejor posicionada
  - Fondo blanco garantizado
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import glob
import os

matplotlib.rcParams['font.family'] = 'serif'

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "..", "data", "raw")
FIG_DIR   = os.path.join(BASE_DIR, "..", "figures")
V_OUT_1G0 = 0.200 * 100e3 * 77.5e-6   # 1.55 V

TOLERANCIA = 0.15
MIN_PUNTOS = 5


def leer_txt(filepath):
    valores = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                try:
                    valores.append(float(linea.replace(',', '.')))
                except ValueError:
                    continue
    if len(valores) < 50:
        return None
    return np.array(valores) / V_OUT_1G0


def score_traza(g):
    if g is None:
        return -1, {}
    pts = {}
    for n in [1, 2, 3]:
        pts[n] = int(np.sum(np.abs(g - n) < TOLERANCIA))
    if any(v < MIN_PUNTOS for v in pts.values()):
        return -1, pts
    if np.median(g[:10]) < 2.5:
        return -1, pts
    if np.median(g[-10:]) > 0.5:
        return -1, pts
    score = pts[1] * pts[2] * pts[3]
    return score, pts


def figura_traza(g, rank=1):
    tiempo = np.arange(len(g)) * 2e-3   # µs → ms

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    # Señal
    ax.plot(tiempo, g, color='#4878CF', linewidth=1.0, alpha=0.88, zorder=2)

    colores = {1: '#CC0000', 2: '#228B22', 3: '#E07B00'}
    labels  = {1: r'$1G_0$', 2: r'$2G_0$', 3: r'$3G_0$'}

    for n, color in colores.items():
        # Línea de referencia más gruesa
        ax.axhline(y=n, color=color, linestyle='--',
                   alpha=0.85, linewidth=2.2,
                   label=labels[n], zorder=3)

        # Sombreado de plateaus más visible
        mascara = np.abs(g - n) < TOLERANCIA
        idx = np.where(mascara)[0]
        if len(idx) > 0:
            breaks = np.where(np.diff(idx) > 5)[0] + 1
            segmentos = np.split(idx, breaks)
            for seg in segmentos:
                if len(seg) > MIN_PUNTOS:
                    ax.axvspan(tiempo[seg[0]], tiempo[seg[-1]],
                               alpha=0.18, color=color, zorder=1)

    # ── Etiquetas de ejes: GRANDES ──────────────────────────────────
    ax.set_xlabel("Tiempo (ms)", fontsize=22, labelpad=10)
    ax.set_ylabel(r"Conductancia ($G/G_0$)", fontsize=22, labelpad=10)
    ax.tick_params(axis='both', labelsize=20, length=6, width=1.2)

    # ── Título limpio (sin nombre de archivo) ───────────────────────
    ax.set_title(
        r"Traza de Ruptura Au–Au — Plateaus Cuánticos"
        "\n"
        r"$V_{\rm bias}$ = 200 mV  |  Temperatura ambiente",
        fontsize=18, pad=12
    )

    ax.set_ylim(-0.15, min(g.max() * 1.08, 4.8))
    ax.set_xlim(left=0)

    # Leyenda con fuente grande
    ax.legend(fontsize=18, loc='upper right',
              framealpha=0.9, edgecolor='#cccccc',
              handlelength=2.0)

    ax.grid(True, alpha=0.22, linestyle=':', linewidth=0.8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.2)
    ax.spines['bottom'].set_linewidth(1.2)

    plt.tight_layout()

    for ext in ['png', 'pdf']:
        nombre = os.path.join(FIG_DIR, f"mejor_traza_rank{rank}.{ext}")
        plt.savefig(nombre, dpi=200, bbox_inches='tight', facecolor='white')
        print(f"  Guardado: {nombre}")
    plt.close()


# ── MAIN ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  BUSQUEDA DE MEJOR TRAZA - 3 PLATEAUS")
    print("=" * 60)

    carpeta  = DATA_DIR
    archivos = glob.glob(os.path.join(carpeta, "**", "*.txt"), recursive=True)
    archivos += glob.glob(os.path.join(carpeta, "*.txt"))
    archivos = sorted(set(archivos))

    print(f"\nBuscando en {len(archivos)} archivos...")

    resultados = []
    for f in archivos:
        g = leer_txt(f)
        s, pts = score_traza(g)
        if s > 0:
            resultados.append((s, pts, f, g))

    resultados.sort(key=lambda x: -x[0])
    print(f"Trazas con los 3 plateaus: {len(resultados)} / {len(archivos)}")

    if not resultados:
        print("\nNo se encontraron trazas con los 3 plateaus.")
        print("Prueba aumentando TOLERANCIA (ej: 0.20) o bajando MIN_PUNTOS (ej: 3).")
    else:
        print(f"\nTOP 10:")
        for i, (s, pts, f, g) in enumerate(resultados[:10]):
            print(f"  {i+1}. score={s:.0f}  "
                  f"@1G0={pts[1]}  @2G0={pts[2]}  @3G0={pts[3]}  "
                  f"{os.path.basename(f)}")

        print("\nGenerando figuras de las 10 mejores trazas...")
        for i, (s, pts, f, g) in enumerate(resultados[:10]):
            figura_traza(g, rank=i + 1)

    print("\n" + "=" * 60)
    print("  Listo. Usa mejor_traza_rank1.png para el poster.")
    print("=" * 60)