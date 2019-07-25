# Pendulum-sandbox

Acesta este un program facut pentru a simula pendule multiple. Acesta dispune de o interfață grafică prin care utilizatorul poate crea mai multe pendule, fie separate, fie legate unul de altul, și apoi, poate observa mișcarea dezordonată a acestora.

## Cerințe de sistem

Windows 10.

## Instalare

Programul a fost făcut in python2.7. 

Dacă ai deja python2.7 instalat, atunci descarcă proiectul. Va trebui să instalezi următoarele module:
    
    pip install numpy
    pip install wxPython

Poți rula programul din folderul principal, cu comanda:
    
    python scripts/main.py
    
## Descriere tehnica

Limbajul de programare folosit este python, versiunea 2.7. Pe langă acesta, au fost utilizate și două module: wxPython și numpy. WxPython a ajutat la crearea unei interfețe grafice în Windows, într-un mod accesibil. WxPython este implementat pe librăriile wxWidgets din C++. Numpy este un modul făcut petru calcule științifice, de exemplu algebră liniară - folosită pentru rezolvarea sistemelor de ecuații.
