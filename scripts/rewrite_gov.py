import re

def main():
    path = r"d:\Novo\core\integracoes_gov.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    out_lines = []
    current_method = None
    
    for line in lines:
        match_def = re.match(r'^    def ([a-z0-9_]+)\(self', line)
        if match_def:
            current_method = match_def.group(1)
            out_lines.append(line)
            continue
            
        if current_method and current_method != "_fazer_request" and "self._fazer_request(" in line and "api_name=" not in line:
            # infer api_name and api_type
            if "pncp" in current_method:
                api_name, api_type = "pncp", "licitacao"
            elif "cnpj" in current_method:
                api_name, api_type = "receita", "cadastral"
            elif "ceis" in current_method or "cnep" in current_method:
                api_name, api_type = "cgu", "sancao"
            elif "tcu" in current_method:
                api_name, api_type = "tcu", "default"
            elif "comprasnet" in current_method:
                api_name, api_type = "comprasnet", "licitacao"
            elif "siconfi" in current_method:
                api_name, api_type = "siconfi", "financeiro"
            elif "dou" in current_method:
                api_name, api_type = "dou", "diario"
            elif "painel" in current_method:
                api_name, api_type = "painel", "financeiro"
            elif "ibge" in current_method:
                api_name, api_type = "ibge", "default"
            else:
                api_name, api_type = "generic", "default"
            
            # replace
            match_req = re.search(r'(self\._fazer_request\()(.*?)(\))', line)
            if match_req:
                start = match_req.group(1)
                args = match_req.group(2)
                end = match_req.group(3)
                
                if args.strip() == "":
                    new_args = f'api_name="{api_name}", api_type="{api_type}"'
                else:
                    new_args = f'{args}, api_name="{api_name}", api_type="{api_type}"'
                    
                line = line.replace(match_req.group(0), f"{start}{new_args}{end}")
                
        out_lines.append(line)

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))
    print("Rewrote integracoes_gov.py successfully.")

if __name__ == "__main__":
    main()
