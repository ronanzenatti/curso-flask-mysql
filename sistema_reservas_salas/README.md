# SalaFácil — Projeto de Referência (Gabarito)

Código final das 10 aulas, montado a partir dos blocos de código do curso e verificado:
testes automáticos (`pytest`), templates compilados e um teste ponta a ponta com banco real.

## Como rodar
```bash
python -m venv venv
# Windows (PowerShell): venv\Scripts\Activate.ps1   |   Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env  (depois edite a senha do MySQL)
python seed_db.py
python run.py               # http://127.0.0.1:5000
```

Testes (opcional): `pip install pytest` e `python -m pytest`.

> Use como **conferência** do seu próprio código. O aprendizado está em digitar e entender cada arquivo seguindo as aulas.
> O arquivo `.env` não existe aqui de propósito: crie o seu a partir do `.env.example`.
