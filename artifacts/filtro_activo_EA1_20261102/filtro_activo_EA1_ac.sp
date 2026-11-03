* AC Analysis of Active Filter (Ideal Op-Amp)
* Sinusoidal Input: VL = 10mV
* Component Values: R1=1k, R2=3.3k, R3=3.3k, R5=1k
* Capacitors: C4=1uF, C5=1uF
*
* Node mapping:
* 1 = Vi
* 2 = Junction C4-C5 and G1
* 3 = Non-inverting input (+)
* 4 = Inverting input (-)
* 5 = Vo

V1 1 0 AC 10m

C4 1 2 1u
C5 2 3 1u

R1 2 5 1k
R2 3 0 3.3k

R5 5 4 1k
R3 4 0 3.3k

* Ideal Op-Amp modeled as E-controlled source
E_A1 5 0 3 4 1e6

.AC DEC 100 1 1MEG
.END
