# Reporte de Delta — Casa Matriz vs Drive (2026-05-08)

**Fuente:** Carpeta de Drive `AutoOfertas - Matriz` (compartido conmigo)
**Archivos analizados:** 58 archivos de cuotas (.ods)
**Comparado contra:** `db.sqlite3` actual (CASA CENTRAL, enterprise AUTO OFERTAS)

---

## Resumen ejecutivo

| Tipo de cambio | Cantidad |
|---|---|
| Cuotas pagadas (en archivo, no en BD) | **40** |
| Ventas truly nuevas (2026, posteriores a CM21/26) | **7** |
| Ventas pre-2025 con cuotas activas (no migradas anteriormente) | **6** |
| Errores parsing | 1 (TUCSON Cardozo, formato roto en 2022) |

---

## A) Cuotas a marcar como pagadas (40)

| Venta | Cliente | Cuota # | Fecha pago | Método | Monto |
|---|---|---|---|---|---|
| CM04/26 | Guillermo Ledesma | #3 | 2026-04-13 | TB | Gs. 1.500.000 |
| CM06/26 | Raul Baez Candia | #2 | 2026-04-22 | EF | Gs. 1.300.000 |
| CM107/25 | Enzo Casco Fernandez | #5 | 2026-04-20 | TB | Gs. 1.300.000 |
| CM108/25 | Mariana Cabral | #5 | 2026-04-15 | TB | Gs. 2.000.000 |
| CM109/25 | Deydi Ojeda Fretes | #5 | 2026-04-15 | TB | Gs. 2.000.000 |
| CM125/25 | Matias Luraschi | #4 | 2026-04-10 | TB | Gs. 500.000 |
| CM129/24 | Jorge Ramirez Ruiz | #13, #14 | 2026-04-08 | TB | Gs. 1.500.000 c/u |
| CM129/24 | Jorge Ramirez Ruiz | #15 | 2026-05-05 | TB | Gs. 1.500.000 |
| CM13/25 | Gricelda Gimenez | #13 | 2026-04-10 | TB | Gs. 1.500.000 |
| CM130/25 | Miriam Azari | #4 | 2026-04-10 | TB | Gs. 1.300.000 |
| CM131/25 | Lucero Paredes Maciel | #4 | 2026-04-16 | EF | Gs. 1.600.000 |
| CM16/25 | Oscar Baez Alvarez | #14 | 2026-04-24 | TB | Gs. 1.300.000 |
| CM18/25 | Monica Figueredo | #13 | 2026-04-10 | TB | Gs. 1.700.000 |
| CM19/26 | Lucas Molinas Rolon | #2 | 2026-04-15 | TB | Gs. 1.500.000 |
| CM20/26 | Victor Gimenez Huerta | #1 | 2026-04-18 | EF | Gs. 1.300.000 |
| CM21/25 | Denis Rivero | #14 | 2026-04-23 | TB | Gs. 1.200.000 |
| CM23/25 | Mirta Zalazar Ayala | #14 | 2026-04-18 | TB | Gs. 1.600.000 |
| CM26/25 | Nelson Gonzalez Escobar | #12 | 2026-05-05 | TB | Gs. 1.550.000 |
| CM33/25 | Erika Benitez Vera | #9 | 2026-04-30 | TB | Gs. 1.500.000 |
| CM36/25 | Liz Vera Benitez | #12 | 2026-04-06 | TB | Gs. 1.750.000 |
| CM36/25 | Liz Vera Benitez | #13 | 2026-05-06 | TB | Gs. 1.750.000 |
| CM37/25 | Dionicio Lopez Aquino | #13 | 2026-04-20 | EF | Gs. 1.700.000 |
| CM40/25 | Fabiola Ramirez Sotelo | #12 | 2026-04-17 | TB | Gs. 1.300.000 |
| CM41/25 | Roberto Romero Olmedo | #11 | 2026-04-10 | TB | Gs. 1.300.000 |
| CM43/25 | Gloria Zorrilla | #11 | 2026-04-02 | TB | Gs. 1.500.000 |
| CM46/25 | Luis Perez Servian | #12 | 2026-04-21 | TB | Gs. 1.300.000 |
| CM54/25 | Roberto Romero Olmedo | #10 | 2026-04-22 | TB | Gs. 1.300.000 |
| CM57/25 | Maria Angelica Melgarejo | #10 | 2026-04-03 | TB | Gs. 1.300.000 |
| CM57/25 | Maria Angelica Melgarejo | #11 | 2026-05-04 | TB | Gs. 1.300.000 |
| CM58/25 | Hector Gimenez Lezcano | #10 | 2026-04-22 | EF | Gs. 2.000.000 |
| CM72/25 | Sandra Alcaraz | #10 | 2026-05-02 | TB | Gs. 1.400.000 |
| CM79/25 | Carlos Acosta | #8 | 2026-04-10 | TB | Gs. 1.400.000 |
| CM79/25 | Carlos Acosta | #9 | 2026-05-07 | TB | Gs. 1.400.000 |
| CM84/25 | Mariela Sanchez Gonzalez | #8 | 2026-04-18 | TB | Gs. 1.300.000 |
| CM85/24 | Mario Bogado Guillen | #16 | 2026-05-05 | EF | Gs. 1.300.000 |
| CM86/24 | Sofia Franco Ramirez | #13 | 2026-04-13 | EF | Gs. 1.400.000 |
| CM88/24 | Milagros Mongelos | #10 | 2026-04-10 | EF | Gs. 1.200.000 |
| CM99/25 | Hugo Insaurralde | #6 | 2026-04-07 | TB | Gs. 1.300.000 |
| CM99/25 | Hugo Insaurralde | #7 | 2026-05-02 | TB | Gs. 1.300.000 |

