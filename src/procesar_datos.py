"""
Histograma MCBJ Au-Au — Figura calidad poster A0
Mejoras aplicadas:
  - Eje Y SIN números NI ticks (escala arbitraria)
  - Fuentes grandes (22pt etiquetas, 20pt ticks X)
  - Gaussianas más gruesas (3pt)
  - Leyenda con µ y sigma formateados claramente
  - Líneas de referencia nGo más visibles
  - Fondo blanco garantizado
  - Título compacto de dos líneas
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from scipy.optimize import curve_fit
from scipy.ndimage import uniform_filter1d
import os
import glob
import pandas as pd

matplotlib.rcParams['font.family']    = 'serif'
matplotlib.rcParams['axes.linewidth'] = 1.5

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "..", "data", "raw")
FIG_DIR   = os.path.join(BASE_DIR, "..", "figures")
V_BIAS    = 0.200
RF        = 100e3
G0        = 77.5e-6
V_OUT_1G0 = V_BIAS * RF * G0    # 1.55 V

# ── Parámetros del filtro ─────────────────────────────────────────────
MONOTONIA_UMBRAL  = 0.30
PICOS_BUSCAR      = [1.0, 2.0, 3.0]
VENTANA_G0        = 0.25
VENTANA_PUNTOS    = 12
STD_MAX           = 0.06
MIN_PUNTOS_CONSEC = 6


# ── Lectura ───────────────────────────────────────────────────────────

def leer_traza(filepath):
    valores = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                try:
                    valores.append(float(linea.replace(',', '.')))
                except ValueError:
                    continue
    if len(valores) < 20:
        return None
    return np.array(valores) / V_OUT_1G0


def encontrar_todos_txt(carpeta):
    pat1 = os.path.join(carpeta, "**", "*.txt")
    pat2 = os.path.join(carpeta, "*.txt")
    return sorted(set(glob.glob(pat1, recursive=True) + glob.glob(pat2)))


# ── Filtro ────────────────────────────────────────────────────────────

def es_monotona_pura(g):
    diffs = np.diff(g)
    return np.sum(diffs > 0) / len(diffs) < MONOTONIA_UMBRAL


def tiene_plateau_cerca_de_entero(g):
    for pico in PICOS_BUSCAR:
        cerca = np.where(np.abs(g - pico) < VENTANA_G0)[0]
        if len(cerca) < VENTANA_PUNTOS + MIN_PUNTOS_CONSEC:
            continue
        g_zona = g[cerca]
        consec = 0
        for i in range(len(g_zona) - VENTANA_PUNTOS):
            if np.std(g_zona[i:i + VENTANA_PUNTOS]) < STD_MAX:
                consec += 1
                if consec >= MIN_PUNTOS_CONSEC:
                    return True
            else:
                consec = 0
    return False


def pasar_filtro(g):
    if g is None:
        return False, "lectura_fallida"
    if es_monotona_pura(g):
        return False, "monotona_pura"
    if not tiene_plateau_cerca_de_entero(g):
        return False, "sin_plateau_en_entero"
    return True, "ok"


# ── Histograma ────────────────────────────────────────────────────────

def construir_histograma(todas_g, bins=300, rango=(0.1, 4.5)):
    todos = np.concatenate(todas_g)
    counts, edges = np.histogram(todos, bins=bins, range=rango)
    centros = (edges[:-1] + edges[1:]) / 2
    return centros, counts


# ── Ajuste gaussiano ──────────────────────────────────────────────────

def ajuste_gaussiano(x, y, pico_est, ventana=0.40):
    mascara = np.abs(x - pico_est) < ventana
    x_loc, y_loc = x[mascara], y[mascara]
    if len(x_loc) < 5:
        return None

    def gauss(x, amp, mu, sigma):
        return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)

    try:
        p0 = [y_loc.max(), pico_est, 0.12]
        popt, pcov = curve_fit(gauss, x_loc, y_loc, p0=p0, maxfev=5000)
        perr = np.sqrt(np.diag(pcov))
        return popt, perr
    except Exception:
        return None


# ── Figura poster ─────────────────────────────────────────────────────

def figura_poster(centros, counts, n_trazas):
    """
    Histograma para poster A0:
    - Eje Y sin números (escala arbitraria)
    - Fuentes 22pt en etiquetas, 20pt en ticks X
    - Gaussianas gruesas (3pt)
    - Barras con buen contraste
    - Fondo blanco
    """
    counts_suave = uniform_filter1d(counts.astype(float), size=5)

    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    # Barras del histograma
    ax.bar(
        centros, counts_suave,
        width=centros[1] - centros[0],
        color='#4878CF', alpha=0.70,
        label='Datos (suavizado 5-bin)',
        zorder=2
    )

    picos   = [1.0, 2.0, 3.0]
    colores = ['#CC0000', '#228B22', '#E07B00']
    x_fino  = np.linspace(0.1, 4.5, 3000)

    print(f"\n  POSICION DE PICOS:")
    print(f"  {'Esperado':>10} {'µ medido':>10} {'±err_µ':>8} {'σ':>8}")

    for pico, color in zip(picos, colores):
        res = ajuste_gaussiano(centros, counts_suave, pico)
        if res is not None:
            (amp, mu, sigma), (_, err_mu, _) = res
            sigma = abs(sigma)
            y_fit = amp * np.exp(-0.5 * ((x_fino - mu) / sigma) ** 2)

            # Etiqueta de leyenda clara
            etiqueta = (
                f"${pico:.0f}G_0$: "
                f"$\\mu={mu:.3f}\\pm{err_mu:.3f}$, "
                f"$\\sigma={sigma:.2f}$"
            )
            ax.plot(x_fino, y_fit, color=color,
                    linewidth=3.0, zorder=4, label=etiqueta)

            print(f"  {pico:.1f} G0  {mu:>10.4f}  ±{err_mu:.4f}  {sigma:>8.4f}")

    # Líneas verticales de referencia
    for g_int in [1, 2, 3]:
        ax.axvline(x=g_int, linestyle='--', color='#888888',
                   alpha=0.50, linewidth=1.5, zorder=3)

    # ── Etiquetas: GRANDES ──────────────────────────────────────────
    ax.set_xlabel(r"Conductancia ($G/G_0$)", fontsize=22, labelpad=10)

    # Eje Y: solo etiqueta, SIN números ni ticks
    ax.set_ylabel("Cuentas (escala arbitraria)", fontsize=22, labelpad=10)
    ax.set_yticks([])           # sin ticks
    ax.set_yticklabels([])      # sin números

    # Ticks del eje X grandes
    ax.tick_params(axis='x', labelsize=20, length=6, width=1.2)
    ax.tick_params(axis='y', length=0)

    # ── Título compacto ─────────────────────────────────────────────
    ax.set_title(
        f"Histograma de Conductancia — Contacto Atómico Au–Au\n"
        f"$N = {n_trazas}$ trazas con plateau  |  "
        f"$V_{{\\rm bias}}$ = {V_BIAS*1000:.0f} mV",
        fontsize=17, pad=12
    )

    ax.set_xlim(0.1, 4.5)
    ax.set_ylim(bottom=0)

    # Leyenda con fuente grande
    ax.legend(fontsize=15, framealpha=0.92,
              edgecolor='#cccccc', loc='upper right')

    ax.grid(True, alpha=0.22, linestyle=':', linewidth=0.8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)   # ocultar eje Y (no hay números)
    ax.spines['bottom'].set_linewidth(1.2)

    plt.tight_layout()

    for ext in ['png', 'pdf']:
        path = os.path.join(FIG_DIR, f"figura_histograma_poster.{ext}")
        plt.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
        print(f"  Guardado: {path}")

    plt.close()
    print("Figura histograma guardada.")


# ── Procesamiento ─────────────────────────────────────────────────────

def procesar_trazas(carpeta=DATA_DIR):
    archivos = encontrar_todos_txt(carpeta)
    print(f"\nArchivos .txt encontrados: {len(archivos)}")

    if not archivos:
        print("ERROR: no se encontraron archivos .txt")
        return None, None, None

    todas_g, archivos_validos = [], []
    conteos = {}

    for f in archivos:
        try:
            g = leer_traza(f)
            ok, razon = pasar_filtro(g)
            conteos[razon] = conteos.get(razon, 0) + 1
            if ok:
                todas_g.append(g)
                archivos_validos.append(f)
        except Exception:
            conteos["error"] = conteos.get("error", 0) + 1

    total     = sum(conteos.values())
    aceptadas = conteos.get("ok", 0)
    print(f"\nResumen ({total} trazas):")
    for razon, n in conteos.items():
        print(f"  {razon:30s}: {n:5d}  ({100*n/total:.1f}%)")
    print(f"\n  => Tasa de aceptación: {100*aceptadas/total:.1f}%")

    if not todas_g:
        print("\nERROR: filtro rechazó todas las trazas.")
        return None, None, None

    centros, counts = construir_histograma(todas_g)

    df = pd.DataFrame({'Conductancia_G0': centros, 'Counts': counts})
    df.to_csv(os.path.join(FIG_DIR, "histograma_filtrado_v2.csv"), index=False)

    return centros, counts, archivos_validos


# ── MAIN ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  MCBJ — CONTACTOS ATOMICOS Au-Au")
    print("  Histograma calidad poster A0")
    print("=" * 60)

    centros, counts, archivos_validos = procesar_trazas()

    if centros is not None:
        figura_poster(centros, counts, len(archivos_validos))

    print("\n" + "=" * 60)
    print("  ARCHIVOS GENERADOS:")
    print("  - figura_histograma_poster.png / .pdf")
    print("  - histograma_filtrado_v2.csv")
    print("=" * 60)