// Keep the existing FastAPI application available to the local preview service.
import {spawn} from 'node:child_process';
import {existsSync,readFileSync} from 'node:fs';
const config=existsSync('.preview-config.json')?JSON.parse(readFileSync('.preview-config.json','utf8')):{};
const args=process.argv.slice(2),value=(key,fallback)=>args.includes(key)?args[args.indexOf(key)+1]:fallback;
const server=spawn(process.env.FRAMATEX_PYTHON||config.python||'python3',['-m','uvicorn',config.app||'app.main:app','--host',value('--host','0.0.0.0'),'--port',value('--port','4173')],{stdio:'inherit',env:{...process.env,...config.env}});
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>server.kill(signal));
server.on('exit',code=>process.exit(code??1));