**Total cobrado en este período:** ~Gs. 60.450.000 (40 cuotas)

---

## B) Ventas TRULY nuevas (2026, posteriores a la última en BD CM21/26)

Estas se deben **CREAR** desde cero (cliente + vehículo + venta + plan de cuotas):

| CM | Cliente | Vehículo | Chasis | Entrega | Total | Cuotas |
|---|---|---|---|---|---|---|
| CM22/26 | Celia Lopez Fernandez | VITZ 1.3 2011 | NSP130-0008109 | 40.000.000 | 45.000.000 | 1×5M |
| CM25/26 | Guido Recalde Morel | VITZ 1.3 2011 | NSP130-0008109* | 30.000.000 | 42.500.000 | 10×1.25M |
| CM30/26 | Jessica Cabello Rojas | AURIS 1.5 2007 | NZE151-1012472 | 25.000.000 | 63.400.000 | 24×1.6M |
| **CM31/26** | Cristian Godoy Gonzalez | ALLION 1.5 2004 | NZT240-5020590 | 25.000.000 | 61.200.000 | 24×1.55M + 2 ref 3.8M |
| CM36/26 | Alexia Rappenecker | VITZ 1.3 2008 | SCP90-5109193 | 20.000.000 | 51.200.000 | 24×1.3M |
| **CM37/26** | Lucas Recalde Leguizamon | RACTIS 1.3 2009 | SCP100-0069350 | 38.000.000 | 40.000.000 | 2×1M |
| CM41/26 | Florencia Bernal | SIENTA 1.5 2012 | NCP81-5174256 | 20.000.000 | 56.000.000 | 24×1.5M |

\* Nota: CM22/26 y CM25/26 comparten chasis NSP130-0008109 — verificar si es error en el archivo del proveedor.

---

## C) Ventas PRE-2025 con cuotas activas (no migradas)

Estas son ventas de 2022/2023/2024 que el proveedor sigue cobrando pero que nunca se cargaron en el sistema. **Decidir si crearlas:**

| CM | Cliente | Cuotas en archivo | Estado |
|---|---|---|---|
| CM78/22 | Natalia Acosta Jimenez | 20 (varias VENCIDAS) | Cuotas vencidas pendientes |
| CM66/23 | Ana Paula Ramos Jimenez | 30 (al día hasta marzo/26) | Activa |
| CM80/23 | Andrea Valobra Velilla | 32 (al día hasta mayo/26) | Activa |
| CM14/24 | Kathyana Benitez | 22 (varias VENCIDAS) | Cuotas vencidas pendientes |
| CM70/24 | Derlis Acosta Garcia | 22 (al día hasta abril/26) | Activa |
| CM105/24 | Carlos Ramos Jimenez | 16 (al día hasta febrero/26) | Activa |

---

## Próximo paso

Confirmar:
1. **¿Aplicar las 40 cuotas pagadas?** (acción reversible — solo cambia status de pending→paid)
2. **¿Crear las 7 ventas truly nuevas?** (incluye crear clientes/vehículos)
3. **¿Crear las 6 ventas pre-2025?** (más invasivo — son ventas históricas)

Si confirmás, aplico todo en un commit con backup de la BD.
