// Independent verification of the issue #3194 reporter's close-event waiting strategy.
// Node 22.18.0, @modelcontextprotocol/client 2.4.0; local synthetic bad+good stdio servers.
// We do not claim the strategy solves every SIGKILL/late onclose case.
import { Client } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';

const spawn=(role)=>new StdioClientTransport({command:process.execPath,args:[new URL('./stdio-repro.mjs',import.meta.url).pathname,role]});
const client=new Client({name:'xbstack-stdio-test',version:'0.0.0'});
const broken=spawn('bad');
let closed=false;
const waitForClosed=new Promise(resolve=>{
  broken.onclose=()=>{closed=true;resolve();};
});
const report={issue:3194,version:'@modelcontextprotocol/client@2.4.0',node:process.version,
  localOnly:true,firstRejected:false,closed:false,clientReused:true,retry:null};
try{ await client.connect(broken); }
catch(err){
 report.firstRejected=true;
 report.handshakeError=String(err.message).slice(0,220);
 if(client.transport===broken) {
   try{ await Promise.race([waitForClosed,new Promise((_,reject)=>setTimeout(()=>reject(Error('close_event_timeout')),6000))]); }
   catch(e){report.cleanupWaitError=String(e.message);}
 }
}
report.closed=closed;
try{await client.connect(spawn('good'));report.retry='resolved';report.tools=await client.listTools();}
catch(e){report.retry='rejected';report.retryError=String(e.message).slice(0,220);}
await client.close().catch(()=>{});
console.log(JSON.stringify(report));
process.exit(0);
