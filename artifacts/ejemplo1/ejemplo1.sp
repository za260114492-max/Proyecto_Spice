* Ejemplo 1 reconstruido de la matriz de incidencia reducida proporcionada
* B2=C4: 1->2; B3=C5: 2->3; B4=R1: 3->0
* B5=R2: 4->0; B6=R5: 4->5; B7=R3: 2->5
* Se conservan V1 y E_A1 y los valores del ejemplo filtro_activo_EA1.
V1 1 0 AC 10m
C4 1 2 1u
C5 2 3 1u
R1 3 0 1k
R2 4 0 3.3k
R5 4 5 1k
R3 2 5 3.3k
E_A1 5 0 3 4 1e6
.AC DEC 100 1 1MEG
.END