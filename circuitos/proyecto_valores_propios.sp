* AC Analysis of Active Filter (Ideal Op-Amp)
* Proyecto: proyecto_valores_propios
* Sinusoidal Input: VL = 10mV
* Component Values:
* R1=1k, R2=1k, R3=1k, R5=1k
* C1=1uF, C2=1uF

V1 1 0 DC 0 AC 10m

* Input Capacitors
C1 1 2 1u
C2 2 3 1u

* Conductances G1 and G2
R1 2 5 1k
R2 3 0 1k

* Op-Amp Feedback Network
R5 5 4 1k
R3 4 0 1k

* Ideal Op-Amp modeled as E-controlled source
E_A1 5 0 3 4 1e6

.AC DEC 100 10 1k

* Print voltages and currents
.PRINT AC V(1) V(5) I(R5) I(V1)
.PROBE AC V(5) I(R5)
.PRINT AC I(V1) I(R5) V(5)

.OPTION POST=1
.OP
.END
