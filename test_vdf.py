import re

content = """\"users\"
{
	\"76561199350618787\"
	{
		\"AccountName\"\t\t\"bpdy94783\"
		\"PersonaName\"\t\t\"Fabra\"
		\"RememberPassword\"\t\t\"1\"
		\"WantsOfflineMode\"\t\t\"0\"
		\"SkipOfflineModeWarning\"\t\t\"0\"
		\"AllowAutoLogin\"\t\t\"0\"
		\"MostRecent\"\t\t\"1\"
		\"Timestamp\"\t\t\"1781833494\"
	}
}"""

def replace_block(match):
    steam_id = match.group(1)
    block_content = match.group(2)
    
    acc_match = re.search(r'"AccountName"\s*"([^"]+)"', block_content)
    if acc_match:
        acc_name = acc_match.group(1)
        is_target = (acc_name.strip() == "bpdy94783")
        
        if re.search(r'"MostRecent"', block_content):
            block_content = re.sub(r'("MostRecent"\s*)"[^"]+"', r'\g<1>"{}"'.format("1" if is_target else "0"), block_content)
            
        if re.search(r'"AllowAutoLogin"', block_content):
            block_content = re.sub(r'("AllowAutoLogin"\s*)"[^"]+"', r'\g<1>"{}"'.format("1" if is_target else "0"), block_content)
            
    return f'"{steam_id}"\n\t{{{block_content}}}'

new_content = re.sub(r'"(\d{17})"\s*\{([^}]+)\}', replace_block, content, flags=re.DOTALL)
print("NEW CONTENT:")
print(new_content)
