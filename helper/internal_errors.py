"""Stable support codes. Never emit exception messages, tokens, URLs or account data."""
import json
import subprocess
import sys
from pathlib import Path
CATALOG = {row['code']: row for row in json.loads(Path(__file__).with_name('error_codes.json').read_text())}
AUTH_CODES = {
 'network request failed':3001,
 'could not start sign-in':3002, 'device authentication failed':3002,
 'Xbox sign-in rejected':3002, 'Xbox service token rejected':3002,
 'renewal rejected':3002, 'sign-in rejected':3002,
 'sign-in expired':3003, 'sign-in cancelled':3004, 'launch cancelled':3004,
 'background service unavailable':3005, 'sign-in did not finish':3006,
 'sign-in required':3008, 'signed out':3008,
 **{s:3007 for s in ('unexpected endpoint','unexpected sign-in address','incomplete session','invalid identity','invalid expiry','inconsistent identity','account changed','token already expiring','invalid privileges','invalid token field','no fresh session')},
 **{s:3101 for s in ('game copy missing','unknown game source','unknown game layout','game executable missing','unknown game executable')},
}
def record(code, error=None):
    value={'code':code if code in CATALOG else 3199}
    number=getattr(error,'errno',None)
    if type(number) is int: value['system_code']=number
    return value

def auth_code(error, operation):
    if operation=='sign-out': return 4001
    if operation=='stop-game': return 4002
    # Only our AuthError's fixed messages participate; never stringify arbitrary exceptions.
    if type(error).__name__=='AuthError': return AUTH_CODES.get(error.args[0] if error.args else '',3199)
    return 3199

def setup_code(error, stage):
    if isinstance(error,OSError): return 2205
    if stage=='visual-cpp': return 2203
    if stage=='steam': return 2204
    if stage=='dependencies':
        return 2201 if isinstance(error,subprocess.CalledProcessError) else 2202
    return 2299

def emit(code, error=None):
    print('MCD2_INTERNAL_ERROR:'+json.dumps(record(code,error),separators=(',',':')),file=sys.stderr)
