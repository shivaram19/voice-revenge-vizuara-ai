import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
for line in open(env_path).readlines():
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, _, v = line.partition('=')
    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

os.environ['DEMO_MODE'] = 'false'

from src.infrastructure.sarvam_tts_client import SarvamTTSClient
from src.infrastructure.sarvam_llm_client import SarvamLLMClient
from src.infrastructure.azure_config import AzureConfig

cfg = AzureConfig.from_env()
missing = cfg.validate()
print('Config missing:', missing if missing else 'NONE - all good')
print('SarvamTTSClient: OK')
print('SarvamLLMClient: OK')
print('Ready to start server.')
