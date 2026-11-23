// Test issue #3194 against released client/server v2.4.0, not the issue's pinned main commit.
// Two real local child processes. The test checks retry on the SAME client.
import {Client} from '@modelcontextprotocol/client';
import {StdioClientTransport} from '@modelcontextprotocol/client/stdio';
import {Server} from '@modelcontextprotocol/server';
import {StdioServerTransport} from '@modelcontextprotocol/server/stdio';
const role=process.argv[2];
if(role==='bad'||role==='good'){
  const s=new Server({name:role,version:'0'}, {capabilities:{tools:{}}});
  if(role==='bad') s.setRequestHandler('initialize',()=>({
    protocolVersion:'1999-01-01',capabilities:{},serverInfo:{name:'bad',version:'0'}
  }));
  s.setRequestHandler('tools/list',()=>({tools:[]}));
  await s.connect(new StdioServerTransport());
}else{
  const spawn=r=>new StdioClientTransport({command:process.execPath,args:[new URL(import.meta.url).pathname,r]});
  const c=new Client({name:'xbstack',version:'0'});
  const out={issue:3194,sdk:'@modelcontextprotocol/client@2.4.0',node:process.version,localOnly:true};
  try{await c.connect(spawn('bad'))}catch(e){out.firstRejected=true;out.firstError=String(e.message).slice(0,250);out.oldTransportStillSet=c.transport!==undefined}
  try{await c.connect(spawn('good'));out.retry='resolved';out.tools=await c.listTools()}
  catch(e){out.retry='rejected';out.retryError=String(e.message).slice(0,250)}
  await c.close().catch(()=>{});
  console.log(JSON.stringify(out));
  process.exit(0);
}
