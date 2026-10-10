import sys
sys.path.insert(0, '.')
from call_llm import callLLM

llmapi = {
    'url': 'demo',
    'token': 'demo',
    'name': 'Demo Mode (Offline)',
    'active': True
}
prompt = """
#Now Write SQL#
Question: did blake book sherry photo
"""

print("Testing mock query...")
res = callLLM(llmapi).init_prompt('system', prompt).call().get_response_content()
print("SQL OUT:\n", res)
