@echo off
echo ===========================================
echo   Mise en place de l'environnement Python
echo ===========================================

REM Creation du venv avec pour nom "tchootchoo"
if not exist "tchootchoo\Scripts\activate.bat" (
    echo [INFO] Creation du virtual environment 'tchootchoo'...
    python -m venv tchootchoo
) else (
    echo [INFO] Le virtual environment 'tchootchoo' existe deja.
)

REM Activation du venv
echo [INFO] Activation du virtual environment...
call tchootchoo\Scripts\activate.bat

REM Installation des requirements
echo [INFO] Installation des dependances depuis requirements.txt...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo ===========================================
echo   Installation terminee !
echo   1. (optionnel) regenerer les donnees : python pipelineuild_dataset.py
echo   2. lancer le dashboard : python appackend.py
echo   3. ouvrir http://127.0.0.1:5000
echo ===========================================

