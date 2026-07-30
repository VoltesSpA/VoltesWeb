#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════
#  ACTUALIZADOR AUTOMATICO DE PARAMETROS LEGALES
#
#  Descarga el PDF mensual de Indicadores Previsionales de Previred,
#  extrae el ingreso minimo y los topes imponibles, y actualiza
#  parametros.json SOLO si detecta un cambio real y valido.
#
#  Se ejecuta desde GitHub Actions. Filosofia de diseño:
#    - Ante cualquier duda, NO modifica nada.
#    - Si el PDF cambia de formato, falla en voz alta (avisa por correo)
#      en vez de escribir datos incorrectos.
#    - Nunca borra entradas historicas: solo agrega.
# ═══════════════════════════════════════════════════════════════════════

import io
import os
import re
import sys
import json
import datetime
import urllib.request

ARCHIVO = "parametros.json"
TIMEOUT = 30

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
MES_NUM = {m.lower(): i + 1 for i, m in enumerate(MESES)}

# Rangos de cordura. Un valor fuera de esto se descarta sin tocar nada.
LIMITES = {
    "imm":               (300_000, 3_000_000),
    "tope_imponible_uf": (60.0, 200.0),
    "tope_afc_uf":       (90.0, 300.0),
    "sis":               (0.3, 6.0),
}


def log(msg):
    print(msg, flush=True)


# ─── Descarga del PDF ──────────────────────────────────────────────────

def urls_candidatas(anio, mes):
    """Previred no usa un nombre 100% constante: cambia mayusculas y a
    veces agrega sufijos (v2, V2, -1). Se prueban las variantes conocidas."""
    nombre = MESES[mes - 1]
    base = "https://www.previred.com/wp-content/uploads"
    variantes = []
    for carpeta_mes in (f"{mes:02d}", f"{(mes % 12) + 1:02d}"):   # mes y mes siguiente
        for nom in (nombre, nombre.lower()):
            for suf in ("", "v2", "V2", "-1", "-V2", "v3"):
                variantes.append(
                    f"{base}/{anio}/{carpeta_mes}/"
                    f"Indicadores-Previsionales-Previred-{nom}-{anio}{suf}.pdf")
    # sin duplicados, conservando el orden
    vistas, limpio = set(), []
    for u in variantes:
        if u not in vistas:
            vistas.add(u)
            limpio.append(u)
    return limpio


def descargar(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; VoltesBot/1.0)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        if r.status != 200:
            return None
        return r.read()


def texto_del_pdf(datos):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(datos)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception:
        pass
    try:
        from pypdf import PdfReader
        lector = PdfReader(io.BytesIO(datos))
        return "\n".join((p.extract_text() or "") for p in lector.pages)
    except Exception as e:
        log(f"  No se pudo leer el PDF: {e}")
        return ""


def obtener_texto_previred():
    """Busca el PDF del mes actual; si no esta, prueba el mes anterior."""
    hoy = datetime.date.today()
    intentos = [(hoy.year, hoy.month)]
    prev = hoy.replace(day=1) - datetime.timedelta(days=1)
    intentos.append((prev.year, prev.month))

    for anio, mes in intentos:
        for url in urls_candidatas(anio, mes):
            try:
                datos = descargar(url)
            except Exception:
                continue
            if not datos or len(datos) < 5000:
                continue
            texto = texto_del_pdf(datos)
            if texto and "Indicadores Previsionales" in texto:
                log(f"  PDF encontrado: {url}")
                return texto, url, datetime.date(anio, mes, 1)
    return "", "", None


# ─── Extraccion de valores ─────────────────────────────────────────────

