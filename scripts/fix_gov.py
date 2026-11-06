import re

def main():
    path = r"d:\Novo\core\integracoes_gov.py"
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    text = text.replace(
        "resultado = self._fazer_request(url, params=params)",
        "resultado = self._fazer_request(url, params=params, api_name='pncp', api_type='licitacao')",
        2
    )
    text = text.replace(
        "resultado = self._fazer_request(url, params=params)",
        "resultado = self._fazer_request(url, params=params, api_name='tcu', api_type='default')",
        1
    )
    text = text.replace(
        "resultado = self._fazer_request(url, params=params)",
        "resultado = self._fazer_request(url, params=params, api_name='comprasnet', api_type='licitacao')",
        1
    )
    text = text.replace(
        "resultado = self._fazer_request(url, params=params)",
        "resultado = self._fazer_request(url, params=params, api_name='siconfi', api_type='financeiro')",
        1
    )
    text = text.replace(
        "resultado = self._fazer_request(url, params=params)",
        "resultado = self._fazer_request(url, params=params, api_name='dou', api_type='diario')",
        1
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Fixed missing api_name in integracoes_gov.py")

if __name__ == "__main__":
    main()
