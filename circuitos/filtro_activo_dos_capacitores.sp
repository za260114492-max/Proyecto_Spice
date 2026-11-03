* Filtro activo de dos capacitores
* Valores propuestos a partir de los datos proporcionados
* Topologia: G1 = R1, G2 = R2, RA = R3, RB = R5

* Fuente de entrada
V1 VI 0 AC 1

* Red de entrada
C4 VI N1 1u
C5 N1 N2 1u

* Conductancias equivalentes
R1 N1 VO 1k
R2 N2 0 3.3k

* Realimentacion del amplificador no inversor
R3 NMINUS 0 3.3k
R5 VO NMINUS 1k

* Amplificador operacional ideal aproximado
* EOP: V(VO) = 1e6 * (V(N2) - V(NMINUS))
EOP VO 0 N2 NMINUS 1e6

* Barrido AC
.AC DEC 100 1 1MEG

.END
