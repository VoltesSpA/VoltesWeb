{
  "_comentario": "Parametros legales de nomina de Chile. Al publicar este archivo, todas las instalaciones de Voltes ERP se actualizan solas dentro de las 24 horas siguientes. Suba la 'version' en cada cambio.",
  "version": 4,
  "actualizado": "2026-07-29",
  "_aviso": "Mensaje opcional que se muestra a TODAS las instalaciones en Configuracion. Dejar en blanco si no hay nada que comunicar.",
  "aviso": "",
  "_imm": "Ingreso Minimo Mensual. Lo fija el Congreso por ley. 'desde' es la fecha en que EMPIEZA A REGIR, no la de publicacion de la ley.",
  "imm": [
    {
      "desde": "2023-05-01",
      "monto": 440000,
      "ley": "21.456"
    },
    {
      "desde": "2023-09-01",
      "monto": 460000,
      "ley": "21.456"
    },
    {
      "desde": "2024-07-01",
      "monto": 500000,
      "ley": "21.578"
    },
    {
      "desde": "2025-01-01",
      "monto": 510636,
      "ley": "reajuste IPC"
    },
    {
      "desde": "2025-05-01",
      "monto": 529000,
      "ley": "21.751"
    },
    {
      "desde": "2026-01-01",
      "monto": 539000,
      "ley": "21.751"
    },
    {
      "desde": "2026-05-01",
      "monto": 553553,
      "ley": "21.830"
    }
  ],
  "_tope_imponible_uf": "Tope de AFP, salud y ley de accidentes, en UF. Lo fija la Superintendencia de Pensiones cada año (rige desde las remuneraciones de febrero).",
  "tope_imponible_uf": [
    {
      "desde": "2024-01-01",
      "valor": 84.3
    },
    {
      "desde": "2025-01-01",
      "valor": 87.8
    },
    {
      "desde": "2026-02-01",
      "valor": 90.0
    }
  ],
  "_tope_afc_uf": "Tope propio del seguro de cesantia, en UF. Mas alto que el previsional.",
  "tope_afc_uf": [
    {
      "desde": "2024-01-01",
      "valor": 126.6
    },
    {
      "desde": "2025-01-01",
      "valor": 131.9
    },
    {
      "desde": "2026-02-01",
      "valor": 135.2
    }
  ],
  "_jornada": "Jornada ordinaria semanal y factor de hora extra con recargo 50% (Ley 21.561). factor = 1,5 / (horas x 30 / 7)",
  "jornada": [
    {
      "desde": "2023-01-01",
      "horas": 45,
      "factor_he": 0.0077778
    },
    {
      "desde": "2024-04-26",
      "horas": 44,
      "factor_he": 0.0079545
    },
    {
      "desde": "2026-04-26",
      "horas": 42,
      "factor_he": 0.0083333
    },
    {
      "desde": "2028-04-26",
      "horas": 40,
      "factor_he": 0.00875
    }
  ],
  "_sis": "Tasa del Seguro de Invalidez y Sobrevivencia, de cargo del empleador. Se fija por licitacion publica y cambia VARIAS VECES AL AÑO, tanto al alza como a la baja. Rige desde el mes de la REMUNERACION, no del pago. Fuente: Previred / Superintendencia de Pensiones. No confundir con la cotizacion de Trabajo Pesado (2% R.I.), que es otra cosa.",
  "sis": [
    {
      "desde": "2025-01-01",
      "valor": 1.38
    },
    {
      "desde": "2025-04-01",
      "valor": 1.78
    },
    {
      "desde": "2026-01-01",
      "valor": 1.54
    },
    {
      "desde": "2026-04-01",
      "valor": 1.62
    },
    {
      "desde": "2026-07-01",
      "valor": 2.0
    }
  ],
  "_retencion_honorarios": "Retencion de segunda categoria de las boletas de honorarios (Art. 74 N°2 LIR). La Ley 21.133 fijo un alza gradual desde 10% en 2019 hasta 17% en 2028, para financiar las cotizaciones previsionales de los trabajadores independientes. La tasa rige por AÑO CALENDARIO completo, no por mes. Las tasas hasta 2028 ya estan cargadas: el sistema cambia solo cada 1 de enero sin que nadie tenga que hacer nada.",
  "retencion_honorarios": [
    {
      "desde": "2019-01-01",
      "valor": 10.0
    },
    {
      "desde": "2020-01-01",
      "valor": 10.75
    },
    {
      "desde": "2021-01-01",
      "valor": 11.5
    },
    {
      "desde": "2022-01-01",
      "valor": 12.25
    },
    {
      "desde": "2023-01-01",
      "valor": 13.0
    },
    {
      "desde": "2024-01-01",
      "valor": 13.75
    },
    {
      "desde": "2025-01-01",
      "valor": 14.5
    },
    {
      "desde": "2026-01-01",
      "valor": 15.25
    },
    {
      "desde": "2027-01-01",
      "valor": 16.0
    },
    {
      "desde": "2028-01-01",
      "valor": 17.0
    }
  ],
  "_afc": "Seguro de Cesantia (Ley 19.728). Los porcentajes estan fijados por ley y no cambian desde 2002, pero se dejan en tabla por si acaso. Invariante legal: indefinido_empleador + indefinido_trabajador = 3,0. Sobre 11 anios de relacion laboral el empleador solo aporta 0,8% al Fondo de Cesantia Solidario y el trabajador deja de cotizar.",
  "afc": [
    {
      "desde": "2002-10-01",
      "indefinido_empleador": 2.4,
      "indefinido_trabajador": 0.6,
      "plazo_fijo_empleador": 3.0,
      "plazo_fijo_trabajador": 0.0,
      "sobre_11_anios_empleador": 0.8,
      "sobre_11_anios_trabajador": 0.0
    }
  ]
}