def a_numero(txt):
    if txt is None:
        return None
    s = str(txt).strip().replace("$", "").replace(" ", "").replace("\u00a0", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def a_uf(txt):
    if txt is None:
        return None
    s = str(txt).strip().replace(" ", "").replace("\u00a0", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def extraer_imm(texto):
    """Ingreso minimo de trabajadores dependientes."""
    patrones = [
        # Formato en prosa (meses con anuncio de cambio)
        r"Sueldo\s+M[ií]nimo\s+Trab\.?\s+Dependientes\s+e\s+Independientes\s*:?\s*\$?\s*([\d.,]+)",
        r"Trabajadores?\s+Dependientes\s+e\s+Independientes\s*:?\s*\$?\s*([\d.,]+)",
        r"Nuevo\s+ingreso\s+m[ií]nimo\s+mensual\s*:?.{0,80}?\$?\s*([\d.]{7,10})",
        r"Trabajadores\s+Dependientes\s*\$?\s*([\d.]{7,10})",
        # Formato de tabla: el monto puede venir mas abajo, en otra columna
        r"Dependientes\s+e\s+Independientes\s*:?[^\d$]{0,200}?\$\s*([\d.]{7,10})",
        r"Trab\.?\s+Dependientes[^\d$]{0,200}?\$\s*([\d.]{7,10})",
    ]
    for p in patrones:
        m = re.search(p, texto, re.I | re.S)
        if m:
            v = a_numero(m.group(1))
            if v and LIMITES["imm"][0] <= v <= LIMITES["imm"][1]:
                return int(v)
    return None


def extraer_tope_afp(texto):
    """Tope imponible de AFP y salud, en UF."""
    patrones = [
        r"afiliados?\s+a\s+una\s+AFP\s*\(\s*([\d.,]+)\s*UF\s*\)",
        r"Para\s+Afiliados?\s+AFP\s*:?\s*([\d.,]+)\s*UF",
        r"Tope\s+imponible.{0,60}?AFP\s*:?\s*([\d.,]+)\s*UF",
    ]
    for p in patrones:
        m = re.search(p, texto, re.I | re.S)
        if m:
            v = a_uf(m.group(1))
            if v and LIMITES["tope_imponible_uf"][0] <= v <= LIMITES["tope_imponible_uf"][1]:
                return v
    return None


def extraer_tope_afc(texto):
    """Tope imponible del seguro de cesantia, en UF."""
    patrones = [
        r"Seguro\s+de\s+Cesant[ií]a\s*\(\s*([\d.,]+)\s*UF\s*\)",
        r"Para\s+Seguro\s+de\s+Cesant[ií]a\s*:?\s*([\d.,]+)\s*UF",
    ]
    for p in patrones:
        m = re.search(p, texto, re.I | re.S)
        if m:
            v = a_uf(m.group(1))
            if v and LIMITES["tope_afc_uf"][0] <= v <= LIMITES["tope_afc_uf"][1]:
                return v
    return None


def pdf_anuncia_cambio(texto):
    """True si este PDF trae un anuncio de cambio del ingreso minimo.

    Previred usa dos formatos distintos:
      - Meses CON cambio: bloque "IMPORTANTE" con los montos en prosa,
        del estilo "Sueldo Minimo Trab. Dependientes...: $ 553.553".
      - Meses normales: tabla de dos columnas donde la etiqueta queda
        separada del monto, por lo que no se puede leer con expresiones
        regulares simples.

    Solo interesa leer el IMM en los meses que anuncian cambio: si no hay
    anuncio, es porque el monto sigue igual y no hay nada que detectar."""
    señales = [
        r"aplican\s+desde\s+las?\s+remuneraciones?",
        r"[Nn]uevo\s+[Ii]ngreso\s+[Mm][ií]nimo",
        r"nuevos\s+valores\s+para\s+ingreso",
        r"se\s+public[oó]\s+en\s+el\s+Diario\s+Oficial",
    ]
    return any(re.search(p, texto, re.I) for p in señales)


def mes_remuneraciones(texto, fallback):
    """Mes de remuneraciones que cubre el PDF.

    El encabezado dice, por ejemplo:
      "Para Cotizaciones a Pagar en Agosto 2026 (Remuneraciones Julio 2026)"
    El SIS rige desde el mes de las REMUNERACIONES (julio), no desde el
    mes en que se paga (agosto)."""
    m = re.search(r"Remuneraciones\s+([a-záéíóú]+)\s*(?:de\s+)?(\d{4})", texto, re.I)
    if m:
        mes = MES_NUM.get(m.group(1).lower())
        if mes:
            return datetime.date(int(m.group(2)), mes, 1)
    return fallback


def extraer_sis(texto):
    """Tasa del SIS, en porcentaje.

    CUIDADO: el PDF de Previred trae tambien la cotizacion de Trabajo
    Pesado (2%) y Trabajo Menos Pesado (1%), que NO son el SIS. Por eso
    todos los patrones se anclan en 'Invalidez y Sobrevivencia' o en la
    sigla SIS, y jamas en un porcentaje suelto."""
    patrones = [
        # "Nueva Tasa del Seguro de Invalidez y Sobrevivencia (SIS)
        #  Remuneraciones Julio: 2,00%"  <- formato real de Previred
        r"Invalidez\s+y\s+Sobrevivencia\s*\(?\s*SIS\s*\)?[^%\d]{0,70}?([\d.,]+)\s*%",
        r"Invalidez\s+y\s+Sobrevivencia\s*\(?\s*SIS\s*\)?\s*:?\s*([\d.,]+)\s*%",
        r"Tasa\s+del\s+Seguro\s+de\s+Invalidez\s+y\s+Sobrevivencia[^\d%]{0,40}?([\d.,]+)\s*%",
        r"Tasa\s+SIS\s*:?\s*([\d.,]+)\s*%",
        r"\bSIS\b[^\d%\n]{0,30}?([\d.,]+)\s*%",
        # Formato de tabla: el valor puede quedar unas lineas mas abajo
        r"Invalidez\s+y\s+Sobrevivencia[^%]{0,150}?([\d,]{3,5})\s*%",
    ]
    for p in patrones:
        m = re.search(p, texto, re.I | re.S)
        if m:
            v = a_uf(m.group(1))
            if v and LIMITES["sis"][0] <= v <= LIMITES["sis"][1]:
                return v
    return None


def extraer_afc(texto):
    """Lee las tasas del seguro de cesantia del PDF de Previred.

    El PDF las muestra en una tabla apretada, del estilo:
        4,2% R.I.  2,8% R.I.  Empleador  Trabajador
        2,4% R.I.  0,6% R.I.  3,0% R.I.  -  0,8% R.I.  -  4%

    Ahi no hay etiquetas confiables por columna, asi que NO se confia en
    las posiciones. La estrategia es distinta: se recogen todos los
    porcentajes de la zona del AFC y se busca la combinacion que cumple
    los invariantes que la Ley 19.728 garantiza:

        indefinido_empleador + indefinido_trabajador = 3,0
        plazo_fijo_empleador = 3,0
        sobre_11_anios entre 0,1 y 2,0

    Si ninguna combinacion los cumple, se devuelve None y no se toca nada.
    """
    # 1) Zonas donde buscar, de la mas acotada a la mas amplia.
    #    En el PDF de julio 2026 los porcentajes salen ANTES del texto
    #    "afc.cl", asi que no basta mirar hacia adelante.
    zonas = []
    m = re.search(r"Seguro\s+de\s+Cesant[ií]a(.{0,800})", texto, re.I | re.S)
    if m:
        zonas.append(m.group(1))
    m = re.search(r"afc\.cl", texto, re.I)
    if m:
        # ventana a ambos lados del ancla
        zonas.append(texto[max(0, m.start() - 700): m.end() + 200])
    m = re.search(r"Tipo\s+de\s+Contrato(.{0,800})", texto, re.I | re.S)
    if m:
        zonas.append(m.group(1))
    # Ultimo recurso: todo el documento. Es seguro porque lo que protege
    # no es la zona sino el invariante legal que se valida mas abajo.
    zonas.append(texto)

    for zona in zonas:
        r = _combinacion_afc(zona)
        if r:
            return r
    return None


def _combinacion_afc(zona):
    """Busca en un texto la combinacion de tasas que cumple la Ley 19.728."""
    crudos = re.findall(r"(\d{1,2}[.,]\d{1,2})\s*%", zona)
    valores = []
    for x in crudos:
        v = a_uf(x)
        if v is not None and 0.05 <= v <= 6.0:
            valores.append(round(v, 2))
    if len(valores) < 3:
        return None

    presentes = set(valores)

    # 3) Buscar el par indefinido que sume 3,0 exacto
    par = None
    for emp in sorted(presentes, reverse=True):
        for trab in sorted(presentes):
            if trab >= emp:
                continue
            if abs((emp + trab) - 3.0) < 0.001:
                par = (emp, trab)
                break
        if par:
            break
    if not par:
        return None

    # 4) Plazo fijo debe ser 3,0 y tiene que aparecer en el PDF
    if not any(abs(v - 3.0) < 0.001 for v in valores):
        return None

    # 5) Tasa del Fondo Solidario sobre 11 anios.
    #    Tiene que quedar ENTRE el aporte del trabajador y el del
    #    empleador (0,6 < 0,8 < 2,4). Ese rango descarta la comision de
    #    AFP (0,1%), que si no se colaria cuando se busca en todo el PDF.
    #    Ademas se limita a 1,5% como maximo: el aporte al Fondo Solidario
    #    ha sido 0,8% desde 2002 y un valor mas alto seria implausible.
    #    Si no aparece nada plausible se devuelve None y NO se toca la
    #    tabla: es mejor quedarse con el valor conocido que publicar uno
    #    tomado de otra parte del PDF.
    sobre11 = None
    for v in sorted(presentes):
        if par[1] < v < par[0] and v <= 1.5:
            sobre11 = v
            break
    if sobre11 is None:
        return None

    return {
        "indefinido_empleador": par[0],
        "indefinido_trabajador": par[1],
        "plazo_fijo_empleador": 3.0,
        "plazo_fijo_trabajador": 0.0,
        "sobre_11_anios_empleador": sobre11,
        "sobre_11_anios_trabajador": 0.0,
    }


def verificar_afc(nuevo, anterior):
    """Los invariantes de la Ley 19.728 deben cumplirse siempre."""
    fallas = []
    ie = nuevo["indefinido_empleador"]
    it = nuevo["indefinido_trabajador"]

    if abs((ie + it) - 3.0) > 0.001:
        fallas.append(f"invariante roto: {ie} + {it} = {round(ie+it,2)}, deberia ser 3,0")
    if abs(nuevo["plazo_fijo_empleador"] - 3.0) > 0.001:
        fallas.append(f"plazo fijo deberia ser 3,0 y salio {nuevo['plazo_fijo_empleador']}")
    if ie <= it:
        fallas.append(f"el empleador ({ie}) no puede aportar menos que el trabajador ({it})")
    if not (0.1 <= nuevo["sobre_11_anios_empleador"] <= 2.0):
        fallas.append(f"tasa sobre 11 anios fuera de rango: {nuevo['sobre_11_anios_empleador']}")
    return fallas


def extraer_vigencia(texto, fallback):
    """Busca 'aplican desde las remuneraciones <mes> <anio>'.

    Es el dato mas delicado: define desde cuando rige el monto nuevo."""
    m = re.search(
        r"aplican\s+desde\s+las?\s+remuneraciones?\s+([a-záéíóú]+)\s*(\d{4})",
        texto, re.I)
    if m:
        mes = MES_NUM.get(m.group(1).lower())
        if mes:
            return datetime.date(int(m.group(2)), mes, 1), True
    return fallback, False


# ─── Verificaciones cruzadas ───────────────────────────────────────────
#  Sin revision humana, el rango por si solo no basta: dentro del mismo
#  PDF hay varios montos plausibles (casa particular, menores de 18,
#  fines no remuneracionales). Estas comprobaciones descartan que se
#  haya tomado el numero equivocado.

def verificar_imm(texto, valor, anterior):
    """Confirma que el IMM extraido es el de trabajadores dependientes."""
    fallas = []

    # 1) El sueldo minimo en Chile nunca baja
    if anterior and valor < anterior:
        fallas.append(f"el IMM bajaria de {anterior} a {valor}")

    # 2) Un alza sobre 25% no ha ocurrido nunca; seria un error de lectura
    if anterior and valor > anterior * 1.25:
        fallas.append(f"alza irreal: {anterior} -> {valor}")

    # 3) NO debe coincidir con los otros minimos del mismo PDF
    otros = {
        "menores de 18 / mayores de 65":
            r"Menores\s+de\s+18\s+y\s+Mayores\s+de\s+65[^$]{0,30}\$?\s*([\d.]+)",
        "fines no remuneracionales":
            r"[Ff]ines\s+no\s+[Rr]emuneracionales\s*:?\s*\$?\s*([\d.]+)",
    }
    for etiqueta, patron in otros.items():
        m = re.search(patron, texto, re.I)
        if m:
            v = a_numero(m.group(1))
            if v and abs(v - valor) < 1:
                fallas.append(f"el valor coincide con el minimo de {etiqueta}")

    # 4) Debe aparecer junto a la palabra "Dependientes"
    cerca = re.search(
        r"Dependientes[^$\n]{0,60}\$?\s*" + re.escape(f"{valor:,}".replace(",", ".")),
        texto, re.I)
    if not cerca:
        # tolerante: puede venir sin separadores de miles
        cerca = re.search(r"Dependientes[^$\n]{0,60}\$?\s*" + str(valor), texto, re.I)
    if not cerca:
        fallas.append("no aparece asociado a 'Dependientes'")

    return fallas


def verificar_sis(valor, anterior):
    """El SIS sube y baja segun la licitacion publica.

    Historial reciente: 1,54% (ene-2026) -> 1,62% (abr-2026) -> 2,00% (jul-2026).
    Los saltos pueden ser de varias decimas, asi que el control es amplio.

    NO se descarta ningun valor puntual por sospecha de ser otra cosa: la
    proteccion contra confundirlo con la cotizacion de Trabajo Pesado (2%)
    esta en los patrones de extraer_sis(), que se anclan siempre en
    'Invalidez y Sobrevivencia' o en la sigla SIS."""
    fallas = []
    if anterior and abs(valor - anterior) > 1.5:
        fallas.append(f"salto excesivo del SIS: {anterior}% -> {valor}%")
    return fallas


def verificar_tope(nombre, valor, anterior, subida_max=1.20):
    """Los topes imponibles suben cada año; nunca bajan."""
    fallas = []
    if anterior:
        if valor < anterior:
            fallas.append(f"{nombre} bajaria de {anterior} a {valor} UF")
        if valor > anterior * subida_max:
            fallas.append(f"{nombre} sube demasiado: {anterior} -> {valor} UF")
    return fallas


# ─── Comparacion y actualizacion ───────────────────────────────────────

def vigente(lista, clave):
    if not lista:
        return None
    hoy = datetime.date.today().isoformat()
    actual = None
    for it in lista:
        if it.get("desde", "") <= hoy:
            actual = it
    return (actual or lista[-1]).get(clave)


def main():
    if not os.path.exists(ARCHIVO):
        log(f"ERROR: no existe {ARCHIVO}")
        return 1

    with open(ARCHIVO, encoding="utf-8") as f:
        p = json.load(f)

    log("Buscando el PDF de indicadores de Previred...")
    texto, url, mes_pdf = obtener_texto_previred()
    if not texto:
        log("ERROR: no se encontro ningun PDF de Previred.")
        log("       Puede que cambiaran la URL. Revisar manualmente.")
        return 2

    imm_pdf = extraer_imm(texto)
    afp_pdf = extraer_tope_afp(texto)
    afc_pdf = extraer_tope_afc(texto)
    sis_pdf = extraer_sis(texto)
    afc_tasas = extraer_afc(texto)   # OJO: distinto de afc_pdf (que es el tope en UF)

    anuncia = pdf_anuncia_cambio(texto)

    log(f"  IMM leido      : {imm_pdf}")
    log(f"  Tope AFP leido : {afp_pdf}")
    log(f"  Tope AFC leido : {afc_pdf}")
    log(f"  Tasa SIS leida : {sis_pdf}")
    if afc_tasas:
        log(f"  AFC leido      : indefinido {afc_tasas['indefinido_empleador']}% + "
            f"{afc_tasas['indefinido_trabajador']}%  |  plazo fijo "
            f"{afc_tasas['plazo_fijo_empleador']}%  |  11+ anios "
            f"{afc_tasas['sobre_11_anios_empleador']}%")
    else:
        log("  AFC leido      : no legible (se mantiene la tabla actual)")
    log(f"  Anuncia cambio : {'SI' if anuncia else 'no'}")

    if afp_pdf is None and afc_pdf is None and sis_pdf is None:
        log("ERROR: no se pudieron leer los topes imponibles ni el SIS.")
        log("       El PDF cambio de formato. Revisar el script.")
        return 3

    # El IMM solo se puede leer cuando el PDF trae el bloque de anuncio.
    # En los meses normales viene en una tabla de dos columnas y queda
    # ilegible, pero eso no importa: si no hay anuncio, no hay cambio.
    if imm_pdf is None:
        if anuncia:
            log("\nERROR: el PDF ANUNCIA un cambio de ingreso minimo pero no se")
            log("       pudo leer el monto. Esto si es un problema: podria estar")
            log("       pasando por alto un reajuste.")
            log(f"       Revisar a mano: {url}")
            return 5
        log("  (mes sin anuncio de cambio: el IMM no aparece legible, es normal)")

    desde, desde_seguro = extraer_vigencia(texto, mes_pdf)
    log(f"  Vigencia       : {desde} ({'del PDF' if desde_seguro else 'estimada'})")

    cambios, rechazos = [], []

    imm_actual = vigente(p["imm"], "monto")
    afp_actual = vigente(p["tope_imponible_uf"], "valor")
    afc_actual = vigente(p["tope_afc_uf"], "valor")

    # ── IMM ──────────────────────────────────────────────────────────
    if imm_pdf is not None and imm_pdf != imm_actual:
        fallas = verificar_imm(texto, imm_pdf, imm_actual)
        if fallas:
            rechazos.append(f"IMM {imm_pdf}: " + "; ".join(fallas))
        elif not desde_seguro:
            rechazos.append(
                f"IMM {imm_pdf}: no se pudo leer la fecha de vigencia en el PDF")
        elif any(e["desde"] == desde.isoformat() for e in p["imm"]):
            log("  IMM: ya existe una entrada con esa fecha, se omite.")
        else:
            p["imm"].append({"desde": desde.isoformat(), "monto": imm_pdf,
                             "ley": "auto/previred"})
            p["imm"].sort(key=lambda e: e["desde"])
            cambios.append(f"IMM: {imm_actual} -> {imm_pdf} desde {desde}")

    # ── Tope AFP / salud ─────────────────────────────────────────────
    if afp_pdf is not None and afp_pdf != afp_actual:
        fallas = verificar_tope("tope AFP/salud", afp_pdf, afp_actual)
        if fallas:
            rechazos.append("; ".join(fallas))
        else:
            d = datetime.date(desde.year, 2, 1)   # los topes rigen desde febrero
            if not any(e["desde"] == d.isoformat() for e in p["tope_imponible_uf"]):
                p["tope_imponible_uf"].append({"desde": d.isoformat(), "valor": afp_pdf})
                p["tope_imponible_uf"].sort(key=lambda e: e["desde"])
                cambios.append(f"Tope AFP/salud: {afp_actual} -> {afp_pdf} UF desde {d}")

    # ── Tope AFC ─────────────────────────────────────────────────────
    if afc_pdf is not None and afc_pdf != afc_actual:
        fallas = verificar_tope("tope cesantia", afc_pdf, afc_actual)
        if fallas:
            rechazos.append("; ".join(fallas))
        else:
            d = datetime.date(desde.year, 2, 1)
            if not any(e["desde"] == d.isoformat() for e in p["tope_afc_uf"]):
                p["tope_afc_uf"].append({"desde": d.isoformat(), "valor": afc_pdf})
                p["tope_afc_uf"].sort(key=lambda e: e["desde"])
                cambios.append(f"Tope cesantia: {afc_actual} -> {afc_pdf} UF desde {d}")

    # ── Tasa SIS ─────────────────────────────────────────────────────
    # A diferencia del IMM, el SIS cambia varias veces al año y rige
    # desde el mes de la remuneracion, no desde una fecha de ley.
    if sis_pdf is not None:
        p.setdefault("sis", [])
        sis_actual = vigente(p["sis"], "valor") if p["sis"] else None
        if sis_pdf != sis_actual:
            fallas = verificar_sis(sis_pdf, sis_actual)
            if fallas:
                rechazos.append("; ".join(fallas))
            else:
                d = mes_remuneraciones(texto, desde)
                if not any(e["desde"] == d.isoformat() for e in p["sis"]):
                    p["sis"].append({"desde": d.isoformat(), "valor": sis_pdf})
                    p["sis"].sort(key=lambda e: e["desde"])
                    cambios.append(f"Tasa SIS: {sis_actual}% -> {sis_pdf}% desde {d}")

    # ── Seguro de cesantia (AFC) ─────────────────────────────────────
    # Estas tasas las fija la Ley 19.728 y no cambian desde 2002, asi que
    # normalmente esto solo CONFIRMA que siguen iguales. Si algun dia
    # cambiaran, se detecta.
    if afc_tasas:
        actual = (p.get("afc") or [{}])[-1]
        distinto = any(
            abs(afc_tasas[k] - float(actual.get(k, -1))) > 0.001
            for k in ("indefinido_empleador", "indefinido_trabajador",
                      "plazo_fijo_empleador", "sobre_11_anios_empleador")
        )
        if distinto:
            fallas = verificar_afc(afc_tasas, actual)
            if fallas:
                rechazos.append("AFC: " + "; ".join(fallas))
            else:
                d = datetime.date(desde.year, desde.month, 1)
                p.setdefault("afc", [])
                if not any(e.get("desde") == d.isoformat() for e in p["afc"]):
                    entrada = {"desde": d.isoformat()}
                    entrada.update(afc_tasas)
                    p["afc"].append(entrada)
                    p["afc"].sort(key=lambda e: e["desde"])
                    cambios.append(
                        f"AFC: indefinido {afc_tasas['indefinido_empleador']}%+"
                        f"{afc_tasas['indefinido_trabajador']}%, plazo fijo "
                        f"{afc_tasas['plazo_fijo_empleador']}%, 11+ anios "
                        f"{afc_tasas['sobre_11_anios_empleador']}% desde {d}")
        else:
            log("  AFC: confirmado igual a lo que ya estaba publicado.")

    # Si algo no paso las verificaciones, NO se publica nada y se avisa
    if rechazos:
        log("\nVALORES RECHAZADOS POR LAS VERIFICACIONES:")
        for r in rechazos:
            log(f"  - {r}")
        log("\nNo se modifico el archivo. Revisar el PDF a mano:")
        log(f"  {url}")
        return 4

    if not cambios:
        log("\nSin cambios: los parametros ya estan al dia.")
        return 0

    # ── Guardar ──────────────────────────────────────────────────────
    p["version"] = int(p.get("version", 0)) + 1
    p["actualizado"] = datetime.date.today().isoformat()

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2, ensure_ascii=False)
        f.write("\n")

    log("\nCAMBIOS APLICADOS:")
    for c in cambios:
        log(f"  - {c}")
    log(f"  Version {p['version']}  |  Fuente: {url}")

    # Resumen para el cuerpo del Pull Request
    resumen = os.environ.get("GITHUB_OUTPUT")
    if resumen:
        cuerpo = ("Actualizacion automatica desde Previred.\\n\\n"
                  + "\\n".join(f"- {c}" for c in cambios)
                  + f"\\n\\nFuente: {url}")
        with open(resumen, "a", encoding="utf-8") as f:
            f.write("hay_cambios=true\n")
            f.write(f"resumen={cuerpo}\n")
            f.write(f"version={p['version']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
