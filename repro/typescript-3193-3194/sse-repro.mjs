// Reproduce upstream #3193 using the actual v1.32.2 SDK.
// Only 127.0.0.1; after 7s, explicit cleanup prevents hanging.
import net from 'node:net';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
const s=net.createServer().listen(0,'127.0.0.1');
await new Promise(r=>s.once('listening',r));
const {port}=s.address(); await new Promise(r=>s.close(r));
const t=new SSEClientTransport(new URL('http://127.0.0.1:'+port+'/sse'));
let errors=0; t.onerror=()=>{errors++};
let rejected=false, initialError='';
try{await new Client({name:'xbstack',version:'0'}).connect(t)}
catch(e){rejected=true;initialError=String(e.message).slice(0,180)}
const first=errors;
await new Promise(r=>setTimeout(r,7100));
const later=errors;
await t.close();
console.log(JSON.stringify({issue:3193,sdk:'@modelcontextprotocol/sdk@1.32.2',
 node:process.version,rejected,initialError,initialErrors:first,errorsAfter7s:later,
 reconnectErrors:later-first,explicitCleanup:true,localOnly:true}));
