###############
## VARIABLES ##
###############

V_vk = float(24) # Volumen vor Kochen
E_vk = float(11) # Extraktgehalt vor Kochen
E_nk = float(19) # Soll-Extraktgehalt nach Kochen (Soll-Stammwürze)
T = float(60) # Kochzeit
v = float(0.1) # Verdampfungskonstante

###############
### FORMULA ###
###############

v_T = 1-(v * T / 60) # Verdampfungsfaktor
V_plus = (((V_vk*E_vk)/E_nk) - v_T * V_vk) / v_T

###############
### RESULT ####
###############

if V_plus < 0:
  print("Error: Zielwert nicht erreichbar. Bitte Kochzeit verlängern")
else:
  print("Wasser dazugeben: V_plus = %f" % V_plus)
  print("Ausschlagwürze: V_nk = %f" % ((V_vk + V_plus)*0.9))